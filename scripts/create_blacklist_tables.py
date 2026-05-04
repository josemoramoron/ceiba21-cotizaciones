"""
Script para crear las tablas de Blacklist en la base de datos.

USO:
    python scripts/create_blacklist_tables.py
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.blacklist import BlacklistEntry, BlacklistAppeal

def create_tables():
    """Crear tablas de blacklist"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Creando tablas de Blacklist...")
        
        try:
            # Crear tablas
            db.create_all()
            
            print("✅ Tablas creadas exitosamente:")
            print("   - blacklist")
            print("   - blacklist_appeals")
            print("\n📊 Estructura de tablas:")
            print("\nBlacklistEntry:")
            print("   - ID, user_id, telegram_id, phone, email, dni")
            print("   - block_type, category, status, reason")
            print("   - severity, evidence_urls, order_references")
            print("   - fraud_check_result, risk_score")
            print("   - blocked_at, expires_at, unblocked_at")
            print("\nBlacklistAppeal:")
            print("   - ID, blacklist_id, appellant info")
            print("   - appeal_text, status, decision")
            print("   - reviewed_at, review_notes")
            
        except Exception as e:
            print(f"❌ Error al crear tablas: {str(e)}")
            return False
        
        return True


if __name__ == '__main__':
    success = create_tables()
    sys.exit(0 if success else 1)