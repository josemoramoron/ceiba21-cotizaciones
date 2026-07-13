"""
Tests de las cuentas de cliente: registro, verificación de email y reset.

El envío de correo se suprime (MAIL_SUPPRESS_SEND) para no mandar mensajes
reales durante los tests.
"""
import uuid

import pytest

from app.models.web_user import WebUser
from app.services.client_auth_service import ClientAuthService


@pytest.fixture(autouse=True)
def sin_correos(app):
    """Impide que los tests envíen correos de verdad."""
    previo = app.config.get('MAIL_SUPPRESS_SEND')
    app.config['MAIL_SUPPRESS_SEND'] = True
    yield
    app.config['MAIL_SUPPRESS_SEND'] = previo


@pytest.fixture
def email_unico():
    """Un email distinto en cada test (la BD de dev es persistente)."""
    return f"test_{uuid.uuid4().hex[:10]}@ceiba21-test.com"


@pytest.fixture
def limpiar_usuarios(db):
    """Borra los WebUser creados durante el test."""
    emails = []
    yield emails
    for email in emails:
        WebUser.query.filter_by(email=email).delete()
    db.session.commit()


class TestRegistro:
    """Alta de cuentas y token de verificación."""

    def test_registro_genera_token_de_verificacion(self, db, email_unico,
                                                   limpiar_usuarios):
        """La cuenta nace sin verificar y con su token listo."""
        limpiar_usuarios.append(email_unico)

        ok, msg, web_user = ClientAuthService.register(
            email=email_unico, password='clave12345',
            first_name='Test', last_name='Usuario', phone='+573001112233',
        )

        assert ok is True
        assert web_user.is_verified is False
        assert web_user.verification_token is not None

    def test_no_permite_email_duplicado(self, db, email_unico,
                                        limpiar_usuarios):
        """No se puede registrar dos veces el mismo correo."""
        limpiar_usuarios.append(email_unico)

        ClientAuthService.register(
            email=email_unico, password='clave12345',
            first_name='Test', last_name='Uno', phone='',
        )
        ok, msg, _ = ClientAuthService.register(
            email=email_unico, password='otraclave123',
            first_name='Test', last_name='Dos', phone='',
        )

        assert ok is False


class TestVerificacionDeEmail:
    """Flujo del token de verificación."""

    def test_token_valido_verifica_la_cuenta(self, db, email_unico,
                                             limpiar_usuarios):
        """Con el token correcto, la cuenta queda verificada."""
        limpiar_usuarios.append(email_unico)
        _, _, web_user = ClientAuthService.register(
            email=email_unico, password='clave12345',
            first_name='Test', last_name='Usuario', phone='',
        )
        token = web_user.verification_token

        assert web_user.verify_email(token) is True
        web_user.save()

        assert web_user.is_verified is True
        assert web_user.verification_token is None  # el token se consume

    def test_token_invalido_no_verifica(self, db, email_unico,
                                        limpiar_usuarios):
        """Un token que no corresponde no activa la cuenta."""
        limpiar_usuarios.append(email_unico)
        _, _, web_user = ClientAuthService.register(
            email=email_unico, password='clave12345',
            first_name='Test', last_name='Usuario', phone='',
        )

        assert web_user.verify_email('token_falso') is False
        assert web_user.is_verified is False

    def test_ruta_con_token_invalido_redirige(self, client):
        """La ruta de verificación no revienta con un token cualquiera."""
        r = client.get('/cuenta/verificar/token_inexistente')
        assert r.status_code in (301, 302)


class TestResetDePassword:
    """Flujo de restablecimiento de contraseña."""

    def test_solicitar_reset_genera_token(self, db, email_unico,
                                          limpiar_usuarios):
        """La solicitud genera un token con vencimiento."""
        limpiar_usuarios.append(email_unico)
        ClientAuthService.register(
            email=email_unico, password='clave12345',
            first_name='Test', last_name='Usuario', phone='',
        )

        web_user = ClientAuthService.solicitar_reset(email_unico)

        assert web_user is not None
        assert web_user.reset_token is not None
        assert web_user.reset_token_expires_at is not None

    def test_solicitar_reset_de_email_inexistente(self, db):
        """Un email que no existe devuelve None (la ruta no lo revela)."""
        assert ClientAuthService.solicitar_reset('nadie@ceiba21-test.com') is None

    def test_no_revela_si_el_email_existe(self, client):
        """La respuesta HTTP es idéntica exista o no la cuenta."""
        r = client.post('/cuenta/recuperar',
                        data={'email': 'nadie@ceiba21-test.com'})
        assert r.status_code in (301, 302)  # siempre redirige igual

    def test_reset_cambia_la_password(self, db, email_unico,
                                      limpiar_usuarios):
        """Con el token válido, la contraseña cambia y el token se consume."""
        limpiar_usuarios.append(email_unico)
        ClientAuthService.register(
            email=email_unico, password='clave12345',
            first_name='Test', last_name='Usuario', phone='',
        )
        web_user = ClientAuthService.solicitar_reset(email_unico)
        token = web_user.reset_token

        assert web_user.reset_password(token, 'nuevaclave999') is True
        web_user.save()

        assert web_user.check_password('nuevaclave999') is True
        assert web_user.check_password('clave12345') is False
        assert web_user.reset_token is None

    def test_token_de_reset_invalido(self, db, email_unico,
                                     limpiar_usuarios):
        """Un token falso no cambia la contraseña."""
        limpiar_usuarios.append(email_unico)
        _, _, web_user = ClientAuthService.register(
            email=email_unico, password='clave12345',
            first_name='Test', last_name='Usuario', phone='',
        )

        assert web_user.reset_password('token_falso', 'hackeada') is False
        assert web_user.check_password('clave12345') is True


class TestAccesoAlArea:
    """El área de cliente exige sesión."""

    def test_cuenta_exige_sesion(self, client):
        """Sin login, /cuenta redirige."""
        r = client.get('/cuenta/', follow_redirects=False)
        assert r.status_code in (301, 302)
