"""
Modelo de Pagos PayPal recibidos via email.
Registra automáticamente los pagos parseados desde Gmail.
"""
from app.models import db
from app.models.base import BaseModel
from typing import Optional, Dict, Any


class PaypalPaymentStatus:
    """Estados posibles de un pago PayPal"""
    PENDIENTE = 'pendiente'        # Recibido, sin procesar
    PROCESADO = 'procesado'        # Tasa aplicada, listo para pagar
    PAGADO = 'pagado'              # Pago enviado al cliente
    REVISION = 'revision'          # Requiere revisión manual
    MANUAL = 'manual'              # Moneda no USD, requiere llenado manual


class PaypalPaymentType:
    """Tipos de pago PayPal"""
    PERSONAL = 'personal'          # Friends & Family (sin comisión)
    COMERCIAL = 'comercial'        # Goods & Services (con comisión)


class PaypalPayment(BaseModel):
    """
    Pago recibido via PayPal, capturado automáticamente desde Gmail.

    El sistema parsea los correos de service@intl.paypal.com con
    asunto 'Ha recibido un pago' y registra los datos aquí.

    Attributes:
        email_message_id: ID único del mensaje Gmail (evita duplicados)
        cuenta_destino: Cuenta Gmail que recibió el correo original
        pagador_nombre: Nombre del pagador según PayPal
        importe_bruto: Monto bruto recibido
        moneda: Moneda del pago (USD, EUR, etc.)
        comision_paypal: Comisión cobrada por PayPal (solo comercial)
        importe_neto: Monto neto después de comisión (solo comercial)
        tipo_pago: 'personal' o 'comercial'
        paypal_transaction_id: ID de transacción PayPal (único)
        fecha_pago: Fecha del pago
        direccion_envio: Dirección del pagador (opcional)
        cotizacion_id: Cotización aplicada (FK a quotes)
        tasa_aplicada: Snapshot de la tasa en el momento de procesar
        valor_a_pagar: Monto calculado en moneda local
        moneda_pago_local: Moneda en que se pagará al cliente
        estado: Estado del pago
        notas: Notas manuales del operador
        procesado_por: WebUser que procesó el pago
    """

    __tablename__ = 'paypal_payments'

    # ── Datos del correo ──────────────────────────────────────────────
    email_message_id = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        comment='ID único del mensaje en Gmail para evitar duplicados'
    )
    cuenta_destino = db.Column(
        db.String(255),
        nullable=True,
        comment='Gmail que recibió el correo (bjhoisa16@, padilla@, etc.)'
    )

    # ── Datos del pagador ─────────────────────────────────────────────
    pagador_nombre = db.Column(
        db.String(255),
        nullable=True,
        comment='Nombre completo del pagador según PayPal'
    )

    # ── Datos financieros del correo ──────────────────────────────────
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
    comision_paypal = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        comment='Comisión cobrada por PayPal (NULL si tipo personal)'
    )
    importe_neto = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        comment='Monto neto después de comisión (NULL si tipo personal)'
    )
    tipo_pago = db.Column(
        db.String(20),
        nullable=False,
        default=PaypalPaymentType.PERSONAL,
        comment='personal=F&F sin comisión, comercial=G&S con comisión'
    )

    # ── Datos de transacción PayPal ───────────────────────────────────
    paypal_transaction_id = db.Column(
        db.String(50),
        unique=True,
        nullable=True,
        comment='ID de transacción PayPal (ej: 8WG02403YE456271N)'
    )
    fecha_pago = db.Column(
        db.DateTime,
        nullable=True,
        comment='Fecha del pago según el correo PayPal'
    )
    direccion_envio = db.Column(
        db.Text,
        nullable=True,
        comment='Dirección de envío del pagador (opcional en ambos tipos)'
    )

    # ── Datos de cotización aplicada ──────────────────────────────────
    cotizacion_id = db.Column(
        db.Integer,
        db.ForeignKey('quotes.id'),
        nullable=True,
        comment='Cotización PayPal aplicada al momento de procesar'
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
        default=PaypalPaymentStatus.PENDIENTE,
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

    # ── Relaciones ────────────────────────────────────────────────────
    cotizacion = db.relationship(
        'Quote',
        foreign_keys=[cotizacion_id],
        backref='paypal_payments'
    )
    procesado_por_usuario = db.relationship(
        'Operator',
        foreign_keys=[procesado_por],
        backref='paypal_payments_procesados'
    )

    def __repr__(self) -> str:
        return (
            f'<PaypalPayment #{self.id} | '
            f'{self.pagador_nombre} | '
            f'{self.importe_bruto} {self.moneda} | '
            f'{self.estado}>'
        )

    @property
    def monto_base_calculo(self) -> Optional[float]:
        """
        Retorna el monto base para calcular el valor a pagar.
        - Si es comercial: usa importe_neto (después de comisión PayPal)
        - Si es personal: usa importe_bruto (no hay comisión)

        Returns:
            float con el monto base, o None si no está disponible
        """
        if self.tipo_pago == PaypalPaymentType.COMERCIAL and self.importe_neto:
            return float(self.importe_neto)
        elif self.importe_bruto:
            return float(self.importe_bruto)
        return None

    @property
    def es_moneda_soportada(self) -> bool:
        """
        Verifica si la moneda del pago tiene cotización automática.
        Por ahora solo USD tiene cotización automática.

        Returns:
            bool: True si la moneda tiene cotización automática
        """
        return self.moneda == 'USD'

    def calcular_valor_pagar(
        self,
        currency_code: str,
        web_user_id: Optional[int] = None
    ) -> Optional[float]:
        """
        Calcula el valor a pagar al cliente en la moneda local indicada.
        Busca la cotización PayPal vigente para esa moneda.

        Args:
            currency_code: Código de moneda local (VES, COP, BRL, etc.)
            web_user_id: ID del WebUser que está procesando

        Returns:
            float con el valor calculado, o None si no hay cotización

        Example:
            >>> pago.calcular_valor_pagar('VES', current_user.id)
            414.96
        """
        from app.models.quote import Quote
        from app.models.payment_method import PaymentMethod
        from app.models.currency import Currency

        # Buscar método de pago PayPal
        paypal_method = PaymentMethod.query.filter_by(code='PAYPAL').first()
        if not paypal_method:
            # Intentar con nombre si el código es diferente
            paypal_method = PaymentMethod.query.filter(
                PaymentMethod.name.ilike('%paypal%')
            ).first()

        if not paypal_method:
            return None

        # Buscar moneda destino
        currency = Currency.query.filter_by(code=currency_code.upper()).first()
        if not currency:
            return None

        # Buscar cotización vigente
        quote = Quote.query.filter_by(
            payment_method_id=paypal_method.id,
            currency_id=currency.id
        ).first()

        if not quote or not quote.final_value:
            return None

        # Monto base × tasa
        monto_base = self.monto_base_calculo
        if not monto_base:
            return None

        # final_value de Quote es el valor de 1 USD en moneda local
        tasa = float(quote.final_value)
        valor = round(monto_base * tasa, 2)

        # Guardar snapshot
        self.cotizacion_id = quote.id
        self.tasa_aplicada = tasa
        self.valor_a_pagar = valor
        self.moneda_pago_local = currency_code.upper()
        if self.estado in (PaypalPaymentStatus.PENDIENTE, PaypalPaymentStatus.MANUAL):
            self.estado = PaypalPaymentStatus.PROCESADO

        if web_user_id:
            self.procesado_por = web_user_id

        return valor

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Serializar pago a diccionario.

        Args:
            include_relationships: Si True incluye datos de cotización

        Returns:
            Dict con todos los campos del pago
        """
        data = super().to_dict()

        # Campos calculados
        data['monto_base_calculo'] = self.monto_base_calculo
        data['es_moneda_soportada'] = self.es_moneda_soportada

        if include_relationships and self.cotizacion:
            data['cotizacion'] = self.cotizacion.to_dict()

        if include_relationships and self.procesado_por_usuario:
            data['procesado_por_nombre'] = self.procesado_por_usuario.full_name
        return data

    @classmethod
    def get_by_transaction_id(
        cls,
        transaction_id: str
    ) -> Optional['PaypalPayment']:
        """
        Buscar pago por ID de transacción PayPal.

        Args:
            transaction_id: ID de transacción (ej: 8WG02403YE456271N)

        Returns:
            PaypalPayment o None
        """
        return cls.query.filter_by(
            paypal_transaction_id=transaction_id
        ).first()

    @classmethod
    def get_by_email_message_id(
        cls,
        message_id: str
    ) -> Optional['PaypalPayment']:
        """
        Buscar pago por ID de mensaje Gmail (para evitar duplicados).

        Args:
            message_id: ID del mensaje en Gmail

        Returns:
            PaypalPayment o None
        """
        return cls.query.filter_by(email_message_id=message_id).first()

    @classmethod
    def get_pendientes(cls) -> list:
        """Obtener todos los pagos pendientes de procesar."""
        return cls.query.filter_by(
            estado=PaypalPaymentStatus.PENDIENTE
        ).order_by(cls.fecha_pago.desc()).all()

    @classmethod
    def get_manuales(cls) -> list:
        """Obtener pagos en moneda no USD que requieren llenado manual."""
        return cls.query.filter_by(
            estado=PaypalPaymentStatus.MANUAL
        ).order_by(cls.fecha_pago.desc()).all()
