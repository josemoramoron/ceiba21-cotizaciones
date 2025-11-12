"""
Modelo de Monedas (CLP, BS, COP, ARS, etc.)
"""
from datetime import datetime
from app.models import db

class Currency(db.Model):
    __tablename__ = 'currencies'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(10))
    active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)  # ← NUEVO
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Currency {self.code}>'
    
    def to_dict(self):
        """Convertir a diccionario para API"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'symbol': self.symbol,
            'active': self.active,
            'display_order': self.display_order
        }
