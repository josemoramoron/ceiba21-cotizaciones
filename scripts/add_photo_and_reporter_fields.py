"""
Script para agregar campos de foto, enlaces y reporter a blacklist.

USO:
    python scripts/add_photo_and_reporter_fields.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def add_fields():
    """Agregar nuevos campos"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Agregando campos de foto, enlaces y reporter...")
        
        try:
            statements = [
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500)",
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS scam_links TEXT",
                "ALTER TABLE blacklist ADD COLUMN IF NOT EXISTS reporter_name VARCHAR(100)"
            ]
            
            for stmt in statements:
                try:
                    db.session.execute(db.text(stmt))
                    print(f"✅ {stmt}")
                except Exception as e:
                    print(f"⚠️  {stmt} - {str(e)}")
            
            db.session.commit()
            
            print("\n✅ Campos agregados:")
            print("   - photo_url (URL de foto optimizada)")
            print("   - scam_links (Enlaces maliciosos)")
            print("   - reporter_name (Quien reporta)")
            
            # Crear carpeta para uploads si no existe
            upload_dir = '/var/www/cotizaciones/app/static/uploads/blacklist'
            os.makedirs(upload_dir, exist_ok=True)
            print(f"\n📁 Carpeta de uploads creada: {upload_dir}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {str(e)}")
            return False
        
        return True


if __name__ == '__main__':
    success = add_fields()
    sys.exit(0 if success else 1)