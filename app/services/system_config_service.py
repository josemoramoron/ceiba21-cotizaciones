"""
Servicio de configuración del sistema.

Abstrae el acceso a SystemConfig con tipado fuerte,
validación y valores por defecto para cada parámetro.
"""
from app.models.system_config import SystemConfig


class SystemConfigService:
    """
    Acceso tipado a los parámetros globales del sistema.

    Cada parámetro expone un par get_/set_ que encapsula
    la conversión de tipos, la validación y el valor por
    defecto. Nunca consultar SystemConfig directamente
    desde rutas o templates.
    """

    # ── Margen calculadora pública ─────────────────────────────────────────
    _DEFAULT_MARGIN: float = 0.0
    _MARGIN_DESCRIPTION = (
        'Margen (%) de la calculadora pública. '
        'Fórmula: precio_cliente = tasa_ref / (1 + margen / 100)'
    )

    @classmethod
    def get_public_calculator_margin(cls) -> float:
        """
        Retorna el margen (%) aplicado a la calculadora pública.

        Fórmula aplicada al precio de referencia::

            precio_cliente = tasa_ref / (1 + margen / 100)

        Returns:
            Float con el margen porcentual. 0.0 si no está configurado.
        """
        raw = SystemConfig.get_value(SystemConfig.KEY_CALC_MARGIN)
        try:
            value = float(raw) if raw is not None else cls._DEFAULT_MARGIN
            return max(0.0, value)
        except (ValueError, TypeError):
            return cls._DEFAULT_MARGIN

    @classmethod
    def set_public_calculator_margin(cls, margin: float) -> bool:
        """
        Persiste el margen de la calculadora pública.

        Args:
            margin: Porcentaje de margen en el rango [0, 100].

        Returns:
            True si se guardó correctamente.

        Raises:
            ValueError: Si margin está fuera del rango [0, 100].
        """
        if not (0.0 <= margin <= 100.0):
            raise ValueError(
                f'El margen debe estar entre 0 y 100, recibido: {margin}'
            )
        return SystemConfig.set_value(
            key=SystemConfig.KEY_CALC_MARGIN,
            value=round(margin, 4),
            description=cls._MARGIN_DESCRIPTION,
        )
