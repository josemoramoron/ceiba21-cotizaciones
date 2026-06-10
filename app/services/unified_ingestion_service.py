"""
Servicio de Ingesta Unificada (multi-metodo).

Orquesta el flujo completo escribiendo en la tabla `payments`:
    1. Lee las fuentes activas (payment_sources) y arma la lista de remitentes.
    2. Trae los correos UNSEEN de esos remitentes via GmailService.
    3. Rutea cada correo al parser correcto (ParserRegistry).
    4. Deduplica por email_message_id y por transaction_id (si lo trae).
    5. Aplica cotizacion automatica si es USD y la fuente lo permite.
    6. Guarda el Payment y marca el correo como leido.

Convive con el PaymentIngestionService legacy (que sigue escribiendo en
paypal_payments). El corte definitivo -repuntar scheduler/rutas/dashboard a
este servicio y a la tabla payments- es un paso posterior y deliberado.
"""
import imaplib
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Union, Tuple
from uuid import uuid4

from flask import current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from app.models.payment import Payment, PaymentStatus
from app.models.payment_source import PaymentSource
from app.services.gmail_service import GmailService
from app.services.parsers.registry import ParserRegistry
from app.services.calculator_service import CalculatorService

logger = logging.getLogger(__name__)


class UnifiedIngestionService:
    """Ingesta de pagos multi-metodo hacia la tabla unificada `payments`."""

    def __init__(self) -> None:
        self.gmail = GmailService()
        self.registry = ParserRegistry()

    def procesar_nuevos_pagos(
        self,
        web_user_id: Optional[int] = None,
        marcar_leidos: bool = True
    ) -> dict:
        """
        Proceso principal: lee Gmail y registra los pagos nuevos.

        Args:
            web_user_id: ID del WebUser que disparo la ejecucion (None si auto).
            marcar_leidos: Si False, no marca los correos como leidos (util para
                pruebas en dev sin consumir el estado UNSEEN; la deduplicacion
                evita registros duplicados al re-ejecutar).

        Returns:
            dict con el resumen de la ejecucion.
        """
        resumen = {
            'success': False, 'procesados': 0, 'duplicados': 0,
            'no_reconocidos': 0, 'errores': 0, 'nuevos': [], 'mensaje': ''
        }

        fuentes = PaymentSource.get_activos()
        if not fuentes:
            resumen['success'] = True
            resumen['mensaje'] = "No hay fuentes de pago activas configuradas"
            return resumen

        remitentes = [f.remitente for f in fuentes]
        logger.info(
            f"Iniciando ingesta unificada "
            f"({'manual' if web_user_id else 'automatico'}) - "
            f"{len(remitentes)} remitentes"
        )

        try:
            correos = self.gmail.get_emails_de_remitentes(remitentes)
        except (imaplib.IMAP4.error, OSError) as e:
            logger.error(f"Error conectando a Gmail: {e}")
            resumen['mensaje'] = f"Error conectando a Gmail: {str(e)}"
            return resumen

        if not correos:
            resumen['success'] = True
            resumen['mensaje'] = "No hay correos nuevos"
            return resumen

        for correo in correos:
            try:
                resultado = self._procesar_correo(correo, fuentes, web_user_id)
                if resultado == 'duplicado':
                    resumen['duplicados'] += 1
                elif resultado == 'no_reconocido':
                    resumen['no_reconocidos'] += 1
                elif resultado == 'error':
                    resumen['errores'] += 1
                else:  # es un Payment guardado
                    resumen['procesados'] += 1
                    resumen['nuevos'].append(self._resumen_pago(resultado))

                if marcar_leidos:
                    self.gmail.mark_as_read(correo['imap_uid'])

            except (ValueError, SQLAlchemyError) as e:
                logger.error(
                    f"Error procesando correo {correo.get('message_id', '?')}: {e}"
                )
                resumen['errores'] += 1

        resumen['success'] = True
        resumen['mensaje'] = (
            f"Procesados: {resumen['procesados']} nuevos, "
            f"{resumen['duplicados']} duplicados, "
            f"{resumen['no_reconocidos']} no reconocidos, "
            f"{resumen['errores']} errores"
        )
        logger.info(resumen['mensaje'])
        return resumen

    def _procesar_correo(
        self,
        correo: dict,
        fuentes: list,
        web_user_id: Optional[int]
    ) -> Union[Payment, str]:
        """
        Procesa un correo: dedup, ruteo, creacion y guardado.

        Returns:
            El Payment guardado, o un string de estado:
            'duplicado' | 'no_reconocido' | 'error'.
        """
        message_id = correo.get('message_id', '')

        if Payment.get_by_email_message_id(message_id):
            logger.debug(f"Correo duplicado (message_id): {message_id}")
            return 'duplicado'

        parsed = self.registry.parse(correo)
        if parsed is None:
            return 'no_reconocido'
        _metodo, datos = parsed

        transaction_id = datos.get('transaction_id')
        if transaction_id and Payment.get_by_transaction_id(transaction_id):
            logger.debug(f"Transaccion duplicada: {transaction_id}")
            return 'duplicado'

        fuente = self._fuente_de(correo, fuentes)
        pago = self._crear_pago(correo, datos, fuente, web_user_id)

        if not pago.save():
            logger.error(f"Error guardando pago: {message_id}")
            return 'error'

        logger.info(
            f"Pago guardado: {pago.metodo} | {pago.pagador_nombre} | "
            f"{pago.importe_bruto} {pago.moneda} | ID: {pago.id} | {pago.estado}"
        )
        return pago

    def crear_pago_manual(
        self,
        datos: dict,
        operador_id: Optional[int] = None
    ) -> Tuple[Optional[Payment], Optional[str]]:
        """Registra un pago ingresado manualmente desde el dashboard.

        Para métodos que no llegan por correo (ej. Zinli). Reutiliza la misma
        cotización que la ingesta automática (CalculatorService +
        Payment.aplicar_calculo), por lo que un método nuevo dado de alta en el
        dashboard de métodos queda disponible aquí sin cambios de código.

        Args:
            datos: dict con claves metodo, pagador_nombre, importe_bruto, moneda,
                moneda_local, transaction_id, cuenta_destino, notas (escalares).
            operador_id: Operator que registra el pago.

        Returns:
            (Payment, None) si se creó, o (None, mensaje_error) si falló.
        """
        metodo = (datos.get('metodo') or '').strip().lower()
        if not metodo:
            return None, 'Debes seleccionar un método de pago'

        try:
            importe = Decimal(str(datos.get('importe_bruto')))
        except (InvalidOperation, TypeError, ValueError):
            return None, 'Monto inválido'
        if importe <= 0:
            return None, 'El monto debe ser mayor que cero'

        transaction_id = (datos.get('transaction_id') or '').strip() or None
        if transaction_id and Payment.get_by_transaction_id(transaction_id):
            return None, f'Ya existe un pago con la referencia {transaction_id}'

        moneda = (datos.get('moneda') or 'USD').strip().upper()
        cotizable = moneda == 'USD'

        pago = Payment(
            email_message_id=f'manual:{uuid4().hex}',
            cuenta_destino=(datos.get('cuenta_destino') or '').strip() or None,
            metodo=metodo,
            pagador_nombre=(datos.get('pagador_nombre') or '').strip() or None,
            importe_bruto=importe,
            moneda=moneda,
            transaction_id=transaction_id,
            fecha_pago=datos.get('fecha_pago') or datetime.utcnow(),
            notas=(datos.get('notas') or '').strip() or None,
            estado=PaymentStatus.PENDIENTE if cotizable else PaymentStatus.MANUAL,
            procesado_por=operador_id,
            datos_extra={'origen': 'manual'},
        )

        if cotizable:
            moneda_local = (
                datos.get('moneda_local')
                or current_app.config.get('DEFAULT_LOCAL_CURRENCY', 'VES')
            )
            self._cotizar_manual(pago, moneda_local, operador_id)

        try:
            db.session.add(pago)
            db.session.commit()
            return pago, None
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error guardando pago manual: {e}")
            return None, 'Error de base de datos al guardar el pago'

    def _cotizar_manual(
        self,
        pago: Payment,
        moneda_local: str,
        operador_id: Optional[int]
    ) -> None:
        """Aplica la cotización a un pago manual (misma tasa que la automática)."""
        monto_base = pago.monto_base_calculo
        if monto_base is None:
            return
        try:
            resultado = CalculatorService.calcular_pago_recibido(
                monto_base=monto_base,
                currency_code=moneda_local,
                metodo_code=pago.metodo
            )
            if resultado and 'error' not in resultado:
                pago.aplicar_calculo(resultado, operador_id)
            else:
                motivo = resultado.get('error') if resultado else 'sin resultado'
                logger.warning(
                    f"Pago manual sin cotización ({pago.metodo}/{moneda_local}): "
                    f"{motivo}; queda pendiente"
                )
        except (ValueError, SQLAlchemyError) as e:
            logger.warning(f"Error cotizando pago manual: {e}")

    def _crear_pago(
        self,
        correo: dict,
        datos: dict,
        fuente: Optional[PaymentSource],
        web_user_id: Optional[int]
    ) -> Payment:
        """Instancia un Payment desde los datos parseados y el sobre del correo."""
        moneda = datos.get('moneda', 'USD')
        auto_cotizar = fuente.auto_cotizar if fuente else True
        cotizable = moneda == 'USD' and auto_cotizar

        estado = PaymentStatus.PENDIENTE if cotizable else PaymentStatus.MANUAL

        cuenta_destino = (correo.get('to_raw') or '').strip() or None

        pago = Payment(
            email_message_id=correo.get('message_id'),
            cuenta_destino=cuenta_destino,
            metodo=datos.get('metodo'),
            pagador_nombre=datos.get('pagador_nombre'),
            importe_bruto=datos.get('importe_bruto'),
            moneda=moneda,
            comision=datos.get('comision'),
            importe_neto=datos.get('importe_neto'),
            transaction_id=datos.get('transaction_id'),
            fecha_pago=datos.get('fecha_pago'),
            estado=estado,
            procesado_por=web_user_id if web_user_id else None,
            datos_extra=datos.get('datos_extra') or {},
        )

        if cotizable:
            self._aplicar_cotizacion(pago, fuente, web_user_id)

        return pago

    def _aplicar_cotizacion(
        self,
        pago: Payment,
        fuente: Optional[PaymentSource],
        web_user_id: Optional[int]
    ) -> None:
        """Aplica cotizacion automatica usando la tasa del metodo del pago."""
        monto_base = pago.monto_base_calculo
        if monto_base is None:
            return

        moneda_local = (
            (fuente.moneda_local_default if fuente else None)
            or current_app.config.get('DEFAULT_LOCAL_CURRENCY', 'VES')
        )
        try:
            resultado = CalculatorService.calcular_pago_recibido(
                monto_base=monto_base,
                currency_code=moneda_local,
                metodo_code=pago.metodo
            )
            if resultado and 'error' not in resultado:
                pago.aplicar_calculo(resultado, web_user_id)
            else:
                motivo = resultado.get('error') if resultado else 'sin resultado'
                logger.warning(
                    f"Sin cotizacion ({pago.metodo}/{moneda_local}): {motivo}; "
                    f"pago queda pendiente"
                )
        except (ValueError, SQLAlchemyError) as e:
            logger.warning(f"Error calculando cotizacion: {e}")

    @staticmethod
    def _fuente_de(correo: dict, fuentes: list) -> Optional[PaymentSource]:
        """Encuentra la fuente cuyo remitente coincide con el del correo."""
        sender = (correo.get('sender') or '').lower()
        for fuente in fuentes:
            if fuente.remitente.lower() in sender:
                return fuente
        return None

    @staticmethod
    def _resumen_pago(pago: Payment) -> dict:
        """Resumen compacto de un pago para incluir en el resultado."""
        return {
            'id': pago.id,
            'metodo': pago.metodo,
            'pagador': pago.pagador_nombre,
            'monto': float(pago.importe_bruto),
            'moneda': pago.moneda,
            'estado': pago.estado,
            'transaction_id': pago.transaction_id,
        }

    def obtener_resumen(self) -> dict:
        """Resumen de los pagos por metodo y estado."""
        try:
            filas = db.session.query(
                Payment.metodo,
                Payment.estado,
                func.count(Payment.id).label('total'),
                func.sum(Payment.importe_bruto).label('monto_total')
            ).group_by(Payment.metodo, Payment.estado).all()

            return {
                'grupos': [
                    {
                        'metodo': f.metodo,
                        'estado': f.estado,
                        'total': f.total,
                        'monto_total': float(f.monto_total or 0)
                    }
                    for f in filas
                ],
                'ultima_actualizacion': datetime.utcnow().isoformat()
            }
        except SQLAlchemyError as e:
            logger.error(f"Error en obtener_resumen: {e}")
            return {'grupos': [], 'ultima_actualizacion': None}
        
    def obtener_resumen(self) -> dict:
        """
        Resumen de pagos por estado y por metodo (sobre la tabla payments).

        Returns:
            dict con conteos y montos por estado, por metodo, y total global.
        """
        try:
            por_estado = db.session.query(
                Payment.estado,
                func.count(Payment.id).label('total'),
                func.sum(Payment.importe_bruto).label('monto_total')
            ).group_by(Payment.estado).all()

            por_metodo = db.session.query(
                Payment.metodo,
                func.count(Payment.id).label('total'),
                func.sum(Payment.importe_bruto).label('monto_total')
            ).group_by(Payment.metodo).all()

            return {
                'estados': [
                    {'estado': r.estado, 'total': r.total,
                     'monto_total': float(r.monto_total or 0)}
                    for r in por_estado
                ],
                'metodos': [
                    {'metodo': r.metodo, 'total': r.total,
                     'monto_total': float(r.monto_total or 0)}
                    for r in por_metodo
                ],
                'total_global': Payment.query.count(),
                'ultima_actualizacion': datetime.utcnow().isoformat()
            }
        except SQLAlchemyError as e:
            logger.error(f"Error de base de datos en obtener_resumen: {e}")
            return {
                'estados': [], 'metodos': [],
                'total_global': 0, 'ultima_actualizacion': None
            }    

    def procesar_desde_fecha(
        self,
        desde_imap: str,
        web_user_id: Optional[int]
    ) -> dict:
        """
        Importación histórica one-time: procesa TODOS los correos (leídos y
        no leídos) de los remitentes activos a partir de `desde_imap`.

        La dedup por message_id y transaction_id evita registros duplicados
        si el correo ya fue procesado previamente. Todos los correos procesados
        se marcan como leídos al finalizar.

        Args:
            desde_imap: Fecha en formato IMAP, ej. '01-Jun-2026'.
            web_user_id: ID del WebUser que disparó la ejecución.

        Returns:
            dict con el resumen de la importación.
        """
        resumen = {
            'success': False, 'procesados': 0, 'duplicados': 0,
            'no_reconocidos': 0, 'errores': 0, 'nuevos': [], 'mensaje': ''
        }

        fuentes = PaymentSource.get_activos()
        if not fuentes:
            resumen['success'] = True
            resumen['mensaje'] = "No hay fuentes de pago activas configuradas"
            return resumen

        remitentes = [f.remitente for f in fuentes]
        logger.info(
            f"Importación histórica desde {desde_imap} — "
            f"{len(remitentes)} remitentes"
        )

        try:
            correos = self.gmail.get_emails_desde_fecha(remitentes, desde_imap)
        except (imaplib.IMAP4.error, OSError) as e:
            logger.error(f"Error conectando a Gmail: {e}")
            resumen['mensaje'] = f"Error conectando a Gmail: {str(e)}"
            return resumen

        if not correos:
            resumen['success'] = True
            resumen['mensaje'] = f"No hay correos desde {desde_imap}"
            return resumen

        for correo in correos:
            try:
                resultado = self._procesar_correo(correo, fuentes, web_user_id)
                if resultado == 'duplicado':
                    resumen['duplicados'] += 1
                elif resultado == 'no_reconocido':
                    resumen['no_reconocidos'] += 1
                elif resultado == 'error':
                    resumen['errores'] += 1
                else:
                    resumen['procesados'] += 1
                    resumen['nuevos'].append(self._resumen_pago(resultado))
                # Importación histórica: siempre marcar como leído
                self.gmail.mark_as_read(correo['imap_uid'])
            except (ValueError, SQLAlchemyError) as e:
                logger.error(
                    f"Error procesando correo "
                    f"{correo.get('message_id', '?')}: {e}"
                )
                resumen['errores'] += 1

        resumen['success'] = True
        resumen['mensaje'] = (
            f"Importación desde {desde_imap}: "
            f"{resumen['procesados']} nuevos, "
            f"{resumen['duplicados']} duplicados, "
            f"{resumen['no_reconocidos']} no reconocidos, "
            f"{resumen['errores']} errores"
        )
        logger.info(resumen['mensaje'])
        return resumen


def inicializar_scheduler_unificado(app) -> None:
    """
    Inicializa APScheduler para la ingesta unificada cada 5 minutos.

    IMPORTANTE: usar SOLO al hacer el corte. Reemplaza a inicializar_scheduler
    del servicio legacy; no corras ambos a la vez (competirian por los mismos
    correos UNSEEN).

    Args:
        app: Instancia de Flask.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler(timezone='UTC')

        def job_ingesta():
            with app.app_context():
                try:
                    service = UnifiedIngestionService()
                    result = service.procesar_nuevos_pagos(web_user_id=None)
                    if result['procesados'] > 0:
                        logger.info(
                            f"Scheduler: {result['procesados']} pagos nuevos"
                        )
                except (imaplib.IMAP4.error, OSError, SQLAlchemyError) as e:
                    logger.error(f"Error en job de ingesta unificada: {e}")

        scheduler.add_job(
            func=job_ingesta,
            trigger=IntervalTrigger(minutes=5),
            id='ingesta_unificada',
            name='Ingesta unificada cada 5 min',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Scheduler de ingesta unificada iniciado (cada 5 minutos)")
        app.scheduler = scheduler

    except ImportError:
        logger.warning("APScheduler no instalado; ingesta automatica deshabilitada")
    except RuntimeError as e:
        logger.error(f"Error iniciando scheduler: {e}")