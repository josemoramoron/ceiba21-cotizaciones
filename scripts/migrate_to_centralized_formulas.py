#!/usr/bin/env python3
"""
Script de migración: Centralizar fórmulas en PaymentMethod
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, PaymentMethod, Quote, Currency

app = create_app()

with app.app_context():
    print("=" * 80)
    print("MIGRACIÓN: CENTRALIZAR FÓRMULAS EN PAYMENT_METHOD")
    print("=" * 80)
    
    # Paso 1: Agregar columnas a payment_methods (si no existen)
    print("\n📋 Paso 1: Verificando estructura de base de datos...")
    print("-" * 80)
    
    try:
        # Intentar agregar las columnas
        with db.engine.connect() as conn:
            # Verificar si las columnas ya existen
            result = conn.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='payment_methods' 
                AND column_name IN ('value_type', 'usd_value', 'usd_formula')
            """))
            existing_columns = [row[0] for row in result]
            
            if 'value_type' not in existing_columns:
                print("  Agregando columna 'value_type'...")
                conn.execute(db.text("""
                    ALTER TABLE payment_methods 
                    ADD COLUMN value_type VARCHAR(20) DEFAULT 'manual'
                """))
                conn.commit()
                print("  ✅ Columna 'value_type' agregada")
            else:
                print("  ✅ Columna 'value_type' ya existe")
            
            if 'usd_value' not in existing_columns:
                print("  Agregando columna 'usd_value'...")
                conn.execute(db.text("""
                    ALTER TABLE payment_methods 
                    ADD COLUMN usd_value NUMERIC(10, 6)
                """))
                conn.commit()
                print("  ✅ Columna 'usd_value' agregada")
            else:
                print("  ✅ Columna 'usd_value' ya existe")
            
            if 'usd_formula' not in existing_columns:
                print("  Agregando columna 'usd_formula'...")
                conn.execute(db.text("""
                    ALTER TABLE payment_methods 
                    ADD COLUMN usd_formula VARCHAR(200)
                """))
                conn.commit()
                print("  ✅ Columna 'usd_formula' agregada")
            else:
                print("  ✅ Columna 'usd_formula' ya existe")
    
    except Exception as e:
        print(f"  ⚠️  Error al agregar columnas: {e}")
        print("  Continuando con la migración de datos...")
    
    # Paso 2: Migrar datos desde Quote (usando VES como referencia)
    print("\n📋 Paso 2: Migrando datos a PaymentMethod...")
    print("-" * 80)
    
    ves = Currency.query.filter_by(code='VES').first()
    if not ves:
        print("❌ Error: Moneda VES no encontrada. Usando primera moneda activa...")
        ves = Currency.query.filter_by(active=True).first()
    
    if not ves:
        print("❌ Error: No hay monedas activas disponibles")
        exit(1)
    
    payment_methods = PaymentMethod.query.all()
    migrated_count = 0
    
    for pm in payment_methods:
        # Buscar cotización de VES para este método de pago
        quote = Quote.query.filter_by(
            payment_method_id=pm.id,
            currency_id=ves.id
        ).first()
        
        if quote:
            # Migrar valores del Quote al PaymentMethod
            pm.value_type = quote.value_type
            pm.usd_value = quote.usd_value
            pm.usd_formula = quote.usd_formula
            migrated_count += 1
            
            print(f"  ✅ {pm.name:<20} type={pm.value_type:<8} ", end="")
            if pm.value_type == 'formula':
                print(f"formula='{pm.usd_formula}'")
            else:
                print(f"value={pm.usd_value}")
        else:
            # Valor por defecto
            pm.value_type = 'manual'
            pm.usd_value = 1.0
            pm.usd_formula = None
            print(f"  ⚠️  {pm.name:<20} Sin cotización VES, usando valor por defecto")
    
    db.session.commit()
    
    print(f"\n✅ {migrated_count}/{len(payment_methods)} métodos migrados")
    
    # Paso 3: Recalcular todas las cotizaciones
    print("\n📋 Paso 3: Recalculando todas las cotizaciones...")
    print("-" * 80)
    
    quotes = Quote.query.all()
    for quote in quotes:
        quote.calculate_final_value()
    
    db.session.commit()
    
    print(f"✅ {len(quotes)} cotizaciones recalculadas")
    
    # Paso 4: Verificación
    print("\n📋 Paso 4: Verificación...")
    print("-" * 80)
    
    # Verificar que los valores son correctos
    test_methods = ['PAYPAL', 'ZELLE', 'USDT']
    test_currencies = ['VES', 'COP', 'BRL', 'MXN']
    
    print("\nEjemplos de valores calculados:")
    for pm_code in test_methods:
        pm = PaymentMethod.query.filter_by(code=pm_code).first()
        if pm:
            usd_val = pm.calculate_usd_value()
            print(f"\n{pm.name} (USD: {usd_val:.4f}):")
            
            for curr_code in test_currencies:
                curr = Currency.query.filter_by(code=curr_code).first()
                if curr:
                    quote = Quote.query.filter_by(
                        payment_method_id=pm.id,
                        currency_id=curr.id
                    ).first()
                    
                    if quote:
                        print(f"  {curr_code}: {float(quote.final_value):.2f}")
    
    print("\n" + "=" * 80)
    print("✅ MIGRACIÓN COMPLETADA")
    print("=" * 80)
    
    print("\n📝 IMPORTANTE:")
    print("   - Las fórmulas ahora están centralizadas en PaymentMethod")
    print("   - Al cambiar una fórmula, se aplica automáticamente a TODAS las monedas")
    print("   - Solo necesitas actualizar el PaymentMethod, no cada Quote")
    print("   - Reinicia el servidor para aplicar los cambios: kill -HUP 4401")
