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
    def create(code, name, symbol, initial_rate=None):
        """
        Crea una nueva moneda y automáticamente genera tasas de cambio
        para todos los métodos de pago existentes.
        """
        try:
            from app.models import Currency
            from datetime import datetime
            
            # Validar que no exista
            existing = Currency.query.filter_by(code=code).first()
            if existing:
                return None, f"Ya existe una moneda con código {code}"
            
            # Determinar tasa por defecto
            if initial_rate is None:
                initial_rate = Currency.get_default_rate_for_currency(code)
            else:
                try:
                    initial_rate = float(initial_rate)
                except (ValueError, TypeError):
                    initial_rate = Currency.get_default_rate_for_currency(code)
            
            # Crear la moneda
            currency = Currency(
                code=code,
                name=name,
                symbol=symbol,
                active=True,
                display_order=0
            )
            
            db.session.add(currency)
            db.session.flush()  # Para obtener el ID sin hacer commit completo
            
            # Crear tasas de cambio automáticamente
            success, message = currency.create_default_exchange_rates(initial_rate)
            
            if not success:
                # Si falla la creación de tasas, revertir todo
                db.session.rollback()
                return None, f"Error al crear tasas: {message}"
            
            db.session.commit()
            
            return currency, None  # Sin error
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
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
