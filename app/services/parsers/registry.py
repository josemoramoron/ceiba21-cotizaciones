"""
Registro/runner de parsers de correos de pago.

Mantiene la lista de parsers disponibles y, dado un correo, devuelve el primero
que lo reconoce (puede_parsear). Agregar un metodo nuevo = registrar su parser
aqui; nada mas cambia en la ingesta.
"""
import logging
from typing import List, Optional, Tuple

from app.services.parsers.base import EmailPaymentParser
from app.services.parsers.paypal_parser import PaypalParser
from app.services.parsers.wise_parser import WiseParser
from app.services.parsers.zelle_parser import ZelleParser
from app.services.parsers.skrill_parser import SkrillParser
from app.services.parsers.binance_parser import BinanceParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registro de parsers (patron Strategy + seleccion por puede_parsear)."""

    def __init__(self, parsers: Optional[List[EmailPaymentParser]] = None) -> None:
        """
        Args:
            parsers: Lista de parsers a usar. Si es None, usa los por defecto.
        """
        self._parsers: List[EmailPaymentParser] = parsers or self._default_parsers()

    @staticmethod
    def _default_parsers() -> List[EmailPaymentParser]:
        """Parsers registrados por defecto (orden = prioridad de evaluacion)."""
        return [PaypalParser(), WiseParser(), ZelleParser(),
                SkrillParser(), BinanceParser()]

    def seleccionar(self, correo: dict) -> Optional[EmailPaymentParser]:
        """
        Devuelve el primer parser que reconoce el correo, o None.

        Args:
            correo: Dict del correo (claves de GmailService).

        Returns:
            El parser que reclama el correo, o None si ninguno lo reconoce.
        """
        for parser in self._parsers:
            try:
                if parser.puede_parsear(correo):
                    return parser
            except Exception as e:
                # Un parser defectuoso no debe tumbar al resto: se registra
                # el error y se sigue evaluando los demas.
                logger.error(
                    f"Error en puede_parsear de {parser.__class__.__name__}: {e}"
                )
        return None

    def parse(self, correo: dict) -> Optional[Tuple[str, dict]]:
        """
        Selecciona el parser adecuado y parsea el correo.

        Args:
            correo: Dict del correo (claves de GmailService).

        Returns:
            Tupla (metodo, datos) si algun parser lo proceso, o None si ninguno
            lo reconocio o el parseo fallo.
        """
        parser = self.seleccionar(correo)
        if parser is None:
            logger.info(
                f"Ningun parser reconocio el correo "
                f"{correo.get('message_id', '?')} de {correo.get('sender', '?')}"
            )
            return None

        datos = parser.parse(correo)
        if datos is None:
            return None
        return parser.metodo, datos