#!/usr/bin/env python3
"""
Agrega USD como moneda activa en la tabla currencies para
habilitar conversiones fiat↔fiat en la calculadora pública.

Solo crea Currency + ExchangeRate(1.0).
NO llama a initialize_for_trading() — no se crean quotes
para métodos de pago (USD es el pivote, no una moneda de
destino en el contexto de métodos de pago).

Ejecutar una sola vez en producción:

    source venv/bin/activate
    python scripts/seed_usd_currency.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db
from app.models.currency import Currency
from app.models.exchange_rate import ExchangeRate


def run() -> None:
    """Crea USD en currencies + ExchangeRate pivote = 1.0."""
    print('\n' + '=' * 60)
    print('💵  SEED USD PIVOT CURRENCY — CEIBA21')
    print('=' * 60 + '\n')

    app = create_app()

    with app.app_context():
        # ── 1. Currency USD ────────────────────────────────────────────
        usd = Currency.query.filter_by(code='USD').first()

        if usd is None:
            usd = Currency(
                code='USD',
                name='Dólar Estadounidense',
                symbol='$',
                active=True,
                display_order=0,
            )
            db.session.add(usd)
            db.session.flush()
            print('✅ Currency USD creada (display_order=0, aparece primero).')
        elif not usd.active:
            usd.active = True
            print('✅ Currency USD activada.')
        else:
            print('ℹ️  Currency USD ya existe y está activa.')

        # ── 2. ExchangeRate USD = 1.0 (pivote fijo) ────────────────────
        rate = ExchangeRate.query.filter_by(currency_id=usd.id).first()

        if rate is None:
            rate = ExchangeRate(
                currency_id=usd.id,
                rate=1.0,
                source_type='manual',
            )
            db.session.add(rate)
            print('✅ ExchangeRate USD = 1.0 creada (pivote).')
        else:
            rate.rate = 1.0
            print('✅ ExchangeRate USD = 1.0 garantizada (pivote).')

        db.session.commit()

    print('\n' + '=' * 60)
    print('USD listo. Aparecerá en la calculadora pública.')
    print('Nota: no se crearon cotizaciones método→USD.')
    print('=' * 60 + '\n')


if __name__ == '__main__':
    run()
