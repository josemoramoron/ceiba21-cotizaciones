from app.models import db
from datetime import datetime
from typing import List, Optional

class Currency(db.Model):
    """Modelo de moneda"""
    __tablename__ = 'currencies'

    # Monedas que están ACTIVAS (sirven en la calculadora pública) pero cuya
    # columna NO debe mostrarse en la tabla pública /cotizaciones, porque su
    # cotización ahí es redundante (p. ej. USD, que actúa como pivote/medida).
    # Es la única fuente de verdad de esta visibilidad: ocultar otra moneda en
    # la tabla a futuro = añadir su código aquí. NO afecta a `active` ni a la
    # calculadora; solo a las columnas de /cotizaciones.
    OCULTAS_EN_COTIZACIONES: frozenset = frozenset({'USD'})

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    display_order = db.Column(db.Integer, default=0)
    
    # Relaciones
    quotes = db.relationship('Quote', back_populates='currency', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Currency {self.code}>'

    @property
    def es_visible_en_cotizaciones(self) -> bool:
        """Indica si la moneda debe mostrarse como columna en /cotizaciones.

        Una moneda aparece en la tabla pública cuando está activa y su código
        no figura entre las ocultas en cotizaciones (``OCULTAS_EN_COTIZACIONES``).
        Es independiente de la calculadora pública, que sigue usando ``active``.

        Returns:
            True si la moneda debe mostrarse en la tabla /cotizaciones;
            False si está inactiva o se oculta explícitamente en esa tabla.
        """
        if not self.active:
            return False
        return (self.code or '').upper() not in self.OCULTAS_EN_COTIZACIONES

    @classmethod
    def get_visibles_en_cotizaciones(cls) -> List['Currency']:
        """Devuelve las monedas que se muestran en la tabla /cotizaciones.

        Filtra por ``active=True`` y excluye las ocultas en cotizaciones,
        manteniendo el mismo orden (``display_order``, luego ``code``) que la
        matriz general, para que el encabezado de columnas quede consistente.

        Returns:
            Lista de Currency visibles en la tabla, ya ordenada.
        """
        activas = (
            cls.query
            .filter_by(active=True)
            .order_by(cls.display_order, cls.code)
            .all()
        )
        return [
            c for c in activas
            if (c.code or '').upper() not in cls.OCULTAS_EN_COTIZACIONES
        ]

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'symbol': self.symbol,
            'active': self.active,
            'visible_en_cotizaciones': self.es_visible_en_cotizaciones,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def create_exchange_rate(self, rate=None):
        """
        Crea la tasa de cambio para esta moneda si no existe
        """
        from app.models.exchange_rate import ExchangeRate
        
        # Verificar si ya existe
        existing_rate = ExchangeRate.query.filter_by(currency_id=self.id).first()
        if existing_rate:
            return existing_rate, False  # Ya existe
        
        # Usar tasa por defecto si no se proporciona
        if rate is None:
            rate = self.get_default_rate_for_currency(self.code)
        
        # Crear nueva tasa de cambio
        new_rate = ExchangeRate(
            currency_id=self.id,
            rate=rate,
            source_type='manual',
            updated_at=datetime.utcnow()
        )
        
        db.session.add(new_rate)
        return new_rate, True  # Creada
    
    def create_quotes_for_all_payment_methods(self, reference_currency_code='VES'):
        """
        Crea cotizaciones para todos los métodos de pago activos
        copiando las configuraciones de una moneda de referencia
        
        Args:
            reference_currency_code: Código de la moneda de referencia (default: 'VES')
        """
        from app.models.payment_method import PaymentMethod
        from app.models.quote import Quote
        
        # Obtener moneda de referencia
        reference_currency = Currency.query.filter_by(code=reference_currency_code).first()
        
        if not reference_currency:
            # Fallback: usar la primera moneda activa disponible
            reference_currency = Currency.query.filter_by(active=True).first()
        
        payment_methods = PaymentMethod.query.filter_by(active=True).all()
        created_count = 0
        
        for method in payment_methods:
            # Verificar si ya existe
            existing_quote = Quote.query.filter_by(
                payment_method_id=method.id,
                currency_id=self.id
            ).first()
            
            if not existing_quote:
                # Buscar cotización de referencia para este método de pago
                reference_quote = None
                if reference_currency:
                    reference_quote = Quote.query.filter_by(
                        payment_method_id=method.id,
                        currency_id=reference_currency.id
                    ).first()
                
                # Si existe una cotización de referencia, copiar sus valores
                if reference_quote:
                    new_quote = Quote(
                        payment_method_id=method.id,
                        currency_id=self.id,
                        value_type=reference_quote.value_type,
                        usd_value=reference_quote.usd_value,
                        usd_formula=reference_quote.usd_formula,
                        calculated_usd=reference_quote.calculated_usd,
                        updated_at=datetime.utcnow()
                    )
                else:
                    # Fallback: usar valor por defecto solo si no hay referencia
                    new_quote = Quote(
                        payment_method_id=method.id,
                        currency_id=self.id,
                        value_type='manual',
                        usd_value=1.0,
                        usd_formula=None,
                        updated_at=datetime.utcnow()
                    )
                
                # Calcular valor final con la tasa de cambio de la nueva moneda
                new_quote.calculate_final_value()
                
                db.session.add(new_quote)
                created_count += 1
        
        return created_count
    
    def initialize_for_trading(self, exchange_rate=None):
        """
        Inicializa completamente una moneda nueva para trading:
        1. Crea la tasa de cambio
        2. Crea todas las cotizaciones para métodos de pago
        
        Retorna: (success, message, details)
        """
        try:
            details = {}
            
            # Paso 1: Crear tasa de cambio
            rate_obj, rate_created = self.create_exchange_rate(exchange_rate)
            details['exchange_rate'] = {
                'created': rate_created,
                'rate': float(rate_obj.rate)
            }
            
            # Paso 2: Crear cotizaciones
            quotes_created = self.create_quotes_for_all_payment_methods()
            details['quotes_created'] = quotes_created
            
            # Commit
            db.session.commit()
            
            message = f"Moneda {self.code} inicializada: "
            if rate_created:
                message += f"Tasa de cambio creada ({rate_obj.rate}), "
            message += f"{quotes_created} cotizaciones creadas"
            
            return True, message, details
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error inicializando moneda: {str(e)}", {}
    
    @staticmethod
    def get_default_rate_for_currency(code):
        """Tasas por defecto USD -> Moneda local"""
        default_rates = {
            'VES': 37.0,
            'COP': 4300.0,
            'CLP': 950.0,
            'ARS': 1000.0,
            'BRL': 5.85,
            'MXN': 17.50,
            'USD': 1.0,
            'EUR': 0.92,
            'PEN': 3.75,
            'UYU': 39.0,
            'PYG': 7300.0,
            'BOB': 6.90,
        }
        return default_rates.get(code.upper(), 1.0)
