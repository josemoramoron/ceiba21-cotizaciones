"""
Configuración base para todos los tests de Ceiba21.
"""
import pytest
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