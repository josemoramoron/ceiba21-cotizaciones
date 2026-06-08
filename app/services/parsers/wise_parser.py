"""
Parser de correos de pago de Wise.

Wise envia desde noreply@wise.com con asunto "Dinero recibido de {nombre}".
El cuerpo trae una lista de definiciones (<dl class="details-list">) con:
    De: {pagador}
    Cantidad recibida: {monto} {MONEDA}
    Numero de transferencia: #{id}

Particularidades:
    - Wise NO siempre es USD (puede llegar en EUR, etc.). El monto no-USD
      quedara en estado manual aguas abajo, igual que cualquier no-USD.
    - El monto usa formato europeo (coma decimal), igual que PayPal, asi que
      reutiliza PaypalParserService._limpiar_monto.
    - No hay comision visible del lado receptor (Wise la cobra al emisor).
    - El cuerpo no trae fecha; se usa el header Date como respaldo.
"""
import re
import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.models.payment import PaymentProvider
from app.services.paypal_parser_service import PaypalParserService
from app.services.parsers.base import EmailPaymentParser

logger = logging.getLogger(__name__)

_SUBJECT_RE = re.compile(r'^dinero recibido de\s+(.+)$', re.IGNORECASE)
_H1_RE = re.compile(r'has recibido\s+([\d.,]+\s+[A-Za-z]{3})', re.IGNORECASE)


class WiseParser(EmailPaymentParser):
    """Parser Strategy para correos de pago de Wise."""

    metodo = PaymentProvider.WISE

    _REMITENTE = 'wise.com'
    # Wise tiene muchos tipos de correo (confirmaciones de envío, recibos, etc.)
    # que contienen "has recibido" en el cuerpo pero NO son pagos recibidos.
    # Discriminar SOLO por asunto evita falsos positivos y el log noise de parse().
    _MARCADORES = ('dinero recibido', 'has recibido', 'you received')

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
            logger.error(f"Correo Wise sin HTML: {message_id}")
            return None

        soup = BeautifulSoup(html, 'html.parser')
        detalles = self._parsear_dl(soup)

        monto = moneda = None
        cantidad = self._buscar(detalles, 'cantidad')
        if cantidad:
            monto, moneda = PaypalParserService._limpiar_monto(cantidad)
        if monto is None:
            monto, moneda = self._desde_h1(soup)
        if monto is None:
            logger.error(f"No se pudo extraer importe Wise: {message_id}")
            return None

        transaction_id = self._buscar(detalles, 'transferencia')
        if transaction_id:
            transaction_id = transaction_id.lstrip('#').strip()

        return {
            'metodo': self.metodo,
            'pagador_nombre': self._pagador(correo, detalles),
            'importe_bruto': monto,
            'moneda': moneda or 'USD',
            'comision': None,
            'importe_neto': None,
            'transaction_id': transaction_id,
            'fecha_pago': self._fecha_desde_header(correo),
            'datos_extra': {},
        }

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _parsear_dl(soup: BeautifulSoup) -> dict:
        """Mapea la lista de detalles: etiqueta normalizada -> valor."""
        detalles: dict = {}
        dl = soup.find('dl', class_='details-list') or soup.find('dl')
        if not dl:
            return detalles
        for dt in dl.find_all('dt'):
            dd = dt.find_next_sibling('dd')
            if dd is None:
                continue
            clave = dt.get_text(strip=True).rstrip(':').strip().lower()
            detalles[clave] = dd.get_text(separator=' ', strip=True)
        return detalles

    @staticmethod
    def _buscar(detalles: dict, sub: str) -> Optional[str]:
        """Busca el primer valor cuya etiqueta contenga `sub`."""
        for clave, valor in detalles.items():
            if sub in clave:
                return valor
        return None

    @classmethod
    def _pagador(cls, correo: dict, detalles: dict) -> Optional[str]:
        """Pagador desde el asunto; si falla, desde la etiqueta 'De:'."""
        match = _SUBJECT_RE.match((correo.get('subject') or '').strip())
        if match:
            return match.group(1).strip()
        return detalles.get('de')

    @staticmethod
    def _desde_h1(soup: BeautifulSoup) -> tuple:
        """Respaldo: extrae monto y moneda del titular <h1>."""
        h1 = soup.find('h1')
        if not h1:
            return None, None
        match = _H1_RE.search(h1.get_text(separator=' ', strip=True))
        if not match:
            return None, None
        return PaypalParserService._limpiar_monto(match.group(1))