"""
Crea las tablas del módulo SMS y siembra los slots del board.

Idempotente: db.create_all() solo crea las tablas que falten, y ensure_slots
solo inserta los slots inexistentes. Seguro de correr varias veces.

Uso (en la RPi, dentro del venv de Ceiba21):
    cd /var/www/cotizaciones
    source venv/bin/activate
    python scripts/init_sms.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.models import db
from app.services.sms_service import SmsService

TOTAL_SIM_SLOTS = 20


def main() -> None:
    """Crea tablas SMS y siembra los slots del board."""
    app = create_app()
    with app.app_context():
        db.create_all()
        SmsService.ensure_slots(TOTAL_SIM_SLOTS)
        print(f'✅ Tablas SMS creadas y {TOTAL_SIM_SLOTS} slots sembrados.')


if __name__ == '__main__':
    main()
