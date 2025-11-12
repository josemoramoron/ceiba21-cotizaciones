"""
Autenticación simple para el dashboard
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """Decorador para proteger rutas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('⚠️ Debes iniciar sesión para acceder al dashboard', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        from flask import current_app
        username = request.form.get('username')
        password = request.form.get('password')
        
        if (username == current_app.config['ADMIN_USERNAME'] and 
            password == current_app.config['ADMIN_PASSWORD']):
            session['logged_in'] = True
            session['username'] = username
            flash('✅ Bienvenido al dashboard', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('❌ Usuario o contraseña incorrectos', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('✅ Sesión cerrada exitosamente', 'success')
    return redirect(url_for('public.home'))
