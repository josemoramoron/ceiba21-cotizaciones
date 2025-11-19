"""
Modelos de la base de datos
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """Usuario administrador"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Currency(db.Model):
    """Monedas disponibles"""
    __tablename__ = 'currencies'
    
    code = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10))
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Currency {self.code}>'


class PaymentMethod(db.Model):
    """Métodos de pago"""
    __tablename__ = 'payment_methods'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PaymentMethod {self.name}>'


class Quote(db.Model):
    """Cotizaciones (relación método de pago - moneda)"""
    __tablename__ = 'quotes'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'), nullable=False)
    currency_id = db.Column(db.String(10), db.ForeignKey('currencies.code'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    formula = db.Column(db.String(255))
    is_manual = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    payment_method = db.relationship('PaymentMethod', backref='quotes')
    currency = db.relationship('Currency', backref='quotes')
    
   def __repr__(self):
    return f'<Quote {self.payment_method.name} - {self.currency_id}: {self.value}>'
