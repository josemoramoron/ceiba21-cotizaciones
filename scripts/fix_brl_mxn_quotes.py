#!/usr/bin/env python3
"""
Script para corregir las cotizaciones de BRL y MXN
copiando los valores correctos desde VES
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import Currency, Quote, PaymentMethod, db

app = create_app()

with app.app_context():
    print("=" * 80)
    print("CORRECCIÓN DE COTIZACIONES BRL Y MXN")
    print("=" * 80)
    
    # Obtener monedas
    ves = Currency.query.filter_by(code='VES').first()
    brl = Currency.query.filter_by(code='BRL').first()
    mxn = Currency.query.filter_by(code='MXN').first()
    
    if not all([ves, brl, mxn]):
        print("❌ Error: No se encontraron todas las monedas necesarias")
        exit(1)
    
    print(f"\n✅ Monedas encontradas:")
    print(f"   VES ID: {ves.id}")
    print(f"   BRL ID: {brl.id}")
    print(f"   MXN ID: {mxn.id}")
    
    # Obtener todos los métodos de pago
    payment_methods = PaymentMethod.query.all()
    
    print(f"\n📋 Procesando {len(payment_methods)} métodos de pago...")
    print("-" * 80)
    
    updated_count = 0
    
    for pm in payment_methods:
        # Obtener la cotización de VES (fuente de verdad)
        quote_ves = Quote.query.filter_by(
            payment_method_id=pm.id,
            currency_id=ves.id
        ).first()
        
        if not quote_ves:
            print(f"⚠️  {pm.name}: No tiene cotización en VES, saltando...")
            continue
        
        # Actualizar BRL
        quote_brl = Quote.query.filter_by(
            payment_method_id=pm.id,
            currency_id=brl.id
        ).first()
        
        if quote_brl:
            # Copiar valores de VES
            quote_brl.value_type = quote_ves.value_type
            quote_brl.usd_value = quote_ves.usd_value
            quote_brl.usd_formula = quote_ves.usd_formula
            quote_brl.calculated_usd = quote_ves.calculated_usd
            
            # Recalcular valor final con la tasa de BRL
            quote_brl.calculate_final_value()
            updated_count += 1
        
        # Actualizar MXN
        quote_mxn = Quote.query.filter_by(
            payment_method_id=pm.id,
            currency_id=mxn.id
        ).first()
        
        if quote_mxn:
            # Copiar valores de VES
            quote_mxn.value_type = quote_ves.value_type
            quote_mxn.usd_value = quote_ves.usd_value
            quote_mxn.usd_formula = quote_ves.usd_formula
            quote_mxn.calculated_usd = quote_ves.calculated_usd
            
            # Recalcular valor final con la tasa de MXN
            quote_mxn.calculate_final_value()
            updated_count += 1
        
        # Mostrar progreso
        print(f"✅ {pm.name:<20} VES: {quote_ves.value_type:<8} USD: {float(quote_ves.calculated_usd):.4f}")
    
    # Guardar cambios
    try:
        db.session.commit()
        print("\n" + "=" * 80)
        print(f"✅ ÉXITO: {updated_count} cotizaciones actualizadas")
        print("=" * 80)
        
        # Verificar resultados
        print("\n📊 VERIFICACIÓN:")
        print("-" * 80)
        
        brl_quotes = Quote.query.filter_by(currency_id=brl.id).all()
        mxn_quotes = Quote.query.filter_by(currency_id=mxn.id).all()
        
        brl_values = set([float(q.calculated_usd) for q in brl_quotes if q.calculated_usd])
        mxn_values = set([float(q.calculated_usd) for q in mxn_quotes if q.calculated_usd])
        
        print(f"\nBRL - Valores USD únicos: {len(brl_values)}")
        print(f"MXN - Valores USD únicos: {len(mxn_values)}")
        
        if len(brl_values) > 1:
            print(f"✅ BRL ahora tiene valores variados (correcto)")
        if len(mxn_values) > 1:
            print(f"✅ MXN ahora tiene valores variados (correcto)")
        
        # Mostrar algunos ejemplos
        print("\n📋 EJEMPLOS DE VALORES CORREGIDOS:")
        print("-" * 80)
        
        examples = ['PAYPAL', 'ZELLE', 'USDT']
        for code in examples:
            pm = PaymentMethod.query.filter_by(code=code).first()
            if pm:
                q_brl = Quote.query.filter_by(payment_method_id=pm.id, currency_id=brl.id).first()
                q_mxn = Quote.query.filter_by(payment_method_id=pm.id, currency_id=mxn.id).first()
                
                if q_brl and q_mxn:
                    print(f"\n{pm.name}:")
                    print(f"  BRL: USD={float(q_brl.calculated_usd):.4f} → Final={float(q_brl.final_value):.2f}")
                    print(f"  MXN: USD={float(q_mxn.calculated_usd):.4f} → Final={float(q_mxn.final_value):.2f}")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ ERROR al guardar cambios: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("PROCESO COMPLETADO")
    print("=" * 80)
