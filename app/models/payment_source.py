"""
Modelo de Fuentes de Pago (configuración de la ingesta).

Cada fila describe un remitente de correo que la ingesta debe vigilar y a qué
método de pago corresponde. Es editable desde el dashboard, de modo que se
puede activar/desactivar una fuente, vigilar un remitente nuevo o ajustar la
política de moneda SIN tocar código.

El parseo del HTML sigue siendo código (un parser por proveedor); esta tabla
solo gobierna QUÉ se busca y con qué política, no CÓMO se extraen los datos.
"""
from typing import List, Optional

from app.models import db
from app.models.base import BaseModel
from app.models.payment import PaymentProvider


class PaymentSource(BaseModel):
    """
    Fuente de ingesta de pagos.

    Attributes:
        nombre: Etiqueta legible (ej. 'PayPal', 'Bank of America (Zelle)').
        metodo: Método al que pertenece ('paypal', 'zelle', 'wise', ...).
        remitente: Dirección From a vigilar en Gmail (única).
        asunto_contiene: Filtro opcional de asunto (NULL = sin filtro). Útil
            para acotar remitentes ruidosos; dejar NULL para no perder
            variantes (ej. los payouts de PayPal con asuntos distintos).
        activo: Si la ingesta debe procesar esta fuente.
        auto_cotizar: Si se intenta cotización automática (solo aplica si USD).
        moneda_local_default: Moneda local de pago por defecto (NULL = usa la
            config global DEFAULT_LOCAL_CURRENCY).
        notas: Notas del operador.
    """

    __tablename__ = 'payment_sources'

    nombre = db.Column(
        db.String(100),
        nullable=False,
        comment='Etiqueta legible'
    )
    metodo = db.Column(
        db.String(20),
        nullable=False,
        index=True,
        comment="Metodo: 'paypal', 'zelle', 'wise', ..."
    )
    remitente = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        comment='Direccion From a vigilar en Gmail'
    )
    asunto_contiene = db.Column(
        db.String(255),
        nullable=True,
        comment='Filtro opcional de asunto (NULL = sin filtro)'
    )
    activo = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        comment='Si la ingesta procesa esta fuente'
    )
    auto_cotizar = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        comment='Intentar cotizacion automatica (solo si la moneda es USD)'
    )
    moneda_local_default = db.Column(
        db.String(10),
        nullable=True,
        comment='Moneda local por defecto (NULL = config global)'
    )
    notas = db.Column(db.Text, nullable=True, comment='Notas del operador')

    def __repr__(self) -> str:
        estado = 'activo' if self.activo else 'inactivo'
        return f'<PaymentSource {self.nombre} ({self.metodo}) [{estado}]>'

    @classmethod
    def get_activos(cls) -> List['PaymentSource']:
        """Fuentes activas (para construir la lista de remitentes a buscar)."""
        return cls.query.filter_by(activo=True).all()

    @classmethod
    def get_by_remitente(cls, remitente: str) -> Optional['PaymentSource']:
        """Busca una fuente por su direccion remitente."""
        return cls.query.filter_by(remitente=remitente).first()

    @classmethod
    def get_by_metodo(cls, metodo: str) -> List['PaymentSource']:
        """Fuentes asociadas a un metodo."""
        return cls.query.filter_by(metodo=metodo).all()

    @classmethod
    def crear_defaults(cls) -> int:
        """
        Inserta las fuentes conocidas si aun no existen (idempotente).

        Returns:
            int: cantidad de fuentes creadas en esta llamada.
        """
        defaults = [
            {
                'nombre': 'PayPal',
                'metodo': PaymentProvider.PAYPAL,
                'remitente': 'service@intl.paypal.com',
                # NULL a proposito: captura "Ha recibido un pago" Y los payouts
                # (You have a payout!, TIKTOK has sent you money, ...)
                'asunto_contiene': None,
            },
            {
                'nombre': 'Wise',
                'metodo': PaymentProvider.WISE,
                'remitente': 'noreply@wise.com',
                'asunto_contiene': None,
            },
            {
                'nombre': 'Bank of America (Zelle)',
                'metodo': PaymentProvider.ZELLE,
                'remitente': 'customerservice@ealerts.bankofamerica.com',
                'asunto_contiene': None,
            },
            {
                'nombre': 'Skrill',
                'metodo': PaymentProvider.SKRILL,
                'remitente': 'no-reply@email.skrill.com',
                'asunto_contiene': None,
            },
            {
                'nombre': 'Binance',
                'metodo': PaymentProvider.BINANCE,
                'remitente': 'do-not-reply@ses.binance.com',
                'asunto_contiene': None,
            },
        ]

        creadas = 0
        for cfg in defaults:
            if cls.get_by_remitente(cfg['remitente']):
                continue
            fuente = cls(**cfg)
            if fuente.save():
                creadas += 1
        return creadas