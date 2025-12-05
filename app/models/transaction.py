"""
Modelo de transacción contable.
Sistema de contabilidad automática para órdenes.
"""
from app.models import db
from app.models.base import BaseModel
from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, Any, List


class TransactionType(Enum):
    """
    Tipos de transacciones.
    
    INCOME: Dinero que entra a Ceiba21 (cliente nos paga)
    EXPENSE: Dinero que sale de Ceiba21 (pagamos al cliente)
    FEE: Comisión/ganancia de Ceiba21
    """
    INCOME = 'income'
    EXPENSE = 'expense'
    FEE = 'fee'


class Transaction(BaseModel):
    """
    Transacción contable.
    
    Cada orden completada genera automáticamente 3 transacciones:
    1. INCOME: Lo que el cliente nos pagó
    2. FEE: Nuestra comisión
    3. EXPENSE: Lo que pagamos al cliente
    
    Attributes:
        order_id: ID de la orden asociada
        type: Tipo de transacción (INCOME, EXPENSE, FEE)
        amount: Monto de la transacción
        currency_code: Código de moneda (USD, VES, COP, etc.)
        payment_method_id: Método de pago usado
        description: Descripción de la transacción
        is_verified: Si la transacción ha sido verificada
        verified_at: Timestamp de verificación
        verified_by_id: ID del operador que verificó
    """
    
    __tablename__ = 'transactions'
    
    # Relación con orden
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    
    # Tipo y monto
    type = db.Column(db.Enum(TransactionType), nullable=False, index=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    
    # Método de pago usado
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'), nullable=True)
    
    # Descripción
    description = db.Column(db.String(255), nullable=False)
    
    # Verificación
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verified_at = db.Column(db.DateTime)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('operators.id'), nullable=True)
    
    # Relaciones
    order = db.relationship('Order', foreign_keys=[order_id], backref='transactions')
    payment_method = db.relationship('PaymentMethod', foreign_keys=[payment_method_id])
    verified_by = db.relationship('Operator', foreign_keys=[verified_by_id])
    
    def __repr__(self) -> str:
        """Representación de la transacción"""
        return f"<Transaction #{self.id} - {self.type.value} {self.amount} {self.currency_code}>"
    
    def verify(self, operator: Optional['Operator'] = None) -> bool:
        """
        Marcar transacción como verificada.
        
        Args:
            operator: Operador que verifica (opcional)
            
        Returns:
            bool: True si se verificó exitosamente
        """
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        if operator:
            self.verified_by_id = operator.id
        return self.save()
    
    def unverify(self) -> bool:
        """
        Deshacer verificación de transacción.
        
        Returns:
            bool: True si se desverifico exitosamente
        """
        self.is_verified = False
        self.verified_at = None
        self.verified_by_id = None
        return self.save()
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convertir transacción a diccionario.
        
        Args:
            include_relationships: Si True, incluye datos relacionados
            
        Returns:
            Dict con datos de la transacción
        """
        data = super().to_dict()
        
        # Convertir type enum a string
        data['type'] = self.type.value
        
        if include_relationships:
            data['order'] = self.order.to_dict() if self.order else None
            data['payment_method'] = self.payment_method.to_dict() if self.payment_method else None
            data['verified_by'] = self.verified_by.to_dict() if self.verified_by else None
        
        return data
    
    @classmethod
    def create_from_order(cls, order: 'Order') -> List['Transaction']:
        """
        Crear las 3 transacciones automáticas desde una orden.
        
        Se llama cuando una orden se completa.
        
        Args:
            order: Orden completada
            
        Returns:
            Lista de transacciones creadas
            
        Example:
            >>> transactions = Transaction.create_from_order(order)
            >>> # Retorna [income_transaction, fee_transaction, expense_transaction]
        """
        transactions = []
        
        try:
            # 1. INCOME: Lo que el cliente nos pagó
            income = cls(
                order_id=order.id,
                type=TransactionType.INCOME,
                amount=order.amount_usd,
                currency_code='USD',
                payment_method_id=order.payment_method_from_id,
                description=f"Ingreso de {order.reference}"
            )
            income.save()
            transactions.append(income)
            
            # 2. FEE: Nuestra comisión
            fee = cls(
                order_id=order.id,
                type=TransactionType.FEE,
                amount=order.fee_usd,
                currency_code='USD',
                payment_method_id=order.payment_method_from_id,
                description=f"Comisión de {order.reference}"
            )
            fee.save()
            transactions.append(fee)
            
            # 3. EXPENSE: Lo que pagamos al cliente
            expense = cls(
                order_id=order.id,
                type=TransactionType.EXPENSE,
                amount=order.amount_local,
                currency_code=order.currency.code if order.currency else 'USD',
                payment_method_id=order.payment_method_to_id,
                description=f"Pago al cliente {order.reference}"
            )
            expense.save()
            transactions.append(expense)
            
        except Exception as e:
            print(f"Error al crear transacciones para Order {order.reference}: {str(e)}")
        
        return transactions
    
    @classmethod
    def get_by_order(cls, order_id: int) -> List['Transaction']:
        """
        Obtener transacciones de una orden.
        
        Args:
            order_id: ID de la orden
            
        Returns:
            Lista de transacciones
        """
        return cls.query.filter_by(order_id=order_id).all()
    
    @classmethod
    def get_by_type(cls, transaction_type: TransactionType, 
                    limit: Optional[int] = None) -> List['Transaction']:
        """
        Obtener transacciones por tipo.
        
        Args:
            transaction_type: Tipo de transacción
            limit: Máximo de transacciones (None = todas)
            
        Returns:
            Lista de transacciones
        """
        query = cls.query.filter_by(type=transaction_type).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_daily_report(cls, date_obj: Optional[date] = None) -> Dict[str, Any]:
        """
        Obtener reporte contable del día.
        
        Args:
            date_obj: Fecha (default: hoy)
            
        Returns:
            Dict con reporte del día
            
        Example:
            >>> report = Transaction.get_daily_report()
            >>> print(f"Ingresos: ${report['total_income_usd']}")
        """
        if date_obj is None:
            date_obj = date.today()
        
        day_start = datetime.combine(date_obj, datetime.min.time())
        day_end = datetime.combine(date_obj, datetime.max.time())
        
        transactions = cls.query.filter(
            cls.created_at >= day_start,
            cls.created_at <= day_end
        ).all()
        
        # Calcular totales por tipo
        income_usd = sum(
            t.amount for t in transactions 
            if t.type == TransactionType.INCOME and t.currency_code == 'USD'
        )
        
        expense_usd = sum(
            t.amount for t in transactions 
            if t.type == TransactionType.EXPENSE and t.currency_code == 'USD'
        )
        
        fees_usd = sum(
            t.amount for t in transactions 
            if t.type == TransactionType.FEE and t.currency_code == 'USD'
        )
        
        # Calcular por moneda
        currencies = {}
        for t in transactions:
            if t.currency_code not in currencies:
                currencies[t.currency_code] = {
                    'income': 0,
                    'expense': 0,
                    'fees': 0
                }
            
            if t.type == TransactionType.INCOME:
                currencies[t.currency_code]['income'] += float(t.amount)
            elif t.type == TransactionType.EXPENSE:
                currencies[t.currency_code]['expense'] += float(t.amount)
            elif t.type == TransactionType.FEE:
                currencies[t.currency_code]['fees'] += float(t.amount)
        
        return {
            'date': date_obj.isoformat(),
            'total_transactions': len(transactions),
            'total_income_usd': float(income_usd),
            'total_expense_usd': float(expense_usd),
            'total_fees_usd': float(fees_usd),
            'net_balance_usd': float(income_usd - expense_usd),
            'by_currency': currencies,
            'verified_count': sum(1 for t in transactions if t.is_verified),
            'unverified_count': sum(1 for t in transactions if not t.is_verified)
        }
    
    @classmethod
    def get_balance_by_currency(cls, currency_code: str, 
                                start_date: Optional[date] = None,
                                end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Obtener balance por moneda en un período.
        
        Args:
            currency_code: Código de moneda (USD, VES, etc.)
            start_date: Fecha inicial (default: inicio del mes)
            end_date: Fecha final (default: hoy)
            
        Returns:
            Dict con balance de la moneda
        """
        if end_date is None:
            end_date = date.today()
        
        if start_date is None:
            start_date = date(end_date.year, end_date.month, 1)
        
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.max.time())
        
        transactions = cls.query.filter(
            cls.currency_code == currency_code,
            cls.created_at >= period_start,
            cls.created_at <= period_end
        ).all()
        
        income = sum(
            t.amount for t in transactions 
            if t.type == TransactionType.INCOME
        )
        
        expense = sum(
            t.amount for t in transactions 
            if t.type == TransactionType.EXPENSE
        )
        
        fees = sum(
            t.amount for t in transactions 
            if t.type == TransactionType.FEE
        )
        
        return {
            'currency_code': currency_code,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_income': float(income),
            'total_expense': float(expense),
            'total_fees': float(fees),
            'net_balance': float(income - expense),
            'transaction_count': len(transactions)
        }
    
    @classmethod
    def get_unverified_transactions(cls, limit: Optional[int] = None) -> List['Transaction']:
        """
        Obtener transacciones sin verificar.
        
        Args:
            limit: Máximo de transacciones (None = todas)
            
        Returns:
            Lista de transacciones sin verificar
        """
        query = cls.query.filter_by(is_verified=False).order_by(cls.created_at.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_monthly_summary(cls, year: int, month: int) -> Dict[str, Any]:
        """
        Obtener resumen mensual de transacciones.
        
        Args:
            year: Año
            month: Mes (1-12)
            
        Returns:
            Dict con resumen del mes
        """
        start_date = date(year, month, 1)
        
        # Último día del mes
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.min.time())
        
        transactions = cls.query.filter(
            cls.created_at >= period_start,
            cls.created_at < period_end
        ).all()
        
        # Agrupar por tipo
        by_type = {
            'income': sum(t.amount for t in transactions if t.type == TransactionType.INCOME),
            'expense': sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE),
            'fees': sum(t.amount for t in transactions if t.type == TransactionType.FEE)
        }
        
        # Agrupar por moneda
        by_currency = {}
        for t in transactions:
            if t.currency_code not in by_currency:
                by_currency[t.currency_code] = 0
            by_currency[t.currency_code] += float(t.amount)
        
        return {
            'year': year,
            'month': month,
            'total_transactions': len(transactions),
            'by_type': {k: float(v) for k, v in by_type.items()},
            'by_currency': by_currency,
            'verified_count': sum(1 for t in transactions if t.is_verified),
            'unverified_count': sum(1 for t in transactions if not t.is_verified)
        }
    
    @classmethod
    def get_total_fees_period(cls, start_date: date, end_date: date) -> float:
        """
        Obtener total de comisiones en un período.
        
        Args:
            start_date: Fecha inicial
            end_date: Fecha final
            
        Returns:
            Total de comisiones en USD
        """
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.max.time())
        
        fees = cls.query.filter(
            cls.type == TransactionType.FEE,
            cls.currency_code == 'USD',
            cls.created_at >= period_start,
            cls.created_at <= period_end
        ).all()
        
        return float(sum(t.amount for t in fees))
