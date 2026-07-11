"""
Migración: soporte de suscripciones Web Push anónimas.

La tabla push_subscriptions ya existe (creada en la fase de Web Push). Este
script la ajusta para el chat anónimo (idempotente):
- web_user_id pasa a NULLABLE (antes NOT NULL).
- se agrega la columna anon_id (VARCHAR 100) + índice.

Las tablas chat_conversations y chat_messages son nuevas: las crea create_all
al arrancar, sin migración.

Ejecutar en dev y en prod:
    python scripts/migrate_push_anon.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app import create_app
from app.models import db

STATEMENTS = [
    "ALTER TABLE push_subscriptions ALTER COLUMN web_user_id DROP NOT NULL",
    "ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS anon_id VARCHAR(100)",
    "CREATE INDEX IF NOT EXISTS ix_push_subscriptions_anon_id "
    "ON push_subscriptions (anon_id)",
]


def main() -> int:
    """Aplicar los ALTER a push_subscriptions. Idempotente."""
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            for stmt in STATEMENTS:
                conn.execute(text(stmt))
                print(f"OK: {stmt}")
    print("✅ Migración de push anónimo completada.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
