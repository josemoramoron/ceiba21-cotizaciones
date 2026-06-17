"""
Área de cuenta de clientes: registro, login, logout y panel personal.

Autenticación basada en sesión (ver app/client_auth.py), independiente del
Flask-Login de operadores.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash)

from app.services.client_auth_service import ClientAuthService
from app.client_auth import (login_client, logout_client, current_client,
                             client_login_required)

cuenta_bp = Blueprint('cuenta', __name__, url_prefix='/cuenta')


@cuenta_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login de cliente."""
    if current_client():
        return redirect(url_for('cuenta.index'))

    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        ok, msg, web_user = ClientAuthService.authenticate(email, password)
        if ok:
            login_client(web_user)
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('cuenta.index'))
        flash(msg, 'error')

    return render_template('cuenta/login.html')


@cuenta_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    """Registro de cliente (self-service)."""
    if current_client():
        return redirect(url_for('cuenta.index'))

    if request.method == 'POST':
        ok, msg, web_user = ClientAuthService.register(
            email=request.form.get('email', ''),
            password=request.form.get('password', ''),
            first_name=request.form.get('first_name', ''),
            last_name=request.form.get('last_name', ''),
            phone=request.form.get('phone', ''),
        )
        if ok:
            login_client(web_user)  # auto-login tras registro
            flash('¡Bienvenido! Tu cuenta ha sido creada.', 'success')
            return redirect(url_for('cuenta.index'))
        flash(msg, 'error')

    return render_template('cuenta/registro.html')


@cuenta_bp.route('/logout')
def logout():
    """Cerrar sesión de cliente."""
    logout_client()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('public.home'))


@cuenta_bp.route('/')
@client_login_required
def index():
    """Panel personal del cliente (placeholder)."""
    return render_template('cuenta/index.html')
