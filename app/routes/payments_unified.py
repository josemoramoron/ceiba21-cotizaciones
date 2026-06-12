"""
Routes del Dashboard de Pagos unificado (multi-metodo).

Lee de la tabla `payments` (modelo Payment), que unifica PayPal, Zelle, Wise
y los metodos que se agreguen. Convive con el blueprint legacy de PayPal
(`paypal_payments_bp`, /dashboard/paypal) sin tocarlo; cuando este dashboard
este validado, se cambia el enlace del menu y se retira el viejo.

Solo orquestacion: la logica vive en los services.
"""
import imaplib
import logging
from datetime import timedelta, date

from flask import (
    Blueprint, render_template, request, jsonify,
    flash, redirect, url_for, current_app
)
from flask_login import login_required, current_user

from app.models import db
from app.models.payment import Payment, PaymentStatus, PaymentProvider
from app.models.currency import Currency
from app.services.unified_ingestion_service import UnifiedIngestionService
from app.services.calculator_service import CalculatorService
from app.services.payment_method_service import PaymentMethodService
from app.utils import formato_eu
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Import por HTTP acotado: el botón del dashboard solo hace "catch-up" reciente.
# Un backfill grande por HTTP excede el timeout de Gunicorn (120s) y mata al
# worker a mitad. Para rangos amplios/antiguos se usa el CLI importar_historico.py.
MAX_DIAS_IMPORT_HTTP = 7      # no aceptar fechas más viejas que esto por HTTP
LIMITE_IMPORT_HTTP = 50       # tope de correos (los más recientes) por HTTP

pagos_bp = Blueprint(
    'pagos',
    __name__,
    url_prefix='/dashboard/pagos'
)


# -- Vistas --------------------------------------------------------------------

@pagos_bp.route('/')
@login_required
def index():
    """
    Lista de pagos con filtros por estado y por metodo.
    GET /dashboard/pagos/?estado=...&metodo=...
    """
    estado = request.args.get('estado', '')
    metodo = request.args.get('metodo', '')
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = Payment.query.order_by(
        Payment.fecha_pago.desc().nullslast(),
        Payment.id.desc()
    )
    if estado:
        query = query.filter_by(estado=estado)
    if metodo:
        query = query.filter_by(metodo=metodo)

    pagos = query.paginate(page=page, per_page=per_page, error_out=False)

    resumen = UnifiedIngestionService().obtener_resumen()

    monedas = Currency.query.filter_by(active=True).order_by(
        Currency.display_order
    ).all()

    return render_template(
        'payments/lista_pagos.html',
        pagos=pagos,
        estado_filtro=estado,
        metodo_filtro=metodo,
        resumen=resumen,
        monedas=monedas,
        estados=PaymentStatus,
        metodos=PaymentProvider,
        timedelta=timedelta,
        hoy=date.today().strftime('%Y-%m-%d')
    )


@pagos_bp.route('/manual', methods=['GET'])
@login_required
def manual():
    """
    Formulario para registrar un pago manualmente.

    Para métodos que no llegan por correo (ej. Zinli). El desplegable de
    métodos se llena dinámicamente desde PaymentMethodService, así que un
    método nuevo dado de alta en el dashboard de métodos aparece aquí solo.

    GET /dashboard/pagos/manual
    """
    metodos = PaymentMethodService.get_active_ordered()
    monedas = Currency.query.filter_by(active=True).order_by(
        Currency.display_order
    ).all()
    moneda_default = current_app.config.get('DEFAULT_LOCAL_CURRENCY', 'VES')

    return render_template(
        'payments/manual.html',
        metodos=metodos,
        monedas=monedas,
        moneda_default=moneda_default
    )


@pagos_bp.route('/manual', methods=['POST'])
@login_required
def crear_manual():
    """
    Crea el pago manual reutilizando la cotización de la ingesta automática.

    POST /dashboard/pagos/manual
    """
    datos = {
        'metodo': request.form.get('metodo'),
        'pagador_nombre': request.form.get('pagador_nombre'),
        'importe_bruto': request.form.get('importe_bruto'),
        'moneda': request.form.get('moneda', 'USD'),
        'moneda_local': request.form.get('moneda_local'),
        'transaction_id': request.form.get('transaction_id'),
        'cuenta_destino': request.form.get('cuenta_destino'),
        'notas': request.form.get('notas'),
    }

    pago, error = UnifiedIngestionService().crear_pago_manual(
        datos, operador_id=current_user.id
    )
    if error:
        flash(f'No se pudo registrar el pago: {error}', 'error')
        return redirect(url_for('pagos.manual'))

    flash(f'Pago manual #{pago.id} registrado correctamente.', 'success')
    return redirect(url_for('pagos.detail', pago_id=pago.id))


@pagos_bp.route('/api/calcular-manual', methods=['POST'])
@login_required
def api_calcular_manual():
    """
    Previsualiza el valor a pagar de un pago manual SIN persistir.

    Devuelve los montos ya formateados en estilo europeo (string), para no
    enviar Decimal por JSON.

    POST /dashboard/pagos/api/calcular-manual
    Body JSON: {"metodo": "ZINLI", "monto": 35.0, "moneda_local": "VES"}
    """
    data = request.get_json(silent=True) or {}
    metodo = (data.get('metodo') or '').strip()
    moneda_local = (data.get('moneda_local') or '').strip()

    try:
        monto = float(data.get('monto'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Monto inválido'}), 400

    if not metodo or monto <= 0 or not moneda_local:
        return jsonify({'error': 'Faltan datos para calcular'}), 400

    resultado = CalculatorService.calcular_pago_recibido(
        monto_base=monto,
        currency_code=moneda_local,
        metodo_code=metodo
    )
    if 'error' in resultado:
        return jsonify(resultado), 200  # el motivo se muestra en el preview

    return jsonify({
        'valor_a_pagar': formato_eu(resultado['valor_a_pagar']),
        'tasa_aplicada': formato_eu(resultado['tasa_aplicada'], 4),
        'monto_base': formato_eu(monto, 2),
        'moneda_local': resultado['moneda_local'],
    }), 200


@pagos_bp.route('/<int:pago_id>')
@login_required
def detail(pago_id: int):
    """
    Detalle y edicion de un pago.
    GET /dashboard/pagos/<id>
    """
    pago = Payment.query.get_or_404(pago_id)

    monedas = Currency.query.filter_by(active=True).order_by(
        Currency.display_order
    ).all()

    return render_template(
        'payments/detalle_pago.html',
        pago=pago,
        monedas=monedas,
        estados=PaymentStatus
    )


# -- API endpoints -------------------------------------------------------------

@pagos_bp.route('/api/ingestar', methods=['POST'])
@login_required
def api_ingestar():
    """
    Dispara la ingesta manual de correos (todos los metodos activos).
    POST /dashboard/pagos/api/ingestar
    """
    try:
        service = UnifiedIngestionService()
        resultado = service.procesar_nuevos_pagos(
            web_user_id=current_user.id
        )
        return jsonify(resultado), 200
    except (imaplib.IMAP4.error, OSError, SQLAlchemyError) as e:
        logger.error(f"Error en ingesta manual: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@pagos_bp.route('/api/calcular/<int:pago_id>', methods=['POST'])
@login_required
def api_calcular(pago_id: int):
    """
    Calcula el valor a pagar usando la cotizacion DEL METODO del pago.

    Con solo_calcular=true solo retorna el resultado sin persistir.
    Con solo_calcular=false (o ausente) aplica y guarda el calculo.

    POST /dashboard/pagos/api/calcular/<id>
    Body JSON: {"moneda": "VES", "solo_calcular": true}
    """
    pago = Payment.query.get_or_404(pago_id)

    data = request.get_json()
    if not data or 'moneda' not in data:
        return jsonify({'error': 'Se requiere el campo moneda'}), 400

    moneda_code = data['moneda'].upper()
    solo_calcular = data.get('solo_calcular', False)

    monto_base = pago.monto_base_calculo
    if not monto_base:
        return jsonify({'error': 'No hay monto base para calcular'}), 400

    try:
        resultado = CalculatorService.calcular_pago_recibido(
            monto_base=monto_base,
            currency_code=moneda_code,
            metodo_code=pago.metodo
        )

        if 'error' in resultado:
            return jsonify(resultado), 404

        if not solo_calcular:
            pago.aplicar_calculo(resultado, operador_id=current_user.id)
            db.session.commit()

        return jsonify({
            'success': True,
            'valor_a_pagar': resultado['valor_a_pagar'],
            'moneda_local': moneda_code,
            'tasa_aplicada': resultado['tasa_aplicada'],
            'monto_base': monto_base,
            'metodo': pago.metodo,
            'estado': pago.estado
        }), 200

    except ValueError as e:
        logger.warning(f"Valor invalido calculando pago {pago_id}: {e}")
        return jsonify({'error': str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error de base de datos calculando pago {pago_id}: {e}")
        return jsonify({'error': 'Error de base de datos'}), 500


@pagos_bp.route('/api/editar/<int:pago_id>', methods=['POST'])
@login_required
def api_editar(pago_id: int):
    """
    Edita campos del pago: notas, estado, moneda y valor manual.

    POST /dashboard/pagos/api/editar/<id>
    Body JSON: {
        "notas": "...",
        "estado": "pagado",
        "moneda_pago_local": "COP",
        "valor_a_pagar": 45000.00,
        "tasa_aplicada": 4500.00
    }
    """
    pago = Payment.query.get_or_404(pago_id)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No se recibieron datos'}), 400

    if 'estado' in data:
        estados_validos = [
            PaymentStatus.PENDIENTE,
            PaymentStatus.PROCESADO,
            PaymentStatus.PAGADO,
            PaymentStatus.REVISION,
            PaymentStatus.MANUAL
        ]
        if data['estado'] not in estados_validos:
            return jsonify({'error': f"Estado invalido: {data['estado']}"}), 400

    try:
        pago.estado = data.get('estado', pago.estado)
        pago.notas = data.get('notas', pago.notas)

        if 'moneda_pago_local' in data:
            pago.moneda_pago_local = data['moneda_pago_local']
        if 'valor_a_pagar' in data and data['valor_a_pagar'] is not None:
            pago.valor_a_pagar = float(data['valor_a_pagar'])
        if 'tasa_aplicada' in data and data['tasa_aplicada'] is not None:
            pago.tasa_aplicada = float(data['tasa_aplicada'])

        pago.procesado_por = current_user.id
        db.session.commit()

        return jsonify({
            'success': True,
            'pago': pago.to_dict(include_relationships=True),
            'mensaje': 'Pago actualizado correctamente'
        }), 200

    except ValueError as e:
        logger.warning(f"Valor invalido editando pago {pago_id}: {e}")
        return jsonify({'error': str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error de base de datos editando pago {pago_id}: {e}")
        return jsonify({'error': 'Error de base de datos'}), 500


@pagos_bp.route('/api/resumen')
@login_required
def api_resumen():
    """
    Retorna resumen de pagos por estado y por metodo.
    GET /dashboard/pagos/api/resumen
    """
    try:
        resumen = UnifiedIngestionService().obtener_resumen()
        return jsonify(resumen), 200
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos en api_resumen: {e}")
        return jsonify({'error': 'Error de base de datos'}), 500


@pagos_bp.route('/api/test-gmail')
@login_required
def api_test_gmail():
    """
    Prueba la conexion IMAP con Gmail.
    GET /dashboard/pagos/api/test-gmail
    """
    try:
        from app.services.gmail_service import GmailService
        gmail = GmailService()
        resultado = gmail.test_connection()
        return jsonify(resultado), 200
    except (imaplib.IMAP4.error, OSError) as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ── Control del scheduler y importación histórica ────────────────────

@pagos_bp.route('/api/scheduler/estado')
@login_required
def api_scheduler_estado():
    """
    Estado actual del scheduler de ingesta.
    GET /dashboard/pagos/api/scheduler/estado
    """
    from flask import current_app
    scheduler = getattr(current_app._get_current_object(), 'scheduler', None)
    if not scheduler:
        return jsonify({'disponible': False, 'estado': 'no_disponible'})
    job = scheduler.get_job('ingesta_unificada')
    if not job:
        return jsonify({'disponible': True, 'estado': 'sin_job'})
    estado = 'pausado' if job.next_run_time is None else 'activo'
    proxima = job.next_run_time.isoformat() if job.next_run_time else None
    return jsonify({'disponible': True, 'estado': estado, 'proxima': proxima})


@pagos_bp.route('/api/scheduler/pausar', methods=['POST'])
@login_required
def api_scheduler_pausar():
    """
    Pausa el job de ingesta automática.
    POST /dashboard/pagos/api/scheduler/pausar
    Útil en dev para no competir con producción por los correos UNSEEN.
    """
    from flask import current_app
    scheduler = getattr(current_app._get_current_object(), 'scheduler', None)
    if not scheduler:
        return jsonify({'success': False, 'error': 'Scheduler no disponible en este entorno'})
    try:
        scheduler.pause_job('ingesta_unificada')
        logger.info("Scheduler de ingesta pausado manualmente")
        return jsonify({'success': True, 'estado': 'pausado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@pagos_bp.route('/api/scheduler/reanudar', methods=['POST'])
@login_required
def api_scheduler_reanudar():
    """
    Reanuda el job de ingesta automática.
    POST /dashboard/pagos/api/scheduler/reanudar
    """
    from flask import current_app
    scheduler = getattr(current_app._get_current_object(), 'scheduler', None)
    if not scheduler:
        return jsonify({'success': False, 'error': 'Scheduler no disponible en este entorno'})
    try:
        scheduler.resume_job('ingesta_unificada')
        logger.info("Scheduler de ingesta reanudado manualmente")
        return jsonify({'success': True, 'estado': 'activo'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@pagos_bp.route('/api/importar_desde', methods=['POST'])
@login_required
def api_importar_desde():
    """
    Importación histórica one-time: procesa TODOS los correos (leídos
    y no leídos) de las fuentes activas a partir de una fecha dada.

    Body JSON: { "desde_fecha": "2026-06-01" }  (formato HTML date input)
    POST /dashboard/pagos/api/importar_desde
    """
    data = request.get_json() or {}
    desde_iso = data.get('desde_fecha', '')
    if not desde_iso:
        return jsonify({'success': False, 'error': 'Se requiere desde_fecha (YYYY-MM-DD)'}), 400

    from datetime import datetime as _dt
    try:
        dt = _dt.strptime(desde_iso, '%Y-%m-%d')
        desde_imap = dt.strftime('%d-%b-%Y')   # '01-Jun-2026'
    except ValueError:
        return jsonify({'success': False, 'error': 'Formato de fecha inválido (esperado YYYY-MM-DD)'}), 400

    # Blindaje: por HTTP solo se permite un rango reciente y acotado, para no
    # exceder el timeout de Gunicorn. Rangos amplios -> script CLI.
    dias_atras = (_dt.now() - dt).days
    if dias_atras > MAX_DIAS_IMPORT_HTTP:
        return jsonify({
            'success': False,
            'error': (
                f'Rango demasiado amplio para el dashboard '
                f'(máximo {MAX_DIAS_IMPORT_HTTP} días). '
                f'Para importar desde {desde_iso} usa el script por terminal: '
                f'python scripts/importar_historico.py {desde_iso}'
            )
        }), 400

    try:
        service = UnifiedIngestionService()
        result = service.procesar_desde_fecha(
            desde_imap, current_user.id, limite=LIMITE_IMPORT_HTTP
        )
        if isinstance(result, dict):
            result['nota'] = (
                f'Procesados hasta {LIMITE_IMPORT_HTTP} correos más recientes. '
                f'Para un backfill completo usa el script CLI.'
            )
        return jsonify(result), 200
    except SQLAlchemyError as e:
        logger.error(f"Error DB en api_importar_desde: {e}")
        return jsonify({'success': False, 'error': 'Error de base de datos'}), 500