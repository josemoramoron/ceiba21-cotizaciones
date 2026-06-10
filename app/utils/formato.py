"""
Utilidades de formato de presentación.
"""
from decimal import Decimal
from typing import Union

Numerico = Union[int, float, Decimal, None]

# Intercambio simultáneo de separadores: US (1,234.56) -> EU (1.234,56)
_SWAP_US_A_EU = str.maketrans({',': '.', '.': ','})


def formato_eu(valor: Numerico, decimales: int = 2) -> str:
    """Formatea un número en estilo europeo: 1.234,56.

    Usa el punto como separador de miles y la coma como separador decimal.

    Args:
        valor: Número a formatear (int, float, Decimal) o None.
        decimales: Cantidad de decimales a mostrar. Por defecto 2.

    Returns:
        Cadena formateada (ej. '1.234,56'), o '' si el valor es None o no
        es numérico.
    """
    if valor is None:
        return ''
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return ''
    formato_us = f"{numero:,.{decimales}f}"  # '1,234.56' (estilo US)
    return formato_us.translate(_SWAP_US_A_EU)