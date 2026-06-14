"""
Seed idempotente del operador-bot de sistema.

Crea (si no existe) un operador con rol BOT que sirve de identidad para
atribuir acciones automáticas del bot conversacional. No puede iniciar sesión
interactiva (bloqueado en ``Operator.authenticate``).

Requiere haber ejecutado antes ``scripts/migrate_add_bot_role.py`` (el ENUM de
la BD debe incluir ya el valor 'bot').

Uso::

    python scripts/seed_bot_operator.py
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.models import db
from app.models.operator import Operator, OperatorRole

BOT_USERNAME = 'ceiba_bot'
BOT_EMAIL = 'bot@ceiba21.com'
BOT_FULL_NAME = 'Ceiba21 Bot'


def main() -> int:
    """Crear el operador-bot si no existe. Idempotente."""
    app = create_app()
    with app.app_context():
        existing = Operator.get_by_username(BOT_USERNAME)
        if existing:
            print(
                f"ℹ️  El operador-bot ya existe "
                f"(id={existing.id}, rol={existing.role.value}). Nada que hacer."
            )
            return 0

        bot = Operator(
            username=BOT_USERNAME,
            full_name=BOT_FULL_NAME,
            email=BOT_EMAIL,
            role=OperatorRole.BOT,
            is_active=True,
        )
        # Contraseña aleatoria inutilizable: el bot no inicia sesión interactiva.
        bot.set_password(secrets.token_urlsafe(48))

        if bot.save():
            print(
                f"✅ Operador-bot creado "
                f"(id={bot.id}, username={BOT_USERNAME}, rol=bot)."
            )
            return 0

        print("❌ No se pudo crear el operador-bot.")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
