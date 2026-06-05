"""
Servicio de Ingesta de Pagos PayPal.
Orquesta la lectura de Gmail, parseo y almacenamiento en PostgreSQL.
También gestiona el scheduler para ejecución automática cada 5 minutos.
"""
import imaplib
import logging
from datetime import datetime
from typing import Optional
from flask import current_app

from app.models import db
from app.models.paypal_payment import PaypalPayment, PaypalPaymentStatus
from app.services.gmail_service import GmailService
from app.services.paypal_parser_service import PaypalParserService
from app.services.calculator_service import CalculatorService
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class PaymentIngestionService:
    """
    Servicio principal de ingesta de pagos PayPal.

    Orquesta el flujo completo:
    1. Lee Gmail via IMAP
    2. Parsea el HTML de cada correo
    3. Determina si ya existe (evita duplicados)
    4. Aplica cotización si es USD
    5. Guarda en PostgreSQL
    6. Marca el correo como leído

    Usage:
        service = PaymentIngestionService()
        result = service.procesar_nuevos_pagos()
    """

    def __init__(self) -> None:
        self.gmail_service = GmailService()
        self.parser_service = PaypalParserService()

    @staticmethod
    def _build_resumen_pago(pago: PaypalPayment) -> dict:
        """
        Construye el dict de resumen de un pago para incluir en el resultado.

        Args:
            pago: Instancia de PaypalPayment recién guardada

        Returns:
            dict con los campos clave del pago
        """
        return {
            'id': pago.id,
            'pagador': pago.pagador_nombre,
            'monto': float(pago.importe_bruto),
            'moneda': pago.moneda,
            'estado': pago.estado,
            'transaction_id': pago.paypal_transaction_id
        }

    def procesar_nuevos_pagos(
        self,
        web_user_id: Optional[int] = None
    ) -> dict:
        """
        Proceso principal: lee Gmail y registra pagos nuevos.

        Args:
            web_user_id: ID del WebUser que disparó la ejecución
                         (None si es automático via scheduler)

        Returns:
            dict con resumen de la ejecución:
            {
                'success': bool,
                'procesados': int,
                'duplicados': int,
                'errores': int,
                'nuevos': list[dict],
                'mensaje': str
            }
        """
        resultado = {
            'success': False,
            'procesados': 0,
            'duplicados': 0,
            'errores': 0,
            'nuevos': [],
            'mensaje': ''
        }

        logger.info(
            f"Iniciando ingesta de pagos PayPal "
            f"({'manual' if web_user_id else 'automático'})"
        )

        # 1. Obtener correos nuevos de Gmail
        try:
            correos = self.gmail_service.get_new_paypal_payments()
        except (imaplib.IMAP4.error, OSError) as e:
            logger.error(f"Error conectando a Gmail: {e}")
            resultado['mensaje'] = f"Error conectando a Gmail: {str(e)}"
            return resultado

        if not correos:
            resultado['success'] = True
            resultado['mensaje'] = "No hay correos nuevos de PayPal"
            return resultado

        logger.info(f"Procesando {len(correos)} correos de PayPal")

        # 2. Procesar cada correo
        for correo in correos:
            try:
                pago_guardado = self._procesar_correo(
                    correo,
                    web_user_id
                )

                if pago_guardado is None:
                    resultado['duplicados'] += 1
                elif pago_guardado is False:
                    resultado['errores'] += 1
                else:
                    resultado['procesados'] += 1
                    resultado['nuevos'].append(
                        self._build_resumen_pago(pago_guardado)
                    )

                # Marcar como leído independientemente del resultado
                self.gmail_service.mark_as_read(correo['imap_uid'])

            except (ValueError, SQLAlchemyError) as e:
                logger.error(
                    f"Error procesando correo {correo.get('message_id', '?')}: {e}"
                )
                resultado['errores'] += 1

        resultado['success'] = True
        resultado['mensaje'] = (
            f"Procesados: {resultado['procesados']} nuevos, "
            f"{resultado['duplicados']} duplicados, "
            f"{resultado['errores']} errores"
        )

        logger.info(resultado['mensaje'])
        return resultado

    def _crear_pago_desde_datos(
        self,
        datos: dict,
        message_id: str,
        web_user_id: Optional[int]
    ) -> PaypalPayment:
        """
        Instancia un PaypalPayment desde los datos parseados del correo.

        Determina el estado inicial y aplica la cotización automática
        si la moneda es USD.

        Args:
            datos: Dict devuelto por PaypalParserService.parse_email()
            message_id: ID del mensaje Gmail (para logs)
            web_user_id: ID del usuario que disparó la ejecución

        Returns:
            PaypalPayment instanciado (aún no guardado en BD)
        """
        moneda = datos.get('moneda', 'USD')
        estado = (
            PaypalPaymentStatus.MANUAL
            if moneda != 'USD'
            else PaypalPaymentStatus.PENDIENTE
        )

        pago = PaypalPayment(
            email_message_id=message_id,
            cuenta_destino=datos.get('cuenta_destino'),
            pagador_nombre=datos.get('pagador_nombre'),
            importe_bruto=datos.get('importe_bruto'),
            moneda=moneda,
            comision_paypal=datos.get('comision_paypal'),
            importe_neto=datos.get('importe_neto'),
            tipo_pago=datos.get('tipo_pago'),
            paypal_transaction_id=datos.get('paypal_transaction_id'),
            fecha_pago=datos.get('fecha_pago'),
            direccion_envio=datos.get('direccion_envio'),
            estado=estado,
            procesado_por=web_user_id if web_user_id else None
        )

        if moneda == 'USD':
            moneda_default = current_app.config.get(
                'DEFAULT_LOCAL_CURRENCY', 'VES'
            )
            try:
                resultado = CalculatorService.calcular_pago_paypal_recibido(
                    monto_base=float(pago.importe_neto or pago.importe_bruto),
                    currency_code=moneda_default
                )
                if resultado:
                    pago.aplicar_calculo(resultado, web_user_id)
                else:
                    logger.warning(
                        f"No hay cotización PayPal para {moneda_default}, "
                        f"pago queda pendiente"
                    )
            except (ValueError, SQLAlchemyError) as e:
                logger.warning(f"Error calculando cotización: {e}")

        return pago

    def _procesar_correo(
        self,
        correo: dict,
        web_user_id: Optional[int]
    ) -> Optional[PaypalPayment]:
        """
        Procesa un correo individual: verifica duplicados, parsea,
        crea el pago y lo guarda en BD.

        Args:
            correo: Dict con datos del correo de GmailService
            web_user_id: ID del usuario que disparó la ejecución

        Returns:
            PaypalPayment guardado si es nuevo
            None si es duplicado
            False si hubo error de parseo o guardado
        """
        message_id = correo.get('message_id', '')

        # Primera línea de defensa: duplicado por message_id
        if PaypalPayment.get_by_email_message_id(message_id):
            logger.debug(f"Correo duplicado: {message_id}")
            return None

        # Parsear HTML del correo
        datos = self.parser_service.parse_email(correo['html_body'], message_id)

        if datos and correo.get('to_raw'):
            datos['cuenta_destino'] = correo['to_raw'].strip()

        if not datos:
            logger.error(f"No se pudo parsear correo: {message_id}")
            return False

        # Segunda línea de defensa: duplicado por transaction_id
        if datos.get('paypal_transaction_id'):
            if PaypalPayment.get_by_transaction_id(datos['paypal_transaction_id']):
                logger.debug(
                    f"Transacción duplicada: {datos['paypal_transaction_id']}"
                )
                return None

        pago = self._crear_pago_desde_datos(datos, message_id, web_user_id)

        if not pago.save():
            logger.error(f"Error guardando pago: {message_id}")
            return False

        logger.info(
            f"Pago guardado: {pago.pagador_nombre} | "
            f"{pago.importe_bruto} {pago.moneda} | "
            f"ID: {pago.id} | Estado: {pago.estado}"
        )
        return pago

    def obtener_resumen(self) -> dict:
        """
        Obtiene un resumen del estado actual de los pagos.

        Returns:
            dict con conteos por estado
        """
        try:
            from sqlalchemy import func
            from app.models.paypal_payment import PaypalPayment

            resumen = db.session.query(
                PaypalPayment.estado,
                func.count(PaypalPayment.id).label('total'),
                func.sum(PaypalPayment.importe_bruto).label('monto_total')
            ).group_by(PaypalPayment.estado).all()

            return {
                'estados': [
                    {
                        'estado': r.estado,
                        'total': r.total,
                        'monto_total': float(r.monto_total or 0)
                    }
                    for r in resumen
                ],
                'ultima_actualizacion': datetime.utcnow().isoformat()
            }
        except SQLAlchemyError as e:
            logger.error(f"Error de base de datos en obtener_resumen: {e}")
            return {'estados': [], 'ultima_actualizacion': None}


def inicializar_scheduler(app) -> None:
    """
    Inicializa APScheduler para ejecutar la ingesta cada 5 minutos.

    Llamar desde app/__init__.py después de crear la app Flask.

    Args:
        app: Instancia de Flask

    Example:
        # En app/__init__.py
        from app.services.payment_ingestion_service import inicializar_scheduler
        inicializar_scheduler(app)
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler(timezone='UTC')

        def job_ingesta():
            """Job del scheduler que corre cada 5 minutos."""
            with app.app_context():
                try:
                    service = PaymentIngestionService()
                    result = service.procesar_nuevos_pagos(web_user_id=None)
                    if result['procesados'] > 0:
                        logger.info(
                            f"Scheduler: {result['procesados']} pagos nuevos procesados"
                        )
                except (imaplib.IMAP4.error, OSError, SQLAlchemyError) as e:
                    logger.error(f"Error en job de ingesta automática: {e}")

        scheduler.add_job(
            func=job_ingesta,
            trigger=IntervalTrigger(minutes=5),
            id='paypal_ingesta',
            name='Ingesta PayPal cada 5 min',
            replace_existing=True
        )

        scheduler.start()
        logger.info("Scheduler de ingesta PayPal iniciado (cada 5 minutos)")

        # Guardar referencia para poder detenerlo si es necesario
        app.scheduler = scheduler

    except ImportError:
        logger.warning(
            "APScheduler no instalado. "
            "Agrega 'APScheduler' a requirements.txt para habilitar "
            "la ingesta automática."
        )
    except RuntimeError as e:
        logger.error(f"Error iniciando scheduler: {e}")