"""
Modelo de Tasas de Cambio (USD → Otras monedas)
"""
from datetime import datetime
from app.models import db

class ExchangeRate(db.Model):
    """
    Tasas de cambio USD a otras monedas
    Ejemplo: 1 USD = 308.17 BS
    """
    __tablename__ = 'exchange_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False, unique=True)
    
    # Tasa: cuántas unidades de la moneda por 1 USD
    rate = db.Column(db.Numeric(10, 4), nullable=False)
    
    # Tipo: 'manual' o 'api'
    source_type = db.Column(db.String(20), default='manual')
    
    # Timestamp
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación
    currency = db.relationship('Currency', backref='exchange_rate')
    
    def __repr__(self):
        return f'<ExchangeRate USD→{self.currency.code}: {self.rate}>'
    
    def recalculate_quotes(self):
        """
        Recalcula todas las cotizaciones asociadas a esta moneda
        cuando se actualiza la tasa de cambio
        """
        from app.models.quote import Quote
        
        quotes = Quote.query.filter_by(currency_id=self.currency_id).all()
        
        for quote in quotes:
            quote.calculate_final_value()
        
        return len(quotes)
    
    def to_dict(self):
        return {
            'id': self.id,
            'currency': self.currency.code,
            'rate': float(self.rate),
            'source_type': self.source_type,
            'updated_at': self.updated_at.isoformat()
        }
