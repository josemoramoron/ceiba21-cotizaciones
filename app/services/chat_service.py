"""
Lógica del chat web operador-cliente.

Resuelve (o crea) el ``User`` de canal webchat y la ``ChatConversation`` del
visitante, guarda mensajes y expone lo nuevo para el polling. En la Fase 1 el
bot no responde: el operador atiende manualmente desde el dashboard.
"""
import html as html_lib
import re
from datetime import datetime
from typing import List, Optional, Tuple

from app.services.base_service import BaseService
from app.models import db
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage
from app.utils.fecha import hora_co

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
            # La pausa por conversación arranca desactivada: quien manda
            # por defecto es el interruptor global (system_config).
            conv.bot_paused = False

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

        if cls.is_bot_active_for(conv):
            cls._bot_reply(conv, text)
        else:
            cls._notify_operators(conv, text)

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
            'last_time': cls._short_time(c.last_message_at),
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
        # El operador toma el control: el bot deja de hablar en esta conversación
        conv.bot_paused = True
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

    # ── Utilidades de presentación y estado efímero ────────────────────────

    @staticmethod
    def _short_time(dt) -> str:
        """Hora compacta en zona Colombia: 'HH:MM' si es hoy, si no 'dd/mm'."""
        if dt is None:
            return ''
        hoy = hora_co(datetime.utcnow(), '%d/%m')
        return (
            hora_co(dt, '%H:%M') if hora_co(dt, '%d/%m') == hoy
            else hora_co(dt, '%d/%m')
        )

    @classmethod
    def _notify_operators(cls, conv: ChatConversation, text: str) -> None:
        """Avisar por push a los operadores de un mensaje entrante. Best-effort."""
        try:
            from app.services.push_service import PushService
            PushService.send_to_operators(
                title=f"Chat: {conv.display_name}",
                body=text[:80],
                url='/dashboard/chat/',
            )
        except Exception as exc:
            cls.log_error("Error al notificar chat a operadores", exc)

    # Indicador "escribiendo": estado efímero en caché (Redis), con TTL.
    _TYPING_TTL = 6

    @staticmethod
    def _typing_key(conversation_id: int, who: str) -> str:
        """Clave de caché del indicador de escritura."""
        return f"chat:typing:{conversation_id}:{who}"

    @classmethod
    def set_typing(cls, conversation_id: int, who: str) -> None:
        """Marcar que 'client' u 'operator' está escribiendo (expira solo)."""
        from app.services.cache_service import CacheService
        CacheService.set(cls._typing_key(conversation_id, who), 1,
                         ttl=cls._TYPING_TTL)

    @classmethod
    def is_typing(cls, conversation_id: int, who: str) -> bool:
        """True si la otra parte está escribiendo ahora mismo."""
        from app.services.cache_service import CacheService
        return bool(CacheService.get(cls._typing_key(conversation_id, who)))



    # ── Bot (Fase 2) ───────────────────────────────────────────────────────

    _TAG_RE = re.compile(r'<[^>]+>')

    @classmethod
    def _to_plain_text(cls, text: str) -> str:
        """Convertir el HTML de Telegram (<b>, <i>...) a texto plano para la web."""
        if not text:
            return ''
        limpio = cls._TAG_RE.sub('', text)
        return html_lib.unescape(limpio).strip()

    @classmethod
    def _bot_reply(cls, conv: ChatConversation, text: str
                   ) -> Optional[ChatMessage]:
        """
        Generar y guardar la respuesta del bot para un mensaje del cliente.

        Reutiliza el ConversationHandler que ya opera en Telegram: mantiene su
        propio estado en Redis por ``User.id``, así que el flujo de órdenes es
        el mismo en todos los canales.

        Args:
            conv: Conversación del chat web.
            text: Mensaje del cliente (texto libre o callback_data de un botón).

        Returns:
            El mensaje del bot, o None si no se pudo generar.
        """
        try:
            from app.bot.conversation_handler import ConversationHandler
            from app.models.user import User

            user = User.query.get(conv.user_id) if conv.user_id else None
            if user is None:
                return None

            handler = ConversationHandler()
            respuesta = handler.handle_message(user, text)

            cuerpo = cls._to_plain_text(respuesta.get('text', ''))
            if not cuerpo:
                return None

            bot_msg = ChatMessage(
                conversation_id=conv.id,
                sender='bot',
                body=cuerpo,
                buttons=respuesta.get('buttons') or [],
            )
            bot_msg.save()

            conv.last_message_at = bot_msg.created_at
            conv.save()
            return bot_msg

        except Exception as exc:
            cls.log_error("Error al generar respuesta del bot", exc)
            return None
