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
        # :5433 porque en esta laptop el cluster nativo de Postgres no está
        # en el puerto default 5432 (ocupado por el contenedor Docker de
        # FVA) — sin el puerto explícito, la conexión cae silenciosamente
        # en el contenedor equivocado en vez de fallar limpio.
        'SQLALCHEMY_DATABASE_URI': 'postgresql://webmaster:postgres123@localhost:5433/ceiba21_dev',
        'WTF_CSRF_ENABLED': False,
    })
    # Limpia la BD 1 de Redis (REDIS_SESSION_DB) al inicio de cada corrida
    # de pytest — ahí vive Flask-Session. Desde que Config expone
    # REDIS_HOST/PORT/DB/SESSION_DB (ver app/config.py) esto ya es
    # configurable por entorno, pero no hay ninguna de esas variables en
    # el .env de dev, así que en la práctica sigue siendo localhost:6379
    # db=1, igual que antes.
    _redis.Redis(host='localhost', port=6379, db=1).flushdb()
    yield app


@pytest.fixture(scope='session', autouse=True)
def _limpiar_rate_limits():
    """
    Limpia los contadores de rate limit (login, chat público, etc.) antes
    de correr la suite.

    OJO: RateLimitService usa app.redis_client, que en app/__init__.py lee
    REDIS_DB de Config (default 0 — ver app/config.py), distinto del
    REDIS_SESSION_DB (default 1) que se flushea en el fixture `app` de
    arriba (ese es solo para Flask-Session). Sin variables REDIS_* en el
    .env, dev y tests siguen compartiendo el mismo Redis local, así que
    sin este flush cada corrida de pytest suma
    intentos de /auth/login contra el límite real de 10 cada 15 min, y
    tarde o temprano un test con credenciales correctas empieza a fallar
    como si fueran inválidas (se ve como un 302 a /auth/login inesperado
    en cualquier ruta protegida). Solo se borran las claves rl:* (rate
    limit), no todo el db 0, para no tocar otro cache real (cotizaciones,
    etc.) que pueda estar viviendo ahí si tienes el servidor de dev
    corriendo en paralelo.
    """
    cliente = _redis.Redis(host='localhost', port=6379, db=0)
    try:
        borradas = 0
        for key in cliente.scan_iter('rl:*'):
            cliente.delete(key)
            borradas += 1
        print(f"[conftest] rate-limit: {borradas} clave(s) rl:* borradas en db=0")
    except Exception as e:
        # Fail-open: si Redis no está disponible, que los tests avancen
        # igual (RateLimitService también es fail-open en ese caso).
        print(f"[conftest] rate-limit: no se pudo limpiar db=0 ({e})")


@pytest.fixture(scope='function')
def client(app):
    """Cliente HTTP para hacer peticiones de prueba."""
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    """Acceso a la base de datos en tests."""
    with app.app_context():
        yield _db
