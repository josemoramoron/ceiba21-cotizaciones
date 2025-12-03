#!/usr/bin/env python3
"""
Script para activar las monedas BRL y MXN
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import Currency, db

app = create_app()

with app.app_context():
    print("=" * 80)
    print("ACTIVANDO MONEDAS BRL Y MXN")
    print("=" * 80)
    
    # Activar BRL
    brl = Currency.query.filter_by(code='BRL').first()
    if brl:
        brl.active = True
        print(f"\n✅ BRL (Real Brasileño) activada")
        print(f"   - ID: {brl.id}")
        print(f"   - Nombre: {brl.name}")
        print(f"   - Estado anterior: inactiva")
        print(f"   - Estado nuevo: activa")
    else:
        print("\n❌ BRL no encontrada en la base de datos")
    
    # Activar MXN
    mxn = Currency.query.filter_by(code='MXN').first()
    if mxn:
        mxn.active = True
        print(f"\n✅ MXN (Peso Mexicano) activada")
        print(f"   - ID: {mxn.id}")
        print(f"   - Nombre: {mxn.name}")
        print(f"   - Estado anterior: inactiva")
        print(f"   - Estado nuevo: activa")
    else:
        print("\n❌ MXN no encontrada en la base de datos")
    
    # Guardar cambios
    try:
        db.session.commit()
        print("\n" + "=" * 80)
        print("✅ CAMBIOS GUARDADOS EXITOSAMENTE")
        print("=" * 80)
        
        # Mostrar estado final
        print("\nESTADO FINAL DE LAS MONEDAS:")
        print("-" * 80)
        currencies = Currency.query.order_by(Currency.code).all()
        for curr in currencies:
            status = "✅ ACTIVA" if curr.active else "❌ INACTIVA"
            print(f"  [{curr.code:4s}] {curr.name:25s} - {status}")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ ERROR al guardar cambios: {str(e)}")
    
    print("\n" + "=" * 80)
