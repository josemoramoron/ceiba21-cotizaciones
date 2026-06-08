"""
Parser de correos de pago de PayPal.

Cubre los tres sabores que recibe Ceiba21, todos con titulo font-size:42px:
    - Personal (F&F): sin comision.
    - Comercial (G&S): con comision.
    - Payout de plataforma (TIKTOK, Clapper, ...): sin comision.

Reutiliza los helpers probados de PaypalParserService (montos, tabla de
detalles, direccion) sin modificarlos. Lo unico nuevo es:
    - Un regex de titulo que admite "le ha enviado" Y "le envio/envio"
      (los payouts usan "le envio", que el parser legacy no reconocia).
    - La deteccion de subtipo (ff/gs/payout).
    - Fallback de fecha al header Date del correo (el layout de payout no
      expone la fecha en la tabla de detalles).
"""
import re
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

from bs4 import BeautifulSoup

from app.models.payment import PaymentProvider, PaypalSubtipo
from app.services.paypal_parser_service import PaypalParserService
from app.services.parsers.base import EmailPaymentParser

logger = logging.getLogger(__name__)

# Admite "le ha enviado" (correos normales) y "le envio/envio" (payouts).
_TITULO_RE = re.compile(
    r'^(.+?)\s+le\s+(?:ha\s+enviado|envi[o\u00f3])\s+(.+)$',
    re.IGNORECASE
)

_MARCAS_PAYOUT = (
    'fondos recibidos', 'fondos que recibi\u00f3', 'fondos que recibio',
    'payout', 'has sent you money',
)


class PaypalParser(EmailPaymentParser):
    """Parser Strategy para correos de pago de PayPal."""

    metodo = PaymentProvider.PAYPAL

    _REMITENTE = 'intl.paypal.com'
    _MARCADORES = (
        'le ha enviado', 'le envi\u00f3', 'le envio',
        'ha recibido un pago',
    ) + _MARCAS_PAYOUT

    def puede_parsear(self, correo: dict) -> bool:
        sender = (correo.get('sender') or '').lower()
        if self._REMITENTE not in sender:
            return False
        texto = (correo.get('html_body') or '').lower()
        asunto = (correo.get('subject') or '').lower()
        return any(m in texto or m in asunto for m in self._MARCADORES)

    def parse(self, correo: dict) -> Optional[dict]:
        html = correo.get('html_body')
        message_id = correo.get('message_id', '')
        if not html:
            logger.error(f"Correo PayPal sin HTML: {message_id}")
            return None

        soup = BeautifulSoup(html, 'html.parser')

        titulo = self._extraer_titulo(soup)
        if not titulo.get('importe_bruto'):
            logger.error(f"No se pudo extraer importe PayPal: {message_id}")
            return None

        detalles = PaypalParserService._parsear_tabla_detalles(soup)
        direccion = PaypalParserService._parsear_direccion(soup)

        comision = detalles.get('comision_paypal')
        subtipo = self._detectar_subtipo(correo, comision)

        datos_extra = {'subtipo': subtipo}
        if direccion:
            datos_extra['direccion_envio'] = direccion

        fecha = detalles.get('fecha_pago') or self._fecha_desde_header(correo)

        return {
            'metodo': self.metodo,
            'pagador_nombre': titulo.get('pagador_nombre'),
            'importe_bruto': titulo.get('importe_bruto'),
            'moneda': titulo.get('moneda') or 'USD',
            'comision': comision,
            'importe_neto': detalles.get('importe_neto'),
            'transaction_id': detalles.get('paypal_transaction_id'),
            'fecha_pago': fecha,
            'datos_extra': datos_extra,
        }

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _extraer_titulo(soup: BeautifulSoup) -> dict:
        """Extrae pagador, importe y moneda del titulo font-size:42px."""
        resultado: dict = {}
        titulo = soup.find('p', style=lambda s: s and 'font-size:42px' in s)
        if not titulo:
            return resultado

        texto = titulo.get_text(separator=' ', strip=True)
        match = _TITULO_RE.match(texto)
        if not match:
            logger.warning(f"Titulo PayPal no reconocido: {texto}")
            return resultado

        resultado['pagador_nombre'] = match.group(1).strip()
        monto, moneda = PaypalParserService._limpiar_monto(match.group(2).strip())
        resultado['importe_bruto'] = monto
        resultado['moneda'] = moneda or 'USD'
        return resultado

    @staticmethod
    def _detectar_subtipo(correo: dict, comision: Optional[float]) -> str:
        """Determina el subtipo del pago PayPal: ff / gs / payout."""
        texto = (correo.get('html_body') or '').lower()
        asunto = (correo.get('subject') or '').lower()
        if any(m in texto or m in asunto for m in _MARCAS_PAYOUT):
            return PaypalSubtipo.PAYOUT
        if comision is not None and comision > 0:
            return PaypalSubtipo.GS
        return PaypalSubtipo.FF

    @staticmethod
    def _fecha_desde_header(correo: dict) -> Optional[datetime]:
        """Fecha del header Date como respaldo (naive, sin tz)."""
        raw = correo.get('date')
        if not raw:
            return None
        try:
            dt = parsedate_to_datetime(raw)
            return dt.replace(tzinfo=None) if dt else None
        except (TypeError, ValueError):
            return None