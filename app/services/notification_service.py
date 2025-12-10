"""
Servicio de notificaciones.
Maneja envío de notificaciones a usuarios y operadores usando canales.
"""
from app.services.base_service import BaseService
from app.models import User, Operator, Order, Message
from app.channels import ChannelFactory
from typing import Optional, Dict, Any, Tuple


class NotificationService(BaseService):
    """
    Servicio para gestión de notificaciones.
    
    Responsabilidades:
    - Enviar notificaciones a usuarios
    - Enviar notificaciones a operadores
    - Guardar historial de mensajes
    
    Nota: Versión básica. En fases futuras se integrará con canales
    (Telegram, WhatsApp, WebChat).
    """
    
    @classmethod
    def create_message(cls, user_id: int, channel: str, content: str,
                      sender_type: str, message_type: str = 'text',
                      order_id: Optional[int] = None,
                      operator_id: Optional[int] = None,
                      attachment_url: Optional[str] = None) -> Tuple[bool, str, Optional[Message]]:
        """
        Crear y guardar un mensaje.
        
        Args:
            user_id: ID del usuario
            channel: Canal (telegram, whatsapp, webchat, app)
            content: Contenido del mensaje
            sender_type: Tipo de remitente (user, bot, operator)
            message_type: Tipo de mensaje (text, image, document)
            order_id: ID de orden asociada (opcional)
            operator_id: ID del operador (si sender_type='operator')
            attachment_url: URL del adjunto (opcional)
            
        Returns:
            Tupla (success, message_text, message_obj)
        """
        try:
            message = Message.create_message(
                user_id=user_id,
                channel=channel,
                content=content,
                sender_type=sender_type,
                message_type=message_type,
                order_id=order_id,
                operator_id=operator_id,
                attachment_url=attachment_url
            )
            
            cls.log_info(f"Mensaje creado: {sender_type} -> user {user_id}")
            return True, "Mensaje creado exitosamente", message
            
        except Exception as e:
            cls.log_error("Error al crear mensaje", e)
            return False, f"Error al crear mensaje: {str(e)}", None
    
    @classmethod
    def notify_order_created(cls, order: Order) -> Tuple[bool, str]:
        """
        Notificar creación de orden (placeholder).
        
        En fases futuras enviará notificación real al usuario.
        
        Args:
            order: Orden creada
            
        Returns:
            Tupla (success, message)
        """
        try:
            # TODO: Integrar con canales para envío real
            cls.log_info(f"Notificación de orden creada: {order.reference}")
            return True, "Notificación enviada (simulated)"
            
        except Exception as e:
            cls.log_error("Error al notificar orden creada", e)
            return False, f"Error: {str(e)}"
    
    @classmethod
    def notify_order_submitted(cls, order: Order) -> Tuple[bool, str]:
        """
        Notificar que orden fue enviada para verificación.
        
        Args:
            order: Orden enviada
            
        Returns:
            Tupla (success, message)
        """
        try:
            # TODO: Integrar con canales
            cls.log_info(f"Notificación de orden enviada: {order.reference}")
            return True, "Notificación enviada (simulated)"
            
        except Exception as e:
            cls.log_error("Error al notificar orden enviada", e)
            return False, f"Error: {str(e)}"
    
    @classmethod
    def notify_order_assigned(cls, order: Order) -> Tuple[bool, str]:
        """
        Notificar que orden fue asignada a operador.
        
        Args:
            order: Orden asignada
            
        Returns:
            Tupla (success, message)
        """
        try:
            # TODO: Integrar con canales
            cls.log_info(f"Notificación de orden asignada: {order.reference}")
            return True, "Notificación enviada (simulated)"
            
        except Exception as e:
            cls.log_error("Error al notificar orden asignada", e)
            return False, f"Error: {str(e)}"
    
    @classmethod
    def notify_order_completed(cls, order: Order) -> Tuple[bool, str]:
        """
        Notificar que orden fue completada.
        
        Args:
            order: Orden completada
            
        Returns:
            Tupla (success, message)
        """
        try:
            # TODO: Integrar con canales
            cls.log_info(f"Notificación de orden completada: {order.reference}")
            return True, "Notificación enviada (simulated)"
            
        except Exception as e:
            cls.log_error("Error al notificar orden completada", e)
            return False, f"Error: {str(e)}"
    
    @classmethod
    def notify_order_cancelled(cls, order: Order, reason: str) -> Tuple[bool, str]:
        """
        Notificar que orden fue cancelada.
        
        Args:
            order: Orden cancelada
            reason: Razón de cancelación
            
        Returns:
            Tupla (success, message)
        """
        try:
            # TODO: Integrar con canales
            cls.log_info(f"Notificación de orden cancelada: {order.reference} - {reason}")
            return True, "Notificación enviada (simulated)"
            
        except Exception as e:
            cls.log_error("Error al notificar orden cancelada", e)
            return False, f"Error: {str(e)}"
    
    @classmethod
    def notify_new_order_to_operators(cls, order: Order) -> Tuple[bool, str]:
        """
        Notificar a operadores disponibles sobre nueva orden.
        
        Args:
            order: Nueva orden pendiente
            
        Returns:
            Tupla (success, message)
        """
        try:
            # Obtener operadores disponibles
            available_operators = Operator.get_available_operators()
            
            if not available_operators:
                cls.log_warning("No hay operadores disponibles para notificar")
                return False, "No hay operadores disponibles"
            
            # TODO: Integrar con canales (Telegram para operadores)
            cls.log_info(f"Notificación a {len(available_operators)} operadores sobre orden {order.reference}")
            return True, f"Notificación enviada a {len(available_operators)} operadores (simulated)"
            
        except Exception as e:
            cls.log_error("Error al notificar operadores", e)
            return False, f"Error: {str(e)}"
    
    @classmethod
    def notify_new_order(cls, order: Order) -> Tuple[bool, str]:
        """
        Alias para notify_new_order_to_operators.
        
        Notificar a operadores sobre nueva orden pendiente.
        
        Args:
            order: Nueva orden
            
        Returns:
            Tupla (success, message)
        """
        return cls.notify_new_order_to_operators(order)
    
    @classmethod
    def get_user_messages(cls, user_id: int, order_id: Optional[int] = None,
                         limit: Optional[int] = None) -> list[Dict[str, Any]]:
        """
        Obtener mensajes de un usuario.
        
        Args:
            user_id: ID del usuario
            order_id: Filtrar por orden (opcional)
            limit: Máximo de mensajes (opcional)
            
        Returns:
            Lista de mensajes
        """
        messages = Message.get_conversation(user_id, order_id, limit)
        return [msg.to_dict() for msg in messages]
    
    @classmethod
    def get_unread_count(cls, operator_id: Optional[int] = None) -> int:
        """
        Obtener cantidad de mensajes sin leer.
        
        Args:
            operator_id: Filtrar por operador (opcional)
            
        Returns:
            Número de mensajes sin leer
        """
        return Message.get_unread_count(operator_id)
    
    @classmethod
    def mark_messages_as_read(cls, user_id: int, order_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Marcar mensajes como leídos.
        
        Args:
            user_id: ID del usuario
            order_id: ID de la orden (opcional)
            
        Returns:
            Tupla (success, message)
        """
        try:
            count = Message.mark_conversation_as_read(user_id, order_id)
            return True, f"{count} mensajes marcados como leídos"
            
        except Exception as e:
            cls.log_error("Error al marcar mensajes como leídos", e)
            return False, f"Error: {str(e)}"
