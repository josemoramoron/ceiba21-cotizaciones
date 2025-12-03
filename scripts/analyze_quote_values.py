#!/usr/bin/env python3
"""
Script para analizar los valores de las cotizaciones
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import Currency, Quote, PaymentMethod

app = create_app()

with app.app_context():
    print("=" * 80)
    print("ANÁLISIS DE COTIZACIONES - COMPARATIVA")
    print("=" * 80)
    
    # Obtener monedas
    ves = Currency.query.filter_by(code='VES').first()
    brl = Currency.query.filter_by(code='BRL').first()
    mxn = Currency.query.filter_by(code='MXN').first()
    cop = Currency.query.filter_by(code='COP').first()
    
    # Obtener algunos métodos de pago para comparar
    payment_methods = PaymentMethod.query.order_by(PaymentMethod.display_order).limit(10).all()
    
    print("\n" + "=" * 80)
    print("COMPARACIÓN DE VALORES USD POR MÉTODO DE PAGO")
    print("=" * 80)
    print(f"\n{'Método de Pago':<20} {'VES USD':<10} {'BRL USD':<10} {'MXN USD':<10} {'COP USD':<10}")
    print("-" * 80)
    
    for pm in payment_methods:
        quote_ves = Quote.query.filter_by(payment_method_id=pm.id, currency_id=ves.id).first()
        quote_brl = Quote.query.filter_by(payment_method_id=pm.id, currency_id=brl.id).first()
        quote_mxn = Quote.query.filter_by(payment_method_id=pm.id, currency_id=mxn.id).first()
        quote_cop = Quote.query.filter_by(payment_method_id=pm.id, currency_id=cop.id).first()
        
        ves_usd = float(quote_ves.calculated_usd) if quote_ves else 0
        brl_usd = float(quote_brl.calculated_usd) if quote_brl else 0
        mxn_usd = float(quote_mxn.calculated_usd) if quote_mxn else 0
        cop_usd = float(quote_cop.calculated_usd) if quote_cop else 0
        
        print(f"{pm.name:<20} {ves_usd:<10.4f} {brl_usd:<10.4f} {mxn_usd:<10.4f} {cop_usd:<10.4f}")
    
    # Detalles de un método específico
    print("\n" + "=" * 80)
    print("DETALLES DEL MÉTODO 'PAYPAL' EN CADA MONEDA")
    print("=" * 80)
    
    paypal = PaymentMethod.query.filter_by(code='PAYPAL').first()
    if paypal:
        for curr in [ves, cop, brl, mxn]:
            quote = Quote.query.filter_by(payment_method_id=paypal.id, currency_id=curr.id).first()
            if quote:
                print(f"\n{curr.code}:")
                print(f"  value_type: {quote.value_type}")
                print(f"  usd_value: {quote.usd_value}")
                print(f"  usd_formula: {quote.usd_formula}")
                print(f"  calculated_usd: {quote.calculated_usd}")
                print(f"  final_value: {quote.final_value}")
    
    print("\n" + "=" * 80)
    print("PROBLEMA IDENTIFICADO:")
    print("=" * 80)
    
    # Verificar si todos los valores de BRL y MXN son iguales
    brl_quotes = Quote.query.filter_by(currency_id=brl.id).all()
    mxn_quotes = Quote.query.filter_by(currency_id=mxn.id).all()
    
    brl_values = set([float(q.calculated_usd) for q in brl_quotes if q.calculated_usd])
    mxn_values = set([float(q.calculated_usd) for q in mxn_quotes if q.calculated_usd])
    
    print(f"\nBRL - Valores USD únicos: {brl_values}")
    print(f"MXN - Valores USD únicos: {mxn_values}")
    
    if len(brl_values) == 1:
        print(f"\n⚠️  PROBLEMA: Todas las cotizaciones de BRL tienen el mismo valor USD: {list(brl_values)[0]}")
    if len(mxn_values) == 1:
        print(f"⚠️  PROBLEMA: Todas las cotizaciones de MXN tienen el mismo valor USD: {list(mxn_values)[0]}")
    
    print("\n" + "=" * 80)
