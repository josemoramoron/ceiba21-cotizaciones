#!/usr/bin/env python3
"""
Script para diagnosticar el estado de las monedas BRL y MXN
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import Currency, ExchangeRate, Quote, PaymentMethod

app = create_app()

with app.app_context():
    print("=" * 80)
    print("DIAGNÓSTICO DE MONEDAS")
    print("=" * 80)
    
    # 1. Verificar todas las monedas
    print("\n1. MONEDAS REGISTRADAS:")
    print("-" * 80)
    currencies = Currency.query.order_by(Currency.code).all()
    for curr in currencies:
        print(f"  [{curr.code:4s}] {curr.name:20s} - Activa: {curr.active} - Order: {curr.display_order}")
    
    # 2. Verificar tasas de cambio
    print("\n2. TASAS DE CAMBIO:")
    print("-" * 80)
    exchange_rates = ExchangeRate.query.join(Currency).order_by(Currency.code).all()
    rates_dict = {}
    for rate in exchange_rates:
        rates_dict[rate.currency.code] = rate.rate
        print(f"  [{rate.currency.code:4s}] Rate: {rate.rate:>10.2f} - Source: {rate.source_type}")
    
    # 3. Verificar monedas sin tasa de cambio
    print("\n3. MONEDAS SIN TASA DE CAMBIO:")
    print("-" * 80)
    currencies_without_rate = []
    for curr in currencies:
        if curr.code not in rates_dict:
            currencies_without_rate.append(curr.code)
            print(f"  ⚠️  {curr.code} - {curr.name}")
    
    if not currencies_without_rate:
        print("  ✅ Todas las monedas tienen tasa de cambio")
    
    # 4. Verificar métodos de pago
    print("\n4. MÉTODOS DE PAGO ACTIVOS:")
    print("-" * 80)
    payment_methods = PaymentMethod.query.filter_by(active=True).order_by(
        PaymentMethod.display_order
    ).all()
    print(f"  Total: {len(payment_methods)}")
    for pm in payment_methods:
        print(f"  [{pm.code:15s}] {pm.name:20s} - Order: {pm.display_order}")
    
    # 5. Verificar cotizaciones para BRL y MXN
    print("\n5. COTIZACIONES POR MONEDA:")
    print("-" * 80)
    
    target_currencies = ['BRL', 'MXN', 'VES', 'COP', 'ARS', 'CLP']
    
    for curr_code in target_currencies:
        curr = Currency.query.filter_by(code=curr_code).first()
        if not curr:
            print(f"  ❌ {curr_code}: Moneda no existe")
            continue
        
        quotes = Quote.query.filter_by(currency_id=curr.id).all()
        print(f"\n  {curr_code} (ID: {curr.id}) - {len(quotes)} cotizaciones:")
        
        if len(quotes) == 0:
            print(f"    ❌ NO tiene cotizaciones")
        else:
            for quote in quotes:
                pm = PaymentMethod.query.get(quote.payment_method_id)
                pm_name = pm.name if pm else "Unknown"
                print(f"    - {pm_name:20s}: USD={quote.calculated_usd:>8.2f} Final={quote.final_value:>12.2f}")
    
    # 6. Conteo de cotizaciones por moneda
    print("\n6. RESUMEN DE COTIZACIONES:")
    print("-" * 80)
    for curr in currencies:
        quote_count = Quote.query.filter_by(currency_id=curr.id).count()
        status = "✅" if quote_count == len(payment_methods) else "⚠️"
        print(f"  {status} [{curr.code:4s}] {quote_count}/{len(payment_methods)} cotizaciones")
    
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO COMPLETADO")
    print("=" * 80)
