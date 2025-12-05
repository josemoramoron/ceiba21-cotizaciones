"""
Servicio de Tasas de Cambio (POO)
"""
from app.models import db, ExchangeRate, Currency
from app.services.quote_service import QuoteService

class ExchangeRateService:
    """Servicio para gestionar tasas de cambio USD → Monedas"""
    
    @staticmethod
    def get_all_rates():
        """Obtener todas las tasas de cambio"""
        rates = ExchangeRate.query.join(Currency).all()
        return rates
    
    @staticmethod
    def get_rates_dict():
        """Obtener tasas en formato diccionario {'BS': 308.17, 'COP': 3721.03}"""
        rates = ExchangeRate.query.join(Currency).all()
        return {rate.currency.code: float(rate.rate) for rate in rates}
    
    @staticmethod
    def update_rate(currency_code, new_rate):
        """
        Actualizar tasa de cambio y recalcular SOLO las cotizaciones de esa moneda (POO)
        """
        currency = Currency.query.filter_by(code=currency_code).first()
        if not currency:
            return None
        
        exchange_rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
        if not exchange_rate:
            # Crear si no existe
            exchange_rate = ExchangeRate(
                currency_id=currency.id,
                rate=new_rate,
                source_type='manual'
            )
            db.session.add(exchange_rate)
            db.session.flush()  # Para obtener el ID
        else:
            exchange_rate.rate = new_rate
        
        # Recalcular SOLO las cotizaciones de esta moneda (POO)
        quotes_updated = exchange_rate.recalculate_quotes()
        
        db.session.commit()
        
        return exchange_rate, quotes_updated
    
    @staticmethod
    def update_multiple_rates(rates_dict):
        """
        Actualizar múltiples tasas de cambio
        rates_dict: {'BS': 308.17, 'COP': 3721.03, ...}
        """
        for currency_code, rate in rates_dict.items():
            ExchangeRateService.update_rate(currency_code, rate)
        
        return True
