"""
Modelo de Historial de Cotizaciones
Guarda cada cambio para tener trazabilidad
"""
from app.utils.fecha import utcnow_naive
from app.models import db

class QuoteHistory(db.Model):
    __tablename__ = 'quote_history'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'))
    old_value = db.Column(db.Numeric(10, 2))
    new_value = db.Column(db.Numeric(10, 2), nullable=False)
    changed_at = db.Column(db.DateTime, default=utcnow_naive)
    published_to_telegram = db.Column(db.Boolean, default=False)
    
    # Relación
    quote = db.relationship('Quote')
    
    def __repr__(self):
        return f'<QuoteHistory {self.quote_id}: {self.old_value}->{self.new_value}>'
