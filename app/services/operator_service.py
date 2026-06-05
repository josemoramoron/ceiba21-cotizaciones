"""
Servicio de gestión de operadores.
Capa de negocio entre routes/dashboard.py y el modelo Operator.
"""
import logging
from typing import Optional, List, Tuple

from app.models.operator import Operator, OperatorRole

logger = logging.getLogger(__name__)


class OperatorService:
    """
    Servicio para gestión de operadores del sistema.

    Centraliza toda la lógica de negocio relacionada con operadores,
    siguiendo la arquitectura Routes → Services → Models del proyecto.
    """

    @staticmethod
    def get_all() -> List[Operator]:
        """
        Obtiene todos los operadores ordenados por fecha de creación.

        Returns:
            Lista de Operator ordenada descendente por created_at
        """
        return Operator.query.order_by(Operator.created_at.desc()).all()

    @staticmethod
    def get_by_id(operator_id: int) -> Optional[Operator]:
        """
        Busca un operador por su ID.

        Args:
            operator_id: ID del operador

        Returns:
            Operator si existe, None si no
        """
        return Operator.query.get(operator_id)

    @staticmethod
    def get_by_username(username: str) -> Optional[Operator]:
        """
        Busca un operador por su username.

        Args:
            username: Nombre de usuario a buscar

        Returns:
            Operator si existe, None si no
        """
        return Operator.get_by_username(username)

    @staticmethod
    def create(
        username: str,
        password: str,
        full_name: str,
        email: str,
        role: str = 'operator'
    ) -> Tuple[Optional[Operator], Optional[str]]:
        """
        Crea un nuevo operador validando que el username no exista.

        Args:
            username: Nombre de usuario único
            password: Contraseña en texto plano
            full_name: Nombre completo
            email: Email del operador
            role: Rol como string ('admin', 'operator', 'viewer')

        Returns:
            Tuple (Operator creado, None) si éxito
            Tuple (None, mensaje_error) si falla
        """
        if Operator.get_by_username(username):
            return None, f"El usuario {username} ya existe"

        operator = Operator(
            username=username,
            full_name=full_name,
            email=email,
            role=OperatorRole(role)
        )
        operator.set_password(password)

        if operator.save():
            logger.info(f"Operador creado: {username} (rol: {role})")
            return operator, None

        logger.error(f"Error guardando operador: {username}")
        return None, "Error al crear operador"

    @staticmethod
    def toggle_active(operator_id: int) -> Tuple[Optional[Operator], Optional[str]]:
        """
        Activa o desactiva un operador.

        Args:
            operator_id: ID del operador a modificar

        Returns:
            Tuple (Operator actualizado, None) si éxito
            Tuple (None, mensaje_error) si no se encontró
        """
        operator = Operator.query.get(operator_id)
        if not operator:
            return None, "Operador no encontrado"

        operator.is_active = not operator.is_active
        operator.save()
        logger.info(
            f"Operador {operator.username} "
            f"{'activado' if operator.is_active else 'desactivado'}"
        )
        return operator, None

    @staticmethod
    def reset_password(
        operator_id: int,
        new_password: str
    ) -> Tuple[Optional[Operator], Optional[str]]:
        """
        Resetea la contraseña de un operador.

        Args:
            operator_id: ID del operador
            new_password: Nueva contraseña en texto plano

        Returns:
            Tuple (Operator actualizado, None) si éxito
            Tuple (None, mensaje_error) si falla
        """
        operator = Operator.query.get(operator_id)
        if not operator:
            return None, "Operador no encontrado"

        operator.set_password(new_password)
        operator.save()
        logger.info(f"Contraseña reseteada para operador: {operator.username}")
        return operator, None
