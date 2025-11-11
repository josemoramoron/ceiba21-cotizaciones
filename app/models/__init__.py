"""
Inicialización de modelos
Importa todos los modelos para que SQLAlchemy los reconozca
"""
from flask_sqlalchemy import SQLAlchemy

# Crear instancia de base de datos
db = SQLAlchemy()

# Importar todos los modelos
from app.models.currency import Currency
from app.models.payment_method import PaymentMethod
from app.models.quote import Quote
from app.models.quote_history import QuoteHistory

# Exportar para facilitar importación
__all__ = ['db', 'Currency', 'PaymentMethod', 'Quote', 'QuoteHistory']
