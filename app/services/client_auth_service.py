"""
Servicio de autenticación de clientes (WebUser).

Capa de negocio sobre el modelo WebUser para registro y login de clientes del
sitio web. La gestión de sesión (cookies) vive en app/client_auth.py, separada
del Flask-Login de operadores.
"""
from typing import Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from app.services.base_service import BaseService
from app.models.web_user import WebUser

MIN_PASSWORD_LENGTH = 8


class ClientAuthService(BaseService):
    """Registro y autenticación de clientes web."""

    @classmethod
    def register(cls, email: str, password: str, first_name: str,
                 last_name: str, phone: Optional[str] = None
                 ) -> Tuple[bool, str, Optional[WebUser]]:
        """
        Registrar un nuevo cliente web (self-service).

        La verificación de email queda diferida: la cuenta se crea activa y sin
        token de verificación.

        Args:
            email: Email (identificador de login).
            password: Contraseña en texto plano.
            first_name: Nombre.
            last_name: Apellido.
            phone: Teléfono (opcional).

        Returns:
            Tupla (success, message, web_user|None).
        """
        email = (email or '').strip().lower()
        first_name = (first_name or '').strip()
        last_name = (last_name or '').strip()

        if not email or not password or not first_name or not last_name:
            return False, "Faltan datos obligatorios", None

        if len(password) < MIN_PASSWORD_LENGTH:
            return False, (
                f"La contraseña debe tener al menos "
                f"{MIN_PASSWORD_LENGTH} caracteres"
            ), None

        if WebUser.get_by_email(email):
            return False, "Ya existe una cuenta con ese email", None

        try:
            web_user = WebUser.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=(phone or '').strip() or None,
                send_verification=True,  # genera el token de verificación
            )
        except SQLAlchemyError as exc:
            cls.rollback()
            cls.log_error("Error al registrar cliente", exc)
            return False, "No se pudo crear la cuenta", None

        cls.log_info(f"Cliente registrado: {email}")
        return True, "Cuenta creada exitosamente", web_user

    @classmethod
    def solicitar_reset(cls, email: str) -> Optional[WebUser]:
        """
        Generar el token de restablecimiento de contraseña.

        Devuelve None si el email no existe. La ruta NO debe revelar esa
        diferencia al usuario (evita enumerar cuentas registradas).
        """
        web_user = WebUser.get_by_email((email or '').strip().lower())
        if web_user is None:
            return None

        web_user.generate_reset_token()
        web_user.save(raise_on_error=True)
        return web_user

    @classmethod
    def authenticate(cls, email: str, password: str
                     ) -> Tuple[bool, str, Optional[WebUser]]:
        """
        Autenticar un cliente por email y contraseña.

        Args:
            email: Email.
            password: Contraseña.

        Returns:
            Tupla (success, message, web_user|None).
        """
        email = (email or '').strip().lower()
        web_user = WebUser.authenticate(email, password)

        if not web_user:
            return False, "Email o contraseña incorrectos", None

        web_user.update_last_login()
        return True, "Sesión iniciada", web_user
