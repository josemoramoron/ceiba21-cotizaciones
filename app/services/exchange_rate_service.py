"""
Servicio de Tasas de Cambio (POO)
"""
from typing import Optional, Dict

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

    @staticmethod
    def get_cross_rate(base_code: str, quote_code: str) -> Optional[float]:
        """Calcula la tasa cruzada base→quote vía el pivote USD.

        Reutiliza las tasas USD→moneda existentes: como cada tasa es
        'unidades por USD', 1 unidad de `base` equivale a
        (rate_quote / rate_base) unidades de `quote`. USD se trata como
        pivote con tasa 1.0 aunque no tenga fila propia en exchange_rates.

        Args:
            base_code: Código de la moneda de origen (ej. 'COP').
            quote_code: Código de la moneda de destino (ej. 'PEN').

        Returns:
            Unidades de `quote` por 1 unidad de `base`, o None si falta
            la tasa de alguna de las dos monedas.
        """
        base_code = base_code.upper()
        quote_code = quote_code.upper()
        rates = ExchangeRateService.get_rates_dict()

        rate_base = 1.0 if base_code == 'USD' else rates.get(base_code)
        rate_quote = 1.0 if quote_code == 'USD' else rates.get(quote_code)

        if not rate_base or not rate_quote:
            return None
        return rate_quote / rate_base

    @staticmethod
    def convert(
        amount: float,
        base_code: str,
        quote_code: str,
        spread_pct: float = 0.0
    ) -> Optional[Dict]:
        """Convierte un monto entre dos monedas vía el pivote USD, con spread.

        El spread es tu margen: reduce lo que recibe el cliente en `quote`
        (un spread de 2 significa que entregas un 2% menos que la tasa media).

        Args:
            amount: Monto en la moneda de origen.
            base_code: Moneda de origen.
            quote_code: Moneda de destino.
            spread_pct: Margen porcentual a tu favor (0 = sin margen).

        Returns:
            dict con base, quote, cross_rate, effective_rate, amount, result
            y spread_pct (todo float, JSON-serializable); o None si falta
            alguna tasa.
        """
        cross = ExchangeRateService.get_cross_rate(base_code, quote_code)
        if cross is None:
            return None

        effective = cross * (1 - spread_pct / 100.0)
        return {
            'base': base_code.upper(),
            'quote': quote_code.upper(),
            'cross_rate': round(cross, 6),
            'effective_rate': round(effective, 6),
            'amount': round(amount, 2),
            'result': round(amount * effective, 2),
            'spread_pct': spread_pct,
        }