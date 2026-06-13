"""
Modelo de configuración del sistema (key-value store).

Almacena parámetros configurables desde el dashboard sin
necesidad de redeploy ni modificación de .env.
"""
from typing import Any, Optional

from app.models import db
from app.models.base import BaseModel


class SystemConfig(BaseModel):
    """
    Almacén key-value para configuración del sistema.

    Cada fila representa un parámetro nombrado. El valor se
    persiste siempre como texto; la conversión de tipos es
    responsabilidad de SystemConfigService.

    Usar SystemConfigService para leer/escribir en lugar
    de consultar esta clase directamente.
    """

    __tablename__ = 'system_config'

    # ── Columnas ──────────────────────────────────────────────────────────
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)

    # ── Constantes de claves conocidas ────────────────────────────────────
    KEY_CALC_MARGIN = 'public_calculator_margin'

    def __repr__(self) -> str:
        return f'<SystemConfig {self.key}={self.value!r}>'

    def to_dict(self) -> dict:
        """Serializa la fila a diccionario plano."""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_value(cls, key: str, default: Any = None) -> Optional[str]:
        """
        Lee el valor raw (string) de una clave.

        Args:
            key: Clave a consultar.
            default: Valor devuelto si la clave no existe.

        Returns:
            String con el valor almacenado, o default si no existe.
        """
        row = cls.query.filter_by(key=key).first()
        return row.value if row else default

    @classmethod
    def set_value(
        cls,
        key: str,
        value: Any,
        description: Optional[str] = None,
    ) -> bool:
        """
        Persiste una clave con su valor (upsert).

        Args:
            key: Clave a escribir.
            value: Valor a almacenar (se convierte a str).
            description: Descripción opcional del parámetro.

        Returns:
            True si se guardó correctamente, False si hubo error.
        """
        try:
            row = cls.query.filter_by(key=key).first()
            if row:
                row.value = str(value)
                if description is not None:
                    row.description = description
            else:
                row = cls(key=key, value=str(value), description=description)
                db.session.add(row)
            db.session.commit()
            return True
        except Exception as exc:
            db.session.rollback()
            return False
