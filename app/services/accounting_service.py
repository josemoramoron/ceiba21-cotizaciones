"""
Servicio de contabilidad y reportes financieros.

RESPONSABILIDAD:
- Calcular balances y totales con precisión monetaria
- Generar reportes financieros
- Métricas y estadísticas
- Integración con Transaction model

IMPORTANTE: Usa Decimal para TODOS los cálculos monetarios.
NUNCA usar float para dinero - causa errores de redondeo.
"""
from app.services.base_service import BaseService
from app.models.transaction import Transaction, TransactionType
from app.models.payment_method import PaymentMethod
from app.models.currency import Currency
from app.models.order import Order, OrderStatus
from app.models import db
from datetime import datetime, timedelta, date
from sqlalchemy import func
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional, Tuple


class AccountingService(BaseService):
    """
    Servicio de contabilidad automática.
    
    PRECISION: Usa Decimal para todos los cálculos monetarios.
    """
    
    # ==========================================
    # CONSTANTES
    # ==========================================
    
    # Contexto de redondeo para Decimal
    DECIMAL_PLACES = Decimal('0.01')  # 2 decimales
    DECIMAL_PERCENTAGE = Decimal('0.1')  # 1 decimal para porcentajes
    
    # ==========================================
    # MÉTODOS DE BALANCE Y TOTALES
    # ==========================================
    
    @classmethod
    def get_balance_summary(cls, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Obtener resumen financiero de un período.
        
        PRECISION: Usa Decimal para evitar errores de redondeo.
        
        Args:
            start_date: Fecha inicio (default: hoy 00:00)
            end_date: Fecha fin (default: ahora)
            
        Returns:
            {
                'total_income_usd': Decimal('2450.00'),
                'total_fees_usd': Decimal('131.85'),
                'total_expenses': {
                    'VES': Decimal('747375.00'),
                    'COP': Decimal('4120000.00'),
                    ...
                },
                'net_profit_usd': Decimal('131.85'),
                'order_count': 25,
                'average_fee_percentage': Decimal('5.38')
            }
            
        Example:
            >>> summary = AccountingService.get_balance_summary()
            >>> print(f"Ganancias: ${summary['total_fees_usd']}")
            Ganancias: $131.85
        """
        # Establecer fechas por defecto (hoy)
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        # Consultar transacciones del período
        transactions = Transaction.query.filter(
            Transaction.created_at.between(start_date, end_date)
        ).all()
        
        # Inicializar con Decimal (NO float)
        summary = {
            'total_income_usd': Decimal('0.00'),
            'total_fees_usd': Decimal('0.00'),
            'total_expenses': {},
            'net_profit_usd': Decimal('0.00'),
            'order_count': 0,
            'average_fee_percentage': Decimal('0.00')
        }
        
        # Procesar transacciones
        order_ids = set()
        
        for t in transactions:
            # IMPORTANTE: amount ya es Decimal desde la BD
            amount = t.amount
            
            if t.type == TransactionType.INCOME and t.currency_code == 'USD':
                summary['total_income_usd'] += amount
                order_ids.add(t.order_id)
            
            elif t.type == TransactionType.FEE:
                summary['total_fees_usd'] += amount
            
            elif t.type == TransactionType.EXPENSE:
                if t.currency_code not in summary['total_expenses']:
                    summary['total_expenses'][t.currency_code] = Decimal('0.00')
                summary['total_expenses'][t.currency_code] += amount
        
        # Calcular métricas derivadas
        summary['net_profit_usd'] = summary['total_fees_usd']
        summary['order_count'] = len(order_ids)
        
        # Calcular fee promedio (con protección división por cero)
        if summary['total_income_usd'] > 0:
            percentage = (summary['total_fees_usd'] / summary['total_income_usd'] * 100)
            # Redondear a 2 decimales
            summary['average_fee_percentage'] = percentage.quantize(
                cls.DECIMAL_PLACES, 
                rounding=ROUND_HALF_UP
            )
        
        cls.log_action('balance_summary_calculated', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_income': float(summary['total_income_usd']),
            'total_fees': float(summary['total_fees_usd'])
        })
        
        return summary
    
    @classmethod
    def get_balance_by_currency(cls,
                               currency_code: str,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Obtener balance específico de una moneda.
        
        Args:
            currency_code: Código de moneda (USD, VES, COP, etc.)
            start_date: Fecha inicio
            end_date: Fecha fin
            
        Returns:
            {
                'currency_code': 'VES',
                'total_income': Decimal('1500000.00'),
                'total_expense': Decimal('1470000.00'),
                'net_balance': Decimal('30000.00'),
                'transaction_count': 45
            }
        """
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        transactions = Transaction.query.filter(
            Transaction.currency_code == currency_code,
            Transaction.created_at.between(start_date, end_date)
        ).all()
        
        # Sumar con Decimal
        income = Decimal('0.00')
        expense = Decimal('0.00')
        
        for t in transactions:
            if t.type == TransactionType.INCOME:
                income += t.amount
            elif t.type == TransactionType.EXPENSE:
                expense += t.amount
        
        return {
            'currency_code': currency_code,
            'total_income': income,
            'total_expense': expense,
            'net_balance': income - expense,
            'transaction_count': len(transactions),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    
    @classmethod
    def get_total_fees(cls,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> Decimal:
        """
        Obtener total de comisiones (ganancias) del período.
        
        PRECISION: Retorna Decimal, no float.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
            
        Returns:
            Total de comisiones como Decimal
            
        Example:
            >>> total = AccountingService.get_total_fees()
            >>> print(f"Ganancias: ${total}")
            Ganancias: $131.85
        """
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        # Usar SQLAlchemy func.sum con coalesce para manejar NULL
        result = db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.type == TransactionType.FEE,
            Transaction.currency_code == 'USD',
            Transaction.created_at.between(start_date, end_date)
        ).scalar()
        
        # Convertir a Decimal si es necesario
        return Decimal(str(result)) if result else Decimal('0.00')
    
    @classmethod
    def get_fees_by_payment_method(cls,
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Obtener distribución de ganancias por método de pago.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
            
        Returns:
            [
                {
                    'method': 'PayPal',
                    'fees': Decimal('98.50'),
                    'percentage': Decimal('74.7'),
                    'order_count': 15
                },
                ...
            ]
            
        USO: Para gráfico de pie en dashboard
        """
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        # Query con join
        results = db.session.query(
            PaymentMethod.name,
            PaymentMethod.id,
            func.sum(Transaction.amount).label('total_fees'),
            func.count(func.distinct(Transaction.order_id)).label('order_count')
        ).join(
            PaymentMethod, Transaction.payment_method_id == PaymentMethod.id
        ).filter(
            Transaction.type == TransactionType.FEE,
            Transaction.created_at.between(start_date, end_date)
        ).group_by(PaymentMethod.id, PaymentMethod.name).all()
        
        # Calcular total para porcentajes
        total_fees = sum(Decimal(str(r.total_fees)) for r in results)
        
        distribution = []
        for result in results:
            fees = Decimal(str(result.total_fees))
            
            # Calcular porcentaje con Decimal
            if total_fees > 0:
                percentage = (fees / total_fees * 100).quantize(
                    cls.DECIMAL_PERCENTAGE, 
                    rounding=ROUND_HALF_UP
                )
            else:
                percentage = Decimal('0.0')
            
            distribution.append({
                'method': result.name,
                'fees': fees,
                'percentage': percentage,
                'order_count': result.order_count
            })
        
        # Ordenar por fees descendente
        distribution.sort(key=lambda x: x['fees'], reverse=True)
        
        return distribution
    
    @classmethod
    def get_orders_by_currency(cls,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Obtener distribución de órdenes por moneda.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
            
        Returns:
            [
                {
                    'currency': 'VES',
                    'count': 18,
                    'percentage': Decimal('72.0'),
                    'total_amount_local': Decimal('5475000.00')
                },
                ...
            ]
        """
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        results = db.session.query(
            Currency.code,
            Currency.name,
            func.count(Order.id).label('order_count'),
            func.sum(Order.amount_local).label('total_amount')
        ).join(
            Currency, Order.currency_id == Currency.id
        ).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.completed_at.between(start_date, end_date)
        ).group_by(Currency.code, Currency.name).all()
        
        total_orders = sum(r.order_count for r in results)
        
        distribution = []
        for result in results:
            if total_orders > 0:
                percentage = (Decimal(result.order_count) / Decimal(total_orders) * 100).quantize(
                    cls.DECIMAL_PERCENTAGE,
                    rounding=ROUND_HALF_UP
                )
            else:
                percentage = Decimal('0.0')
            
            distribution.append({
                'currency': result.code,
                'currency_name': result.name,
                'count': result.order_count,
                'percentage': percentage,
                'total_amount_local': Decimal(str(result.total_amount)) if result.total_amount else Decimal('0.00')
            })
        
        distribution.sort(key=lambda x: x['count'], reverse=True)
        
        return distribution
    
    # ==========================================
    # MÉTRICAS DIARIAS
    # ==========================================
    
    @classmethod
    def get_today_summary(cls) -> Dict[str, Any]:
        """
        Resumen rápido del día actual.
        
        Returns:
            Resumen financiero de hoy
            
        Example:
            >>> summary = AccountingService.get_today_summary()
            >>> print(f"Hoy ganamos: ${summary['total_fees_usd']}")
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return cls.get_balance_summary(today_start, datetime.now())
    
    @classmethod
    def compare_with_yesterday(cls) -> Dict[str, Any]:
        """
        Comparar métricas de hoy vs ayer.
        
        Returns:
            {
                'today_fees': Decimal('131.85'),
                'yesterday_fees': Decimal('98.20'),
                'growth_amount': Decimal('33.65'),
                'growth_percentage': Decimal('34.3'),
                'is_growing': True
            }
        """
        # Hoy
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now()
        today_fees = cls.get_total_fees(today_start, today_end)
        
        # Ayer
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start
        yesterday_fees = cls.get_total_fees(yesterday_start, yesterday_end)
        
        # Crecimiento
        growth_amount = today_fees - yesterday_fees
        
        if yesterday_fees > 0:
            growth_percentage = (growth_amount / yesterday_fees * 100).quantize(
                cls.DECIMAL_PERCENTAGE,
                rounding=ROUND_HALF_UP
            )
        else:
            growth_percentage = Decimal('0.0')
        
        return {
            'today_fees': today_fees,
            'yesterday_fees': yesterday_fees,
            'growth_amount': growth_amount,
            'growth_percentage': growth_percentage,
            'is_growing': growth_amount > 0
        }
    
    @classmethod
    def get_daily_fees(cls, days: int = 7) -> List[Dict[str, Any]]:
        """
        Obtener ganancias (fees) diarias de los últimos N días.
        
        Args:
            days: Número de días a consultar
            
        Returns:
            [
                {'date': '2024-12-01', 'fees': Decimal('45.80')},
                {'date': '2024-12-02', 'fees': Decimal('62.15')},
                ...
            ]
            
        USO: Para gráfico de línea de tendencia
        """
        start_date = datetime.now() - timedelta(days=days)
        
        results = db.session.query(
            func.date(Transaction.created_at).label('date'),
            func.sum(Transaction.amount).label('total_fees')
        ).filter(
            Transaction.type == TransactionType.FEE,
            Transaction.currency_code == 'USD',
            Transaction.created_at >= start_date
        ).group_by(func.date(Transaction.created_at)).order_by('date').all()
        
        return [
            {
                'date': result.date.isoformat(),
                'fees': Decimal(str(result.total_fees)) if result.total_fees else Decimal('0.00')
            }
            for result in results
        ]
    
    # ==========================================
    # UTILIDADES DE CONVERSIÓN
    # ==========================================
    
    @classmethod
    def to_json_safe(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertir Decimals a float para JSON serialization.
        
        IMPORTANTE: Solo usar para enviar a frontend.
        NUNCA usar para cálculos internos.
        
        Args:
            data: Dict que puede contener Decimals
            
        Returns:
            Dict con Decimals convertidos a float
            
        Example:
            >>> summary = AccountingService.get_balance_summary()
            >>> json_data = AccountingService.to_json_safe(summary)
            >>> return jsonify(json_data)  # Ahora es serializable
        """
        result = {}
        
        for key, value in data.items():
            if isinstance(value, Decimal):
                result[key] = float(value)
            elif isinstance(value, dict):
                result[key] = cls.to_json_safe(value)
            elif isinstance(value, list):
                result[key] = [
                    cls.to_json_safe(item) if isinstance(item, dict) else 
                    float(item) if isinstance(item, Decimal) else 
                    item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def format_currency(cls, amount: Decimal, currency_code: str) -> str:
        """
        Formatear monto con símbolo de moneda.
        
        Args:
            amount: Monto como Decimal
            currency_code: Código de moneda (USD, VES, etc.)
            
        Returns:
            String formateado (ej: "$1,234.56", "Bs 28,808.65")
            
        Example:
            >>> formatted = AccountingService.format_currency(Decimal('1234.56'), 'USD')
            >>> print(formatted)
            $1,234.56
        """
        symbols = {
            'USD': '$',
            'VES': 'Bs',
            'COP': '$',
            'CLP': '$',
            'ARS': '$',
            'EUR': '€',
            'BRL': 'R$',
            'MXN': '$'
        }
        
        symbol = symbols.get(currency_code, currency_code)
        
        # Formatear con separadores de miles
        formatted_amount = f"{amount:,.2f}"
        
        if currency_code == 'USD' or currency_code in ['COP', 'CLP', 'ARS', 'MXN']:
            return f"{symbol}{formatted_amount}"
        else:
            return f"{symbol} {formatted_amount}"
