"""
Modelo de Métodos de Pago / Billeteras (REF, PayPal, Zelle, etc.)
"""
from datetime import datetime
from app.models import db

class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Configuración USD centralizada (aplica a todas las monedas)
    value_type = db.Column(db.String(20), default='manual', nullable=False)
    usd_value = db.Column(db.Numeric(10, 6), nullable=True)
    usd_formula = db.Column(db.String(200), nullable=True)
    
    def __repr__(self):
        return f'<PaymentMethod {self.code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'active': self.active,
            'display_order': self.display_order,
            'value_type': self.value_type,
            'usd_value': float(self.usd_value) if self.usd_value else None,
            'usd_formula': self.usd_formula
        }
    
    def calculate_usd_value(self):
        """
        Calcula el valor en USD basado en el tipo de valor
        Este método es usado por todas las monedas
        """
        if self.value_type == 'manual':
            return float(self.usd_value) if self.usd_value else 1.0
        elif self.value_type == 'formula' and self.usd_formula:
            try:
                return float(eval(self.usd_formula))
            except:
                return 1.0
        return 1.0
