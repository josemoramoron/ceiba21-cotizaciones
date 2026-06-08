"""
Parsers de correos de pago (patron Strategy).

Cada parser sabe reconocer los correos de un proveedor y extraer los datos
en un shape canonico comun. La ingesta recorre los parsers registrados y usa
el primero cuyo puede_parsear() reconozca el correo.
"""
from app.services.parsers.base import EmailPaymentParser
from app.services.parsers.paypal_parser import PaypalParser
from app.services.parsers.wise_parser import WiseParser
from app.services.parsers.zelle_parser import ZelleParser

__all__ = [
    'EmailPaymentParser',
    'PaypalParser',
    'WiseParser',
    'ZelleParser',
]