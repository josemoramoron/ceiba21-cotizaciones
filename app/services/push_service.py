"""
Envío de notificaciones Web Push (pywebpush + VAPID).

El envío a cada endpoint es una petición HTTP corta al servicio de push del
navegador (FCM/Mozilla/etc.), compatible con los workers sync de Gunicorn.
"""
import json

from flask import current_app
from py_vapid import Vapid01
from pywebpush import webpush, WebPushException

from app.services.base_service import BaseService
from app.models.push_subscription import PushSubscription


class PushService(BaseService):
    """Envía notificaciones Web Push a las suscripciones de un cliente."""

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
            # Errores no-HTTP (p. ej. clave VAPID mal formada): registrar y
            # continuar, para no tumbar la petición con un 500.
            cls.log_error("Error inesperado enviando push", exc)
            return False

    @classmethod
    def send_to_user(cls, web_user_id: int, title: str, body: str,
                     url: str = '/cuenta') -> int:
        """
        Enviar una notificación a todas las suscripciones activas de un cliente.

        Returns:
            Número de envíos exitosos.
        """
        if not current_app.config.get('VAPID_PRIVATE_KEY'):
            cls.log_error("VAPID no configurado: no se envían push")
            return 0

        payload = json.dumps({'title': title, 'body': body, 'url': url})
        sent = 0
        for sub in PushSubscription.get_active_for_user(web_user_id):
            if cls._send_one(sub, payload):
                sent += 1
        return sent
