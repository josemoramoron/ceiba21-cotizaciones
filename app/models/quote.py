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
    currency = db.relationship('Currency', back_populates='quotes')
    
    def __repr__(self):
        return f'<Quote {self.payment_method.code}-{self.currency.code}>'
    
    def calculate_final_value(self):
        """
        Calcula el valor final de la cotización basado en:
        1. Valor en USD (lee del PaymentMethod centralizado)
        2. Tasa de cambio de la moneda
        """
        from app.models.exchange_rate import ExchangeRate
        
        # Paso 1: Obtener valor USD del método de pago (centralizado)
        # Primero intenta usar los valores del PaymentMethod (nuevo diseño)
        if hasattr(self.payment_method, 'value_type') and self.payment_method.value_type:
            calculated_usd = self.payment_method.calculate_usd_value()
        else:
            # Fallback: usar valores propios de Quote (diseño antiguo, por compatibilidad)
            if self.value_type == 'manual':
                calculated_usd = float(self.usd_value) if self.usd_value else 0
            elif self.value_type == 'formula' and self.usd_formula:
                try:
                    calculated_usd = float(eval(self.usd_formula))
                except Exception as e:
                    print(f"Error evaluando fórmula '{self.usd_formula}': {e}")
                    calculated_usd = 0
            else:
                calculated_usd = 0
        
        self.calculated_usd = calculated_usd
        
        # Paso 2: Obtener tasa de cambio y calcular valor final
        exchange_rate = ExchangeRate.query.filter_by(currency_id=self.currency_id).first()
        
        if exchange_rate and self.calculated_usd:
            # Valor final = Valor USD × Tasa de cambio
            self.final_value = float(self.calculated_usd) * float(exchange_rate.rate)
        else:
            self.final_value = 0
        
        return self.final_value
    
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
