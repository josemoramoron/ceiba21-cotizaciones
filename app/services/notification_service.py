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
    - Enviar notificaciones a usuarios (por el canal de la orden)
    - Enviar notificaciones a operadores
    - Guardar historial de mensajes

    Nota: las notificaciones al cliente se despachan de forma agnóstica al
    canal mediante ``ChannelFactory`` (telegram, whatsapp, webchat, ...).
    La notificación a operadores sigue pendiente de integración con su canal.
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
    def _send_to_order_channel(cls, order: Order, message_text: str) -> Tuple[bool, str]:
        """
        Enviar un mensaje al cliente por el canal de la orden.

        Despacha al canal correcto (telegram, whatsapp, webchat, ...) usando
        ``ChannelFactory``, de modo que el servicio no quede acoplado a un canal
        específico. Valida que la orden tenga canal y chat_id, y que el canal
        esté disponible.

        Args:
            order: Orden cuyo ``channel`` y ``channel_chat_id`` definen el destino.
            message_text: Texto del mensaje a enviar.

        Returns:
            Tupla (success, message).
        """
        if not order.channel or not order.channel_chat_id:
            cls.log_warning(
                f"No se puede notificar orden {order.reference}: sin canal o chat_id"
            )
            return False, "Canal no disponible"

        try:
            channel = ChannelFactory.get_channel(order.channel)
        except ValueError as e:
            cls.log_error(f"Canal desconocido para orden {order.reference}", e)
            return False, f"Canal desconocido: {order.channel}"

        if not channel or not channel.is_available():
            cls.log_warning(
                f"Canal '{order.channel}' no disponible para orden {order.reference}"
            )
            return False, "Canal no disponible"

        success, result = channel.send_message(
            recipient_id=order.channel_chat_id,
            text=message_text,
            parse_mode='HTML'
        )

        if success:
            cls.log_info(
                f"Notificación enviada para orden {order.reference} vía '{order.channel}'"
            )
            return True, "Notificación enviada"

        cls.log_error(f"Error al enviar notificación: {result}", None)
        return False, f"Error al enviar: {result}"

    @classmethod
    def _push_to_order_client(cls, order: Order, title: str, body: str) -> None:
        """
        Enviar Web Push a los clientes (WebUser) vinculados al usuario de la orden.

        Best-effort: si no hay WebUser vinculado o el envío falla, no interrumpe
        el flujo de notificación por canal conversacional.

        Args:
            order: Orden cuyo cambio de estado se notifica.
            title: Título de la notificación push.
            body: Cuerpo de la notificación push.
        """
        try:
            from app.models.web_user import WebUser
            from app.services.push_service import PushService
            web_users = WebUser.query.filter_by(
                user_id=order.user_id, is_active=True
            ).all()
            for web_user in web_users:
                PushService.send_to_user(web_user.id, title, body, url='/cuenta')
        except Exception as exc:
            cls.log_error("Error al enviar push de orden", exc)

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
            cls._push_to_order_client(
                order,
                'Ceiba21',
                f"Recibimos tu orden {order.reference}, está en verificación.",
            )
            cls.log_info(f"Notificación de orden enviada: {order.reference}")
            return True, "Notificación enviada"

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
            operator_name = order.operator.full_name if order.operator else "un operador"
            currency_code = order.currency.code if order.currency else ''

            message_text = f"""
✅ <b>¡Tu orden ha sido tomada!</b>

Tu orden <b>{order.reference}</b> está siendo procesada por {operator_name}.

💵 Monto: ${order.amount_usd:.2f} USD → {order.amount_local:.2f} {currency_code}

⏳ <i>Estamos verificando tu pago y procesando la transferencia.</i>

Te notificaremos cuando esté completada.
            """.strip()

            cls._push_to_order_client(
                order,
                'Ceiba21',
                f"Tu orden {order.reference} está siendo procesada ✅",
            )
            return cls._send_to_order_channel(order, message_text)

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
            currency_code = order.currency.code if order.currency else ''
            payment_method = order.payment_method_to.name if order.payment_method_to else 'tu cuenta'

            message_text = f"""
🎉 <b>¡Pago Completado Exitosamente!</b>

Tu orden <b>{order.reference}</b> ha sido procesada.

✅ <b>Detalles:</b>
💵 Monto enviado: <b>{order.amount_local:.2f} {currency_code}</b>
📤 Método: {payment_method}
💰 Total USD: ${order.amount_usd:.2f}

<i>El dinero debería reflejarse en tu cuenta en los próximos minutos.</i>

¡Gracias por usar nuestro servicio! 🌳
            """.strip()

            cls._push_to_order_client(
                order,
                'Ceiba21',
                f"🎉 Tu orden {order.reference} fue completada.",
            )
            return cls._send_to_order_channel(order, message_text)

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
            message_text = f"""
❌ <b>Orden Cancelada</b>

Lo sentimos, tu orden <b>{order.reference}</b> ha sido cancelada.

📝 <b>Motivo:</b>
<i>{reason}</i>

💵 Monto: ${order.amount_usd:.2f} USD

Si tienes alguna duda, por favor contáctanos.

Puedes crear una nueva orden cuando desees. 🌳
            """.strip()

            cls._push_to_order_client(
                order,
                'Ceiba21',
                f"Tu orden {order.reference} fue cancelada.",
            )
            return cls._send_to_order_channel(order, message_text)

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

            # TODO (Fase de gestión de admins): enviar la notificación real al
            # canal de operadores según rol (admin/agente). De momento se registra.
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
