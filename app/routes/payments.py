"""
Routes del Dashboard de Pagos PayPal.
Solo orquestación — toda la lógica está en los services.
"""
import logging
from datetime import timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.models import db
from app.models.paypal_payment import PaypalPayment, PaypalPaymentStatus
from app.models.currency import Currency
from app.services.payment_ingestion_service import PaymentIngestionService
from app.services.calculator_service import CalculatorService

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
    estado = request.args.get('estado', '')
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = PaypalPayment.query.order_by(PaypalPayment.id.desc())

    if estado:
        query = query.filter_by(estado=estado)

    pagos = query.paginate(page=page, per_page=per_page, error_out=False)

    service = PaymentIngestionService()
    resumen = service.obtener_resumen()

    monedas = Currency.query.filter_by(active=True).order_by(
        Currency.display_order
    ).all()

    # Total global sin filtro para el stat card "Todos"
    total_global = PaypalPayment.query.count()
    resumen['total_global'] = total_global

    return render_template(
        'payments/list.html',
        pagos=pagos,
        estado_filtro=estado,
        resumen=resumen,
        monedas=monedas,
        estados=PaypalPaymentStatus,
        timedelta=timedelta
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

    Con solo_calcular=true solo retorna el resultado sin persistir nada.
    Con solo_calcular=false (o ausente) aplica y guarda el cálculo.

    POST /dashboard/paypal/api/calcular/<id>
    Body JSON: {"moneda": "VES", "solo_calcular": true}
    """
    pago = PaypalPayment.query.get_or_404(pago_id)

    data = request.get_json()
    if not data or 'moneda' not in data:
        return jsonify({'error': 'Se requiere el campo moneda'}), 400

    moneda_code = data['moneda'].upper()
    solo_calcular = data.get('solo_calcular', False)

    monto_base = pago.monto_base_calculo
    if not monto_base:
        return jsonify({'error': 'No hay monto base para calcular'}), 400

    try:
        resultado = CalculatorService.calcular_pago_paypal_recibido(
            monto_base=monto_base,
            currency_code=moneda_code
        )

        if 'error' in resultado:
            return jsonify(resultado), 404

        if not solo_calcular:
            # Aplica y persiste el cálculo en el modelo
            pago.aplicar_calculo(resultado, operador_id=current_user.id)
            db.session.commit()

        return jsonify({
            'success': True,
            'valor_a_pagar': resultado['valor_a_pagar'],
            'moneda_local': moneda_code,
            'tasa_aplicada': resultado['tasa_aplicada'],
            'monto_base': monto_base,
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
    Edita campos del pago: notas, estado, moneda y valor manual.

    POST /dashboard/paypal/api/editar/<id>
    Body JSON: {
        "notas": "...",
        "estado": "pagado",
        "moneda_pago_local": "COP",
        "valor_a_pagar": 45000.00,
        "tasa_aplicada": 4500.00
    }
    """
    pago = PaypalPayment.query.get_or_404(pago_id)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No se recibieron datos'}), 400

    # Validar estado
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