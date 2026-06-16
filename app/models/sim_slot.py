"""
Modelo de Slots SIM del board multi-SIM.

Cada slot físico del board (1..N) tiene una etiqueta identificable, operador,
país y número asociado. El slot activo (el que el teléfono está leyendo en un
momento dado) se persiste en SystemConfig, no aquí, porque es estado mutable
de operación, no metadata del slot.
"""
from typing import List, Optional

from app.models import db
from app.models.base import BaseModel


class SimSlot(BaseModel):
    """
    Slot físico del board multi-SIM.

    Attributes:
        slot_number: Posición física en el board (1..N). Único.
        label: Nombre identificable (p. ej. "Movistar Venezuela").
        phone_number: Número de la SIM en formato E.164 (+58...).
        operator: Operador de telefonía (Movistar, Claro, Digitel...).
        country: Código de país ISO corto (VE, CO, US).
        color: Color hex para identificación visual en la interfaz.
        active: Si la SIM está instalada y disponible para uso.
        notes: Notas libres (saldo, límites, propósito).
    """

    __tablename__ = 'sms_sim_slots'

    slot_number = db.Column(db.Integer, unique=True, nullable=False, index=True)
    label = db.Column(db.String(64), nullable=True)
    phone_number = db.Column(db.String(32), nullable=True)
    operator = db.Column(db.String(32), nullable=True)
    country = db.Column(db.String(8), nullable=True)
    color = db.Column(db.String(16), default='#F7D917', nullable=False)
    active = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f'<SimSlot {self.slot_number}: {self.label}>'

    @property
    def display_name(self) -> str:
        """Nombre legible del slot, con fallback al número de slot.

        Returns:
            La etiqueta si existe; en caso contrario ``SIM {n}``.
        """
        return self.label or f'SIM {self.slot_number}'

    @classmethod
    def get_ordered(cls) -> List['SimSlot']:
        """Devuelve todos los slots ordenados por número de slot.

        Returns:
            Lista de SimSlot ordenada ascendentemente por ``slot_number``.
        """
        return cls.query.order_by(cls.slot_number.asc()).all()

    @classmethod
    def get_active_ordered(cls) -> List['SimSlot']:
        """Devuelve los slots con SIM instalada, ordenados.

        Returns:
            Lista de SimSlot con ``active=True`` ordenada por ``slot_number``.
        """
        return (
            cls.query
            .filter_by(active=True)
            .order_by(cls.slot_number.asc())
            .all()
        )

    @classmethod
    def get_by_slot(cls, slot_number: int) -> Optional['SimSlot']:
        """Busca un slot por su número físico.

        Args:
            slot_number: Número de slot en el board.

        Returns:
            El SimSlot correspondiente, o None si no existe.
        """
        return cls.query.filter_by(slot_number=slot_number).first()
