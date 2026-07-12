"""
Migración: botones del bot en los mensajes de chat.

Agrega la columna ``buttons`` (JSON) a chat_messages para persistir los botones
que devuelve el bot (menús, selección de moneda, etc.). Sin ella, los botones se
perderían al recargar el widget y el usuario quedaría sin opciones que pulsar.

Idempotente. Ejecutar en dev y en prod:
    python scripts/migrate_chat_buttons.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app import create_app
from app.models import db

STATEMENTS = [
    "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS buttons JSON",
]


def main() -> int:
    """Aplicar el ALTER a chat_messages. Idempotente."""
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            for stmt in STATEMENTS:
                conn.execute(text(stmt))
                print(f"OK: {stmt}")
    print("✅ Migración de botones de chat completada.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
