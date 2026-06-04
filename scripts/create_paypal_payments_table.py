"""
Migración: Crear tabla paypal_payments

Ejecutar una sola vez:
    python scripts/create_paypal_payments_table.py

Verifica que la tabla no exista antes de crearla.
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Crea la tabla paypal_payments si no existe."""
    from app import create_app, db
    from app.models.paypal_payment import PaypalPayment

    app = create_app()

    with app.app_context():
        # Verificar si ya existe
        from sqlalchemy import inspect
        inspector = inspect(db.engine)

        if 'paypal_payments' in inspector.get_table_names():
            print("✅ La tabla 'paypal_payments' ya existe. Nada que hacer.")
            return

        print("Creando tabla 'paypal_payments'...")

        try:
            # Crear solo esta tabla
            PaypalPayment.__table__.create(db.engine)
            print("✅ Tabla 'paypal_payments' creada exitosamente.")

            # Verificar columnas
            columns = [col['name'] for col in inspector.get_columns('paypal_payments')]
            print(f"   Columnas creadas: {len(columns)}")
            for col in columns:
                print(f"   - {col}")

        except Exception as e:
            print(f"❌ Error creando tabla: {e}")
            sys.exit(1)


if __name__ == '__main__':
    run_migration()
