#!/usr/bin/env python3
"""
Script para crear operadores iniciales del sistema.
Crea un operador ADMIN por defecto.
"""
import sys
import os

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, Operator, OperatorRole

def seed_operators():
    """Crear operadores iniciales"""
    app = create_app()
    
    with app.app_context():
        print("👤 Creando operadores iniciales...\n")
        
        try:
            # 1. Verificar si ya existe un admin
            existing_admin = Operator.query.filter_by(username='admin').first()
            
            if existing_admin:
                print("⚠️  El operador 'admin' ya existe.")
                print(f"   Email: {existing_admin.email}")
                print(f"   Rol: {existing_admin.role.value}")
                return True
            
            # 2. Crear operador ADMIN
            admin = Operator.create_operator(
                username='admin',
                password='admin123',  # CAMBIAR DESPUÉS DEL PRIMER LOGIN
                full_name='Administrador del Sistema',
                email='admin@ceiba21.com',
                role=OperatorRole.ADMIN
            )
            
            print("✅ Operador ADMIN creado exitosamente!")
            print(f"   Username: admin")
            print(f"   Password: admin123")
            print(f"   Email: {admin.email}")
            print(f"   Rol: {admin.role.value}")
            print(f"\n⚠️  IMPORTANTE: Cambia la contraseña después del primer login!\n")
            
            # 3. Crear operador de ejemplo (OPERATOR)
            operator = Operator.create_operator(
                username='operador1',
                password='operador123',
                full_name='Operador de Prueba',
                email='operador@ceiba21.com',
                role=OperatorRole.OPERATOR,
                permissions={
                    'view_orders': True,
                    'take_orders': True,
                    'approve_orders': True,
                    'cancel_orders': False,
                    'view_reports': True,
                    'view_messages': True,
                    'send_messages': True
                }
            )
            
            print("✅ Operador de prueba creado!")
            print(f"   Username: operador1")
            print(f"   Password: operador123")
            print(f"   Email: {operator.email}")
            print(f"   Rol: {operator.role.value}")
            
            # 4. Crear viewer de ejemplo
            viewer = Operator.create_operator(
                username='viewer1',
                password='viewer123',
                full_name='Visor de Prueba',
                email='viewer@ceiba21.com',
                role=OperatorRole.VIEWER
            )
            
            print("\n✅ Visor de prueba creado!")
            print(f"   Username: viewer1")
            print(f"   Password: viewer123")
            print(f"   Email: {viewer.email}")
            print(f"   Rol: {viewer.role.value}")
            
            print("\n" + "="*50)
            print("✅ Operadores iniciales creados exitosamente!")
            print("="*50)
            
            return True
            
        except Exception as e:
            print(f"❌ Error al crear operadores: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    success = seed_operators()
    sys.exit(0 if success else 1)
