"""
Corrida única de la ingesta unificada de pagos.

Para PRODUCCIÓN: lo invoca cron cada 5 minutos. Un solo proceso por ejecución,
lo que evita la condición de carrera de tener el scheduler embebido en cada
worker de Gunicorn. En DEV se sigue usando el scheduler embebido (gateado por
FLASK_ENV=development en create_app), con su botón de pausa.

Reutiliza exactamente UnifiedIngestionService.procesar_nuevos_pagos, así que el
comportamiento es idéntico al del scheduler (UNSEEN, marcar_leidos=True, dedup).

Uso manual:
    python scripts/run_ingesta.py

Cron en el Raspberry (cada 5 min, con flock para no solapar corridas lentas):
    */5 * * * * /usr/bin/flock -n /tmp/ceiba21_ingesta.lock \\
        /var/www/cotizaciones/venv/bin/python \\
        /var/www/cotizaciones/scripts/run_ingesta.py \\
        >> /home/webmaster/logs/ingesta.log 2>&1
"""
import os
import sys
from datetime import datetime

# Permitir importar el paquete `app` al correr el script desde la raíz del repo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.unified_ingestion_service import UnifiedIngestionService


def main() -> None:
    """Ejecuta una corrida de la ingesta y reporta el resultado por stdout."""
    app = create_app()
    with app.app_context():
        service = UnifiedIngestionService()
        resultado = service.procesar_nuevos_pagos(web_user_id=None)
        marca = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{marca}] {resultado.get('mensaje', resultado)}")


if __name__ == '__main__':
    main()