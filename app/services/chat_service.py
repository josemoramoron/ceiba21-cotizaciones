"""
Lógica del chat web operador-cliente.

Resuelve (o crea) el ``User`` de canal webchat y la ``ChatConversation`` del
visitante, guarda mensajes y expone lo nuevo para el polling. En la Fase 1 el
bot no responde: el operador atiende manualmente desde el dashboard.
"""
from typing import List, Optional, Tuple

from app.services.base_service import BaseService
from app.models import db
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage

MAX_MESSAGE_LEN = 2000


class ChatService(BaseService):
    """Chat web: conversaciones y mensajes."""

    @staticmethod
    def country_from_request(request) -> Optional[str]:
        """País del visitante desde el header CF-IPCountry (Cloudflare)."""
        code = request.headers.get('CF-IPCountry')
        if code and len(code) == 2 and code.isalpha():
            return code.upper()
        return None

    @classmethod
    def _resolve_conversation(cls, anon_id: str, web_user, country: Optional[str]
                              ) -> ChatConversation:
        """Obtener o crear la conversación (y su User webchat) del visitante."""
        user, _ = User.find_or_create_from_channel(
            'webchat', anon_id, {'first_name': 'Visitante web'}
        )

        conv = ChatConversation.get_for_anon(anon_id)
        if conv is None:
            conv = ChatConversation(anon_id=anon_id, channel='web')
            conv.user_id = user.id
            conv.bot_paused = True  # operación manual (Fase 1)

        if user.id and conv.user_id is None:
            conv.user_id = user.id
        if country and not conv.country:
            conv.country = country

        if web_user is not None:
            conv.web_user_id = web_user.id
            # Enlazar el WebUser con su User webchat si aún no tiene vínculo
            if getattr(web_user, 'user_id', None) is None and user.id:
                web_user.user_id = user.id
                web_user.save()

        conv.save()
        return conv

    @classmethod
    def post_client_message(cls, anon_id: str, web_user, text: str,
                            country: Optional[str] = None
                            ) -> Tuple[Optional[ChatConversation], Optional[ChatMessage]]:
        """
        Guardar un mensaje entrante del cliente.

        Args:
            anon_id: Id de sesión anónima del visitante.
            web_user: WebUser si está logueado, o None.
            text: Contenido del mensaje.
            country: País (CF-IPCountry) si se pudo determinar.

        Returns:
            Tupla (conversación, mensaje) o (None, None) si el texto es inválido.
        """
        text = (text or '').strip()
        if not text:
            return None, None
        text = text[:MAX_MESSAGE_LEN]

        conv = cls._resolve_conversation(anon_id, web_user, country)

        msg = ChatMessage(conversation_id=conv.id, sender='client', body=text)
        msg.save()

        conv.touch(for_operator=True)
        conv.save()

        cls.log_info(f"Chat: mensaje de cliente en conversación {conv.id}")
        return conv, msg

    @classmethod
    def get_new_for_client(cls, conversation_id: int, after_id: int
                           ) -> List[dict]:
        """Mensajes de operador/bot nuevos (para el polling del widget)."""
        msgs = ChatMessage.get_since(conversation_id, after_id)
        return [m.to_dict() for m in msgs if m.sender != 'client']

    @classmethod
    def history(cls, conversation_id: int) -> List[dict]:
        """Todos los mensajes de una conversación (para abrir el hilo)."""
        msgs = ChatMessage.get_since(conversation_id, 0)
        return [m.to_dict() for m in msgs]

    # ── Operador ───────────────────────────────────────────────────────────

    @classmethod
    def list_conversations(cls, limit: int = 50) -> List[dict]:
        """Conversaciones ordenadas por actividad reciente (para el panel)."""
        convs = (
            ChatConversation.query
            .order_by(ChatConversation.last_message_at.desc().nullslast())
            .limit(limit)
            .all()
        )
        return [{
            'id': c.id,
            'name': c.display_name,
            'country': c.country,
            'unread': c.unread_for_operator or 0,
            'bot_paused': c.bot_paused,
            'is_client': c.web_user_id is not None,
            'last_message_at': (
                c.last_message_at.isoformat() if c.last_message_at else None
            ),
        } for c in convs]

    @classmethod
    def mark_read_by_operator(cls, conversation_id: int) -> None:
        """Poner a cero los no leídos de una conversación."""
        conv = ChatConversation.query.get(conversation_id)
        if conv is not None:
            conv.unread_for_operator = 0
            conv.save()

    @classmethod
    def operator_reply(cls, conversation_id: int, operator_id: int,
                       text: str) -> Optional[ChatMessage]:
        """
        Guardar la respuesta del operador y notificar al cliente por push.

        Args:
            conversation_id: Conversación destino.
            operator_id: Operador que responde.
            text: Contenido del mensaje.

        Returns:
            El mensaje creado, o None si el texto es inválido.
        """
        text = (text or '').strip()
        if not text:
            return None
        text = text[:MAX_MESSAGE_LEN]

        conv = ChatConversation.query.get(conversation_id)
        if conv is None:
            return None

        msg = ChatMessage(
            conversation_id=conv.id, sender='operator',
            body=text, operator_id=operator_id,
        )
        msg.save()

        conv.last_message_at = msg.created_at
        conv.unread_for_operator = 0
        conv.save()

        cls._notify_client(conv, text)
        return msg

    @classmethod
    def _notify_client(cls, conv: ChatConversation, text: str) -> None:
        """Enviar push al cliente (logueado o anónimo). Best-effort."""
        try:
            from app.services.push_service import PushService
            preview = text[:80]
            if conv.web_user_id:
                PushService.send_to_user(
                    conv.web_user_id, 'Ceiba21', preview, url='/cuenta')
            elif conv.anon_id:
                PushService.send_to_anon(
                    conv.anon_id, 'Ceiba21', preview, url='/')
        except Exception as exc:
            cls.log_error("Error al notificar respuesta de chat", exc)

    @classmethod
    def set_bot_paused(cls, conversation_id: int, paused: bool) -> bool:
        """Pausar o reanudar el bot en una conversación concreta."""
        conv = ChatConversation.query.get(conversation_id)
        if conv is None:
            return False
        conv.bot_paused = bool(paused)
        return conv.save()

    @classmethod
    def is_bot_active_for(cls, conv: ChatConversation) -> bool:
        """True si el bot debe responder en esa conversación (Fase 2).

        El bot responde solo si no hay pausa global ni pausa por conversación.
        """
        from app.services.system_config_service import SystemConfigService
        if SystemConfigService.get_webchat_bot_paused():
            return False
        return not conv.bot_paused

