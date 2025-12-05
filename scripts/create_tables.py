#!/usr/bin/env python3
"""
Script para crear todas las tablas de la base de datos.
Ejecutar una vez durante setup inicial.
"""
import sys
import os

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db


def create_all_tables():
    """Crear todas las tablas definidas en los modelos"""
    print("\n" + "="*60)
    print("🗄️  CREACIÓN DE TABLAS - CEIBA21")
    print("="*60 + "\n")
    
    try:
        app = create_app()
        
        with app.app_context():
            # Crear todas las tablas
            print("📝 Creando tablas...")
            db.create_all()
            
            # Verificar tablas creadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n✅ {len(tables)} tablas creadas exitosamente:\n")
            
            for table in sorted(tables):
                print(f"   ✓ {table}")
            
            print("\n" + "="*60)
            print("✅ BASE DE DATOS LISTA")
            print("="*60)
            print("\n📌 Próximo paso: python scripts/seed_operators.py\n")
            
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = create_all_tables()
    sys.exit(0 if success else 1)
