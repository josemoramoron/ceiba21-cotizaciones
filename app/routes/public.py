"""
Rutas públicas (sin autenticación)
"""
from flask import Blueprint, render_template, request, jsonify, session, make_response
from app.services import QuoteService, ExchangeRateService
from app.services.calculator_service import CalculatorService
from app.services.system_config_service import SystemConfigService
from app.services.cookie_consent_service import CookieConsentService
from app.services.client_session_service import ClientSessionService

public_bp = Blueprint('public', __name__)


@public_bp.before_request
def _ensure_client_session() -> None:
    """Garantizar un identificador de sesión para el visitante web."""
    ClientSessionService.ensure_session()


@public_bp.context_processor
def _inject_cookie_consent() -> dict:
    """Exponer estado y configuración del consentimiento a los templates."""
    return {
        'cookie_consent': CookieConsentService.get_consent(request),
        'cookie_cfg': CookieConsentService.get_client_config(),
    }


@public_bp.route('/')
def home():
    """Página principal con cotizaciones reales para el hero"""
    # Matriz pública: excluye métodos pivote (REF) en cualquier superficie
    # pública, presente o futura. El whitelist HERO_METHODS se aplica encima.
    matrix = QuoteService.get_public_quotes_matrix()

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

    # Matriz de la TABLA pública: sin método pivote (REF) en la fila y sin las
    # monedas ocultas en la tabla (USD) como columna. USD sigue activa y
    # disponible en la calculadora; solo no se lista aquí.
    matrix = QuoteService.get_cotizaciones_matrix()
    rates = ExchangeRateService.get_rates_dict()

    # get_cotizaciones_matrix ya filtra monedas; esta variable se mantiene
    # para compatibilidad con el template existente (encabezado y celdas)
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
    # Matriz pública: el selector método→fiat no ofrece el pivote (REF).
    matrix = QuoteService.get_public_quotes_matrix()
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
        # Los métodos usan su cotización directa — sin margen adicional.
        # calcular_publico_method_to_fiat rechaza los métodos pivote (REF).
        resultado = CalculatorService.calcular_publico_method_to_fiat(
            metodo_code=tengo,
            quiero_code=quiero,
            monto=monto,
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


@public_bp.route('/cookies/consent', methods=['POST'])
def cookies_consent():
    """
    Registrar la elección de consentimiento de cookies del visitante.

    Acepta JSON ``{"categories": {"preferences": bool, "analytics": bool}}`` y
    devuelve el estado normalizado, escribiendo la cookie de consentimiento.

    Returns:
        JSON con las categorías aplicadas y código 200.
    """
    data = request.get_json(silent=True) or {}
    categories = CookieConsentService.normalize_categories(data.get('categories'))

    response = make_response(jsonify({'ok': True, 'categories': categories}))
    return CookieConsentService.apply_consent_cookie(response, categories)
