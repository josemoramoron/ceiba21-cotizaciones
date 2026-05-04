"""
Script para agregar campos de auditoría a blacklist.

USO:
    python scripts/add_audit_fields.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def add_fields():
    """Agregar campos de auditoría"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Agregando campos de auditoría a blacklist...")
        
        try:
            statements = [
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS last_edited_at TIMESTAMP",
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS last_edited_by_operator_id INTEGER REFERENCES operators(id)"
            ]
            
            for stmt in statements:
                try:
                    db.session.execute(db.text(stmt))
                    print(f"✅ {stmt}")
                except Exception as e:
                    print(f"⚠️  {stmt} - {str(e)}")
            
            db.session.commit()
            
            print("\n✅ Campos de auditoría agregados:")
            print("   - last_edited_at (Fecha de última edición)")
            print("   - last_edited_by_operator_id (Quién editó)")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {str(e)}")
            return False
        
        return True


if __name__ == '__main__':
    success = add_fields()
    sys.exit(0 if success else 1)