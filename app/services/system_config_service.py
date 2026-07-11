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

    # ── Slot SIM activo del módulo SMS ─────────────────────────────────────
    _KEY_SMS_ACTIVE_SLOT = 'sms_active_sim_slot'
    _SMS_SLOT_DESCRIPTION = 'Número de slot SIM activo en el board multi-SIM.'

    @classmethod
    def get_sms_active_slot(cls):
        """Devuelve el número de slot SIM activo, o None si no se ha fijado.

        Returns:
            int con el slot activo, o None.
        """
        raw = SystemConfig.get_value(cls._KEY_SMS_ACTIVE_SLOT)
        try:
            return int(raw) if raw is not None else None
        except (ValueError, TypeError):
            return None

    @classmethod
    def set_sms_active_slot(cls, slot_number: int) -> bool:
        """Persiste el slot SIM activo.

        Args:
            slot_number: Número de slot del board.

        Returns:
            True si se guardó correctamente.
        """
        return SystemConfig.set_value(
            key=cls._KEY_SMS_ACTIVE_SLOT,
            value=int(slot_number),
            description=cls._SMS_SLOT_DESCRIPTION,
        )

    # ── Pausa global del bot del chat web ──────────────────────────────────
    _KEY_WEBCHAT_BOT_PAUSED = 'webchat_bot_paused'
    _WEBCHAT_BOT_DESCRIPTION = (
        'Si el bot del chat web está en pausa global (operación manual).'
    )

    @classmethod
    def get_webchat_bot_paused(cls) -> bool:
        """Devuelve True si el bot del chat web está en pausa global.

        Por defecto True (operación manual mientras se valida el bot).
        """
        raw = SystemConfig.get_value(cls._KEY_WEBCHAT_BOT_PAUSED)
        if raw is None:
            return True
        return str(raw).lower() in ('1', 'true', 't', 'yes', 'si')

    @classmethod
    def set_webchat_bot_paused(cls, paused: bool) -> bool:
        """Persiste la pausa global del bot del chat web."""
        return SystemConfig.set_value(
            key=cls._KEY_WEBCHAT_BOT_PAUSED,
            value='true' if paused else 'false',
            description=cls._WEBCHAT_BOT_DESCRIPTION,
        )
