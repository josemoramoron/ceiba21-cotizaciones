"""
Servicio de Métodos de Pago (POO)
"""
from app.models import db, PaymentMethod, Quote, Currency

class PaymentMethodService:
    """Servicio para gestionar métodos de pago"""
    
    @staticmethod
    def get_all():
        """Obtener todos los métodos de pago"""
        return PaymentMethod.query.order_by(PaymentMethod.display_order).all()
    
    @staticmethod
    def get_by_id(pm_id):
        """Obtener método de pago por ID"""
        return PaymentMethod.query.get(pm_id)
    
    @staticmethod
    def get_by_code(code):
        """Obtener método de pago por código"""
        return PaymentMethod.query.filter_by(code=code.upper()).first()
    
    @staticmethod
    def create(code, name, display_order=None, active=True, value_type='manual', usd_value=1.0, usd_formula=None):
        """Crear nuevo método de pago y sus cotizaciones"""
        # Verificar que no exista
        if PaymentMethodService.get_by_code(code):
            return None, "Ya existe un método de pago con ese código"
        
        # Si no se especifica orden, ponerlo al final
        if display_order is None:
            max_order = db.session.query(db.func.max(PaymentMethod.display_order)).scalar() or 0
            display_order = max_order + 1
        
        pm = PaymentMethod(
            code=code.upper(),
            name=name,
            display_order=display_order,
            active=active
        )
        
        db.session.add(pm)
        db.session.flush()  # Para obtener el ID
        
        # Crear cotizaciones para todas las monedas activas
        PaymentMethodService._create_quotes_for_all_currencies(
            pm, value_type, usd_value, usd_formula
        )
        
        db.session.commit()
        return pm, None
    
    @staticmethod
    def _create_quotes_for_all_currencies(pm, value_type, usd_value, usd_formula):
        """Crear cotizaciones para todas las monedas"""
        from app.models import ExchangeRate
        
        currencies = Currency.query.filter_by(active=True).all()
        
        for currency in currencies:
            # Calcular valor en USD
            if value_type == 'manual':
                calc_usd = usd_value
            elif value_type == 'formula' and usd_formula:
                try:
                    calc_usd = eval(usd_formula)
                except:
                    calc_usd = 1.0
            else:
                calc_usd = 1.0
            
            # Obtener tasa de cambio
            exchange_rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
            final_val = calc_usd * float(exchange_rate.rate) if exchange_rate else 0
            
            quote = Quote(
                payment_method_id=pm.id,
                currency_id=currency.id,
                value_type=value_type,
                usd_value=usd_value if value_type == 'manual' else None,
                usd_formula=usd_formula if value_type == 'formula' else None,
                calculated_usd=calc_usd,
                final_value=final_val
            )
            db.session.add(quote)
    
    @staticmethod
    def update(pm_id, code=None, name=None, display_order=None, active=None):
        """Actualizar método de pago"""
        pm = PaymentMethodService.get_by_id(pm_id)
        if not pm:
            return None, "Método de pago no encontrado"
        
        if code:
            pm.code = code.upper()
        if name:
            pm.name = name
        if display_order is not None:
            pm.display_order = display_order
        if active is not None:
            pm.active = active
        
        db.session.commit()
        return pm, None
    
    @staticmethod
    def update_formula(pm_id, value_type, usd_value=None, usd_formula=None):
        """Actualizar fórmula de un método de pago y recalcular sus cotizaciones"""
        from app.services.quote_service import QuoteService
        
        pm = PaymentMethodService.get_by_id(pm_id)
        if not pm:
            return None, "Método de pago no encontrado"
        
        # Actualizar todas las cotizaciones de este método
        quotes = Quote.query.filter_by(payment_method_id=pm.id).all()
        
        for quote in quotes:
            quote.value_type = value_type
            quote.usd_value = usd_value if value_type == 'manual' else None
            quote.usd_formula = usd_formula if value_type == 'formula' else None
            QuoteService.recalculate_quote(quote)
        
        db.session.commit()
        return pm, None
    
    @staticmethod
    def reorder(order_list):
        """
        Reordenar métodos de pago
        order_list: lista de IDs en el nuevo orden [3, 1, 2, 4...]
        """
        for index, pm_id in enumerate(order_list, start=1):
            pm = PaymentMethodService.get_by_id(pm_id)
            if pm:
                pm.display_order = index
        
        db.session.commit()
        return True
    
    @staticmethod
    def delete(pm_id):
        """Eliminar método de pago"""
        pm = PaymentMethodService.get_by_id(pm_id)
        if not pm:
            return False, "Método de pago no encontrado"
        
        # Eliminar cotizaciones asociadas primero
        Quote.query.filter_by(payment_method_id=pm.id).delete()
        
        db.session.delete(pm)
        db.session.commit()
        return True, None
