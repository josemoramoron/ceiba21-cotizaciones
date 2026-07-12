"""
Envío de notificaciones Web Push (pywebpush + VAPID).

Destinatarios soportados: clientes logueados (WebUser), visitantes anónimos
(anon_id del chat) y operadores/admins (avisos del panel).
"""
import json

from flask import current_app
from py_vapid import Vapid01
from pywebpush import webpush, WebPushException

from app.services.base_service import BaseService
from app.models.push_subscription import PushSubscription


class PushService(BaseService):
    """Envía notificaciones Web Push."""

    @staticmethod
    def _vapid_private_key() -> Vapid01:
        """Reconstruir la clave VAPID privada (raw base64url) desde la config."""
        raw = current_app.config.get('VAPID_PRIVATE_KEY')
        return Vapid01.from_raw(raw.encode())

    @classmethod
    def _send_one(cls, sub: PushSubscription, payload: str) -> bool:
        """Enviar a una suscripción; desactivarla si el endpoint está muerto."""
        try:
            webpush(
                subscription_info=sub.to_subscription_info(),
                data=payload,
                vapid_private_key=cls._vapid_private_key(),
                vapid_claims={
                    'sub': f"mailto:{current_app.config.get('VAPID_CLAIM_EMAIL')}"
                },
            )
            return True
        except WebPushException as exc:
            status = getattr(exc.response, 'status_code', None)
            if status in (404, 410):
                PushSubscription.deactivate_by_endpoint(sub.endpoint)
            cls.log_error(f"Error enviando push (status={status})", exc)
            return False
        except Exception as exc:
            cls.log_error("Error inesperado enviando push", exc)
            return False

    @classmethod
    def _send_to_subs(cls, subs, title: str, body: str, url: str) -> int:
        """Enviar un payload a una lista de suscripciones."""
        if not current_app.config.get('VAPID_PRIVATE_KEY'):
            cls.log_error("VAPID no configurado: no se envían push")
            return 0
        payload = json.dumps({'title': title, 'body': body, 'url': url})
        sent = 0
        for sub in subs:
            if cls._send_one(sub, payload):
                sent += 1
        return sent

    @classmethod
    def send_to_user(cls, web_user_id: int, title: str, body: str,
                     url: str = '/cuenta') -> int:
        """Enviar a todas las suscripciones activas de un cliente logueado."""
        return cls._send_to_subs(
            PushSubscription.get_active_for_user(web_user_id), title, body, url
        )

    @classmethod
    def send_to_anon(cls, anon_id: str, title: str, body: str,
                     url: str = '/') -> int:
        """Enviar a todas las suscripciones activas de un visitante anónimo."""
        return cls._send_to_subs(
            PushSubscription.get_active_for_anon(anon_id), title, body, url
        )

    @classmethod
    def send_to_operators(cls, title: str, body: str,
                          url: str = '/dashboard/chat/') -> int:
        """Enviar a todos los operadores/admins suscritos (avisos del panel)."""
        return cls._send_to_subs(
            PushSubscription.get_active_for_operators(), title, body, url
        )
