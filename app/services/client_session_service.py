"""
Servicio de sesión de cliente (visitante web anónimo).

Gestiona un identificador estable de sesión para el visitante, almacenado en
la sesión de servidor (Flask-Session sobre Redis). Sirve de ancla para asociar
el estado del visitante y, más adelante, su cuenta autenticada (login de
clientes) y la conversación de chat web.
"""
import uuid
from typing import Optional

from flask import session

from app.services.base_service import BaseService


class ClientSessionService(BaseService):
    """Gestiona el identificador de sesión del visitante web."""

    SESSION_KEY = 'client_session_id'

    @classmethod
    def ensure_session(cls) -> str:
        """
        Garantizar que el visitante tenga un identificador de sesión.

        Si no existe, genera uno nuevo (UUID4) y lo persiste en la sesión.

        Returns:
            El identificador de sesión del cliente.
        """
        session_id = session.get(cls.SESSION_KEY)
        if not session_id:
            session_id = uuid.uuid4().hex
            session[cls.SESSION_KEY] = session_id
            session.permanent = True
        return session_id

    @classmethod
    def get_session_id(cls) -> Optional[str]:
        """
        Obtener el identificador de sesión del cliente si existe.

        Returns:
            El identificador, o None si aún no se ha creado.
        """
        return session.get(cls.SESSION_KEY)
