"""
Modelo de Cotizaciones
Cada celda puede ser:
- Valor manual: "308.17"
- Fórmula: "REF / 1.1"
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
    
    # Valor manual (si aplica)
    manual_value = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Fórmula (si aplica): "REF / 1.1"
    formula = db.Column(db.String(200), nullable=True)
    
    # Valor calculado final
    calculated_value = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Timestamp
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    payment_method = db.relationship('PaymentMethod', backref='quotes')
    currency = db.relationship('Currency', backref='quotes')
    
    def __repr__(self):
        return f'<Quote {self.payment_method.code}-{self.currency.code}>'
    
    def get_value(self):
        """Obtener el valor actual (manual o calculado)"""
        if self.value_type == 'manual':
            return float(self.manual_value) if self.manual_value else 0
        else:
            return float(self.calculated_value) if self.calculated_value else 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'payment_method': self.payment_method.name,
            'payment_method_code': self.payment_method.code,
            'currency': self.currency.code,
            'value_type': self.value_type,
            'manual_value': float(self.manual_value) if self.manual_value else None,
            'formula': self.formula,
            'calculated_value': float(self.calculated_value) if self.calculated_value else None,
            'display_value': self.get_value(),
            'updated_at': self.updated_at.isoformat()
        }
