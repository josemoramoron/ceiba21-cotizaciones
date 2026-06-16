"""
Modelo de Mensajes SMS (enviados y recibidos).

Una sola tabla `sms_messages` almacena ambas direcciones, diferenciadas por la
columna `direction` (igual que Payment unifica métodos en una tabla). El estado
de entrega (Pending/Sent/Delivered/Failed) solo aplica a los salientes.

La lógica de envío/ingesta vive en app/services/sms_service.py.
"""
from typing import List, Optional

from app.models import db
from app.models.base import BaseModel


class SmsDirection:
    """Dirección del mensaje (valor de la columna `direction`)."""
    INBOUND = 'inbound'      # Recibido
    OUTBOUND = 'outbound'    # Enviado

    TODOS = (INBOUND, OUTBOUND)


class SmsStatus:
    """Estados de entrega de un SMS saliente (provistos por el gateway)."""
    PENDING = 'Pending'
    SENT = 'Sent'
    DELIVERED = 'Delivered'
    FAILED = 'Failed'


class SmsMessage(BaseModel):
    """
    Mensaje SMS entrante o saliente capturado/enviado vía el gateway Android.

    Attributes:
        gateway_id: ID del mensaje en el gateway (para dedupe y status).
        direction: SmsDirection.INBOUND o SmsDirection.OUTBOUND.
        phone: Número de la otra parte (remitente si entra, destino si sale).
        text: Contenido del mensaje.
        status: Estado de entrega (solo salientes; SmsStatus.*).
        sim_slot: Número de slot del board usado (si se conoce).
        device_id: ID del dispositivo Android que procesó el mensaje.
        is_read: Marca de leído (solo entrantes).
    """

    __tablename__ = 'sms_messages'

    gateway_id = db.Column(db.String(128), nullable=True, index=True)
    direction = db.Column(db.String(16), nullable=False, index=True)
    phone = db.Column(db.String(32), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=True)
    sim_slot = db.Column(db.Integer, nullable=True)
    device_id = db.Column(db.String(128), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f'<SmsMessage {self.direction} {self.phone}>'

    @classmethod
    def get_inbound(cls, unread_only: bool = False):
        """Query base de mensajes entrantes, más recientes primero.

        Args:
            unread_only: Si True, filtra solo los no leídos.

        Returns:
            Query de SQLAlchemy (sin ejecutar) para paginar o listar.
        """
        query = (
            cls.query
            .filter_by(direction=SmsDirection.INBOUND)
            .order_by(cls.created_at.desc())
        )
        if unread_only:
            query = query.filter_by(is_read=False)
        return query

    @classmethod
    def get_outbound(cls):
        """Query base de mensajes salientes, más recientes primero.

        Returns:
            Query de SQLAlchemy (sin ejecutar) para paginar o listar.
        """
        return (
            cls.query
            .filter_by(direction=SmsDirection.OUTBOUND)
            .order_by(cls.created_at.desc())
        )

    @classmethod
    def count_unread(cls) -> int:
        """Cuenta los mensajes entrantes no leídos.

        Returns:
            Número de SMS entrantes con ``is_read=False``.
        """
        return (
            cls.query
            .filter_by(direction=SmsDirection.INBOUND, is_read=False)
            .count()
        )

    @classmethod
    def exists_gateway_id(cls, gateway_id: str) -> bool:
        """Verifica si ya existe un mensaje con ese ID de gateway (dedupe).

        Args:
            gateway_id: Identificador del mensaje en el gateway.

        Returns:
            True si ya está registrado; False en caso contrario.
        """
        if not gateway_id:
            return False
        return cls.query.filter_by(gateway_id=gateway_id).first() is not None
