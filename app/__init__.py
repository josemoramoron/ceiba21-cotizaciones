"""
Inicialización de la aplicación Flask
"""
from flask import Flask
from app.config import Config
from app.models import db

def create_app(config_class=Config):
    """Factory para crear la aplicación"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Secret key para sesiones
    app.secret_key = app.config['SECRET_KEY']
    
    # Inicializar extensiones
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
