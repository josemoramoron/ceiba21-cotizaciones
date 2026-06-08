"""
Migracion de datos: paypal_payments -> payments.

Copia cada registro de la tabla legacy `paypal_payments` a la nueva tabla
unificada `payments`, mapeando los campos renombrados y trasladando lo
especifico de PayPal (subtipo, direccion de envio) a datos_extra.

- NO modifica ni borra paypal_payments (solo lee). El corte de rutas/servicios
  a la nueva tabla es una fase posterior.
- Idempotente: omite los pagos cuyo email_message_id ya exista en payments,
  asi que puede ejecutarse varias veces sin duplicar.
- Preserva created_at / updated_at originales (integridad para contabilidad).

Uso (ejecutar PRIMERO en dev, que ya tiene los datos de produccion):
    python scripts/migrate_paypal_to_payments.py             # ejecuta la migracion
    python scripts/migrate_paypal_to_payments.py --dry-run   # solo reporta, no escribe
"""
import os
import sys

# Permitir importar el paquete `app` al correr el script desde la raiz del repo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.models import db
from app.models.paypal_payment import PaypalPayment, PaypalPaymentType
from app.models.payment import Payment, PaymentProvider, PaypalSubtipo


def _construir_datos_extra(origen: PaypalPayment) -> dict:
    """Arma datos_extra a partir del registro PayPal legacy."""
    subtipo = (
        PaypalSubtipo.GS
        if origen.tipo_pago == PaypalPaymentType.COMERCIAL
        else PaypalSubtipo.FF
    )
    datos: dict = {'subtipo': subtipo}
    if origen.direccion_envio:
        datos['direccion_envio'] = origen.direccion_envio
    return datos


def _mapear_a_payment(origen: PaypalPayment) -> Payment:
    """Crea un Payment (sin guardar) desde un PaypalPayment legacy."""
    return Payment(
        email_message_id=origen.email_message_id,
        cuenta_destino=origen.cuenta_destino,
        metodo=PaymentProvider.PAYPAL,
        pagador_nombre=origen.pagador_nombre,
        importe_bruto=origen.importe_bruto,
        moneda=origen.moneda,
        comision=origen.comision_paypal,
        importe_neto=origen.importe_neto,
        transaction_id=origen.paypal_transaction_id,
        fecha_pago=origen.fecha_pago,
        cotizacion_id=origen.cotizacion_id,
        tasa_aplicada=origen.tasa_aplicada,
        valor_a_pagar=origen.valor_a_pagar,
        moneda_pago_local=origen.moneda_pago_local,
        estado=origen.estado,
        notas=origen.notas,
        procesado_por=origen.procesado_por,
        datos_extra=_construir_datos_extra(origen),
        created_at=origen.created_at,
        updated_at=origen.updated_at,
    )


def migrar(dry_run: bool = False) -> dict:
    """
    Ejecuta la migracion paypal_payments -> payments.

    Args:
        dry_run: Si True, no escribe en BD; solo reporta lo que haria.

    Returns:
        dict con conteos: total, migrados, omitidos, errores.
    """
    resumen = {'total': 0, 'migrados': 0, 'omitidos': 0, 'errores': 0}

    origenes = PaypalPayment.query.order_by(PaypalPayment.id).all()
    resumen['total'] = len(origenes)
    print(f"Registros en paypal_payments: {resumen['total']}")

    nuevos = []
    for origen in origenes:
        if Payment.get_by_email_message_id(origen.email_message_id):
            resumen['omitidos'] += 1
            continue
        try:
            nuevos.append(_mapear_a_payment(origen))
            resumen['migrados'] += 1
        except (AttributeError, KeyError, TypeError) as e:
            resumen['errores'] += 1
            print(f"  Error mapeando paypal_payment #{origen.id}: {e}")

    if dry_run:
        print("DRY-RUN: no se escribio nada en la base de datos.")
        return resumen

    if not nuevos:
        print("No hay registros nuevos para migrar.")
        return resumen

    try:
        db.session.add_all(nuevos)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error guardando en payments (rollback aplicado): {e}")
        resumen['errores'] += resumen['migrados']
        resumen['migrados'] = 0

    return resumen


def main() -> None:
    """Punto de entrada del script."""
    dry_run = '--dry-run' in sys.argv
    app = create_app()
    with app.app_context():
        # Asegura que la tabla payments exista (no toca las demas)
        db.create_all()

        resumen = migrar(dry_run=dry_run)

        total_payments = Payment.query.count()
        print("\n--- Resumen ---")
        print(f"Origen (paypal_payments):    {resumen['total']}")
        print(f"Migrados:                    {resumen['migrados']}")
        print(f"Omitidos (ya existian):      {resumen['omitidos']}")
        print(f"Errores:                     {resumen['errores']}")
        print(f"Total ahora en payments:     {total_payments}")


if __name__ == '__main__':
    main()