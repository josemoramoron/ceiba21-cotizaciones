"""
Inicialización de la aplicación Flask
"""
from flask import Flask
from app.config import Config
from app.models import db
from flask_caching import Cache
from flask_session import Session
from redis import Redis

# Instancias globales
cache = Cache()
redis_client = None
sess = Session()

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
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    
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
    
    # Inicializar extensiones
    cache.init_app(app)
    sess.init_app(app)
    db.init_app(app)
    
    # Registrar blueprints
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.dashboard import dashboard_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)
    
    # Crear tablas si no existen
    with app.app_context():
        db.create_all()
    
    return app
