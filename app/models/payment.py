"""
Modelo de Pagos unificado (multi-método).

Reemplaza conceptualmente a PaypalPayment: una sola tabla `payments` recibe
los ingresos de TODOS los métodos (PayPal, Zelle, Wise, y los que se agreguen),
diferenciados por la columna `metodo`. Lo específico de cada proveedor vive en
la columna JSONB `datos_extra`, de modo que agregar un método nuevo NO requiere
alterar el esquema.

Convivencia: este modelo se crea AL LADO de paypal_payments (no lo toca).
La migración de datos y el corte se harán en una fase posterior.

La lógica de cálculo de valor a pagar sigue en:
    app/services/calculator_service.py
"""
from typing import Optional, Dict, Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict

from app.models import db
from app.models.base import BaseModel


class PaymentProvider:
    """Métodos de pago soportados por la ingesta (valor de la columna `metodo`)."""
    PAYPAL = 'paypal'
    ZELLE = 'zelle'
    WISE = 'wise'
    SKRILL = 'skrill'
    BINANCE = 'binance'

    TODOS = (PAYPAL, ZELLE, WISE, SKRILL, BINANCE)


class PaymentStatus:
    """Estados posibles de un pago (genéricos para cualquier método)."""
    PENDIENTE = 'pendiente'    # Recibido, sin procesar
    PROCESADO = 'procesado'    # Tasa aplicada, listo para pagar
    PAGADO = 'pagado'          # Pago enviado al cliente
    REVISION = 'revision'      # Requiere revisión manual
    MANUAL = 'manual'          # Moneda no USD, requiere llenado manual


class PaypalSubtipo:
    """Subtipos de pago PayPal (se guardan en datos_extra['subtipo'])."""
    FF = 'ff'              # Friends & Family (sin comisión)
    GS = 'gs'             # Goods & Services (con comisión)
    PAYOUT = 'payout'     # Payout de plataforma (TikTok, Clapper, etc.)


class Payment(BaseModel):
    """
    Pago recibido por cualquier método, capturado desde Gmail.

    Columnas genéricas comunes a todos los métodos. Lo que es propio de un
    proveedor (subtipo PayPal, dirección de envío, memo de Zelle, etc.) se
    guarda en `datos_extra` para no tener columnas nullable por proveedor.

    Attributes:
        email_message_id: ID único del mensaje Gmail. Dedup universal.
        cuenta_destino: Cuenta/casilla que recibió el correo original.
        metodo: Método de pago ('paypal', 'zelle', 'wise', ...).
        pagador_nombre: Nombre del pagador (o plataforma: TIKTOK, Clapper...).
        importe_bruto: Monto bruto recibido (antes de comisión).
        moneda: Moneda del pago (USD, EUR, ...).
        comision: Comisión del proveedor (NULL si no aplica).
        importe_neto: Monto neto tras comisión (NULL si no aplica).
        transaction_id: Referencia externa de transacción (NULL si no la trae).
        fecha_pago: Fecha del pago según el correo.
        cotizacion_id: Cotización aplicada (FK a quotes).
        tasa_aplicada: Snapshot de la tasa al procesar.
        valor_a_pagar: Monto a pagar al cliente en moneda local.
        moneda_pago_local: Moneda local de pago (VES, COP, ...).
        estado: Estado del pago.
        notas: Notas manuales del operador.
        procesado_por: Operador que procesó/editó el pago.
        datos_extra: JSONB con datos específicos del proveedor.
    """

    __tablename__ = 'payments'

    # ── Identidad del correo y método ─────────────────────────────────
    email_message_id = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        comment='ID único del mensaje en Gmail para evitar duplicados'
    )
    cuenta_destino = db.Column(
        db.String(255),
        nullable=True,
        comment='Cuenta/casilla que recibió el correo original'
    )
    metodo = db.Column(
        db.String(20),
        nullable=False,
        index=True,
        comment="Método de pago: 'paypal', 'zelle', 'wise', ..."
    )

    # ── Datos del pagador ─────────────────────────────────────────────
    pagador_nombre = db.Column(
        db.String(255),
        nullable=True,
        comment='Nombre del pagador o plataforma (TIKTOK, Clapper, ...)'
    )

    # ── Datos financieros ─────────────────────────────────────────────
    importe_bruto = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        comment='Monto bruto recibido (antes de comisión)'
    )
    moneda = db.Column(
        db.String(10),
        nullable=False,
        default='USD',
        comment='Moneda del pago: USD, EUR, BRL, etc.'
    )
    comision = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        comment='Comisión del proveedor (NULL si no aplica)'
    )
    importe_neto = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        comment='Monto neto después de comisión (NULL si no aplica)'
    )
    transaction_id = db.Column(
        db.String(100),
        unique=True,
        nullable=True,
        comment='Referencia externa de transacción (NULL si no la trae)'
    )
    fecha_pago = db.Column(
        db.DateTime,
        nullable=True,
        comment='Fecha del pago según el correo'
    )

    # ── Cotización aplicada ───────────────────────────────────────────
    cotizacion_id = db.Column(
        db.Integer,
        db.ForeignKey('quotes.id'),
        nullable=True,
        comment='Cotización aplicada al momento de procesar'
    )
    tasa_aplicada = db.Column(
        db.Numeric(12, 4),
        nullable=True,
        comment='Snapshot de la tasa aplicada (para historial)'
    )
    valor_a_pagar = db.Column(
        db.Numeric(15, 2),
        nullable=True,
        comment='Monto a pagar al cliente en moneda local'
    )
    moneda_pago_local = db.Column(
        db.String(10),
        nullable=True,
        comment='Moneda local de pago: VES, COP, BRL, etc.'
    )

    # ── Gestión ───────────────────────────────────────────────────────
    estado = db.Column(
        db.String(20),
        nullable=False,
        default=PaymentStatus.PENDIENTE,
        index=True,
        comment='pendiente/procesado/pagado/revision/manual'
    )
    notas = db.Column(
        db.Text,
        nullable=True,
        comment='Notas manuales del operador sobre el pago o cliente'
    )
    procesado_por = db.Column(
        db.Integer,
        db.ForeignKey('operators.id'),
        nullable=True,
        comment='Operador que procesó/editó el pago'
    )

    # ── Datos específicos del proveedor ───────────────────────────────
    datos_extra = db.Column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        comment='Datos propios del proveedor: subtipo, direccion, memo, ...'
    )

    # ── Relaciones ────────────────────────────────────────────────────
    cotizacion = db.relationship(
        'Quote',
        foreign_keys=[cotizacion_id],
        backref='payments'
    )
    procesado_por_usuario = db.relationship(
        'Operator',
        foreign_keys=[procesado_por],
        backref='payments_procesados'
    )

    def __repr__(self) -> str:
        return (
            f'<Payment #{self.id} | {self.metodo} | '
            f'{self.pagador_nombre} | '
            f'{self.importe_bruto} {self.moneda} | {self.estado}>'
        )

    # ── Propiedades calculadas ────────────────────────────────────────
    @property
    def monto_base_calculo(self) -> Optional[float]:
        """
        Monto base para calcular el valor a pagar.

        Regla universal (sirve para PayPal G&S, Wise y Zelle por igual):
        usa el neto si existe, si no el bruto.

        Returns:
            float con el monto base, o None si no está disponible.
        """
        if self.importe_neto is not None:
            return float(self.importe_neto)
        if self.importe_bruto is not None:
            return float(self.importe_bruto)
        return None

    @property
    def es_moneda_soportada(self) -> bool:
        """True si la moneda tiene cotización automática (por ahora solo USD)."""
        return self.moneda == 'USD'

    # Lectores planos de datos_extra (regla MVC: templates usan dot notation,
    # nunca dicts con claves string como p.datos_extra['subtipo']).
    @property
    def subtipo(self) -> Optional[str]:
        """Subtipo del pago (solo PayPal: ff/gs/payout)."""
        return (self.datos_extra or {}).get('subtipo')

    @property
    def direccion_envio(self) -> Optional[str]:
        """Dirección de envío si el correo la trajo (solo PayPal)."""
        return (self.datos_extra or {}).get('direccion_envio')

    @property
    def memo(self) -> Optional[str]:
        """Nota/concepto del remitente si existe (p. ej. memo de Zelle)."""
        return (self.datos_extra or {}).get('memo')

    @property
    def es_manual(self) -> bool:
        """True si el pago se registró manualmente (no vino de un correo)."""
        return (self.datos_extra or {}).get('origen') == 'manual'

    # ── Mutadores ─────────────────────────────────────────────────────
    def set_dato_extra(self, clave: str, valor: Any) -> None:
        """
        Asigna un dato específico del proveedor en datos_extra.

        Usa MutableDict, por lo que SQLAlchemy detecta el cambio sin
        necesidad de flag_modified.

        Args:
            clave: Nombre del campo (ej. 'subtipo', 'memo').
            valor: Valor a guardar.
        """
        if self.datos_extra is None:
            self.datos_extra = {}
        self.datos_extra[clave] = valor

    def aplicar_calculo(
        self,
        resultado: dict,
        operador_id: Optional[int] = None
    ) -> None:
        """
        Aplica el resultado de CalculatorService y actualiza el estado.

        Solo avanza a PROCESADO si estaba en estado inicial.

        Args:
            resultado: Dict de CalculatorService con cotizacion_id,
                tasa_aplicada, valor_a_pagar, moneda_local.
            operador_id: ID del Operator que aplica el cálculo.
        """
        self.cotizacion_id = resultado['cotizacion_id']
        self.tasa_aplicada = resultado['tasa_aplicada']
        self.valor_a_pagar = resultado['valor_a_pagar']
        self.moneda_pago_local = resultado['moneda_local']

        if self.estado in (PaymentStatus.PENDIENTE, PaymentStatus.MANUAL):
            self.estado = PaymentStatus.PROCESADO

        if operador_id:
            self.procesado_por = operador_id

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Serializa el pago a diccionario.

        Incluye campos calculados y aplana datos_extra para el template.

        Args:
            include_relationships: Si True incluye cotización y operador.

        Returns:
            Dict con todos los campos del pago.
        """
        data = super().to_dict()

        data['monto_base_calculo'] = self.monto_base_calculo
        data['es_moneda_soportada'] = self.es_moneda_soportada
        data['subtipo'] = self.subtipo
        data['direccion_envio'] = self.direccion_envio
        data['memo'] = self.memo
        data['es_manual'] = self.es_manual

        if include_relationships and self.cotizacion:
            data['cotizacion'] = self.cotizacion.to_dict()

        if include_relationships and self.procesado_por_usuario:
            data['procesado_por_nombre'] = self.procesado_por_usuario.full_name

        return data

    # ── Consultas ─────────────────────────────────────────────────────
    @classmethod
    def get_by_email_message_id(cls, message_id: str) -> Optional['Payment']:
        """Busca un pago por ID de mensaje Gmail (dedup universal)."""
        return cls.query.filter_by(email_message_id=message_id).first()

    @classmethod
    def get_by_transaction_id(cls, transaction_id: str) -> Optional['Payment']:
        """Busca un pago por referencia externa de transacción."""
        return cls.query.filter_by(transaction_id=transaction_id).first()

    @classmethod
    def get_pendientes(cls) -> list:
        """Pagos pendientes de procesar, más recientes primero."""
        return cls.query.filter_by(
            estado=PaymentStatus.PENDIENTE
        ).order_by(cls.id.desc()).all()

    @classmethod
    def get_manuales(cls) -> list:
        """Pagos en moneda no USD que requieren llenado manual."""
        return cls.query.filter_by(
            estado=PaymentStatus.MANUAL
        ).order_by(cls.id.desc()).all()

    @classmethod
    def get_by_metodo(cls, metodo: str) -> list:
        """Pagos de un método específico, más recientes primero."""
        return cls.query.filter_by(metodo=metodo).order_by(cls.id.desc()).all()