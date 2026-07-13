"""
Limpieza de órdenes DRAFT abandonadas.

Las órdenes en DRAFT son las de quien llenó los datos pero **nunca subió el
comprobante** (curiosos probando la plataforma). No estorban a la conciliación
—que solo mira las PENDING— pero sí ensucian la tabla de órdenes.

Se CANCELAN, no se borran: quedan para las métricas de embudo (cuánta gente
abandona y en qué paso).

Uso:
    python scripts/cleanup_orders.py --dry-run    # solo listar
    python scripts/cleanup_orders.py              # cancelar DRAFT de +48h
    python scripts/cleanup_orders.py --hours 72
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.models.order import Order, OrderStatus

DEFAULT_HOURS = 48


def main() -> int:
    """Cancelar las órdenes DRAFT abandonadas más antiguas que N horas."""
    parser = argparse.ArgumentParser(description='Limpieza de órdenes DRAFT')
    parser.add_argument('--hours', type=int, default=DEFAULT_HOURS,
                        help=f'Antigüedad mínima (por defecto {DEFAULT_HOURS}h)')
    parser.add_argument('--dry-run', action='store_true', help='Listar sin cancelar')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        limite = datetime.utcnow() - timedelta(hours=args.hours)

        abandonadas = (
            Order.query
            .filter(Order.status == OrderStatus.DRAFT)
            .filter(Order.created_at < limite)
            .filter(Order.payment_proof_url.is_(None))
            .all()
        )

        canceladas = 0
        for orden in abandonadas:
            if args.dry_run:
                print(f"[dry-run] cancelaría: {orden.reference} "
                      f"(creada {orden.created_at})")
            else:
                ok, msg = orden.transition_to(OrderStatus.CANCELLED)
                if ok:
                    orden.save()
                    print(f"🚫 cancelada: {orden.reference}")
                else:
                    print(f"⚠️  no se pudo cancelar {orden.reference}: {msg}")
                    continue
            canceladas += 1

        accion = 'se cancelarían' if args.dry_run else 'canceladas'
        print(f"\n✅ Órdenes DRAFT abandonadas {accion}: {canceladas}")
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
