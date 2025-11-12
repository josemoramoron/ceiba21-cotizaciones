"""
Servicio de Monedas (POO)
"""
from app.models import db, Currency, ExchangeRate

class CurrencyService:
    """Servicio para gestionar monedas"""
    
    @staticmethod
    def get_all():
        """Obtener todas las monedas"""
        return Currency.query.order_by(Currency.code).all()
    
    @staticmethod
    def get_by_id(currency_id):
        """Obtener moneda por ID"""
        return Currency.query.get(currency_id)
    
    @staticmethod
    def get_by_code(code):
        """Obtener moneda por código"""
        return Currency.query.filter_by(code=code.upper()).first()
    
    @staticmethod
    def create(code, name, symbol, active=True, initial_rate=None):
        """Crear nueva moneda y su tasa de cambio inicial"""
        # Verificar que no exista
        if CurrencyService.get_by_code(code):
            return None, "Ya existe una moneda con ese código"
        
        currency = Currency(
            code=code.upper(),
            name=name,
            symbol=symbol,
            active=active
        )
        
        db.session.add(currency)
        db.session.flush()  # Para obtener el ID antes de commit
        
        # Crear tasa de cambio inicial si se proporciona
        if initial_rate:
            exchange_rate = ExchangeRate(
                currency_id=currency.id,
                rate=initial_rate,
                source_type='manual'
            )
            db.session.add(exchange_rate)
        
        db.session.commit()
        return currency, None
    
    @staticmethod
    def update(currency_id, code=None, name=None, symbol=None, active=None):
        """Actualizar moneda"""
        currency = CurrencyService.get_by_id(currency_id)
        if not currency:
            return None, "Moneda no encontrada"
        
        if code:
            currency.code = code.upper()
        if name:
            currency.name = name
        if symbol:
            currency.symbol = symbol
        if active is not None:
            currency.active = active
        
        db.session.commit()
        return currency, None
    
    @staticmethod
    def toggle_active(currency_id):
        """Alternar estado activo/inactivo"""
        currency = CurrencyService.get_by_id(currency_id)
        if not currency:
            return None, "Moneda no encontrada"
        
        currency.active = not currency.active
        db.session.commit()
        return currency, None
    
    @staticmethod
    def delete(currency_id):
        """Eliminar moneda"""
        currency = CurrencyService.get_by_id(currency_id)
        if not currency:
            return False, "Moneda no encontrada"
        
        # Verificar que no tenga cotizaciones asociadas
        if currency.quotes:
            return False, "No se puede eliminar: tiene cotizaciones asociadas. Desactívala en su lugar."
        
        db.session.delete(currency)
        db.session.commit()
        return True, None
    
    @staticmethod
    def reorder(order_list):
        """
        Reordenar monedas
        order_list: lista de IDs en el nuevo orden [3, 1, 2, 4...]
        """
        for index, currency_id in enumerate(order_list, start=1):
            currency = CurrencyService.get_by_id(currency_id)
            if currency:
                currency.display_order = index
        
        db.session.commit()
        return True
