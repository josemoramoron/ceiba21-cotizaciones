"""
Modelo de orden de cambio de divisas.
Entidad central del negocio con máquina de estados.
"""
from app.models import db
from app.models.base import BaseModel
from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple


class OrderStatus(Enum):
    """
    Estados de una orden.
    
    Flujo normal:
    DRAFT → PENDING → IN_PROCESS → COMPLETED
    
    Puede cancelarse desde cualquier estado.
    """
    DRAFT = 'draft'              # Usuario completando datos
    PENDING = 'pending'          # Esperando verificación del operador
    IN_PROCESS = 'in_process'    # Operador procesando
    COMPLETED = 'completed'      # Completada exitosamente
    CANCELLED = 'cancelled'      # Cancelada


class Order(BaseModel):
    """
    Orden de cambio de divisas.
    
    Entidad CENTRAL del negocio. Representa una transacción completa.
    
    Attributes:
        reference: Referencia única (ORD-YYYYMMDD-XXX)
        user_id: ID del usuario que creó la orden
        operator_id: ID del operador asignado (nullable)
        currency_id: Moneda involucrada
        payment_method_from_id: Método de pago de origen (cliente paga con)
        payment_method_to_id: Método de pago destino (cliente recibe en)
        amount_usd: Monto en USD
        amount_local: Monto en moneda local
        fee_usd: Comisión en USD
        net_usd: Monto neto en USD (después de comisión)
        exchange_rate: Tasa de cambio usada
        client_payment_data: JSON con datos de pago del cliente
        payment_proof_url: URL del comprobante enviado por cliente
        operator_proof_url: URL del comprobante enviado por operador
        status: Estado actual de la orden
        channel: Canal de origen (telegram, whatsapp, webchat, app)
        channel_chat_id: ID del chat en el canal
        submitted_at: Timestamp de envío
        assigned_at: Timestamp de asignación a operador
        completed_at: Timestamp de completado
        cancelled_at: Timestamp de cancelación
        cancellation_reason: Razón de cancelación
        operator_notes: Notas del operador
    """
    
    __tablename__ = 'orders'
    
    # Identificación
    reference = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Relaciones
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'), nullable=True, index=True)
    
    # Referencias a Currency y PaymentMethod
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    payment_method_from_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'), nullable=False)
    payment_method_to_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'), nullable=False)
    
    # Datos financieros (snapshot al momento de crear)
    amount_usd = db.Column(db.Numeric(12, 2), nullable=False)
    amount_local = db.Column(db.Numeric(15, 2), nullable=False)
    fee_usd = db.Column(db.Numeric(10, 2), nullable=False)
    net_usd = db.Column(db.Numeric(12, 2), nullable=False)
    exchange_rate = db.Column(db.Numeric(10, 4), nullable=False)
    
    # Datos del cliente (JSON flexible)
    client_payment_data = db.Column(db.JSON, nullable=False)
    
    # Comprobantes
    payment_proof_url = db.Column(db.String(500))
    operator_proof_url = db.Column(db.String(500))
    
    # Estado
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.DRAFT, nullable=False, index=True)
    
    # Canal de origen
    channel = db.Column(db.String(20), nullable=False, default='telegram')
    channel_chat_id = db.Column(db.String(100))
    
    # Timestamps específicos
    submitted_at = db.Column(db.DateTime)
    assigned_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Notas
    cancellation_reason = db.Column(db.Text)
    operator_notes = db.Column(db.Text)
    
    # Relaciones (con back_populates)
    user = db.relationship('User', foreign_keys=[user_id], backref='orders')
    operator = db.relationship('Operator', foreign_keys=[operator_id], backref='assigned_orders')
    currency = db.relationship('Currency', foreign_keys=[currency_id])
    payment_method_from = db.relationship('PaymentMethod', foreign_keys=[payment_method_from_id])
    payment_method_to = db.relationship('PaymentMethod', foreign_keys=[payment_method_to_id])
    
    # Relaciones que se definirán en otros modelos
    # transactions = db.relationship('Transaction', back_populates='order', cascade='all, delete-orphan')
    # messages = db.relationship('Message', back_populates='order')
    
    def __repr__(self) -> str:
        """Representación de la orden"""
        return f"<Order {self.reference} - {self.status.value}>"
    
    # Propiedades para acceder fácilmente a datos del cliente
    @property
    def client_phone(self) -> Optional[str]:
        """Obtener teléfono del cliente desde JSON"""
        return self.client_payment_data.get('phone') if self.client_payment_data else None
    
    @property
    def client_bank(self) -> Optional[str]:
        """Obtener banco del cliente desde JSON"""
        return self.client_payment_data.get('bank') if self.client_payment_data else None
    
    @property
    def client_account(self) -> Optional[str]:
        """Obtener cuenta del cliente desde JSON"""
        return self.client_payment_data.get('account') if self.client_payment_data else None
    
    @property
    def client_holder(self) -> Optional[str]:
        """Obtener titular del cliente desde JSON"""
        return self.client_payment_data.get('holder') if self.client_payment_data else None
    
    @property
    def client_dni(self) -> Optional[str]:
        """Obtener DNI del cliente desde JSON"""
        return self.client_payment_data.get('dni') if self.client_payment_data else None
    
    @property
    def client_proof_url(self) -> Optional[str]:
        """Alias para payment_proof_url"""
        return self.payment_proof_url
    
    @staticmethod
    def generate_reference(date_obj: Optional[date] = None) -> str:
        """
        Generar referencia única para orden.
        
        Formato: ORD-YYYYMMDD-XXX
        
        Args:
            date_obj: Fecha para la referencia (default: hoy)
            
        Returns:
            Referencia única
            
        Example:
            >>> Order.generate_reference()
            'ORD-20250104-001'
        """
        if date_obj is None:
            date_obj = date.today()
        
        date_str = date_obj.strftime('%Y%m%d')
        
        # Contar órdenes del día
        today_start = datetime.combine(date_obj, datetime.min.time())
        today_end = datetime.combine(date_obj, datetime.max.time())
        
        count = Order.query.filter(
            Order.created_at >= today_start,
            Order.created_at <= today_end
        ).count()
        
        # Siguiente número
        next_num = count + 1
        
        return f"ORD-{date_str}-{next_num:03d}"
    
    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """
        Verificar si se puede transicionar al nuevo estado.
        
        Transiciones válidas:
        - DRAFT → PENDING (cliente envía comprobante)
        - PENDING → IN_PROCESS (operador toma orden)
        - PENDING → CANCELLED (se rechaza)
        - IN_PROCESS → COMPLETED (operador confirma pago)
        - IN_PROCESS → CANCELLED (hay problema)
        - Cualquier estado → CANCELLED (siempre se puede cancelar)
        
        Args:
            new_status: Nuevo estado deseado
            
        Returns:
            bool: True si la transición es válida
        """
        # Siempre se puede cancelar
        if new_status == OrderStatus.CANCELLED:
            return True
        
        # No se puede cambiar desde COMPLETED o CANCELLED
        if self.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
            return False
        
        # Transiciones válidas
        valid_transitions = {
            OrderStatus.DRAFT: [OrderStatus.PENDING],
            OrderStatus.PENDING: [OrderStatus.IN_PROCESS, OrderStatus.CANCELLED],
            OrderStatus.IN_PROCESS: [OrderStatus.COMPLETED, OrderStatus.CANCELLED]
        }
        
        return new_status in valid_transitions.get(self.status, [])
    
    def transition_to(self, new_status: OrderStatus, operator: Optional['Operator'] = None,
                     reason: Optional[str] = None) -> Tuple[bool, str]:
        """
        Transicionar orden a nuevo estado.
        
        Args:
            new_status: Nuevo estado
            operator: Operador que ejecuta la transición
            reason: Razón del cambio (requerido para CANCELLED)
            
        Returns:
            Tupla (success, message)
            
        Example:
            >>> success, msg = order.transition_to(OrderStatus.IN_PROCESS, operator)
        """
        if not self.can_transition_to(new_status):
            return False, f"No se puede cambiar de {self.status.value} a {new_status.value}"
        
        old_status = self.status
        self.status = new_status
        
        # Actualizar timestamps y datos según el estado
        if new_status == OrderStatus.PENDING:
            self.submitted_at = datetime.utcnow()
        
        elif new_status == OrderStatus.IN_PROCESS:
            self.assigned_at = datetime.utcnow()
            if operator:
                self.operator_id = operator.id
        
        elif new_status == OrderStatus.COMPLETED:
            self.completed_at = datetime.utcnow()
            # Crear transacciones automáticamente
            self._create_transactions()
            # Actualizar estadísticas de usuario
            if self.user:
                self.user.update_stats()
            # Actualizar estadísticas de operador
            if self.operator:
                processing_time = None
                if self.assigned_at:
                    processing_time = int((datetime.utcnow() - self.assigned_at).total_seconds())
                self.operator.update_stats(processing_time)
        
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = datetime.utcnow()
            self.cancellation_reason = reason or "Sin razón especificada"
        
        if self.save():
            return True, f"Orden cambiada de {old_status.value} a {new_status.value}"
        else:
            return False, "Error al guardar cambios"
    
    def _create_transactions(self) -> None:
        """
        Crear transacciones contables automáticamente.
        
        Se llama cuando la orden se COMPLETA.
        """
        try:
            from app.models.transaction import Transaction, TransactionType
            
            # 1. INCOME: Lo que el cliente nos pagó
            Transaction(
                order_id=self.id,
                type=TransactionType.INCOME,
                amount=self.amount_usd,
                currency_code='USD',
                payment_method_id=self.payment_method_from_id,
                description=f"Ingreso de {self.reference}"
            ).save()
            
            # 2. FEE: Nuestra comisión
            Transaction(
                order_id=self.id,
                type=TransactionType.FEE,
                amount=self.fee_usd,
                currency_code='USD',
                payment_method_id=self.payment_method_from_id,
                description=f"Comisión de {self.reference}"
            ).save()
            
            # 3. EXPENSE: Lo que pagamos al cliente
            Transaction(
                order_id=self.id,
                type=TransactionType.EXPENSE,
                amount=self.amount_local,
                currency_code=self.currency.code if self.currency else 'USD',
                payment_method_id=self.payment_method_to_id,
                description=f"Pago al cliente {self.reference}"
            ).save()
            
        except Exception as e:
            print(f"Error al crear transacciones para Order {self.reference}: {str(e)}")
    
    def get_summary_for_notification(self) -> Dict[str, Any]:
        """
        Obtener resumen de la orden para notificaciones.
        
        Returns:
            Dict con información resumida
        """
        return {
            'reference': self.reference,
            'amount_usd': float(self.amount_usd),
            'amount_local': float(self.amount_local),
            'currency': self.currency.code if self.currency else 'N/A',
            'fee_usd': float(self.fee_usd),
            'net_usd': float(self.net_usd),
            'exchange_rate': float(self.exchange_rate),
            'status': self.status.value,
            'channel': self.channel,
            'user_name': self.user.get_display_name() if self.user else 'N/A',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convertir orden a diccionario.
        
        Args:
            include_relationships: Si True, incluye datos relacionados
            
        Returns:
            Dict con datos de la orden
        """
        data = super().to_dict()
        
        # Convertir status enum a string
        data['status'] = self.status.value
        
        if include_relationships:
            data['user'] = self.user.to_dict() if self.user else None
            data['operator'] = self.operator.to_dict() if self.operator else None
            data['currency'] = self.currency.to_dict() if self.currency else None
            data['payment_method_from'] = self.payment_method_from.to_dict() if self.payment_method_from else None
            data['payment_method_to'] = self.payment_method_to.to_dict() if self.payment_method_to else None
        
        return data
    
    @classmethod
    def get_by_reference(cls, reference: str) -> Optional['Order']:
        """
        Buscar orden por referencia.
        
        Args:
            reference: Referencia de la orden
            
        Returns:
            Orden encontrada o None
        """
        return cls.query.filter_by(reference=reference).first()
    
    @classmethod
    def get_by_status(cls, status: OrderStatus, limit: Optional[int] = None) -> List['Order']:
        """
        Obtener órdenes por estado.
        
        Args:
            status: Estado a filtrar
            limit: Máximo de órdenes (None = todas)
            
        Returns:
            Lista de órdenes
        """
        query = cls.query.filter_by(status=status).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_pending_orders(cls) -> List['Order']:
        """
        Obtener órdenes pendientes de atención.
        
        Returns:
            Lista de órdenes pendientes
        """
        return cls.query.filter_by(status=OrderStatus.PENDING).order_by(cls.created_at.asc()).all()
    
    @classmethod
    def get_operator_orders(cls, operator_id: int, status: Optional[OrderStatus] = None) -> List['Order']:
        """
        Obtener órdenes de un operador.
        
        Args:
            operator_id: ID del operador
            status: Filtrar por estado (opcional)
            
        Returns:
            Lista de órdenes del operador
        """
        query = cls.query.filter_by(operator_id=operator_id)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_daily_stats(cls, date_obj: Optional[date] = None) -> Dict[str, Any]:
        """
        Obtener estadísticas del día.
        
        Args:
            date_obj: Fecha (default: hoy)
            
        Returns:
            Dict con estadísticas del día
        """
        if date_obj is None:
            date_obj = date.today()
        
        day_start = datetime.combine(date_obj, datetime.min.time())
        day_end = datetime.combine(date_obj, datetime.max.time())
        
        orders = cls.query.filter(
            cls.created_at >= day_start,
            cls.created_at <= day_end
        ).all()
        
        total = len(orders)
        completed = sum(1 for o in orders if o.status == OrderStatus.COMPLETED)
        cancelled = sum(1 for o in orders if o.status == OrderStatus.CANCELLED)
        pending = sum(1 for o in orders if o.status == OrderStatus.PENDING)
        in_process = sum(1 for o in orders if o.status == OrderStatus.IN_PROCESS)
        
        total_volume = sum(o.amount_usd for o in orders if o.status == OrderStatus.COMPLETED)
        total_fees = sum(o.fee_usd for o in orders if o.status == OrderStatus.COMPLETED)
        
        return {
            'date': date_obj.isoformat(),
            'total': total,
            'completed': completed,
            'cancelled': cancelled,
            'pending': pending,
            'in_process': in_process,
            'total_volume_usd': float(total_volume),
            'total_fees_usd': float(total_fees)
        }
    
    @classmethod
    def get_pending_count(cls) -> int:
        """
        Contar órdenes pendientes.
        
        Returns:
            Número de órdenes pendientes
        """
        return cls.query.filter_by(status=OrderStatus.PENDING).count()
    
    @classmethod
    def get_user_orders(cls, user_id: int, limit: Optional[int] = None) -> List['Order']:
        """
        Obtener órdenes de un usuario.
        
        Args:
            user_id: ID del usuario
            limit: Máximo de órdenes (None = todas)
            
        Returns:
            Lista de órdenes del usuario
        """
        query = cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
