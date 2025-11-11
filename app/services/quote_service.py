"""
Servicio de Cotizaciones (POO)
Maneja toda la lógica de negocio relacionada con cotizaciones
"""
from app.models import db, Quote, PaymentMethod, Currency, ExchangeRate

class QuoteService:
    """Servicio para gestionar cotizaciones"""
    
    @staticmethod
    def get_all_quotes():
        """Obtener todas las cotizaciones organizadas por método de pago"""
        quotes = Quote.query.join(PaymentMethod).join(Currency).order_by(
            PaymentMethod.display_order,
            Currency.code
        ).all()
        return quotes
    
    @staticmethod
    def get_quotes_by_payment_method(payment_method_code):
        """Obtener cotizaciones de un método de pago específico"""
        pm = PaymentMethod.query.filter_by(code=payment_method_code).first()
        if not pm:
            return []
        return Quote.query.filter_by(payment_method_id=pm.id).all()
    
    @staticmethod
    def get_quotes_matrix():
        """
        Obtener cotizaciones en formato matriz (como tu Google Sheets)
        Retorna: {
            'payment_methods': [...],
            'currencies': [...],
            'quotes': {
                'PAYPAL': {'BS': 280.15, 'COP': 3382.75, ...},
                'ZELLE': {...}
            }
        }
        """
        payment_methods = PaymentMethod.query.order_by(PaymentMethod.display_order).all()
        currencies = Currency.query.order_by(Currency.code).all()
        
        quotes_dict = {}
        for pm in payment_methods:
            quotes_dict[pm.code] = {}
            for curr in currencies:
                quote = Quote.query.filter_by(
                    payment_method_id=pm.id,
                    currency_id=curr.id
                ).first()
                quotes_dict[pm.code][curr.code] = {
                    'id': quote.id if quote else None,
                    'value': float(quote.final_value) if quote and quote.final_value else 0,
                    'type': quote.value_type if quote else 'manual',
                    'formula': quote.usd_formula if quote else None,
                    'usd': float(quote.calculated_usd) if quote and quote.calculated_usd else 0
                }
        
        return {
            'payment_methods': [pm.to_dict() for pm in payment_methods],
            'currencies': [curr.to_dict() for curr in currencies],
            'quotes': quotes_dict
        }
    
    @staticmethod
    def update_quote(quote_id, value_type=None, usd_value=None, usd_formula=None):
        """Actualizar una cotización"""
        quote = Quote.query.get(quote_id)
        if not quote:
            return None
        
        if value_type:
            quote.value_type = value_type
        if usd_value is not None:
            quote.usd_value = usd_value
        if usd_formula is not None:
            quote.usd_formula = usd_formula
        
        # Recalcular
        QuoteService.recalculate_quote(quote)
        
        db.session.commit()
        return quote
    
    @staticmethod
    def recalculate_quote(quote):
        """Recalcular una cotización individual"""
        # Calcular valor en USD
        if quote.value_type == 'manual':
            quote.calculated_usd = quote.usd_value
        elif quote.value_type == 'formula':
            try:
                # Evaluar fórmula simple
                calc_usd = eval(quote.usd_formula)
                quote.calculated_usd = calc_usd
            except:
                quote.calculated_usd = 0
        
        # Obtener tasa de cambio y calcular valor final
        exchange_rate = ExchangeRate.query.filter_by(currency_id=quote.currency_id).first()
        if exchange_rate and quote.calculated_usd:
            quote.final_value = float(quote.calculated_usd) * float(exchange_rate.rate)
        
        return quote
    
    @staticmethod
    def recalculate_all_quotes():
        """Recalcular todas las cotizaciones (después de cambiar tasas de cambio)"""
        quotes = Quote.query.all()
        for quote in quotes:
            QuoteService.recalculate_quote(quote)
        db.session.commit()
        return len(quotes)
