"""
Utilidades de fecha/hora para presentación y para consultas de negocio.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

_TZ_COLOMBIA = ZoneInfo('America/Bogota')

# Colombia no tiene horario de verano: el offset frente a UTC es fijo los
# 365 días del año. Sirve para desplazar timestamps en consultas SQL (ver
# AccountingService.get_daily_fees) sin tener que convertir fila por fila.
BOGOTA_UTC_OFFSET = timedelta(hours=5)


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


def utcnow_naive() -> datetime:
    """Hora actual en UTC, naive (sin tzinfo).

    Reemplazo de datetime.utcnow() (deprecado desde Python 3.12): da
    exactamente el mismo valor que daba datetime.utcnow(), listo para
    guardar en columnas DateTime que no llevan zona horaria, pero sin el
    warning de deprecación.

    Returns:
        datetime naive que representa el instante actual en UTC.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def limites_dia_bogota(momento: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Límites (inicio y fin) de un día calendario de Bogotá, en UTC naive.

    El servidor de producción corre con el reloj del sistema en hora de
    Colombia, pero los timestamps se guardan en UTC (datetime.utcnow /
    utcnow_naive). Por eso "hoy" no se puede calcular con datetime.now():
    hay que tomar el día calendario de Bogotá y convertir sus límites a UTC
    ANTES de usarlos para filtrar columnas guardadas en UTC — si no, cerca
    de la medianoche de Bogotá los reportes pierden o desplazan pagos hasta
    por 5 horas.

    Args:
        momento: Instante de referencia (naive = se asume UTC, o aware).
            Por defecto, el instante actual.

    Returns:
        Tupla (inicio_utc, fin_utc): medianoche de Bogotá de ese día
        calendario y el último microsegundo antes de la medianoche
        siguiente, ambos como datetime naive en UTC.
    """
    if momento is None:
        referencia = datetime.now(_TZ_COLOMBIA)
    else:
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=timezone.utc)
        referencia = momento.astimezone(_TZ_COLOMBIA)

    inicio_bogota = referencia.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_bogota = inicio_bogota + timedelta(days=1, microseconds=-1)

    inicio_utc = inicio_bogota.astimezone(timezone.utc).replace(tzinfo=None)
    fin_utc = fin_bogota.astimezone(timezone.utc).replace(tzinfo=None)
    return inicio_utc, fin_utc
