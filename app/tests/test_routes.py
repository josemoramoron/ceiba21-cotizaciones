"""
Tests de rutas HTTP para Ceiba21.
Verifican que los endpoints responden correctamente.
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    """Cliente HTTP para pruebas."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'postgresql://webmaster:postgres123@localhost/ceiba21_dev',
        'WTF_CSRF_ENABLED': False,
    })
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_client(client):
    """Cliente HTTP con sesión autenticada."""
    client.post('/auth/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)
    return client


class TestRutasPublicas:
    """Tests de rutas accesibles sin login."""

    def test_home_responde_200(self, client):
        """La página principal debe estar disponible."""
        resp = client.get('/')
        assert resp.status_code == 200

    def test_cotizaciones_publicas_responde_200(self, client):
        """La página pública de cotizaciones debe estar disponible."""
        resp = client.get('/cotizaciones')
        assert resp.status_code == 200

    def test_login_page_responde_200(self, client):
        """La página de login debe estar disponible."""
        resp = client.get('/auth/login')
        assert resp.status_code == 200


class TestRutasProtegidas:
    """Tests de rutas que requieren autenticación."""

    def test_dashboard_sin_login_redirige(self, client):
        """El dashboard sin login debe redirigir al login."""
        resp = client.get('/dashboard/')
        assert resp.status_code in [301, 302]

    def test_dashboard_con_login_responde_200(self, auth_client):
        """El dashboard con login debe responder 200."""
        resp = auth_client.get('/dashboard/')
        assert resp.status_code == 200

    def test_tasas_con_login_responde_200(self, auth_client):
        """La página de tasas con login debe responder 200."""
        resp = auth_client.get('/dashboard/rates')
        assert resp.status_code == 200

    def test_login_credenciales_invalidas(self, client):
        """Login con credenciales incorrectas debe fallar."""
        resp = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'password_incorrecta'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert 'login' in resp.request.path