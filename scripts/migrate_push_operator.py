"""
Migración: suscripciones Web Push de operadores.

Agrega la columna operator_id (FK a operators) a push_subscriptions, para que
los operadores/admins puedan recibir avisos push del panel (chat entrante).
Idempotente.

Ejecutar en dev y en prod:
    python scripts/migrate_push_operator.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app import create_app
from app.models import db

STATEMENTS = [
    "ALTER TABLE push_subscriptions "
    "ADD COLUMN IF NOT EXISTS operator_id INTEGER REFERENCES operators(id)",
    "CREATE INDEX IF NOT EXISTS ix_push_subscriptions_operator_id "
    "ON push_subscriptions (operator_id)",
]


def main() -> int:
    """Aplicar los ALTER a push_subscriptions. Idempotente."""
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            for stmt in STATEMENTS:
                conn.execute(text(stmt))
                print(f"OK: {stmt}")
    print("✅ Migración de push para operadores completada.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
