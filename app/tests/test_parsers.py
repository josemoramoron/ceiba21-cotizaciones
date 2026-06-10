"""
Tests de los parsers de correos de pago (PayPal, Wise, Zelle, Skrill, Binance)
y el registry.

Son tests puros: construyen dicts `correo` (con las claves que produce
GmailService) y verifican el ruteo (puede_parsear) y la extracción (parse),
sin tocar la base de datos.
"""
from bs4 import BeautifulSoup

from app.models.payment import PaymentProvider
from app.services.parsers.paypal_parser import PaypalParser
from app.services.parsers.wise_parser import WiseParser
from app.services.parsers.zelle_parser import ZelleParser
from app.services.parsers.skrill_parser import SkrillParser
from app.services.parsers.binance_parser import BinanceParser
from app.services.parsers.registry import ParserRegistry

PAYPAL = 'service@intl.paypal.com'
WISE = 'noreply@wise.com'
BOA = 'customerservice@ealerts.bankofamerica.com'


def _correo(sender: str = '', subject: str = '', html_body: str = '') -> dict:
    """Construye un dict `correo` con las claves que entrega GmailService."""
    return {
        'message_id': '<test@local>',
        'subject': subject,
        'sender': sender,
        'to_raw': 'ceiba21@gmail.com',
        'date': 'Mon, 08 Jun 2026 12:00:00 -0500',
        'html_body': html_body,
        'imap_uid': '1',
    }


class TestPaypalRuteo:
    """puede_parsear de PaypalParser: reconoce pagos, descarta no-pagos."""

    def setup_method(self):
        self.parser = PaypalParser()

    def test_pago_recibido_por_asunto(self):
        c = _correo(sender=PAYPAL, subject='Juan Perez le ha enviado $50,00 USD')
        assert self.parser.puede_parsear(c) is True

    def test_remitente_distinto_no_aplica(self):
        c = _correo(sender='phishing@example.com',
                    subject='Juan le ha enviado $50,00 USD')
        assert self.parser.puede_parsear(c) is False

    def test_retiro_a_banco_se_descarta(self):
        # "Estamos transfiriendo fondos" = retiro (egreso), no un pago recibido
        c = _correo(sender=PAYPAL,
                    subject='Estamos transfiriendo fondos a su cuenta bancaria')
        assert self.parser.puede_parsear(c) is False

    def test_solicitud_de_pago_se_descarta(self):
        # Crítico: una solicitud de cobro dice "le ha enviado una solicitud de
        # pago"; no debe colarse como pago pese a contener "le ha enviado".
        c = _correo(sender=PAYPAL,
                    subject='Maria Lopez le ha enviado una solicitud de pago')
        assert self.parser.puede_parsear(c) is False

    def test_aviso_de_saldo_se_descarta(self):
        c = _correo(sender=PAYPAL,
                    subject='Ahora tiene más fondos disponibles al instante')
        assert self.parser.puede_parsear(c) is False

    def test_aviso_fiscal_se_descarta(self):
        c = _correo(
            sender=PAYPAL,
            subject='Confirme su condición de contribuyente estadounidense'
        )
        assert self.parser.puede_parsear(c) is False


class TestPaypalTitulo:
    """Extracción del título de 42px (pagador/monto/moneda) de PaypalParser."""

    def test_titulo_pago_valido(self):
        html = ('<p style="font-size:42px">'
                'Juan Perez le ha enviado $\xa050,00\xa0USD</p>')
        titulo = PaypalParser._extraer_titulo(BeautifulSoup(html, 'html.parser'))
        assert titulo['pagador_nombre'] == 'Juan Perez'
        assert titulo['importe_bruto'] == 50.0
        assert titulo['moneda'] == 'USD'

    def test_titulo_no_pago_queda_vacio(self):
        html = ('<p style="font-size:42px">'
                'Estamos transfiriendo fondos de PayPal a su cuenta bancaria</p>')
        titulo = PaypalParser._extraer_titulo(BeautifulSoup(html, 'html.parser'))
        assert titulo.get('importe_bruto') is None


class TestWiseRuteo:
    """puede_parsear de WiseParser: solo 'dinero recibido' en el asunto."""

    def setup_method(self):
        self.parser = WiseParser()

    def test_dinero_recibido_por_asunto(self):
        c = _correo(sender=WISE, subject='Dinero recibido de Carlos Ruiz')
        assert self.parser.puede_parsear(c) is True

    def test_confirmacion_envio_se_descarta(self):
        # El cuerpo dice "has recibido" pero el asunto no es de pago recibido:
        # con la discriminación por asunto ya no se cuela.
        c = _correo(
            sender=WISE,
            subject='Tu transferencia va en camino',
            html_body='<p>El destinatario has recibido los fondos.</p>'
        )
        assert self.parser.puede_parsear(c) is False

    def test_remitente_distinto_no_aplica(self):
        c = _correo(sender='x@y.com', subject='Dinero recibido de Carlos')
        assert self.parser.puede_parsear(c) is False


class TestWiseParse:
    """Extracción completa de WiseParser (monto no-USD, transaction_id)."""

    def test_extrae_eur_pagador_y_transaccion(self):
        html = (
            '<dl class="details-list">'
            '<dt>De:</dt><dd>Carlos Ruiz</dd>'
            '<dt>Cantidad recibida:</dt><dd>€\xa0105,00\xa0EUR</dd>'
            '<dt>Número de transferencia:</dt><dd>#TR123456</dd>'
            '</dl>'
        )
        datos = WiseParser().parse(
            _correo(sender=WISE, subject='Dinero recibido de Carlos Ruiz',
                    html_body=html)
        )
        assert datos is not None
        assert datos['metodo'] == PaymentProvider.WISE
        assert datos['pagador_nombre'] == 'Carlos Ruiz'
        assert datos['importe_bruto'] == 105.0
        assert datos['moneda'] == 'EUR'
        assert datos['transaction_id'] == 'TR123456'
        assert datos['comision'] is None


class TestZelleRuteo:
    """puede_parsear de ZelleParser (alertas de BoA)."""

    def setup_method(self):
        self.parser = ZelleParser()

    def test_le_envio_por_asunto(self):
        c = _correo(sender=BOA, subject='Luis Barrios le envió $1,355.66')
        assert self.parser.puede_parsear(c) is True

    def test_remitente_distinto_no_aplica(self):
        c = _correo(sender='x@y.com', subject='Luis le envió $50.00')
        assert self.parser.puede_parsear(c) is False


class TestZelleParse:
    """Extracción de ZelleParser desde el asunto (formato US, siempre USD)."""

    def test_extrae_de_asunto_formato_us(self):
        datos = ZelleParser().parse(
            _correo(sender=BOA, subject='Luis Barrios le envió $1,355.66')
        )
        assert datos is not None
        assert datos['metodo'] == PaymentProvider.ZELLE
        assert datos['pagador_nombre'] == 'Luis Barrios'
        assert datos['importe_bruto'] == 1355.66   # coma = miles en formato US
        assert datos['moneda'] == 'USD'
        assert datos['comision'] is None
        assert datos['transaction_id'] is None


class TestRegistry:
    """Selección y ruteo del ParserRegistry."""

    def setup_method(self):
        self.registry = ParserRegistry()

    def test_selecciona_paypal_para_pago(self):
        c = _correo(sender=PAYPAL, subject='Juan le ha enviado $50,00 USD')
        assert isinstance(self.registry.seleccionar(c), PaypalParser)

    def test_parsea_zelle_devuelve_metodo_y_datos(self):
        res = self.registry.parse(
            _correo(sender=BOA, subject='Luis le envió $50.00')
        )
        assert res is not None
        metodo, datos = res
        assert metodo == PaymentProvider.ZELLE
        assert datos['importe_bruto'] == 50.0

    def test_correo_desconocido_devuelve_none(self):
        c = _correo(sender='random@example.com', subject='Hola',
                    html_body='<p>nada</p>')
        assert self.registry.parse(c) is None

    def test_retiro_paypal_no_lo_reclama_nadie(self):
        c = _correo(sender=PAYPAL,
                    subject='Estamos transfiriendo fondos a su cuenta bancaria')
        assert self.registry.seleccionar(c) is None

SKRILL = 'no-reply@email.skrill.com'
BINANCE = 'do-not-reply@ses.binance.com'


class TestSkrillRuteo:
    """puede_parsear de SkrillParser."""

    def setup_method(self):
        self.parser = SkrillParser()

    def test_dinero_recibido_por_asunto(self):
        c = _correo(sender=SKRILL, subject='Dinero recibido')
        assert self.parser.puede_parsear(c) is True

    def test_remitente_distinto_no_aplica(self):
        c = _correo(sender='x@y.com', subject='Dinero recibido')
        assert self.parser.puede_parsear(c) is False


class TestSkrillParse:
    """Extracción de SkrillParser (formato US, USD, pagador, transaction_id)."""

    _HTML = (
        '<div>Hola <strong>Jose</strong>,</div>'
        '<div>ha recibido</div>'
        '<div>35.00 USD</div>'
        '<div>de Gershon Reshef</div>'
        '<table>'
        '<tr><td>ID de la transacción</td><td>7067088074</td></tr>'
        '<tr><td>Fecha</td><td>Thu Jun 04 16:29:06 CEST 2026</td></tr>'
        '</table>'
    )

    def test_extrae_usd_pagador_y_transaccion(self):
        datos = SkrillParser().parse(
            _correo(sender=SKRILL, subject='Dinero recibido', html_body=self._HTML)
        )
        assert datos is not None
        assert datos['metodo'] == PaymentProvider.SKRILL
        assert datos['pagador_nombre'] == 'Gershon Reshef'
        assert datos['importe_bruto'] == 35.0
        assert datos['moneda'] == 'USD'
        assert datos['transaction_id'] == '7067088074'
        assert datos['comision'] is None


class TestBinanceRuteo:
    """puede_parsear de BinanceParser."""

    def setup_method(self):
        self.parser = BinanceParser()

    def test_pago_recibido_por_asunto(self):
        c = _correo(
            sender=BINANCE,
            subject='[Binance] Pago recibido correctamente - 2026-06-10 13:33:47 (UTC)'
        )
        assert self.parser.puede_parsear(c) is True

    def test_remitente_distinto_no_aplica(self):
        c = _correo(sender='x@y.com',
                    subject='[Binance] Pago recibido correctamente')
        assert self.parser.puede_parsear(c) is False


class TestBinanceParse:
    """Extracción de BinanceParser: stablecoin -> USD, activo en datos_extra."""

    _HTML = (
        '<table>'
        '<tr><td>Fecha y hora:</td><td>2026-06-10 13:33:45(UTC)</td></tr>'
        '<tr><td>Remitente:</td><td>ceiba21</td></tr>'
        '<tr><td>Monto:</td><td>5000 USDT</td></tr>'
        '</table>'
        '<div style="display:none;">'
        '<strong id="uuid">Y2026061013fa04fa78a7184cf48da1928b66c93e22</strong>'
        '</div>'
    )

    def test_usdt_se_normaliza_a_usd(self):
        datos = BinanceParser().parse(
            _correo(sender=BINANCE, subject='[Binance] Pago recibido correctamente',
                    html_body=self._HTML)
        )
        assert datos is not None
        assert datos['metodo'] == PaymentProvider.BINANCE
        assert datos['pagador_nombre'] == 'ceiba21'
        assert datos['importe_bruto'] == 5000.0
        assert datos['moneda'] == 'USD'                      # USDT -> USD
        assert datos['datos_extra']['moneda_original'] == 'USDT'
        assert datos['transaction_id'] == (
            'Y2026061013fa04fa78a7184cf48da1928b66c93e22'
        )

    def test_cripto_no_stable_conserva_moneda(self):
        html = self._HTML.replace('5000 USDT', '0.05 BTC')
        datos = BinanceParser().parse(
            _correo(sender=BINANCE, subject='[Binance] Pago recibido correctamente',
                    html_body=html)
        )
        assert datos is not None
        assert datos['moneda'] == 'BTC'              # no-stable -> manual aguas abajo
        assert 'moneda_original' not in datos['datos_extra']
        assert datos['importe_bruto'] == 0.05


class TestRegistrySkrillBinance:
    """El registry rutea Skrill y Binance al parser correcto."""

    def setup_method(self):
        self.registry = ParserRegistry()

    def test_rutea_skrill(self):
        c = _correo(sender=SKRILL, subject='Dinero recibido')
        assert isinstance(self.registry.seleccionar(c), SkrillParser)

    def test_rutea_binance(self):
        c = _correo(sender=BINANCE,
                    subject='[Binance] Pago recibido correctamente')
        assert isinstance(self.registry.seleccionar(c), BinanceParser)