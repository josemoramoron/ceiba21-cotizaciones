"""
Script para agregar nuevos campos a la tabla blacklist.

USO:
    python scripts/add_blacklist_fields.py
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def add_fields():
    """Agregar nuevos campos a blacklist"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Agregando nuevos campos a blacklist...")
        
        try:
            # Ejecutar ALTER TABLE para agregar columnas
            statements = [
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS state VARCHAR(100)",
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(100)",
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS bank_info VARCHAR(500)",
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS additional_info TEXT"
            ]
            
            for stmt in statements:
                try:
                    db.session.execute(db.text(stmt))
                    print(f"✅ {stmt}")
                except Exception as e:
                    print(f"⚠️  {stmt} - {str(e)}")
            
            db.session.commit()
            
            print("\n✅ Campos agregados exitosamente:")
            print("   - country (País)")
            print("   - state (Estado/Región)")
            print("   - transaction_type (Tipo de transacción)")
            print("   - bank_info (Datos bancarios)")
            print("   - additional_info (Información adicional)")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {str(e)}")
            return False
        
        return True


if __name__ == '__main__':
    success = add_fields()
    sys.exit(0 if success else 1)