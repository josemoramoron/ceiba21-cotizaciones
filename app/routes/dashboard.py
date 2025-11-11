"""
Rutas del Dashboard CRUD
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.services import QuoteService, ExchangeRateService, CurrencyService, PaymentMethodService

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
# ==================== CRUD MONEDAS ====================

@dashboard_bp.route('/currencies')
def manage_currencies():
    """Gestionar monedas (CRUD)"""
    currencies = CurrencyService.get_all()
    return render_template('dashboard/currencies.html', currencies=currencies)

@dashboard_bp.route('/currencies/add', methods=['POST'])
def add_currency():
    """Agregar nueva moneda"""
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    symbol = request.form.get('symbol', '').strip()
    initial_rate = request.form.get('initial_rate', '').strip()
    
    if not code or not name:
        flash('❌ Código y nombre son obligatorios', 'error')
        return redirect(url_for('dashboard.manage_currencies'))
    
    # Convertir tasa inicial
    try:
        initial_rate = float(initial_rate) if initial_rate else None
    except ValueError:
        initial_rate = None
    
    currency, error = CurrencyService.create(code, name, symbol, initial_rate=initial_rate)
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash(f'✅ Moneda {code} creada exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_currencies'))

@dashboard_bp.route('/currencies/<int:currency_id>/edit', methods=['POST'])
def edit_currency(currency_id):
    """Editar moneda"""
    name = request.form.get('name', '').strip()
    symbol = request.form.get('symbol', '').strip()
    
    currency, error = CurrencyService.update(currency_id, name=name, symbol=symbol)
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash(f'✅ Moneda actualizada exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_currencies'))

@dashboard_bp.route('/currencies/<int:currency_id>/toggle', methods=['POST'])
def toggle_currency(currency_id):
    """Activar/Desactivar moneda"""
    currency, error = CurrencyService.toggle_active(currency_id)
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        status = "activada" if currency.active else "desactivada"
        flash(f'✅ Moneda {status} exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_currencies'))

@dashboard_bp.route('/currencies/<int:currency_id>/delete', methods=['POST'])
def delete_currency(currency_id):
    """Eliminar moneda"""
    success, error = CurrencyService.delete(currency_id)
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash('✅ Moneda eliminada exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_currencies'))

# ==================== CRUD MÉTODOS DE PAGO ====================

@dashboard_bp.route('/payment-methods')
def manage_payment_methods():
    """Gestionar métodos de pago (CRUD)"""
    payment_methods = PaymentMethodService.get_all()
    return render_template('dashboard/payment_methods.html', payment_methods=payment_methods)

@dashboard_bp.route('/payment-methods/add', methods=['POST'])
def add_payment_method():
    """Agregar nuevo método de pago"""
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    display_order = request.form.get('display_order')
    value_type = request.form.get('value_type', 'manual')
    usd_value = request.form.get('usd_value')
    usd_formula = request.form.get('usd_formula', '').strip()
    
    if not code or not name:
        flash('❌ Código y nombre son obligatorios', 'error')
        return redirect(url_for('dashboard.manage_payment_methods'))
    
    try:
        display_order = int(display_order) if display_order else None
        usd_value = float(usd_value) if usd_value else 1.0
    except ValueError:
        display_order = None
        usd_value = 1.0
    
    pm, error = PaymentMethodService.create(
        code, name, display_order, 
        value_type=value_type, 
        usd_value=usd_value, 
        usd_formula=usd_formula if value_type == 'formula' else None
    )
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash(f'✅ Método de pago {code} creado exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_payment_methods'))

@dashboard_bp.route('/payment-methods/<int:pm_id>/edit', methods=['POST'])
def edit_payment_method(pm_id):
    """Editar método de pago"""
    name = request.form.get('name', '').strip()
    display_order = request.form.get('display_order')
    
    try:
        display_order = int(display_order) if display_order else None
    except ValueError:
        display_order = None
    
    pm, error = PaymentMethodService.update(pm_id, name=name, display_order=display_order)
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash(f'✅ Método de pago actualizado exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_payment_methods'))

@dashboard_bp.route('/payment-methods/<int:pm_id>/formula', methods=['POST'])
def update_formula(pm_id):
    """Actualizar fórmula del método de pago"""
    value_type = request.form.get('value_type', 'manual')
    usd_value = request.form.get('usd_value')
    usd_formula = request.form.get('usd_formula', '').strip()
    
    try:
        usd_value = float(usd_value) if usd_value else 1.0
    except ValueError:
        usd_value = 1.0
    
    pm, error = PaymentMethodService.update_formula(
        pm_id, 
        value_type, 
        usd_value=usd_value if value_type == 'manual' else None,
        usd_formula=usd_formula if value_type == 'formula' else None
    )
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash(f'✅ Fórmula actualizada y cotizaciones recalculadas', 'success')
    
    return redirect(url_for('dashboard.manage_payment_methods'))

@dashboard_bp.route('/payment-methods/reorder', methods=['POST'])
def reorder_payment_methods():
    """Reordenar métodos de pago (drag & drop)"""
    data = request.get_json()
    order_list = data.get('order', [])
    
    PaymentMethodService.reorder(order_list)
    
    return jsonify({'success': True})

@dashboard_bp.route('/payment-methods/<int:pm_id>/delete', methods=['POST'])
def delete_payment_method(pm_id):
    """Eliminar método de pago"""
    success, error = PaymentMethodService.delete(pm_id)
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash('✅ Método de pago eliminado exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_payment_methods'))

# ==================== API ENDPOINTS ====================

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
