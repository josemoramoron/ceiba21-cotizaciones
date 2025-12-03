"""
Script para arreglar monedas existentes que no tienen
tasas de cambio o cotizaciones configuradas correctamente
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Currency, ExchangeRate, Quote, PaymentMethod

def fix_all_currencies():
    """Arregla todas las monedas existentes"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("ARREGLANDO MONEDAS EXISTENTES")
        print("=" * 60)
        
        currencies = Currency.query.all()
        
        for currency in currencies:
            print(f"\n📋 Procesando {currency.code} ({currency.name})...")
            
            # Verificar tasa de cambio
            exchange_rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
            if not exchange_rate:
                print(f"  ⚠️  No tiene tasa de cambio")
            else:
                print(f"  ✅ Tasa de cambio: 1 USD = {exchange_rate.rate} {currency.code}")
            
            # Verificar cotizaciones
            quotes = Quote.query.filter_by(currency_id=currency.id).all()
            print(f"  📊 Cotizaciones existentes: {len(quotes)}")
            
            # Contar cotizaciones en cero
            zero_quotes = [q for q in quotes if not q.final_value or q.final_value == 0]
            if zero_quotes:
                print(f"  ⚠️  {len(zero_quotes)} cotizaciones en 0")
            
            # Inicializar si es necesario
            needs_fix = not exchange_rate or zero_quotes or len(quotes) == 0
            
            if needs_fix:
                print(f"  🔧 Inicializando {currency.code}...")
                success, message, details = currency.initialize_for_trading()
                
                if success:
                    print(f"  ✅ {message}")
                    if details.get('quotes_created', 0) > 0:
                        print(f"     - {details['quotes_created']} nuevas cotizaciones creadas")
                else:
                    print(f"  ❌ Error: {message}")
        
        print("\n" + "=" * 60)
        print("RESUMEN FINAL")
        print("=" * 60)
        
        # Mostrar estado final
        for currency in Currency.query.all():
            exchange_rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
            quotes = Quote.query.filter_by(currency_id=currency.id).all()
            zero_quotes = [q for q in quotes if not q.final_value or q.final_value == 0]
            
            status = "✅" if exchange_rate and not zero_quotes else "⚠️"
            print(f"{status} {currency.code}: Tasa={'Sí' if exchange_rate else 'No'}, "
                  f"Cotizaciones={len(quotes)}, En cero={len(zero_quotes)}")
        
        print("\n✅ Proceso completado\n")

if __name__ == '__main__':
    fix_all_currencies()
