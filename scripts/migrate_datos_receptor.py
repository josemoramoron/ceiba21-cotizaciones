"""
Migración: datos del receptor por método de pago.

Agrega la columna ``datos_receptor`` (TEXT) a payment_methods. Ahí el operador
escribe los datos reales de cobro de cada método (correo PayPal, dirección
USDT, cuenta bancaria...), que el bot muestra al cliente al pedirle el pago.

Antes esos datos estaban hardcodeados en app/bot/responses.py con valores de
ejemplo; ahora la única fuente de verdad es la base de datos.

Idempotente. Ejecutar en dev y en prod:
    python scripts/migrate_datos_receptor.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app import create_app
from app.models import db

STATEMENTS = [
    "ALTER TABLE payment_methods ADD COLUMN IF NOT EXISTS datos_receptor TEXT",
]


def main() -> int:
    """Aplicar el ALTER a payment_methods. Idempotente."""
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            for stmt in STATEMENTS:
                conn.execute(text(stmt))
                print(f"OK: {stmt}")
    print("✅ Migración de datos_receptor completada.")
    print("👉 Ahora completa los datos de cada método en /dashboard/payment-methods")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
