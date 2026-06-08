"""
Interfaz Strategy para parsers de correos de pago.

Cada proveedor (PayPal, Wise, Zelle, ...) implementa un parser que sabe
reconocer sus correos y extraer los datos en un shape canonico comun.

La ingesta recorre los parsers registrados, le pregunta a cada uno
puede_parsear(correo) y usa el primero que reconoce el correo.

Shape canonico que devuelve parse() (o None si no pudo):
    {
        'metodo': str,                  # PaymentProvider
        'pagador_nombre': str | None,
        'importe_bruto': float,
        'moneda': str,
        'comision': float | None,
        'importe_neto': float | None,
        'transaction_id': str | None,
        'fecha_pago': datetime | None,
        'datos_extra': dict,            # propio del proveedor (subtipo, memo, ...)
    }

Los campos de sobre (email_message_id, cuenta_destino) NO los pone el parser:
los rellena la ingesta desde el dict `correo` (message_id, to_raw).

El dict `correo` que recibe cada parser viene de GmailService con las claves:
    message_id, subject, sender, to_raw, date, html_body, imap_uid
"""
from abc import ABC, abstractmethod
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional


class EmailPaymentParser(ABC):
    """Clase base para los parsers de correos de pago (patron Strategy)."""

    #: Metodo al que pertenece el parser (valor de PaymentProvider).
    metodo: str = ''

    @abstractmethod
    def puede_parsear(self, correo: dict) -> bool:
        """
        Indica si este parser reconoce el correo como un pago suyo.

        Debe ser barato y especifico: validar remitente Y marcadores reales
        de pago (no basta el remitente, que tambien manda otros correos).

        Args:
            correo: Dict del correo (claves de GmailService).

        Returns:
            bool: True si parse() deberia poder extraer el pago.
        """

    @abstractmethod
    def parse(self, correo: dict) -> Optional[dict]:
        """
        Extrae los datos del pago en el shape canonico.

        Args:
            correo: Dict del correo (claves de GmailService).

        Returns:
            dict con el shape canonico, o None si no se pudo extraer.
        """

    @staticmethod
    def _fecha_desde_header(correo: dict) -> Optional[datetime]:
        """
        Fecha del header Date del correo, como respaldo.

        Util cuando el cuerpo no expone una fecha de pago (Zelle) o el layout
        la esconde (payouts de PayPal). Devuelve datetime naive (sin tz) para
        ser consistente con las columnas DateTime del modelo.

        Args:
            correo: Dict del correo (debe traer la clave 'date').

        Returns:
            datetime naive, o None si no se pudo parsear.
        """
        raw = correo.get('date')
        if not raw:
            return None
        try:
            dt = parsedate_to_datetime(raw)
            return dt.replace(tzinfo=None) if dt else None
        except (TypeError, ValueError):
            return None