"""
Envío de correos con smtplib (sin dependencias extra).

Patrón adaptado de wepart3, con dos diferencias importantes:

1. **El cuerpo se renderiza desde plantillas Jinja** (``app/templates/email/``),
   no con f-strings dentro del servicio. La lógica se queda en el servicio y la
   presentación en las plantillas.
2. **Las URL se construyen ANTES de lanzar el hilo.** ``url_for(_external=True)``
   necesita el contexto de la petición para saber el dominio; dentro de un
   ``Thread`` ese contexto ya no existe. Quien llama pasa el enlace ya hecho.

En desarrollo, ``MAIL_SUPPRESS_SEND=true`` imprime el correo por consola en vez
de enviarlo.
"""
import smtplib
import ssl
from email.message import EmailMessage
from threading import Thread
from typing import Optional

from flask import current_app, render_template

from app.services.base_service import BaseService


class EmailService(BaseService):
    """Composición y envío de correos transaccionales."""

    @classmethod
    def _enviar_sync(cls, app, mensaje: EmailMessage) -> bool:
        """Enviar por SMTP. Se ejecuta dentro del hilo, con contexto de app."""
        with app.app_context():
            if app.config.get('MAIL_SUPPRESS_SEND'):
                print("─" * 60)
                print(f"[MAIL SUPRIMIDO] Para: {mensaje['To']}")
                print(f"Asunto: {mensaje['Subject']}")
                print(mensaje.get_body(('plain',)).get_content())
                print("─" * 60)
                return True

            servidor = app.config.get('MAIL_SERVER')
            puerto = app.config.get('MAIL_PORT')
            usuario = app.config.get('MAIL_USERNAME')
            password = app.config.get('MAIL_PASSWORD')

            if not servidor or not usuario or not password:
                cls.log_error("SMTP no configurado: no se envía el correo")
                return False

            try:
                contexto = ssl.create_default_context()
                with smtplib.SMTP(servidor, puerto, timeout=20) as smtp:
                    if app.config.get('MAIL_USE_TLS', True):
                        smtp.starttls(context=contexto)
                    smtp.login(usuario, password)
                    smtp.send_message(mensaje)

                cls.log_info(f"Correo enviado a {mensaje['To']}")
                return True

            except (smtplib.SMTPException, OSError) as exc:
                cls.log_error(f"Error al enviar correo a {mensaje['To']}", exc)
                return False

    @classmethod
    def enviar(cls, destinatario: str, asunto: str, plantilla: str,
               **contexto) -> None:
        """
        Componer y enviar un correo en segundo plano.

        Args:
            destinatario: Email de destino.
            asunto: Asunto del mensaje.
            plantilla: Nombre base en ``app/templates/email/`` (sin extensión);
                se usan las variantes ``.txt`` y ``.html``.
            **contexto: Variables para la plantilla (p. ej. ``enlace``).
        """
        app = current_app._get_current_object()

        mensaje = EmailMessage()
        mensaje['Subject'] = asunto
        mensaje['From'] = app.config.get('MAIL_DEFAULT_SENDER')
        mensaje['To'] = destinatario

        reply_to = app.config.get('MAIL_REPLY_TO')
        if reply_to:
            mensaje['Reply-To'] = reply_to

        mensaje.set_content(render_template(f'email/{plantilla}.txt', **contexto))
        mensaje.add_alternative(
            render_template(f'email/{plantilla}.html', **contexto), subtype='html'
        )

        Thread(target=cls._enviar_sync, args=(app, mensaje), daemon=True).start()

    @classmethod
    def enviar_verificacion(cls, web_user, enlace: str) -> None:
        """Correo de verificación de cuenta (el enlace ya viene construido)."""
        cls.enviar(
            destinatario=web_user.email,
            asunto='Verifica tu cuenta de Ceiba21',
            plantilla='verificacion',
            nombre=web_user.first_name,
            enlace=enlace,
        )

    @classmethod
    def enviar_reset(cls, web_user, enlace: str,
                     vigencia_min: Optional[int] = 60) -> None:
        """Correo para restablecer la contraseña."""
        cls.enviar(
            destinatario=web_user.email,
            asunto='Restablece tu contraseña de Ceiba21',
            plantilla='reset',
            nombre=web_user.first_name,
            enlace=enlace,
            vigencia_min=vigencia_min,
        )
