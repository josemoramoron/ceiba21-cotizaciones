"""
Área de cuenta de clientes: registro, login, logout y panel personal.

Autenticación basada en sesión (ver app/client_auth.py), independiente del
Flask-Login de operadores.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash)

from app.models.web_user import WebUser
from app.services.email_service import EmailService

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
            _enviar_verificacion(web_user)
            login_client(web_user)  # auto-login tras registro
            flash(
                '¡Bienvenido! Te enviamos un correo para verificar tu cuenta.',
                'success'
            )
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

def _enviar_verificacion(web_user) -> None:
    """
    Enviar el correo de verificación.

    El enlace se construye AQUÍ, dentro de la petición: ``_external=True``
    necesita conocer el dominio, y el envío ocurre en un hilo donde ya no hay
    contexto de petición.
    """
    token = web_user.verification_token or web_user.generate_verification_token()
    web_user.save(raise_on_error=True)

    enlace = url_for('cuenta.verificar', token=token, _external=True)
    EmailService.enviar_verificacion(web_user, enlace)


@cuenta_bp.route('/verificar/<token>')
def verificar(token: str):
    """Verificar la cuenta con el token recibido por correo."""
    web_user = WebUser.get_by_verification_token(token)

    if web_user is None:
        flash('El enlace de verificación no es válido o ya fue usado.', 'error')
        return redirect(url_for('cuenta.login'))

    if web_user.verify_email(token):
        web_user.save(raise_on_error=True)
        flash('¡Cuenta verificada! Ya puedes usar todos los servicios.', 'success')
    else:
        flash('No pudimos verificar la cuenta.', 'error')

    return redirect(url_for('cuenta.index') if current_client()
                    else url_for('cuenta.login'))


@cuenta_bp.route('/reenviar-verificacion', methods=['POST'])
@client_login_required
def reenviar_verificacion():
    """Reenviar el correo de verificación al cliente autenticado."""
    web_user = current_client()

    if web_user.is_verified:
        flash('Tu cuenta ya está verificada.', 'success')
    else:
        _enviar_verificacion(web_user)
        flash('Te reenviamos el correo de verificación.', 'success')

    return redirect(url_for('cuenta.index'))


@cuenta_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    """Solicitar el restablecimiento de contraseña."""
    if current_client():
        return redirect(url_for('cuenta.index'))

    if request.method == 'POST':
        email = request.form.get('email', '')
        web_user = ClientAuthService.solicitar_reset(email)

        if web_user is not None:
            enlace = url_for(
                'cuenta.restablecer', token=web_user.reset_token, _external=True
            )
            EmailService.enviar_reset(web_user, enlace)

        # Mismo mensaje exista o no la cuenta: no revelamos qué emails existen
        flash(
            'Si el correo está registrado, te enviamos un enlace para '
            'restablecer tu contraseña.',
            'success'
        )
        return redirect(url_for('cuenta.login'))

    return render_template('cuenta/recuperar.html')


@cuenta_bp.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer(token: str):
    """Elegir una nueva contraseña con el token del correo."""
    web_user = WebUser.get_by_reset_token(token)

    if web_user is None or not web_user.verify_reset_token(token):
        flash('El enlace expiró o no es válido. Solicítalo de nuevo.', 'error')
        return redirect(url_for('cuenta.recuperar'))

    if request.method == 'POST':
        password = request.form.get('password', '')

        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'error')
            return render_template('cuenta/restablecer.html', token=token)

        if web_user.reset_password(token, password):
            web_user.save(raise_on_error=True)
            flash('Contraseña actualizada. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('cuenta.login'))

        flash('No pudimos restablecer la contraseña.', 'error')

    return render_template('cuenta/restablecer.html', token=token)

