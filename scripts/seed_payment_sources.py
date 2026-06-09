"""
Siembra las fuentes de pago conocidas: PayPal, Wise y Zelle (vía Bank of America).

Necesario en CADA entorno (dev y prod) para que la ingesta sepa qué remitentes
vigilar. Sin fuentes activas, run_ingesta.py / el scheduler reportan
"No hay fuentes de pago activas configuradas" y no procesan nada.

Idempotente: PaymentSource.crear_defaults() solo inserta las que falten, así que
puede correrse varias veces sin duplicar.

Uso:
    python scripts/seed_payment_sources.py
"""
import os
import sys

# Permitir importar el paquete `app` al correr el script desde la raíz del repo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.payment_source import PaymentSource


def main() -> None:
    """Siembra las fuentes por defecto y reporta el estado resultante."""
    app = create_app()
    with app.app_context():
        creadas = PaymentSource.crear_defaults()
        activas = PaymentSource.get_activos()

        print(f"Fuentes creadas en esta corrida: {creadas}")
        print(f"Fuentes activas ahora: {len(activas)}")
        for fuente in activas:
            print(f"  - {fuente.nombre}: {fuente.remitente} ({fuente.metodo})")


if __name__ == '__main__':
    main()