"""
Inicialización de la aplicación Flask
"""
from flask import Flask
from app.config import Config
from app.models import db
from flask_caching import Cache
from flask_session import Session
from flask_login import LoginManager
from redis import Redis

# Instancias globales
cache = Cache()
redis_client = None
sess = Session()
login_manager = LoginManager()

def create_app(config_class=Config):
    """Factory para crear la aplicación"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Secret key para sesiones
    app.secret_key = app.config['SECRET_KEY']
    
    # ✨ Configuración de Redis y Cache
    app.config['CACHE_TYPE'] = 'redis'
    app.config['CACHE_REDIS_HOST'] = 'localhost'
    app.config['CACHE_REDIS_PORT'] = 6379
    app.config['CACHE_REDIS_DB'] = 0
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutos
    
    # ✨ Configuración de sesiones en Redis
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = Redis(host='localhost', port=6379, db=1)
    app.config['SESSION_PERMANENT'] = True  # Sesión persistente
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 horas
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_COOKIE_SECURE'] = False  # True solo con HTTPS
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # ✨ Configuración de Connection Pooling PostgreSQL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True
    }
    
    # Inicializar Redis client global
    global redis_client
    redis_client = Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True  # Retorna strings en vez de bytes
    )
    
    # ✨ Configuración de Flask-Login
    app.config['REMEMBER_COOKIE_DURATION'] = 2592000  # 30 días
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    
    # Inicializar extensiones
    cache.init_app(app)
    sess.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configurar Flask-Login
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
        return Operator.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        """
        Callback cuando usuario no autorizado intenta acceder.
        """
        from flask import flash, redirect, url_for, request
        flash('⚠️ Debes iniciar sesión para acceder a esta página', 'error')
        # Guardar URL solicitada para redirigir después del login
        return redirect(url_for('auth.login', next=request.path))
    
    # Registrar blueprints
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.bot_control import bot_control_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(bot_control_bp)
    
    # Crear tablas si no existen
    with app.app_context():
        db.create_all()
    
    return app
