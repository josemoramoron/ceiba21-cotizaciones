"""
Parser de correos de pago Zelle via Bank of America.

BoA envia desde customerservice@ealerts.bankofamerica.com con asunto
"{pagador} le envio ${monto}". El mismo texto aparece en el titulo del cuerpo.

Particularidades:
    - Zelle es domestico de EE.UU.: la moneda siempre es USD.
    - NO trae transaction_id ni comision (Zelle es gratis). La deduplicacion
      depende solo de email_message_id.
    - Usa formato numerico US (coma=miles, punto=decimal), OPUESTO al europeo
      de PayPal/Wise, por eso tiene su propia normalizacion (_monto_us).
    - El cuerpo no trae fecha; se usa el header Date como respaldo.
    - Memo: BoA muestra la nota del remitente (ej. 'C21'). Se captura como
      best-effort; es preliminar y conviene afinarlo con mas muestras.
"""
import re
import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.models.payment import PaymentProvider
from app.services.parsers.base import EmailPaymentParser

logger = logging.getLogger(__name__)

_TITULO_RE = re.compile(
    r'^(.+?)\s+le\s+envi[o\u00f3]\s+\$?\s*([\d.,]+)',
    re.IGNORECASE
)
_BOILERPLATE = (
    'por favor', 'espere', 'minuto', 'deposit', 'zelle',
    'bank of america', 'consultar', 'saldo',
)


class ZelleParser(EmailPaymentParser):
    """Parser Strategy para correos Zelle via Bank of America."""

    metodo = PaymentProvider.ZELLE

    _REMITENTE = 'ealerts.bankofamerica.com'

    def puede_parsear(self, correo: dict) -> bool:
        sender = (correo.get('sender') or '').lower()
        if self._REMITENTE not in sender:
            return False
        texto = (
            (correo.get('subject') or '') + ' ' + (correo.get('html_body') or '')
        ).lower()
        # "le envio/envio" identifica una alerta de dinero recibido (no otras
        # alertas que BoA manda desde el mismo remitente).
        return 'le envi' in texto

    def parse(self, correo: dict) -> Optional[dict]:
        html = correo.get('html_body') or ''
        message_id = correo.get('message_id', '')
        soup = BeautifulSoup(html, 'html.parser') if html else None

        pagador, monto = self._desde_asunto(correo.get('subject') or '')
        if monto is None and soup is not None:
            pagador, monto = self._desde_titulo(soup)
        if monto is None:
            logger.error(f"No se pudo extraer importe Zelle: {message_id}")
            return None

        datos_extra: dict = {}
        memo = self._extraer_memo(soup) if soup is not None else None
        if memo:
            datos_extra['memo'] = memo

        return {
            'metodo': self.metodo,
            'pagador_nombre': pagador,
            'importe_bruto': monto,
            'moneda': 'USD',  # BoA Zelle es domestico USD
            'comision': None,
            'importe_neto': None,
            'transaction_id': None,
            'fecha_pago': self._fecha_desde_header(correo),
            'datos_extra': datos_extra,
        }

    # ── Helpers ───────────────────────────────────────────────────────
    @classmethod
    def _desde_asunto(cls, subject: str) -> tuple:
        """Extrae pagador e importe del asunto ya decodificado."""
        match = _TITULO_RE.match((subject or '').strip())
        if not match:
            return None, None
        return match.group(1).strip(), cls._monto_us(match.group(2))

    @classmethod
    def _desde_titulo(cls, soup: BeautifulSoup) -> tuple:
        """Respaldo: extrae pagador e importe del titulo del cuerpo."""
        td = soup.find('td', class_='tdMobZ1BottomPadding30px')
        if td is None:
            return None, None
        match = _TITULO_RE.match(td.get_text(separator=' ', strip=True))
        if not match:
            return None, None
        return match.group(1).strip(), cls._monto_us(match.group(2))

    @staticmethod
    def _monto_us(texto: str) -> Optional[float]:
        """Normaliza un monto en formato US (coma=miles, punto=decimal)."""
        match = re.search(r'[\d,]*\.?\d+', texto)
        if not match:
            return None
        try:
            return float(match.group(0).replace(',', ''))
        except ValueError:
            return None

    @staticmethod
    def _extraer_memo(soup: BeautifulSoup) -> Optional[str]:
        """
        Captura best-effort de la nota del remitente (ej. 'C21').

        Filtra el texto boilerplate del template y toma el primer candidato
        corto. PRELIMINAR: conviene afinarlo con mas muestras de Zelle.
        """
        for td in soup.find_all('td'):
            clases = ' '.join(td.get('class') or [])
            if 'tblMobZ3Content9Center' not in clases:
                continue
            texto = td.get_text(strip=True)
            if not texto or len(texto) > 40:
                continue
            if any(b in texto.lower() for b in _BOILERPLATE):
                continue
            return texto
        return None