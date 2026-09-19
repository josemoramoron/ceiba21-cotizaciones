"""
Inicialización de la aplicación Flask
"""
import os

from flask import Flask
from app.config import Config
from app.models import db
from flask_caching import Cache
from flask_session import Session
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from redis import Redis

# Instancias globales
cache = Cache()
redis_client = None
sess = Session()
login_manager = LoginManager()
csrf = CSRFProtect()

def _check_secret_key_or_fail(app, is_production):
    """
    Fail-fast: en producción, un SECRET_KEY ausente o en su valor de
    desarrollo comprometería la firma de las cookies de sesión. Mejor que
    el proceso no arranque a que arranque firmando sesiones con un secreto
    público (visible en este mismo archivo/repo).
    """
    if is_production and app.config['SECRET_KEY'] in (None, '', 'dev-secret-key-change-me'):
        raise RuntimeError(
            "SECRET_KEY no está configurado (o sigue en el valor de desarrollo) "
            "con FLASK_ENV=production. Define SECRET_KEY en el .env antes de arrancar."
        )


def _configure_redis_and_cache(app, is_production):
    """Cache, sesiones en Redis, pool de Postgres y cookies de remember-me."""
    # ✨ Configuración de Redis y Cache
    app.config['CACHE_TYPE'] = 'RedisCache'
    app.config['CACHE_REDIS_HOST'] = 'localhost'
    app.config['CACHE_REDIS_PORT'] = 6379
    app.config['CACHE_REDIS_DB'] = 0
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutos

    # ✨ Configuración de sesiones en Redis
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = Redis(host='localhost', port=6379, db=1)
    app.config['SESSION_PERMANENT'] = True  # Sesión persistente
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 horas
    # Seguridad de cookies de sesión:
    #   - HTTPONLY: el JavaScript no puede leer la cookie de sesión.
    #   - SECURE: solo se envía por HTTPS. Activo en producción (detrás de
    #     Cloudflare); en desarrollo (localhost sin TLS) debe ir en False o la
    #     sesión no se enviaría.
    #   - SAMESITE 'Lax': mitiga CSRF en navegación entre sitios.
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = is_production
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # ✨ Configuración de Connection Pooling PostgreSQL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True
    }

    # ✨ Configuración de Flask-Login
    app.config['REMEMBER_COOKIE_DURATION'] = 2592000  # 30 días
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True


def _configure_login_manager():
    """login_view, mensajes y los callbacks de carga/no-autorizado de Flask-Login."""
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '⚠️ Debes iniciar sesión para acceder a esta página'
    login_manager.login_message_category = 'error'
    login_manager.session_protection = 'basic'  # Protección básica (strong era muy restrictivo)

    @login_manager.user_loader
    def load_user(user_id):
        """
        Callback para cargar usuario desde sesión.
        Flask-Login llama esta función en cada request.
        """
        from app.models.operator import Operator
        return db.session.get(Operator, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        """
        Callback cuando usuario no autorizado intenta acceder.
        """
        from flask import flash, redirect, url_for, request
        flash('⚠️ Debes iniciar sesión para acceder a esta página', 'error')
        # Guardar URL solicitada para redirigir después del login
        return redirect(url_for('auth.login', next=request.path))


def _register_blueprints(app):
    """Importa y registra todos los blueprints de la aplicación."""
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.bot_control import bot_control_bp
    from app.routes.operator_dashboard import operator_bp
    from app.routes.blacklist import blacklist_bp
    from app.routes.payments_unified import pagos_bp
    from app.routes.sms import sms_bp
    from app.routes.cuenta import cuenta_bp
    from app.routes.push import push_bp
    from app.routes.chat import chat_bp
    from app.routes.chat_admin import chat_admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(bot_control_bp)
    app.register_blueprint(operator_bp)
    app.register_blueprint(blacklist_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(sms_bp)
    app.register_blueprint(cuenta_bp)
    app.register_blueprint(push_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(chat_admin_bp)


def _register_context_processors(app):
    """Variables/servicios que se exponen a TODAS las plantillas."""

    # Exponer el cliente autenticado (sesión) a todas las plantillas
    @app.context_processor
    def inject_current_client():
        from app.client_auth import current_client
        return {'current_client': current_client()}

    # Exponer el consentimiento de cookies a TODAS las plantillas que extienden
    # public_base.html (no solo las rutas de public_bp). Sin esto, páginas como
    # /cuenta/* fallan con "cookie_consent is undefined".
    @app.context_processor
    def inject_cookie_consent():
        from flask import request
        from app.services.cookie_consent_service import CookieConsentService
        return {
            'cookie_consent': CookieConsentService.get_consent(request),
            'cookie_cfg': CookieConsentService.get_client_config(),
        }

    # Año actual para el copyright del footer de public_base.html.
    # No todas las rutas pasan `now` a la plantilla (solo cotizaciones/dashboard
    # lo hacen para sus propios usos), así que el footer necesita su propia
    # variable siempre disponible en vez de depender de eso.
    @app.context_processor
    def inject_current_year():
        from datetime import datetime
        return {'current_year': datetime.now().year}


def _maybe_start_ingestion_scheduler(app):
    """
    Scheduler de ingesta de pagos:
      - DEV (FLASK_ENV=development): scheduler embebido, con su botón de pausa.
      - PRODUCCIÓN: NO se arranca aquí. Si se hiciera, cada worker de Gunicorn
        levantaría su propio scheduler (3 workers = 3 schedulers compitiendo
        por los mismos correos). En prod la ingesta la dispara cron cada 5 min
        vía scripts/run_ingesta.py (un único proceso por ejecución).
    """
    if os.environ.get('FLASK_ENV', '').lower() == 'development':
        from app.services.unified_ingestion_service import (
            inicializar_scheduler_unificado
        )
        inicializar_scheduler_unificado(app)


def create_app(config_class=Config):
    """Factory para crear la aplicación"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Se calcula una sola vez y se reutiliza (cookies de sesión, fail-fast de
    # abajo, y cualquier otro lugar que necesite saber si esto es producción).
    _is_production = os.environ.get('FLASK_ENV', '').lower() == 'production'

    _check_secret_key_or_fail(app, _is_production)

    # Secret key para sesiones
    app.secret_key = app.config['SECRET_KEY']

    _configure_redis_and_cache(app, _is_production)

    # Inicializar Redis client global
    global redis_client
    redis_client = Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True  # Retorna strings en vez de bytes
    )

    # Inicializar extensiones
    cache.init_app(app)
    sess.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Filtros Jinja personalizados
    from app.utils import formato_eu, hora_co
    app.add_template_filter(formato_eu, 'eu')
    app.add_template_filter(hora_co, 'hora_co')

    _configure_login_manager()
    _register_blueprints(app)
    _register_context_processors(app)

    # Crear tablas si no existen
    with app.app_context():
        db.create_all()

    _maybe_start_ingestion_scheduler(app)

    return app