"""
Migración: vínculo entre pagos y órdenes (conciliación).

Agrega ``payments.order_id`` (FK a orders, nullable) + índice. Es el vínculo que
permite: (a) mostrar el pago recibido junto a su orden en el chat, (b) marcar el
pago como PAGADO al completar la orden, y (c) reportes de qué pago corresponde a
qué orden.

Idempotente. Ejecutar en dev y en prod:
    python scripts/migrate_payment_order.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app import create_app
from app.models import db

STATEMENTS = [
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS order_id INTEGER "
    "REFERENCES orders(id)",
    "CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments (order_id)",
]


def main() -> int:
    """Aplicar los ALTER a payments. Idempotente."""
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            for stmt in STATEMENTS:
                conn.execute(text(stmt))
                print(f"OK: {stmt}")
    print("✅ Migración de conciliación completada.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
