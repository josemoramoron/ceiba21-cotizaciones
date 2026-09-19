"""
Script para poblar la base de datos Ceiba21
Sistema basado en USD como moneda base
"""
import sys
sys.path.insert(0, '/var/www/cotizaciones')

from app import create_app
from app.models import db, Currency, PaymentMethod, Quote, ExchangeRate

import logging

logger = logging.getLogger(__name__)

def seed_currencies():
    """Crear las 4 monedas principales"""
    currencies = [
        {'code': 'BS', 'name': 'Bolívares', 'symbol': 'Bs'},
        {'code': 'COP', 'name': 'Peso Colombiano', 'symbol': '$'},
        {'code': 'CLP', 'name': 'Peso Chileno', 'symbol': '$'},
        {'code': 'ARS', 'name': 'Peso Argentino', 'symbol': '$'},
    ]
    
    print("📊 Creando monedas...")
    for curr_data in currencies:
        currency = Currency.query.filter_by(code=curr_data['code']).first()
        if not currency:
            currency = Currency(**curr_data)
            db.session.add(currency)
            print(f"   ✅ {curr_data['name']} ({curr_data['code']})")
        else:
            print(f"   ⏭️  {curr_data['name']} ya existe")
    
    db.session.commit()

def seed_exchange_rates():
    """Crear tasas de cambio USD → Monedas (basado en tu Google Sheets)"""
    rates_data = [
        {'code': 'BS', 'rate': 308.17},
        {'code': 'COP', 'rate': 3721.03},
        {'code': 'CLP', 'rate': 911.34},
        {'code': 'ARS', 'rate': 735.00},
    ]
    
    print("\n💱 Creando tasas de cambio (USD → Monedas)...")
    for rate_data in rates_data:
        currency = Currency.query.filter_by(code=rate_data['code']).first()
        if currency:
            exchange_rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
            if not exchange_rate:
                exchange_rate = ExchangeRate(
                    currency_id=currency.id,
                    rate=rate_data['rate'],
                    source_type='manual'
                )
                db.session.add(exchange_rate)
                print(f"   ✅ 1 USD = {rate_data['rate']} {rate_data['code']}")
            else:
                exchange_rate.rate = rate_data['rate']
                print(f"   🔄 Actualizado: 1 USD = {rate_data['rate']} {rate_data['code']}")
    
    db.session.commit()

def seed_payment_methods():
    """Crear métodos de pago (sin Euro, lo agregarás después)"""
    payment_methods = [
        {'code': 'REF', 'name': 'REF', 'display_order': 1},
        {'code': 'PAYPAL', 'name': 'PayPal', 'display_order': 2},
        {'code': 'ZELLE', 'name': 'Zelle', 'display_order': 3},
        {'code': 'ZINLI', 'name': 'Zinli', 'display_order': 4},
        {'code': 'USDT', 'name': 'USDT', 'display_order': 5},
        {'code': 'WISE', 'name': 'Wise', 'display_order': 6},
        {'code': 'VENMO', 'name': 'Venmo', 'display_order': 7},
        {'code': 'AIRTM', 'name': 'Airtm', 'display_order': 8},
        {'code': 'PAYONEER', 'name': 'Payoneer', 'display_order': 9},
        {'code': 'SKRILL', 'name': 'Skrill', 'display_order': 10},
        {'code': 'VOLET', 'name': 'volet', 'display_order': 11},
        {'code': 'PAXUM', 'name': 'paxum', 'display_order': 12},
        {'code': 'EPAY_CHINA', 'name': 'Epay china', 'display_order': 13},
        {'code': 'EPAYSERVICES', 'name': 'EpayServices', 'display_order': 14},
        {'code': 'COSMOPAYMENT', 'name': 'CosmoPayment', 'display_order': 15},
        {'code': 'METAMASK', 'name': 'MetaMask', 'display_order': 16},
        {'code': 'PERFECTMONEY', 'name': 'PerfecMoney', 'display_order': 17},
        {'code': 'WEBMONEY', 'name': 'WebMoney', 'display_order': 18},
        {'code': 'NETELLER', 'name': 'Neteller', 'display_order': 19},
        {'code': 'USD_C21', 'name': 'USD -> C21', 'display_order': 20},
        {'code': 'C21_USD', 'name': 'C21 -> USD', 'display_order': 21},
    ]
    
    print("\n💳 Creando métodos de pago...")
    for pm_data in payment_methods:
        pm = PaymentMethod.query.filter_by(code=pm_data['code']).first()
        if not pm:
            pm = PaymentMethod(**pm_data)
            db.session.add(pm)
            print(f"   ✅ {pm_data['name']}")
        else:
            print(f"   ⏭️  {pm_data['name']} ya existe")
    
    db.session.commit()

def seed_quotes():
    """
    Crear cotizaciones en USD (base)
    Luego se calculan automáticamente para cada moneda
    """
    print("\n💰 Creando cotizaciones base (en USD)...")
    
    # Fórmulas en USD (basadas en tu Google Sheets)
    formulas_usd = [
    ('REF', 'manual', 1.0, None),
    ('PAYPAL', 'formula', None, '1 / 1.1'),
    ('ZELLE', 'formula', None, '1 / 1.06'),
    ('ZINLI', 'formula', None, '1 / 1.055'),
    ('USDT', 'formula', None, '1 / 1.04'),
    ('WISE', 'formula', None, '1 / 1.067'),
    ('VENMO', 'formula', None, '1 / 1.092'),
    ('AIRTM', 'formula', None, '1 / 1.05'),
    ('PAYONEER', 'formula', None, '1 / 1.116'),
    ('SKRILL', 'formula', None, '1 / 1.11'),
    ('VOLET', 'formula', None, '1 / 1.055'),
    ('PAXUM', 'formula', None, '1 / 1.08'),  # ← AGREGAR FÓRMULAS
    ('EPAY_CHINA', 'formula', None, '1 / 1.05'),
    ('EPAYSERVICES', 'formula', None, '1 / 1.06'),
    ('COSMOPAYMENT', 'formula', None, '1 / 1.07'),
    ('METAMASK', 'formula', None, '1 / 1.03'),
    ('PERFECTMONEY', 'formula', None, '1 / 1.04'),
    ('WEBMONEY', 'formula', None, '1 / 1.05'),
    ('NETELLER', 'formula', None, '1 / 1.06'),
    ('USD_C21', 'manual', 0.97, None),
    ('C21_USD', 'manual', 1.05, None),
]
    
    # Obtener todas las monedas
    currencies = Currency.query.all()
    
    # Crear cotizaciones para cada método de pago en cada moneda
    for code, value_type, usd_val, formula in formulas_usd:
        pm = PaymentMethod.query.filter_by(code=code).first()
        if not pm:
            continue
        
        for currency in currencies:
            quote = Quote.query.filter_by(
                payment_method_id=pm.id,
                currency_id=currency.id
            ).first()
            
            if not quote:
                # Calcular valor en USD
                if value_type == 'manual':
                    calc_usd = usd_val
                else:
                    # Evaluar fórmula
                    try:
                        calc_usd = eval(formula)
                    except Exception as e:
                        logger.warning(f"Formula USD invalida ({formula!r}) para {code}: {e}")
                        calc_usd = 1.0
                
                # Obtener tasa de cambio
                exchange_rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
                final_val = calc_usd * float(exchange_rate.rate) if exchange_rate else 0
                
                quote = Quote(
                    payment_method_id=pm.id,
                    currency_id=currency.id,
                    value_type=value_type,
                    usd_value=usd_val,
                    usd_formula=formula,
                    calculated_usd=calc_usd,
                    final_value=final_val
                )
                db.session.add(quote)
                
        print(f"   ✅ {pm.name} ({value_type})")
    
    db.session.commit()

def main():
    """Ejecutar población completa"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Poblando base de datos Ceiba21")
        print("📄 Sistema basado en USD\n")
        
        seed_currencies()
        seed_exchange_rates()
        seed_payment_methods()
        seed_quotes()
        
        print("\n" + "="*60)
        print("✅ ¡Base de datos poblada exitosamente!")
        print("="*60)
        print("\n📈 Resumen:")
        print(f"   - Monedas: {Currency.query.count()}")
        print(f"   - Tasas de cambio: {ExchangeRate.query.count()}")
        print(f"   - Métodos de pago: {PaymentMethod.query.count()}")
        print(f"   - Cotizaciones: {Quote.query.count()}")
        print("\n🎯 Próximo paso: Dashboard para gestionar cotizaciones")

if __name__ == '__main__':
    main()

