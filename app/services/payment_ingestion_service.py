"""
Servicio de Ingesta de Pagos PayPal.
Orquesta la lectura de Gmail, parseo y almacenamiento en PostgreSQL.
También gestiona el scheduler para ejecución automática cada 5 minutos.
"""
import logging
from datetime import datetime
from typing import Optional
from flask import current_app

from app.models import db
from app.models.paypal_payment import PaypalPayment, PaypalPaymentStatus
from app.services.gmail_service import GmailService
from app.services.paypal_parser_service import PaypalParserService

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
        except Exception as e:
            logger.error(f"Error obteniendo correos de Gmail: {e}")
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
                    resultado['nuevos'].append({
                        'id': pago_guardado.id,
                        'pagador': pago_guardado.pagador_nombre,
                        'monto': float(pago_guardado.importe_bruto),
                        'moneda': pago_guardado.moneda,
                        'estado': pago_guardado.estado,
                        'transaction_id': pago_guardado.paypal_transaction_id
                    })

                # Marcar como leído independientemente del resultado
                self.gmail_service.mark_as_read(correo['imap_uid'])

            except Exception as e:
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

    def _procesar_correo(
        self,
        correo: dict,
        web_user_id: Optional[int]
    ) -> Optional[PaypalPayment]:
        """
        Procesa un correo individual.

        Args:
            correo: Dict con datos del correo de GmailService
            web_user_id: ID del usuario que disparó la ejecución

        Returns:
            PaypalPayment guardado si es nuevo
            None si es duplicado
            False si hubo error de parseo
        """
        message_id = correo.get('message_id', '')

        # Verificar duplicado por message_id
        existente = PaypalPayment.get_by_email_message_id(message_id)
        if existente:
            logger.debug(f"Correo duplicado: {message_id}")
            return None

        # Parsear HTML
        datos = self.parser_service.parse_email(
            correo['html_body'],
            message_id
        )

        if datos and correo.get('to_raw'):
            # Guardar el header To: completo "Nombre <email@gmail.com>"
            # El template separa nombre y email para mostrar/tooltip
            datos['cuenta_destino'] = correo['to_raw'].strip()

        if not datos:
            logger.error(f"No se pudo parsear correo: {message_id}")
            return False

        # Verificar duplicado por transaction_id (segunda línea de defensa)
        if datos.get('paypal_transaction_id'):
            existente_tx = PaypalPayment.get_by_transaction_id(
                datos['paypal_transaction_id']
            )
            if existente_tx:
                logger.debug(
                    f"Transacción duplicada: {datos['paypal_transaction_id']}"
                )
                return None

        # Determinar estado inicial
        moneda = datos.get('moneda', 'USD')
        if moneda != 'USD':
            # Moneda no soportada automáticamente → llenado manual
            estado = PaypalPaymentStatus.MANUAL
        else:
            estado = PaypalPaymentStatus.PENDIENTE

        # Crear el objeto de pago
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

        # Si es USD, aplicar cotización automáticamente
        # Usamos moneda local por defecto configurada (VES)
        if moneda == 'USD':
            moneda_default = current_app.config.get(
                'DEFAULT_LOCAL_CURRENCY',
                'VES'
            )
            try:
                valor = pago.calcular_valor_pagar(moneda_default, web_user_id)
                if not valor:
                    # Si no hay cotización, queda pendiente sin valor
                    logger.warning(
                        f"No hay cotización PayPal para {moneda_default}, "
                        f"pago queda pendiente"
                    )
            except Exception as e:
                logger.warning(f"Error calculando cotización: {e}")

        # Guardar en base de datos
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
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
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
                except Exception as e:
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
    except Exception as e:
        logger.error(f"Error iniciando scheduler: {e}")