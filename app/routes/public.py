"""
Rutas públicas (sin autenticación)
"""
from flask import Blueprint, render_template
from app.services import QuoteService, ExchangeRateService

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def home():
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

@public_bp.route('/contacto')
def contacto():
    """Página de contacto"""
    return render_template('public/contacto.html')
