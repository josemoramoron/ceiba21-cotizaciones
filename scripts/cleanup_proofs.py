"""
Limpieza de comprobantes huérfanos.

Borra los archivos de ``app/static/proofs/`` que **no están referenciados por
ninguna orden** (ni en ``payment_proof_url`` ni en ``operator_proof_url``) y que
superan cierta antigüedad. Son restos de flujos abandonados o de gente probando
el clip del chat.

Los comprobantes que SÍ pertenecen a una orden NUNCA se borran: son evidencia
de pago y su retención es una decisión de negocio, no de mantenimiento.

Uso:
    python scripts/cleanup_proofs.py --dry-run     # solo listar (recomendado la primera vez)
    python scripts/cleanup_proofs.py               # borrar huérfanos de más de 7 días
    python scripts/cleanup_proofs.py --days 30     # cambiar la antigüedad mínima
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.models.order import Order

PROOFS_DIR = os.path.join('app', 'static', 'proofs')
DEFAULT_DAYS = 7


def _referenciados() -> set:
    """Nombres de archivo de comprobantes referenciados por alguna orden."""
    nombres = set()
    columnas = (Order.payment_proof_url, Order.operator_proof_url)
    for columna in columnas:
        for (url,) in Order.query.with_entities(columna).filter(columna.isnot(None)):
            if url:
                nombres.add(os.path.basename(url))
    return nombres


def _humano(num_bytes: int) -> str:
    """Formatear un tamaño en unidades legibles."""
    for unidad in ('B', 'KB', 'MB', 'GB'):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unidad}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def main() -> int:
    """Borrar los comprobantes huérfanos más antiguos que N días."""
    parser = argparse.ArgumentParser(description='Limpieza de comprobantes huérfanos')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS,
                        help=f'Antigüedad mínima en días (por defecto {DEFAULT_DAYS})')
    parser.add_argument('--dry-run', action='store_true',
                        help='Listar sin borrar')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if not os.path.isdir(PROOFS_DIR):
            print(f"ℹ️  No existe {PROOFS_DIR}: nada que limpiar.")
            return 0

        en_uso = _referenciados()
        limite = time.time() - (args.days * 86400)

        borrados, liberado, conservados = 0, 0, 0

        for nombre in os.listdir(PROOFS_DIR):
            ruta = os.path.join(PROOFS_DIR, nombre)
            if not os.path.isfile(ruta) or nombre == '.gitkeep':
                continue

            if nombre in en_uso:
                conservados += 1
                continue

            if os.path.getmtime(ruta) > limite:
                continue  # huérfano, pero aún reciente

            tamano = os.path.getsize(ruta)
            if args.dry_run:
                print(f"[dry-run] borraría: {nombre} ({_humano(tamano)})")
            else:
                os.remove(ruta)
                print(f"🗑️  borrado: {nombre} ({_humano(tamano)})")
            borrados += 1
            liberado += tamano

        accion = 'se borrarían' if args.dry_run else 'borrados'
        print(
            f"\n✅ Huérfanos {accion}: {borrados} ({_humano(liberado)} liberados). "
            f"Conservados por pertenecer a una orden: {conservados}."
        )
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
