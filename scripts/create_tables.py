#!/usr/bin/env python3
"""
Script para crear todas las tablas de la base de datos.
Ejecutar después de crear nuevos modelos.
"""
import sys
import os

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db

def create_tables():
    """Crear todas las tablas en la base de datos"""
    app = create_app()
    
    with app.app_context():
        print("🔨 Creando tablas en la base de datos...")
        try:
            db.create_all()
            print("✅ Tablas creadas exitosamente!")
            print("\nTablas disponibles:")
            
            # Listar tablas creadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            for table in sorted(tables):
                print(f"  - {table}")
            
            print(f"\n📊 Total: {len(tables)} tablas")
            
        except Exception as e:
            print(f"❌ Error al crear tablas: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    success = create_tables()
    sys.exit(0 if success else 1)
