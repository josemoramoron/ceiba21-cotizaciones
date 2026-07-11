"""
Suscripción Web Push de un cliente (WebUser) o de un visitante anónimo.

Cada navegador/dispositivo produce una suscripción con un endpoint único y dos
claves (p256dh, auth). Se asocia a un WebUser (logueado) o a un ``anon_id``
(visitante anónimo del chat), nunca a ambos.
"""
from typing import List, Optional

from app.models import db
from app.models.base import BaseModel


class PushSubscription(BaseModel):
    """Suscripción Web Push (de un WebUser o de un anónimo)."""

    __tablename__ = 'push_subscriptions'

    web_user_id = db.Column(
        db.Integer, db.ForeignKey('web_users.id'), nullable=True, index=True
    )
    anon_id = db.Column(db.String(100), index=True)
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
    def upsert(cls, endpoint: str, p256dh: str, auth: str,
               web_user_id: Optional[int] = None,
               anon_id: Optional[str] = None,
               user_agent: Optional[str] = None) -> Optional['PushSubscription']:
        """
        Crear o actualizar (por endpoint) una suscripción.

        Se asocia a ``web_user_id`` (logueado) o a ``anon_id`` (anónimo).

        Returns:
            La suscripción guardada, o None si el guardado falló.
        """
        sub = cls.query.filter_by(endpoint=endpoint).first()
        if sub is None:
            sub = cls(endpoint=endpoint)
        sub.web_user_id = web_user_id
        sub.anon_id = anon_id
        sub.p256dh = p256dh
        sub.auth = auth
        sub.user_agent = user_agent
        sub.is_active = True
        if not sub.save():
            return None
        return sub

    @classmethod
    def get_active_for_user(cls, web_user_id: int) -> List['PushSubscription']:
        """Suscripciones activas de un cliente logueado."""
        return cls.query.filter_by(
            web_user_id=web_user_id, is_active=True
        ).all()

    @classmethod
    def get_active_for_anon(cls, anon_id: str) -> List['PushSubscription']:
        """Suscripciones activas de un visitante anónimo."""
        return cls.query.filter_by(anon_id=anon_id, is_active=True).all()

    @classmethod
    def deactivate_by_endpoint(cls, endpoint: str) -> None:
        """Desactivar una suscripción muerta (respuesta 404/410)."""
        sub = cls.query.filter_by(endpoint=endpoint).first()
        if sub is not None:
            sub.is_active = False
            sub.save()
