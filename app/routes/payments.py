"""
Routes del Dashboard de Pagos PayPal.
Solo orquestación — toda la lógica está en los services.
"""
import logging
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.models import db
from app.models.paypal_payment import PaypalPayment, PaypalPaymentStatus
from app.models.currency import Currency
from app.services.payment_ingestion_service import PaymentIngestionService

logger = logging.getLogger(__name__)

paypal_payments_bp = Blueprint(
    'paypal_payments',
    __name__,
    url_prefix='/dashboard/paypal'
)


# ── Vistas ────────────────────────────────────────────────────────────────────

@paypal_payments_bp.route('/')
@login_required
def index():
    """
    Lista de pagos PayPal con filtros por estado.
    GET /dashboard/paypal/
    """
    # Filtros opcionales por query string
    estado = request.args.get('estado', '')
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = PaypalPayment.query.order_by(PaypalPayment.fecha_pago.desc())

    if estado:
        query = query.filter_by(estado=estado)

    pagos = query.paginate(page=page, per_page=per_page, error_out=False)

    # Resumen de conteos por estado para los badges del header
    service = PaymentIngestionService()
    resumen = service.obtener_resumen()

    # Monedas activas para el desplegable de cálculo
    monedas = Currency.query.filter_by(active=True).order_by(
        Currency.display_order
    ).all()

    return render_template(
        'payments/list.html',
        pagos=pagos,
        estado_filtro=estado,
        resumen=resumen,
        monedas=monedas,
        estados=PaypalPaymentStatus
    )


@paypal_payments_bp.route('/<int:pago_id>')
@login_required
def detail(pago_id: int):
    """
    Detalle y edición de un pago PayPal.
    GET /dashboard/paypal/<id>
    """
    pago = PaypalPayment.query.get_or_404(pago_id)

    monedas = Currency.query.filter_by(active=True).order_by(
        Currency.display_order
    ).all()

    return render_template(
        'payments/detail.html',
        pago=pago,
        monedas=monedas,
        estados=PaypalPaymentStatus
    )


# ── API endpoints ─────────────────────────────────────────────────────────────

@paypal_payments_bp.route('/api/ingestar', methods=['POST'])
@login_required
def api_ingestar():
    """
    Dispara la ingesta manual de correos PayPal.
    POST /dashboard/paypal/api/ingestar

    Returns:
        JSON con resultado de la ingesta
    """
    try:
        service = PaymentIngestionService()
        resultado = service.procesar_nuevos_pagos(
            web_user_id=current_user.id
        )
        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"Error en ingesta manual: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@paypal_payments_bp.route('/api/calcular/<int:pago_id>', methods=['POST'])
@login_required
def api_calcular(pago_id: int):
    """
    Calcula el valor a pagar para una moneda local seleccionada.
    Similar a la calculadora PayPal existente.

    POST /dashboard/paypal/api/calcular/<id>
    Body JSON: {"moneda": "VES"}

    Returns:
        JSON con el valor calculado y la tasa aplicada
    """
    pago = PaypalPayment.query.get_or_404(pago_id)

    data = request.get_json()
    if not data or 'moneda' not in data:
        return jsonify({'error': 'Se requiere el campo moneda'}), 400

    moneda_code = data['moneda'].upper()

    try:
        valor = pago.calcular_valor_pagar(
            moneda_code,
            web_user_id=current_user.id
        )

        if valor is None:
            return jsonify({
                'error': f'No hay cotización PayPal activa para {moneda_code}'
            }), 404

        # Guardar los cambios calculados
        db.session.commit()

        return jsonify({
            'success': True,
            'valor_a_pagar': valor,
            'moneda_local': moneda_code,
            'tasa_aplicada': float(pago.tasa_aplicada) if pago.tasa_aplicada else None,
            'monto_base': pago.monto_base_calculo,
            'estado': pago.estado
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error calculando pago {pago_id}: {e}")
        return jsonify({'error': str(e)}), 500


@paypal_payments_bp.route('/api/editar/<int:pago_id>', methods=['POST'])
@login_required
def api_editar(pago_id: int):
    """
    Edita campos editables de un pago (notas, estado, moneda, valor manual).

    POST /dashboard/paypal/api/editar/<id>
    Body JSON: {
        "notas": "...",
        "estado": "pagado",
        "moneda_pago_local": "COP",
        "valor_a_pagar": 45000.00,
        "tasa_aplicada": 4500.00
    }

    Returns:
        JSON con el pago actualizado
    """
    pago = PaypalPayment.query.get_or_404(pago_id)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No se recibieron datos'}), 400

    # Campos editables permitidos
    campos_editables = [
        'notas',
        'estado',
        'moneda_pago_local',
        'valor_a_pagar',
        'tasa_aplicada'
    ]

    # Validar estado si se envía
    if 'estado' in data:
        estados_validos = [
            PaypalPaymentStatus.PENDIENTE,
            PaypalPaymentStatus.PROCESADO,
            PaypalPaymentStatus.PAGADO,
            PaypalPaymentStatus.REVISION,
            PaypalPaymentStatus.MANUAL
        ]
        if data['estado'] not in estados_validos:
            return jsonify({'error': f"Estado inválido: {data['estado']}"}), 400

    try:
        # Actualizar solo campos permitidos
        cambios = {
            k: v for k, v in data.items()
            if k in campos_editables
        }
        cambios['procesado_por'] = current_user.id

        pago.update(**cambios)

        return jsonify({
            'success': True,
            'pago': pago.to_dict(include_relationships=True),
            'mensaje': 'Pago actualizado correctamente'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editando pago {pago_id}: {e}")
        return jsonify({'error': str(e)}), 500


@paypal_payments_bp.route('/api/resumen')
@login_required
def api_resumen():
    """
    Retorna resumen de pagos por estado.
    GET /dashboard/paypal/api/resumen

    Returns:
        JSON con conteos y montos por estado
    """
    try:
        service = PaymentIngestionService()
        resumen = service.obtener_resumen()
        return jsonify(resumen), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@paypal_payments_bp.route('/api/test-gmail')
@login_required
def api_test_gmail():
    """
    Prueba la conexión IMAP con Gmail.
    GET /dashboard/paypal/api/test-gmail

    Returns:
        JSON con estado de la conexión
    """
    try:
        from app.services.gmail_service import GmailService
        gmail = GmailService()
        resultado = gmail.test_connection()
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
