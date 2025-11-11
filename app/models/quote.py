"""
Modelo de Cotizaciones basado en USD
"""
from datetime import datetime
from app.models import db

class Quote(db.Model):
    __tablename__ = 'quotes'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'), nullable=False)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    
    # Tipo: 'manual' o 'formula'
    value_type = db.Column(db.String(20), default='manual', nullable=False)
    
    # Valor en USD (manual)
    usd_value = db.Column(db.Numeric(10, 6), nullable=True)
    
    # Fórmula en USD: "1 / 1.1"
    usd_formula = db.Column(db.String(200), nullable=True)
    
    # Valor calculado en USD
    calculated_usd = db.Column(db.Numeric(10, 6), nullable=True)
    
    # Valor final en la moneda local (USD × tasa de cambio)
    final_value = db.Column(db.Numeric(12, 2), nullable=True)
    
    # Timestamp
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    payment_method = db.relationship('PaymentMethod', backref='quotes')
    currency = db.relationship('Currency', backref='quotes')
    
    def __repr__(self):
        return f'<Quote {self.payment_method.code}-{self.currency.code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'payment_method': self.payment_method.name,
            'payment_method_code': self.payment_method.code,
            'currency': self.currency.code,
            'value_type': self.value_type,
            'usd_value': float(self.usd_value) if self.usd_value else None,
            'usd_formula': self.usd_formula,
            'calculated_usd': float(self.calculated_usd) if self.calculated_usd else None,
            'final_value': float(self.final_value) if self.final_value else None,
            'updated_at': self.updated_at.isoformat()
        }
