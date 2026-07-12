"""
Modelos del chat web operador-cliente.

Una ``ChatConversation`` agrupa los mensajes de un visitante (anónimo o cliente
logueado) que escribe desde el widget web. Cada visitante web tiene además un
``User`` de canal ``webchat`` (para que las órdenes se guarden como siempre),
enlazado por ``user_id``. El estado ``bot_paused`` controla si el bot responde
(Fase 2); en la operación manual (Fase 1) arranca en pausa.
"""
from datetime import datetime
from typing import List, Optional

from app.models import db
from app.models.base import BaseModel


class ChatConversation(BaseModel):
    """Conversación de chat web de un visitante (anónimo o logueado)."""

    __tablename__ = 'chat_conversations'

    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=True, index=True
    )
    web_user_id = db.Column(
        db.Integer, db.ForeignKey('web_users.id'), nullable=True, index=True
    )
    anon_id = db.Column(db.String(100), index=True)

    channel = db.Column(db.String(20), default='web', nullable=False)
    bot_paused = db.Column(db.Boolean, default=True, nullable=False)
    country = db.Column(db.String(2))

    unread_for_operator = db.Column(db.Integer, default=0, nullable=False)
    last_message_at = db.Column(db.DateTime)

    messages = db.relationship(
        'ChatMessage', backref='conversation', lazy='dynamic',
        order_by='ChatMessage.created_at'
    )
    web_user = db.relationship('WebUser', foreign_keys=[web_user_id])
    user = db.relationship('User', foreign_keys=[user_id])

    @property
    def display_name(self) -> str:
        """Nombre visible de la conversación para el operador."""
        if self.web_user_id and self.web_user:
            return self.web_user.get_full_name()
        return f"Visitante {self.anon_id[:8]}" if self.anon_id else "Visitante"

    def touch(self, for_operator: bool = False) -> None:
        """Actualizar marca temporal y (opcional) contador de no leídos."""
        self.last_message_at = datetime.utcnow()
        if for_operator:
            self.unread_for_operator = (self.unread_for_operator or 0) + 1

    @classmethod
    def get_for_anon(cls, anon_id: str) -> Optional['ChatConversation']:
        """Conversación de un visitante anónimo por su anon_id."""
        return cls.query.filter_by(anon_id=anon_id).first()


class ChatMessage(BaseModel):
    """Mensaje individual dentro de una conversación de chat web."""

    __tablename__ = 'chat_messages'

    conversation_id = db.Column(
        db.Integer, db.ForeignKey('chat_conversations.id'),
        nullable=False, index=True
    )
    sender = db.Column(db.String(20), nullable=False)
    body = db.Column(db.Text, nullable=False)
    buttons = db.Column(db.JSON)  # botones del bot: [[{text, callback_data|url}]]
    operator_id = db.Column(
        db.Integer, db.ForeignKey('operators.id'), nullable=True
    )
    read_by_client = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        """Representación JSON para el widget y el panel."""
        return {
            'id': self.id,
            'sender': self.sender,
            'body': self.body,
            'buttons': self.buttons or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def get_since(cls, conversation_id: int, after_id: int = 0
                  ) -> List['ChatMessage']:
        """Mensajes de una conversación con id mayor que ``after_id``."""
        return (
            cls.query
            .filter(cls.conversation_id == conversation_id, cls.id > after_id)
            .order_by(cls.id.asc())
            .all()
        )
