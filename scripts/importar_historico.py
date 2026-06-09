"""
Importación histórica one-time de pagos desde una fecha (PayPal, Zelle, Wise).

CORRER POR TERMINAL, no por el dashboard. Un backfill de cientos de correos
descarga cada correo por IMAP uno a uno y tarda varios minutos, lo que excede el
timeout de Gunicorn (120s) y mata al worker a mitad del proceso (WORKER TIMEOUT),
dejando la importación incompleta. Por terminal no hay timeout.

Hace lo mismo que el botón "Importar desde" del dashboard: procesa TODOS los
correos (leídos y no leídos) de las fuentes activas desde la fecha dada y los
marca como leídos. Es dedup-safe: los pagos ya existentes (por message_id /
transaction_id) se cuentan como duplicados, no se re-insertan.

Uso:
    python scripts/importar_historico.py 2026-06-01
"""
import os
import sys
from datetime import datetime

# Permitir importar el paquete `app` al correr el script desde la raíz del repo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.unified_ingestion_service import UnifiedIngestionService


def main() -> None:
    """Importa el histórico desde la fecha pasada como argumento (YYYY-MM-DD)."""
    if len(sys.argv) != 2:
        print("Uso: python scripts/importar_historico.py YYYY-MM-DD")
        print("Ejemplo: python scripts/importar_historico.py 2026-06-01")
        sys.exit(1)

    desde_iso = sys.argv[1]
    try:
        dt = datetime.strptime(desde_iso, '%Y-%m-%d')
    except ValueError:
        print(f"Fecha inválida: '{desde_iso}'. Formato esperado: YYYY-MM-DD")
        sys.exit(1)

    desde_imap = dt.strftime('%d-%b-%Y')  # '01-Jun-2026'

    app = create_app()
    with app.app_context():
        print(f"Importando correos desde {desde_iso} ({desde_imap})...")
        print("Puede tardar varios minutos según el volumen. No interrumpas.")
        service = UnifiedIngestionService()
        resultado = service.procesar_desde_fecha(desde_imap, web_user_id=None)
        print(resultado.get('mensaje', resultado))


if __name__ == '__main__':
    main()