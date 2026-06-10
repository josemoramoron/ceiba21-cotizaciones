"""
Parser de correos de pago de Binance (Binance Pay).

Binance envia desde do-not-reply@ses.binance.com con asunto
"[Binance] Pago recibido correctamente - {fecha} (UTC)". El cuerpo (HTML)
trae una tabla con celdas etiqueta/valor:
    Fecha y hora:  {fecha}
    Remitente:     {nick del pagador}
    Monto:         {cantidad} {ACTIVO}   (ej. "5000 USDT")
y un identificador interno en <strong id="uuid">...</strong>.

Particularidades:
    - El monto puede ser un stablecoin (USDT, USDC, ...) o cualquier cripto.
      Los stablecoins se NORMALIZAN a moneda='USD' (paridad 1:1, unidad de
      liquidacion de Ceiba21) para que coticen con la tasa del metodo 'binance';
      el activo original se guarda en datos_extra['moneda_original'].
      Los NO-stablecoin (BTC, ETH, ...) conservan su moneda -> quedan manuales.
    - No hay comision visible (Binance Pay P2P no la expone al receptor).
    - 'Remitente' es el nick de Binance Pay del pagador, no su nombre legal.
    - transaction_id = el id interno de <strong id="uuid">.
    - La fecha del cuerpo es UTC; se usa el header Date (ya normalizado a UTC).
"""
import re
import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.models.payment import PaymentProvider
from app.services.parsers.base import EmailPaymentParser

logger = logging.getLogger(__name__)

_MONTO_RE = re.compile(r'([\d.,]+)\s*([A-Za-z]{2,6})')
_STABLECOINS = {'USDT', 'USDC', 'BUSD', 'FDUSD', 'DAI', 'TUSD'}


class BinanceParser(EmailPaymentParser):
    """Parser Strategy para correos de Binance Pay (pago recibido)."""

    metodo = PaymentProvider.BINANCE

    _REMITENTE = 'ses.binance.com'
    _MARCADORES = ('pago recibido', 'payment received')

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
            logger.error(f"Correo Binance sin HTML: {message_id}")
            return None

        soup = BeautifulSoup(html, 'html.parser')
        lineas = self._lineas(soup)

        monto, activo = self._monto_activo(self._valor_tras(lineas, 'Monto'))
        if monto is None:
            logger.error(f"No se pudo extraer importe Binance: {message_id}")
            return None

        # Stablecoin -> se liquida como USD; el activo real va en datos_extra.
        datos_extra: dict = {}
        if activo in _STABLECOINS:
            moneda = 'USD'
            datos_extra['moneda_original'] = activo
        else:
            moneda = activo or 'USD'

        return {
            'metodo': self.metodo,
            'pagador_nombre': self._valor_tras(lineas, 'Remitente'),
            'importe_bruto': monto,
            'moneda': moneda,
            'comision': None,
            'importe_neto': None,
            'transaction_id': self._uuid(soup),
            'fecha_pago': self._fecha_desde_header(correo),
            'datos_extra': datos_extra,
        }

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _lineas(soup: BeautifulSoup) -> list:
        """Lineas de texto no vacias del cuerpo."""
        texto = soup.get_text(separator='\n')
        return [ln.strip() for ln in texto.splitlines() if ln.strip()]

    @staticmethod
    def _valor_tras(lineas: list, etiqueta: str) -> Optional[str]:
        """
        Valor asociado a una etiqueta ('Remitente', 'Monto').

        Binance maqueta etiqueta y valor en celdas separadas, asi que el valor
        suele ir en la linea siguiente; tambien soporta 'Etiqueta: valor' en
        la misma linea.
        """
        et = etiqueta.lower()
        for i, linea in enumerate(lineas):
            if linea.lower().startswith(et):
                resto = linea[len(etiqueta):].lstrip(' :').strip()
                if resto:
                    return resto
                if i + 1 < len(lineas):
                    return lineas[i + 1]
        return None

    @classmethod
    def _monto_activo(cls, texto: Optional[str]) -> tuple:
        """Extrae (monto, ACTIVO) de un valor tipo '5000 USDT'."""
        if not texto:
            return None, None
        match = _MONTO_RE.search(texto)
        if not match:
            return None, None
        try:
            monto = float(match.group(1).replace(',', ''))
        except ValueError:
            return None, None
        return monto, match.group(2).upper()

    @staticmethod
    def _uuid(soup: BeautifulSoup) -> Optional[str]:
        """Identificador interno del pago (<strong id='uuid'>)."""
        nodo = soup.find(id='uuid')
        if nodo is None:
            return None
        valor = nodo.get_text(strip=True)
        return valor or None