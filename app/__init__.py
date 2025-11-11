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
    
    # Inicializar extensiones
    db.init_app(app)
    
    # Registrar blueprints (rutas modulares)
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)
    
    # Crear tablas si no existen
    with app.app_context():
        db.create_all()
    
    return app
