"""
Autenticación de operadores con Flask-Login.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import AuthService
from app.services.rate_limit_service import RateLimitService
from app.models.operator import Operator
from app.decorators import home_endpoint_for_role

# Intentos de login permitidos por IP antes de frenar (ventana deslizante).
_LOGIN_RATE_LIMIT = 10
_LOGIN_RATE_WINDOW = 900  # 15 minutos

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de login para operadores.
    
    Sistema de autenticación con Flask-Login:
    - Valida credenciales contra BD (tabla operators)
    - Verifica que operador esté activo
    - Crea sesión en Redis
    - Registra último acceso
    """
    # Si ya está autenticado, redirigir a su inicio según el rol
    if current_user.is_authenticated:
        return redirect(url_for(home_endpoint_for_role(current_user.role)))
    
    if request.method == 'POST':
        # Freno de fuerza bruta por IP real (detrás del Cloudflare Tunnel).
        # Cuenta el intento ANTES de validar credenciales, para que también
        # limite peticiones con campos vacíos o basura.
        ip = RateLimitService.client_ip(request)
        permitido, reintentar = RateLimitService.hit(
            f"rl:login:i:{ip}", _LOGIN_RATE_LIMIT, _LOGIN_RATE_WINDOW
        )
        if not permitido:
            minutos = max(reintentar // 60, 1)
            flash(f'⏱️ Demasiados intentos de acceso. Intenta de nuevo en {minutos} min.', 'error')
            return render_template('auth/login.html')

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        # Validar que no estén vacíos
        if not username or not password:
            flash('❌ Por favor completa todos los campos', 'error')
            return render_template('auth/login.html')
        
        # Autenticar con AuthService
        operator = AuthService.authenticate_operator(username, password)
        
        if operator:
            # Verificar que esté activo
            if not operator.is_active:
                flash('❌ Tu cuenta está desactivada. Contacta al administrador.', 'error')
                return render_template('auth/login.html')
            
            # Login con Flask-Login
            login_user(operator, remember=remember)
            
            # Registrar último acceso
            operator.update_last_login()
            
            flash(f'✅ Bienvenido {operator.full_name}', 'success')
            
            # Redirigir a página solicitada o al inicio según el rol
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for(home_endpoint_for_role(operator.role)))
        else:
            flash('❌ Credenciales inválidas', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Cerrar sesión del operador.
    
    - Registra logout en logs
    - Limpia sesión de Redis
    - Redirige a login
    """
    # Registrar logout (pasar ID, no objeto)
    AuthService.logout_operator(current_user.id)
    
    # Logout de Flask-Login
    logout_user()
    
    flash('✅ Sesión cerrada exitosamente', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/unauthorized')
def unauthorized():
    """
    Página mostrada cuando usuario no tiene permisos.
    """
    return render_template('auth/unauthorized.html'), 403
