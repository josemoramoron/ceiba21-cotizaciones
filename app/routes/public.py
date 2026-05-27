"""
Rutas públicas (sin autenticación)
"""
from flask import Blueprint, render_template
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
    """Página principal con cotizaciones reales para el hero"""
    matrix = QuoteService.get_quotes_matrix()

    HERO_METHODS    = ['paypal', 'zelle', 'usdt', 'zinli', 'wise']


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
    """Página principal"""
    return render_template('public/home.html')

@public_bp.route('/cotizaciones')
def cotizaciones():
    """Tabla de cotizaciones pública"""
    from datetime import datetime
    
    matrix = QuoteService.get_quotes_matrix()
    rates = ExchangeRateService.get_rates_dict()
    
    # Filtrar solo monedas activas
    active_currencies = [c for c in matrix['currencies'] if c['active']]
    
    return render_template('public/cotizaciones.html', 
                         matrix=matrix,
                         rates=rates,
                         active_currencies=active_currencies,
                         now=datetime.now())
@public_bp.route('/calculadora')
def calculadora():
    """Calculadora de conversión"""
    matrix = QuoteService.get_quotes_matrix()
    return render_template('public/calculadora.html', matrix=matrix)

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
