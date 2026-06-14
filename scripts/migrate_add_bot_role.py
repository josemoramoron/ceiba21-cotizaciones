"""
Migración: añade el valor 'BOT' al tipo ENUM de roles de operador en PostgreSQL.

IMPORTANTE — nombre vs valor:
SQLAlchemy persiste el NOMBRE del miembro del Enum, no su `.value`. Es decir,
`OperatorRole.BOT` se almacena como 'BOT' (igual que ADMIN/OPERATOR/VIEWER se
guardan como 'ADMIN'/'OPERATOR'/'VIEWER'). Por eso el valor que debe existir en
el ENUM de PostgreSQL es 'BOT' (mayúsculas), aunque en Python `.value` sea 'bot'.

El rol se almacena como ENUM nativo de PostgreSQL, así que añadir un valor
requiere `ALTER TYPE ... ADD VALUE` (no lo hace `db.create_all()`). Este script
descubre el nombre real del tipo ENUM de `operators.role` y le añade 'BOT' de
forma idempotente.

Ejecutar en dev y en prod ANTES de sembrar el operador-bot:

    python scripts/migrate_add_bot_role.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app import create_app
from app.models import db


def main() -> int:
    """Añadir 'BOT' al ENUM de roles de operador. Idempotente."""
    app = create_app()
    with app.app_context():
        engine = db.engine

        # Descubrir el nombre real del tipo ENUM de operators.role
        with engine.connect() as conn:
            type_name = conn.execute(text(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_name = 'operators' AND column_name = 'role'"
            )).scalar()

        if not type_name:
            print("❌ No se encontró la columna operators.role. ¿Existe la tabla?")
            return 1

        print(f"🔎 Tipo ENUM detectado para operators.role: {type_name}")

        # ALTER TYPE ... ADD VALUE en autocommit. IF NOT EXISTS lo hace
        # idempotente (PostgreSQL 12+). Se añade 'BOT' (el NOMBRE del miembro,
        # que es lo que SQLAlchemy persiste).
        with engine.connect() as conn:
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text(
                f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS 'BOT'"
            ))

        print("✅ Valor 'BOT' disponible en el ENUM de roles (o ya existía).")
        return 0


if __name__ == '__main__':
    raise SystemExit(main())