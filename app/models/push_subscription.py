"""
Suscripción Web Push de un cliente (WebUser).

Cada navegador/dispositivo del cliente produce una suscripción con un endpoint
único y dos claves (p256dh, auth), que se usan para cifrar y enrutar las
notificaciones push.
"""
from typing import Optional

from app.models import db
from app.models.base import BaseModel


class PushSubscription(BaseModel):
    """Suscripción Web Push asociada a un WebUser."""

    __tablename__ = 'push_subscriptions'

    web_user_id = db.Column(
        db.Integer, db.ForeignKey('web_users.id'), nullable=False, index=True
    )
    endpoint = db.Column(db.String(500), unique=True, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    user_agent = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_subscription_info(self) -> dict:
        """Formato de suscripción que espera pywebpush."""
        return {
            'endpoint': self.endpoint,
            'keys': {'p256dh': self.p256dh, 'auth': self.auth},
        }

    @classmethod
    def upsert(cls, web_user_id: int, endpoint: str, p256dh: str,
               auth: str, user_agent: Optional[str] = None
               ) -> Optional['PushSubscription']:
        """
        Crear o actualizar (por endpoint) una suscripción del cliente.

        Returns:
            La suscripción guardada, o None si el guardado falló.
        """
        sub = cls.query.filter_by(endpoint=endpoint).first()
        if sub is None:
            sub = cls(endpoint=endpoint)
        sub.web_user_id = web_user_id
        sub.p256dh = p256dh
        sub.auth = auth
        sub.user_agent = user_agent
        sub.is_active = True
        if not sub.save():
            return None
        return sub

    @classmethod
    def get_active_for_user(cls, web_user_id: int) -> list['PushSubscription']:
        """Suscripciones activas de un cliente."""
        return cls.query.filter_by(
            web_user_id=web_user_id, is_active=True
        ).all()

    @classmethod
    def deactivate_by_endpoint(cls, endpoint: str) -> None:
        """Desactivar una suscripción muerta (respuesta 404/410 del push service)."""
        sub = cls.query.filter_by(endpoint=endpoint).first()
        if sub is not None:
            sub.is_active = False
            sub.save()
