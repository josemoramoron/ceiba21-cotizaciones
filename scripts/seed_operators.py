#!/usr/bin/env python3
"""
Script para crear operadores de prueba en la base de datos.
"""
import sys
import os
import secrets

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.operator import Operator, OperatorRole


def seed_operators():
    """Crear operadores de prueba"""
    print("\n" + "="*60)
    print("👥 CREACIÓN DE OPERADORES - CEIBA21")
    print("="*60 + "\n")
    
    try:
        app = create_app()
        
        with app.app_context():
            # Generar passwords aleatorias
            admin_password = secrets.token_urlsafe(12)
            operator_password = secrets.token_urlsafe(12)
            
            # Verificar si admin ya existe
            existing_admin = Operator.get_by_username('admin')
            if existing_admin:
                print("⚠️  El operador 'admin' ya existe. Saltando creación.\n")
            else:
                # Crear operador ADMIN
                admin = Operator.create_operator(
                    username='admin',
                    password=admin_password,
                    full_name='Administrador Ceiba21',
                    email='admin@ceiba21.com',
                    role=OperatorRole.ADMIN
                )
                print("✅ Operador ADMIN creado:")
                print(f"   Username: admin")
                print(f"   Password: {admin_password}")
                print(f"   Email: admin@ceiba21.com")
                print(f"   Rol: ADMIN\n")
            
            # Verificar si operator1 ya existe
            existing_operator = Operator.get_by_username('operator1')
            if existing_operator:
                print("⚠️  El operador 'operator1' ya existe. Saltando creación.\n")
            else:
                # Crear operador OPERATOR
                operator1 = Operator.create_operator(
                    username='operator1',
                    password=operator_password,
                    full_name='Operador de Prueba',
                    email='operator1@ceiba21.com',
                    role=OperatorRole.OPERATOR
                )
                print("✅ Operador OPERATOR creado:")
                print(f"   Username: operator1")
                print(f"   Password: {operator_password}")
                print(f"   Email: operator1@ceiba21.com")
                print(f"   Rol: OPERATOR\n")
            
            # Resumen
            total_operators = Operator.query.count()
            print("="*60)
            print(f"✅ OPERADORES LISTOS ({total_operators} en total)")
            print("="*60)
            print("\n📌 Guarda estas credenciales en un lugar seguro!")
            print("📌 Próximo paso: Arrancar servidor web\n")
            
            # Guardar credenciales en archivo temporal
            with open('/tmp/ceiba21_credentials.txt', 'w') as f:
                if not existing_admin:
                    f.write(f"ADMIN:\n")
                    f.write(f"  Username: admin\n")
                    f.write(f"  Password: {admin_password}\n\n")
                if not existing_operator:
                    f.write(f"OPERATOR:\n")
                    f.write(f"  Username: operator1\n")
                    f.write(f"  Password: {operator_password}\n")
            
            print("💾 Credenciales guardadas en: /tmp/ceiba21_credentials.txt\n")
            
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = seed_operators()
    sys.exit(0 if success else 1)
