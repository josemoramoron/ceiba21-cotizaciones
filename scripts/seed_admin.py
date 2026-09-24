"""
Crea el operador admin de desarrollo (username: admin, password: admin123).
Uso: python scripts/seed_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.operator import Operator, OperatorRole


def main():
    app = create_app()
    with app.app_context():
        existing = Operator.get_by_username('admin')
        if existing:
            print(f"El operador 'admin' ya existe (id={existing.id})")
            return

        operator = Operator.create_operator(
            username='admin',
            password='admin123',
            full_name='Administrador',
            email='admin@ceiba21.dev',
            role=OperatorRole.ADMIN,
        )
        print(f"Operador creado: {operator.username} (id={operator.id}, role={operator.role.value})")


if __name__ == '__main__':
    main()
