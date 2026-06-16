"""
Utilidades de fecha/hora para presentación.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_TZ_COLOMBIA = ZoneInfo('America/Bogota')


def hora_co(dt: datetime, fmt: str = '%d/%m/%Y %H:%M') -> str:
    """Convierte un datetime UTC a hora de Colombia y lo formatea.

    Los timestamps se persisten en UTC (datetime.utcnow). Esta función los
    convierte a la zona horaria de Colombia (UTC-5, sin horario de verano)
    para mostrarlos al usuario.

    Args:
        dt: Datetime en UTC (naive o aware). None devuelve cadena vacía.
        fmt: Formato strftime de salida. Por defecto 'dd/mm/aaaa HH:MM'.

    Returns:
        Cadena con la hora local de Colombia, o '' si dt es None.
    """
    if dt is None:
        return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ_COLOMBIA).strftime(fmt)