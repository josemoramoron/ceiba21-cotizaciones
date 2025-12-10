"""
Rutas del Dashboard CRUD
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.services import QuoteService, ExchangeRateService, CurrencyService, PaymentMethodService
from app.routes.auth import login_required
from app.models import db  # ← AGREGAR ESTA LÍNEA
import os
from werkzeug.utils import secure_filename
from app.telegram.bot import TelegramPublisher
from app.telegram.image_generator import TelegramImageGenerator

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
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
@login_required
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
        
        # Recalcular todas las cotizaciones con las nuevas tasas
        QuoteService.recalculate_all_quotes()
        
        flash('✅ Tasas de cambio actualizadas y cotizaciones recalculadas', 'success')
        return redirect(url_for('dashboard.index'))
    
    rates = ExchangeRateService.get_all_rates()
    return render_template('dashboard/rates.html', rates=rates)
# ==================== CRUD MONEDAS ====================

@dashboard_bp.route('/currencies')
@login_required
def manage_currencies():
    """Gestionar monedas (CRUD)"""
    currencies = CurrencyService.get_all()
    return render_template('dashboard/currencies.html', currencies=currencies)

@dashboard_bp.route('/currencies/add', methods=['POST'])
@login_required
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
@login_required
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
@login_required
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
@login_required
def delete_currency(currency_id):
    """Eliminar moneda"""
    success, error = CurrencyService.delete(currency_id)
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash('✅ Moneda eliminada exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_currencies'))

@dashboard_bp.route('/currencies/reorder', methods=['POST'])
@login_required
def reorder_currencies():
    """Reordenar monedas (drag & drop)"""
    data = request.get_json()
    order_list = data.get('order', [])
    
    CurrencyService.reorder(order_list)
    
    return jsonify({'success': True, 'message': 'Orden guardado exitosamente'})


# ==================== CRUD MÉTODOS DE PAGO ====================

@dashboard_bp.route('/payment-methods')
@login_required
def manage_payment_methods():
    """Gestionar métodos de pago (CRUD)"""
    payment_methods = PaymentMethodService.get_all()
    return render_template('dashboard/payment_methods.html', payment_methods=payment_methods)

@dashboard_bp.route('/payment-methods/add', methods=['POST'])
@login_required
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
@login_required
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
@login_required
def reorder_payment_methods():
    """Reordenar métodos de pago (drag & drop)"""
    data = request.get_json()
    order_list = data.get('order', [])
    
    PaymentMethodService.reorder(order_list)
    
    return jsonify({'success': True})

@dashboard_bp.route('/payment-methods/<int:pm_id>/delete', methods=['POST'])
@login_required
def delete_payment_method(pm_id):
    """Eliminar método de pago"""
    success, error = PaymentMethodService.delete(pm_id)
    
    if error:
        flash(f'❌ {error}', 'error')
    else:
        flash('✅ Método de pago eliminado exitosamente', 'success')
    
    return redirect(url_for('dashboard.manage_payment_methods'))

# ==================== CRUD OPERADORES ====================

@dashboard_bp.route('/operators')
@login_required
def operators():
    """Gestionar operadores (CRUD)"""
    from app.models.operator import Operator
    operators = Operator.query.order_by(Operator.created_at.desc()).all()
    return render_template('dashboard/operators.html', operators=operators)

@dashboard_bp.route('/operators/add', methods=['POST'])
@login_required
def add_operator():
    """Crear nuevo operador"""
    from app.models.operator import Operator, OperatorRole
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'agent')
    
    if not username or not password or not full_name:
        flash('❌ Usuario, contraseña y nombre completo son obligatorios', 'error')
        return redirect(url_for('dashboard.operators'))
    
    # Verificar que no exista
    existing = Operator.query.filter_by(username=username).first()
    if existing:
        flash(f'❌ El usuario {username} ya existe', 'error')
        return redirect(url_for('dashboard.operators'))
    
    # Crear operador
    operator = Operator(
        username=username,
        full_name=full_name,
        email=email,
        role=OperatorRole(role)
    )
    operator.set_password(password)
    
    if operator.save():
        flash(f'✅ Operador {username} creado exitosamente', 'success')
    else:
        flash('❌ Error al crear operador', 'error')
    
    return redirect(url_for('dashboard.operators'))

@dashboard_bp.route('/operators/<int:operator_id>/toggle', methods=['POST'])
@login_required
def toggle_operator(operator_id):
    """Activar/Desactivar operador"""
    from app.models.operator import Operator
    
    operator = Operator.query.get(operator_id)
    if not operator:
        flash('❌ Operador no encontrado', 'error')
        return redirect(url_for('dashboard.operators'))
    
    operator.is_active = not operator.is_active
    operator.save()
    
    status = "activado" if operator.is_active else "desactivado"
    flash(f'✅ Operador {status} exitosamente', 'success')
    
    return redirect(url_for('dashboard.operators'))

@dashboard_bp.route('/operators/<int:operator_id>/reset-password', methods=['POST'])
@login_required
def reset_operator_password(operator_id):
    """Resetear contraseña de operador"""
    from app.models.operator import Operator
    
    operator = Operator.query.get(operator_id)
    if not operator:
        flash('❌ Operador no encontrado', 'error')
        return redirect(url_for('dashboard.operators'))
    
    new_password = request.form.get('new_password', '').strip()
    if not new_password:
        flash('❌ La nueva contraseña es obligatoria', 'error')
        return redirect(url_for('dashboard.operators'))
    
    operator.set_password(new_password)
    operator.save()
    
    flash(f'✅ Contraseña de {operator.username} actualizada', 'success')
    return redirect(url_for('dashboard.operators'))

# ==================== API ENDPOINTS ====================

@dashboard_bp.route('/api/quote/<int:quote_id>', methods=['PUT'])
@login_required
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
@login_required
def recalculate_all():
    """API: Recalcular todas las cotizaciones"""
    count = QuoteService.recalculate_all_quotes()
    return jsonify({'success': True, 'updated': count})

# ==================== API EXTERNA ====================

@dashboard_bp.route('/api/fetch-rate/<currency_code>', methods=['POST'])
@login_required
def fetch_rate_from_api(currency_code):
    """Obtener tasa de cambio desde API externa"""
    from app.services import APIService
    
    # Siempre obtenemos tasas en base USD
    rate, provider, error = APIService.fetch_rate_with_fallback('USD', currency_code)
    
    if error:
        return jsonify({
            'success': False,
            'error': error
        }), 400
    
    # Actualizar la tasa en la base de datos
    from app.services import ExchangeRateService
    exchange_rate = ExchangeRateService.update_rate(currency_code, rate)
    
    if exchange_rate:
        # Cambiar tipo a 'api'
        exchange_rate.source_type = 'api'
        from app.models import db
        db.session.commit()
        
        # Recalcular todas las cotizaciones con la nueva tasa
        QuoteService.recalculate_all_quotes()
        
        return jsonify({
            'success': True,
            'rate': float(rate),
            'currency': currency_code,
            'provider': provider,
            'message': f'✅ Tasa actualizada desde {provider} y cotizaciones recalculadas'
        })
    
    return jsonify({
        'success': False,
        'error': 'No se pudo actualizar la tasa'
    }), 400

@dashboard_bp.route('/api/test-providers')
@login_required
def test_api_providers():
    """Probar todos los proveedores de API"""
    from app.services import APIService
    
    providers = APIService.get_available_providers()
    results = []
    
    for provider_name in providers:
        rate, provider_used, error = APIService.fetch_rate(
            'USD', 'EUR', provider_name
        )
        
        results.append({
            'provider': provider_name,
            'rate': rate,
            'error': error,
            'status': 'success' if rate else 'error'
        })
    return jsonify({
    	'providers': results,
    	'total': len(providers)
    })
    
@dashboard_bp.route('/telegram', methods=['GET', 'POST'])
@login_required
def telegram_publisher():
    """Publicar cotizaciones en Telegram"""
    from app.models import PaymentMethod, Quote, Currency
    
    if request.method == 'POST':
        try:
            # Obtener configuración
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
            
            if not token or not channel_id:
                flash('Error: Configuración de Telegram incompleta en .env', 'error')
                return redirect(url_for('dashboard.telegram_publisher'))
            
            # Obtener tipo de publicación
            publication_type = request.form.get('publication_type', 'full_ves')
            
            # Iconos
            icons = {
                'PayPal': '💳', 'Zelle': '💵', 'USDT': '₿', 
                'Wise': '🏦', 'Zinli': '💸', 'Binance': '🔶',
                'Venmo': '💰', 'Airtm': '🔷', 'Payoneer': '🎯',
                'Skrill': '⚡', 'Epay china': '🏮', 'Euro €': '💶',
                'REF': '📊'
            }
            
            # Determinar moneda
            currency_code = 'VES' if publication_type == 'full_ves' else 'COP'
            currency_symbol = 'Bs' if publication_type == 'full_ves' else '$COP'
            
            # Obtener cotizaciones ordenadas y limitadas a 6
            quotes_data = []
            payment_methods = PaymentMethod.query.filter_by(active=True).order_by(
                PaymentMethod.display_order.asc()
            ).limit(6).all()
            
            # Obtener currency por código
            currency = Currency.query.filter_by(code=currency_code).first()
            if not currency:
                flash(f'❌ Moneda {currency_code} no encontrada', 'error')
                return redirect(url_for('dashboard.telegram_publisher'))
            
            for pm in payment_methods:
                quote = Quote.query.filter_by(
                    payment_method_id=pm.id,
                    currency_id=currency.id
                ).first()
                
                if quote:
                    quotes_data.append({
                        'name': pm.name,
                        'icon': icons.get(pm.name, '💱'),
                        'rate': round(quote.final_value, 2),  # Redondear a 2 decimales
                        'currency': currency_code  # VES o COP, no USD
                    })
            
            if not quotes_data:
                flash('❌ No hay cotizaciones disponibles', 'error')
                return redirect(url_for('dashboard.telegram_publisher'))
            
            # Manejar imagen personalizada
            custom_image_path = None
            if 'custom_image' in request.files:
                file = request.files['custom_image']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    filepath = os.path.join('app/static/img/telegram_posts', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    file.save(filepath)
                    custom_image_path = filepath
            
            # Generar imagen
            generator = TelegramImageGenerator()
            image_path = generator.generate_quotes_image(quotes_data, custom_image_path)
            
            # Mensaje personalizado
            custom_message = request.form.get('custom_message', '').strip()
            
            # Publicar en Telegram
            publisher = TelegramPublisher(token, channel_id)
            result = publisher.publish_quotes_sync(image_path, custom_message or None)
            
            if result['success']:
                flash(f'✅ Publicado exitosamente en Telegram!', 'success')
                return redirect(url_for('dashboard.telegram_publisher'))
            else:
                flash(f'❌ Error al publicar: {result["error"]}', 'error')
                
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'error')
    
    # GET: Mostrar formulario con datos de vista previa
    quotes_ves = []
    quotes_cop = []
    
    try:
        # Iconos
        icons = {
            'PayPal': '💳', 'Zelle': '💵', 'USDT': '₿', 
            'Wise': '🏦', 'Zinli': '💸', 'Binance': '🔶',
            'Venmo': '💰', 'Airtm': '🔷', 'Payoneer': '🎯',
            'Skrill': '⚡', 'Epay china': '🏮', 'Euro €': '💶',
            'REF': '📊'
        }
        
        # Obtener métodos activos ordenados (primeros 6)
        payment_methods = PaymentMethod.query.filter_by(active=True).order_by(
            PaymentMethod.display_order.asc()
        ).limit(6).all()
        
        # Obtener monedas
        currency_ves = Currency.query.filter_by(code='VES').first()
        currency_cop = Currency.query.filter_by(code='COP').first()
        
        print(f"DEBUG: VES ID = {currency_ves.id if currency_ves else 'None'}")
        print(f"DEBUG: COP ID = {currency_cop.id if currency_cop else 'None'}")
        print(f"DEBUG: Payment methods: {len(payment_methods)}")
        
        # Cotizaciones VES
        if currency_ves:
            for pm in payment_methods:
                quote = Quote.query.filter_by(
                    payment_method_id=pm.id,
                    currency_id=currency_ves.id
                ).first()
                
                print(f"DEBUG: {pm.name} - Quote VES: {quote.final_value if quote else 'None'}")
                
                if quote:
                    quotes_ves.append({
                        'name': pm.name,
                        'icon': icons.get(pm.name, '💱'),
                        'rate': f"{quote.final_value:.2f}"
                    })
        
        # Cotizaciones COP
        if currency_cop:
            for pm in payment_methods:
                quote = Quote.query.filter_by(
                    payment_method_id=pm.id,
                    currency_id=currency_cop.id
                ).first()
                
                if quote:
                    quotes_cop.append({
                        'name': pm.name,
                        'icon': icons.get(pm.name, '💱'),
                        'rate': f"{quote.final_value:,.2f}"
                    })
        
        print(f"DEBUG: quotes_ves length: {len(quotes_ves)}")
        print(f"DEBUG: quotes_cop length: {len(quotes_cop)}")
    
    except Exception as e:
        flash(f'⚠️ Error al cargar vista previa: {str(e)}', 'warning')
        import traceback
        print(f"Error completo: {traceback.format_exc()}")
    
    return render_template('dashboard/telegram.html', 
                         quotes_ves=quotes_ves, 
                         quotes_cop=quotes_cop)
