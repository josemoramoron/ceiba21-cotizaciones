"""
Configuración base para todos los tests de Ceiba21.
"""
import pytest
import redis as _redis
from app import create_app, db as _db


@pytest.fixture(scope='session')
def app():
    """Crea la app Flask en modo testing."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'postgresql://webmaster:postgres123@localhost/ceiba21_dev',
        'WTF_CSRF_ENABLED': False,
        'REDIS_URL': 'redis://localhost:6379/1'  # BD 1 separada para tests
    })
    # Limpia la BD 1 de Redis al inicio de cada corrida de pytest. Sin esto,
    # contadores que persisten en Redis entre corridas separadas (ej. el
    # rate limit de /auth/login) se van acumulando cada vez que se corre la
    # suite completa varias veces seguidas, y terminan haciendo fallar tests
    # que no tienen nada que ver con lo que realmente se está probando.
    _redis.Redis(host='localhost', port=6379, db=1).flushdb()
    yield app


@pytest.fixture(scope='function')
def client(app):
    """Cliente HTTP para hacer peticiones de prueba."""
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    """Acceso a la base de datos en tests."""
    with app.app_context():
        yield _db