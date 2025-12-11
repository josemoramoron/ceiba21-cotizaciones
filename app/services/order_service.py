"""
Servicio de gestión de órdenes.
Maneja todo el ciclo de vida de las órdenes de cambio de divisas.
"""
from app.services.base_service import BaseService
from app.models import db, Order, OrderStatus, User, Operator, Currency, PaymentMethod, Transaction
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date


class OrderService(BaseService):
    """
    Servicio para gestión completa de órdenes.
    
    Responsabilidades:
    - Crear órdenes nuevas
    - Gestionar transiciones de estado
    - Asignar operadores
    - Completar/cancelar órdenes
    - Consultar órdenes
    - Estadísticas
    """
    
    @classmethod
    def create_order(cls, user_id: int, currency_id: int,
                    payment_method_from_id: int, payment_method_to_id: int,
                    amount_usd: float, amount_local: float,
                    fee_usd: float, net_usd: float, exchange_rate: float,
                    client_payment_data: Dict[str, Any],
                    channel: str = 'telegram',
                    channel_chat_id: Optional[str] = None) -> Tuple[bool, str, Optional[Order]]:
        """
        Crear una nueva orden.
        
        Args:
            user_id: ID del usuario
            currency_id: ID de la moneda
            payment_method_from_id: Método de pago origen
            payment_method_to_id: Método de pago destino
            amount_usd: Monto en USD
            amount_local: Monto en moneda local
            fee_usd: Comisión
            net_usd: Neto en USD
            exchange_rate: Tasa de cambio
            client_payment_data: Datos de pago del cliente (JSON)
            channel: Canal de origen
            channel_chat_id: ID del chat en el canal
            
        Returns:
            Tupla (success, message, order)
        """
        try:
            # Validar que el usuario existe
            user = User.find_by_id(user_id)
            if not user:
                return False, "Usuario no encontrado", None
            
            # Generar referencia única
            reference = Order.generate_reference()
            
            # Crear orden
            order = Order(
                reference=reference,
                user_id=user_id,
                currency_id=currency_id,
                payment_method_from_id=payment_method_from_id,
                payment_method_to_id=payment_method_to_id,
                amount_usd=amount_usd,
                amount_local=amount_local,
                fee_usd=fee_usd,
                net_usd=net_usd,
                exchange_rate=exchange_rate,
                client_payment_data=client_payment_data,
                channel=channel,
                channel_chat_id=channel_chat_id,
                status=OrderStatus.DRAFT
            )
            
            if cls.save(order):
                cls.log_info(f"Orden {reference} creada para usuario {user_id}")
                return True, f"Orden {reference} creada exitosamente", order
            else:
                return False, "Error al guardar la orden", None
                
        except Exception as e:
            cls.log_error("Error al crear orden", e)
            return False, f"Error al crear orden: {str(e)}", None
    
    @classmethod
    def submit_order(cls, order_id: int, payment_proof_url: Optional[str] = None) -> Tuple[bool, str]:
        """
        Enviar orden para verificación (DRAFT → PENDING).
        
        Args:
            order_id: ID de la orden
            payment_proof_url: URL del comprobante de pago
            
        Returns:
            Tupla (success, message)
        """
        try:
            order = Order.find_by_id(order_id)
            if not order:
                return False, "Orden no encontrada"
            
            if order.status != OrderStatus.DRAFT:
                return False, f"La orden está en estado {order.status.value}, no se puede enviar"
            
            # Actualizar comprobante si se proporciona
            if payment_proof_url:
                order.payment_proof_url = payment_proof_url
            
            # Transicionar a PENDING
            success, message = order.transition_to(OrderStatus.PENDING)
            
            if success:
                cls.log_info(f"Orden {order.reference} enviada para verificación")
            
            return success, message
            
        except Exception as e:
            cls.log_error("Error al enviar orden", e)
            return False, f"Error al enviar orden: {str(e)}"
    
    @classmethod
    def assign_order(cls, order_id: int, operator_id: int) -> Tuple[bool, str, Optional[Order]]:
        """
        Asignar orden a operador (PENDING → IN_PROCESS).
        
        Args:
            order_id: ID de la orden
            operator_id: ID del operador
            
        Returns:
            Tupla (success, message, order)
        """
        try:
            order = Order.find_by_id(order_id)
            if not order:
                return False, "Orden no encontrada", None
            
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return False, "Operador no encontrado", None
            
            if not operator.is_active:
                return False, "Operador no está activo", None
            
            # Transicionar a IN_PROCESS
            success, message = order.transition_to(OrderStatus.IN_PROCESS, operator)
            
            if success:
                cls.log_info(f"Orden {order.reference} asignada a operador {operator.username}")
                # Notificar al cliente
                from app.services.notification_service import NotificationService
                NotificationService.notify_order_assigned(order)
            
            return success, message, order
            
        except Exception as e:
            cls.log_error("Error al asignar orden", e)
            return False, f"Error al asignar orden: {str(e)}", None
    
    @classmethod
    def complete_order(cls, order_id: int, operator_id: int,
                      operator_proof_url: Optional[str] = None,
                      notes: Optional[str] = None) -> Tuple[bool, str, Optional[Order]]:
        """
        Completar orden (IN_PROCESS → COMPLETED).
        
        Genera transacciones automáticamente.
        
        Args:
            order_id: ID de la orden
            operator_id: ID del operador que completa
            operator_proof_url: URL del comprobante del operador
            notes: Notas adicionales
            
        Returns:
            Tupla (success, message, order)
        """
        try:
            order = Order.find_by_id(order_id)
            if not order:
                return False, "Orden no encontrada", None
            
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return False, "Operador no encontrado", None
            
            # Validar que el operador asignado es quien completa
            if order.operator_id != operator_id:
                return False, "Solo el operador asignado puede completar la orden", None
            
            # Actualizar campos opcionales
            if operator_proof_url:
                order.operator_proof_url = operator_proof_url
            if notes:
                order.operator_notes = notes
            
            # Transicionar a COMPLETED (crea transacciones automáticamente)
            success, message = order.transition_to(OrderStatus.COMPLETED, operator)
            
            if success:
                cls.log_info(f"Orden {order.reference} completada por operador {operator.username}")
                # Notificar al cliente
                from app.services.notification_service import NotificationService
                NotificationService.notify_order_completed(order)
            
            return success, message, order
            
        except Exception as e:
            cls.log_error("Error al completar orden", e)
            return False, f"Error al completar orden: {str(e)}", None
    
    @classmethod
    def cancel_order(cls, order_id: int, reason: str,
                    operator_id: Optional[int] = None) -> Tuple[bool, str, Optional[Order]]:
        """
        Cancelar orden (Cualquier estado → CANCELLED).
        
        Args:
            order_id: ID de la orden
            reason: Razón de cancelación
            operator_id: ID del operador que cancela (opcional)
            
        Returns:
            Tupla (success, message, order)
        """
        try:
            order = Order.find_by_id(order_id)
            if not order:
                return False, "Orden no encontrada", None
            
            if order.status == OrderStatus.COMPLETED:
                return False, "No se puede cancelar una orden completada", None
            
            operator = None
            if operator_id:
                operator = Operator.find_by_id(operator_id)
            
            # Transicionar a CANCELLED
            success, message = order.transition_to(OrderStatus.CANCELLED, operator, reason)
            
            if success:
                cls.log_info(f"Orden {order.reference} cancelada: {reason}")
                # Notificar al cliente
                from app.services.notification_service import NotificationService
                NotificationService.notify_order_cancelled(order, reason)
            
            return success, message, order
            
        except Exception as e:
            cls.log_error("Error al cancelar orden", e)
            return False, f"Error al cancelar orden: {str(e)}", None
    
    @classmethod
    def get_order_by_id(cls, order_id: int, include_relationships: bool = False) -> Optional[Dict[str, Any]]:
        """
        Obtener orden por ID.
        
        Args:
            order_id: ID de la orden
            include_relationships: Si se incluyen datos relacionados
            
        Returns:
            Dict con datos de la orden o None
        """
        order = Order.find_by_id(order_id)
        if order:
            return order.to_dict(include_relationships=include_relationships)
        return None
    
    @classmethod
    def get_order_by_reference(cls, reference: str, include_relationships: bool = False) -> Optional[Dict[str, Any]]:
        """
        Obtener orden por referencia.
        
        Args:
            reference: Referencia de la orden
            include_relationships: Si se incluyen datos relacionados
            
        Returns:
            Dict con datos de la orden o None
        """
        order = Order.get_by_reference(reference)
        if order:
            return order.to_dict(include_relationships=include_relationships)
        return None
    
    @classmethod
    def get_pending_orders(cls) -> List[Dict[str, Any]]:
        """
        Obtener órdenes pendientes de atención.
        
        Returns:
            Lista de órdenes pendientes
        """
        orders = Order.get_pending_orders()
        return [order.to_dict(include_relationships=True) for order in orders]
    
    @classmethod
    def get_operator_orders(cls, operator_id: int, status: Optional[OrderStatus] = None) -> List[Dict[str, Any]]:
        """
        Obtener órdenes de un operador.
        
        Args:
            operator_id: ID del operador
            status: Filtrar por estado (opcional)
            
        Returns:
            Lista de órdenes del operador
        """
        orders = Order.get_operator_orders(operator_id, status)
        return [order.to_dict(include_relationships=True) for order in orders]
    
    @classmethod
    def get_user_orders(cls, user_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtener órdenes de un usuario.
        
        Args:
            user_id: ID del usuario
            limit: Máximo de órdenes (None = todas)
            
        Returns:
            Lista de órdenes del usuario
        """
        orders = Order.get_user_orders(user_id, limit)
        return [order.to_dict(include_relationships=True) for order in orders]
    
    @classmethod
    def get_orders_by_status(cls, status: OrderStatus, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtener órdenes por estado.
        
        Args:
            status: Estado a filtrar
            limit: Máximo de órdenes (None = todas)
            
        Returns:
            Lista de órdenes
        """
        orders = Order.get_by_status(status, limit)
        return [order.to_dict(include_relationships=True) for order in orders]
    
    @classmethod
    def get_daily_stats(cls, date_obj: Optional[date] = None) -> Dict[str, Any]:
        """
        Obtener estadísticas del día.
        
        Args:
            date_obj: Fecha (default: hoy)
            
        Returns:
            Dict con estadísticas
        """
        return Order.get_daily_stats(date_obj)
    
    @classmethod
    def get_pending_count(cls) -> int:
        """
        Contar órdenes pendientes.
        
        Returns:
            Número de órdenes pendientes
        """
        return Order.get_pending_count()
    
    @classmethod
    def add_note(cls, order_id: int, note: str, operator_id: int) -> Tuple[bool, str]:
        """
        Agregar nota a una orden.
        
        Args:
            order_id: ID de la orden
            note: Nota a agregar
            operator_id: ID del operador que agrega la nota
            
        Returns:
            Tupla (success, message)
        """
        try:
            order = Order.find_by_id(order_id)
            if not order:
                return False, "Orden no encontrada"
            
            # Agregar nota existente
            current_notes = order.operator_notes or ""
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            operator = Operator.find_by_id(operator_id)
            operator_name = operator.username if operator else f"Operador #{operator_id}"
            
            new_note = f"[{timestamp}] {operator_name}: {note}\n"
            order.operator_notes = current_notes + new_note
            
            if cls.commit():
                return True, "Nota agregada exitosamente"
            else:
                return False, "Error al guardar la nota"
                
        except Exception as e:
            cls.log_error("Error al agregar nota", e)
            return False, f"Error al agregar nota: {str(e)}"
