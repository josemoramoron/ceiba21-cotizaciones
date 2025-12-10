"""
Script para verificar datos de una orden
"""
import sys
sys.path.insert(0, '/var/www/cotizaciones')

from app import create_app, db
from app.models.order import Order

app = create_app()

with app.app_context():
    # Ver todas las órdenes
    orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    print("=" * 60)
    print(f"ÚLTIMAS 5 ÓRDENES:")
    print("=" * 60)
    
    for order in orders:
        print(f"\n📋 {order.reference} (ID: {order.id})")
        print(f"   Estado: {order.status.value}")
        print(f"   Cliente: {order.user.get_display_name()}")
        print(f"   Canal: {order.channel}")
        print(f"   Monto: ${order.amount_usd} → {order.amount_local} {order.currency.code}")
        print(f"\n   💼 DATOS DEL CLIENTE:")
        print(f"   - Teléfono: {order.client_phone or 'NO GUARDADO'}")
        print(f"   - Banco: {order.client_bank or 'NO GUARDADO'}")
        print(f"   - Cuenta: {order.client_account or 'NO GUARDADO'}")
        print(f"   - Titular: {order.client_holder or 'NO GUARDADO'}")
        print(f"   - DNI: {order.client_dni or 'NO GUARDADO'}")
        print(f"   - Comprobante: {order.client_proof_url or 'NO GUARDADO'}")
        print("-" * 60)
