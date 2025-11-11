"""
Rutas del Dashboard CRUD
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.services import QuoteService, ExchangeRateService
from app.models import Currency, PaymentMethod

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
def index():
    """Dashboard principal - Tabla de cotizaciones"""
    from datetime import datetime
    
    matrix = QuoteService.get_quotes_matrix()
    rates = ExchangeRateService.get_rates_dict()
    
    return render_template('dashboard/index.html', 
                         matrix=matrix, 
                         rates=rates,
                         now=datetime.now())

@dashboard_bp.route('/rates', methods=['GET', 'POST'])
def manage_rates():
    """Gestionar tasas de cambio"""
    if request.method == 'POST':
        # Actualizar tasas
        rates_data = request.form.to_dict()
        rates_dict = {}
        
        for key, value in rates_data.items():
            if key.startswith('rate_'):
                currency_code = key.replace('rate_', '')
                try:
                    rates_dict[currency_code] = float(value)
                except ValueError:
                    continue
        
        ExchangeRateService.update_multiple_rates(rates_dict)
        flash('✅ Tasas de cambio actualizadas exitosamente', 'success')
        return redirect(url_for('dashboard.index'))
    
    rates = ExchangeRateService.get_all_rates()
    return render_template('dashboard/rates.html', rates=rates)

@dashboard_bp.route('/currencies')
def manage_currencies():
    """Gestionar monedas (CRUD)"""
    currencies = Currency.query.all()
    return render_template('dashboard/currencies.html', currencies=currencies)

@dashboard_bp.route('/payment-methods')
def manage_payment_methods():
    """Gestionar métodos de pago (CRUD)"""
    payment_methods = PaymentMethod.query.order_by(PaymentMethod.display_order).all()
    return render_template('dashboard/payment_methods.html', payment_methods=payment_methods)

# API Endpoints
@dashboard_bp.route('/api/quote/<int:quote_id>', methods=['PUT'])
def update_quote_api(quote_id):
    """API: Actualizar cotización"""
    data = request.get_json()
    quote = QuoteService.update_quote(
        quote_id,
        value_type=data.get('value_type'),
        usd_value=data.get('usd_value'),
        usd_formula=data.get('usd_formula')
    )
    if quote:
        return jsonify({'success': True, 'quote': quote.to_dict()})
    return jsonify({'success': False, 'error': 'Quote not found'}), 404

@dashboard_bp.route('/api/recalculate', methods=['POST'])
def recalculate_all():
    """API: Recalcular todas las cotizaciones"""
    count = QuoteService.recalculate_all_quotes()
    return jsonify({'success': True, 'updated': count})
