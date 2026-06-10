"""
Parser de correos de pago de Skrill.

Skrill envia desde no-reply@email.skrill.com con asunto "Dinero recibido".
El cuerpo (HTML) muestra:
    ha recibido
    {monto} {MONEDA}            (ej. "35.00 USD" -- formato US, punto decimal)
    de {pagador}                (ej. "de Gershon Reshef")
    Detalles de la transaccion
      ID de la transaccion  {id}
      Fecha  {fecha en formato Java, ej. "Thu Jun 04 16:29:06 CEST 2026"}

Particularidades:
    - Skrill puede llegar en USD/EUR/GBP. El no-USD queda en estado manual
      aguas abajo, igual que cualquier no-USD.
    - El monto usa formato US (punto decimal), como Zelle (_monto_us).
    - No hay comision visible del lado receptor.
    - La fecha del cuerpo viene en formato Java (CEST, no estandar): se usa el
      header Date como respaldo (ya normalizado a UTC en base.py).
"""
import re
import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.models.payment import PaymentProvider
from app.services.parsers.base import EmailPaymentParser

logger = logging.getLogger(__name__)

_MONTO_RE = re.compile(r'([\d.,]+)\s*(USD|EUR|GBP)', re.IGNORECASE)
_PAGADOR_RE = re.compile(r'(?im)^\s*de\s+([A-Za-z\u00c0-\u00ff][^\n]{1,60})\s*$')
_TXID_RE = re.compile(
    r'ID\s+de\s+la\s+transacci[o\u00f3]n[\s\S]{0,40}?(\d{4,})',
    re.IGNORECASE
)


class SkrillParser(EmailPaymentParser):
    """Parser Strategy para correos de pago de Skrill."""

    metodo = PaymentProvider.SKRILL

    _REMITENTE = 'email.skrill.com'
    # Skrill manda muchos correos; discriminar por asunto evita falsos positivos.
    _MARCADORES = ('dinero recibido', 'money received')

    def puede_parsear(self, correo: dict) -> bool:
        sender = (correo.get('sender') or '').lower()
        if self._REMITENTE not in sender:
            return False
        asunto = (correo.get('subject') or '').lower()
        return any(m in asunto for m in self._MARCADORES)

    def parse(self, correo: dict) -> Optional[dict]:
        html = correo.get('html_body')
        message_id = correo.get('message_id', '')
        if not html:
            logger.error(f"Correo Skrill sin HTML: {message_id}")
            return None

        soup = BeautifulSoup(html, 'html.parser')
        texto = soup.get_text(separator='\n')

        monto, moneda = self._monto_moneda(texto)
        if monto is None:
            logger.error(f"No se pudo extraer importe Skrill: {message_id}")
            return None

        return {
            'metodo': self.metodo,
            'pagador_nombre': self._pagador(texto),
            'importe_bruto': monto,
            'moneda': moneda or 'USD',
            'comision': None,
            'importe_neto': None,
            'transaction_id': self._transaction_id(texto),
            'fecha_pago': self._fecha_desde_header(correo),
            'datos_extra': {},
        }

    # ── Helpers ───────────────────────────────────────────────────────
    @classmethod
    def _monto_moneda(cls, texto: str) -> tuple:
        """Extrae (monto, MONEDA) del primer 'NN.NN CCC' del cuerpo."""
        match = _MONTO_RE.search(texto)
        if not match:
            return None, None
        return cls._monto_us(match.group(1)), match.group(2).upper()

    @staticmethod
    def _monto_us(texto: str) -> Optional[float]:
        """Normaliza un monto en formato US (coma=miles, punto=decimal)."""
        limpio = re.search(r'[\d,]*\.?\d+', texto)
        if not limpio:
            return None
        try:
            return float(limpio.group(0).replace(',', ''))
        except ValueError:
            return None

    @staticmethod
    def _pagador(texto: str) -> Optional[str]:
        """Pagador desde la linea 'de {nombre}'."""
        match = _PAGADOR_RE.search(texto)
        return match.group(1).strip() if match else None

    @staticmethod
    def _transaction_id(texto: str) -> Optional[str]:
        """ID de la transaccion (cadena de digitos tras la etiqueta)."""
        match = _TXID_RE.search(texto)
        return match.group(1) if match else None