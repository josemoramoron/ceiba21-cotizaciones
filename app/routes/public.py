"""
Rutas públicas (sin autenticación)
"""
from flask import Blueprint, render_template, request, jsonify
from app.services import QuoteService, ExchangeRateService

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def home():
    """Página principal con cotizaciones reales para el hero"""
    matrix = QuoteService.get_quotes_matrix()

    HERO_METHODS = ['paypal', 'zelle', 'usdt', 'zinli', 'wise']

    hero_quotes = []
    for pm in matrix['payment_methods']:
        if pm['code'].lower() not in HERO_METHODS:
            continue
        row = {
            'name': pm['name'],
            'code': pm['code'],
            'ves':  matrix['quotes'].get(pm['code'], {}).get('VES', {}).get('value', 0),
            'cop':  matrix['quotes'].get(pm['code'], {}).get('COP', {}).get('value', 0),
        }
        hero_quotes.append(row)

    order = {code: i for i, code in enumerate(HERO_METHODS)}
    hero_quotes.sort(key=lambda x: order.get(x['code'].lower(), 99))

    return render_template('public/home.html', hero_quotes=hero_quotes)


@public_bp.route('/cotizaciones')
def cotizaciones():
    """Tabla de cotizaciones pública"""
    from datetime import datetime

    matrix = QuoteService.get_quotes_matrix()
    rates = ExchangeRateService.get_rates_dict()

    # get_quotes_matrix ya filtra activas; esta variable se mantiene
    # para compatibilidad con el template existente
    active_currencies = matrix['currencies']

    return render_template(
        'public/cotizaciones.html',
        matrix=matrix,
        rates=rates,
        active_currencies=active_currencies,
        now=datetime.now(),
    )


@public_bp.route('/calculadora')
def calculadora():
    """Calculadora de conversión — PayPal + Conversor de monedas"""
    matrix = QuoteService.get_quotes_matrix()
    return render_template('public/calculadora.html', matrix=matrix)


@public_bp.route('/api/calcular', methods=['POST'])
def api_calcular():
    """
    API de conversión para la calculadora pública.

    Acepta conversiones fiat↔fiat y método→fiat, aplicando
    el margen global configurado en el dashboard.

    POST JSON::

        {
            "tengo": "USD",          # código moneda o método
            "quiero": "VES",         # código moneda destino
            "monto": 100,
            "tipo": "fiat_to_fiat"   # o "method_to_fiat"
        }

    Returns:
        JSON con tasa_ref, tasa_efectiva, resultado y margen,
        o JSON con 'error' si faltan datos o no hay tasa.
    """
    from app.services.calculator_service import CalculatorService
    from app.services.system_config_service import SystemConfigService

    data = request.get_json(silent=True) or {}
    tengo = (data.get('tengo') or '').strip().upper()
    quiero = (data.get('quiero') or '').strip().upper()
    tipo = (data.get('tipo') or '').strip()

    try:
        monto = float(data.get('monto', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Monto inválido'}), 400

    if not tengo or not quiero or monto <= 0:
        return jsonify({'error': 'Faltan datos para calcular'}), 400

    margen = SystemConfigService.get_public_calculator_margin()

    if tipo == 'fiat_to_fiat':
        resultado = CalculatorService.calcular_publico_fiat_to_fiat(
            tengo_code=tengo,
            quiero_code=quiero,
            monto=monto,
            margen_pct=margen,
        )
    elif tipo == 'method_to_fiat':
        resultado = CalculatorService.calcular_publico_method_to_fiat(
            metodo_code=tengo,
            quiero_code=quiero,
            monto=monto,
            margen_pct=margen,
        )
    else:
        return jsonify({'error': 'Tipo de conversión no válido'}), 400

    if 'error' in resultado:
        return jsonify(resultado), 200

    return jsonify(resultado), 200


@public_bp.route('/servicios')
def servicios():
    """Página de servicios"""
    return render_template('public/servicios.html')


@public_bp.route('/condiciones')
def condiciones():
    """Términos y condiciones"""
    return render_template('public/condiciones.html')


@public_bp.route('/tienda')
def tienda():
    """Tienda online"""
    return render_template('public/tienda.html')
