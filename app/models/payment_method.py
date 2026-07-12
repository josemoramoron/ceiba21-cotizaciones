"""
Modelo de Métodos de Pago / Billeteras (REF, PayPal, Zelle, etc.)
"""
from datetime import datetime
from typing import List, Optional

from app.models import db


class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'

    # Códigos de métodos ESTRUCTURALES/PIVOTE: permanecen activos (se usan para
    # calcular los demás métodos) pero NUNCA se muestran en superficies públicas
    # (tabla pública, calculadora, publicaciones de Telegram). Es la única
    # fuente de verdad de la visibilidad pública: para ocultar un método nuevo
    # en el futuro basta con añadir su código aquí, y toda superficie pública
    # que pase por get_visibles_publico lo respetará sin tocar cada vista.
    CODIGOS_NO_PUBLICOS: frozenset = frozenset({'REF'})

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Configuración USD centralizada (aplica a todas las monedas)
    # Datos del receptor que se muestran al cliente al pagar (correo PayPal,
    # dirección USDT, cuenta bancaria...). Texto libre: cada método pide datos
    # distintos, así que agregar un método nuevo no requiere tocar código.
    datos_receptor = db.Column(db.Text, nullable=True)

    value_type = db.Column(db.String(20), default='manual', nullable=False)
    usd_value = db.Column(db.Numeric(10, 6), nullable=True)
    usd_formula = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<PaymentMethod {self.code}>'

    @property
    def es_visible_publico(self) -> bool:
        """Indica si el método debe mostrarse en superficies públicas.

        Un método es público cuando está activo y su código no figura entre
        los códigos estructurales/pivote (``CODIGOS_NO_PUBLICOS``). Tanto los
        services como las rutas consultan esta propiedad en vez de comparar
        códigos sueltos, de modo que la regla de visibilidad vive en un solo
        lugar.

        Returns:
            True si el método puede mostrarse al público; False si está
            inactivo o es un método pivote.
        """
        if not self.active:
            return False
        return (self.code or '').upper() not in self.CODIGOS_NO_PUBLICOS

    @classmethod
    def get_visibles_publico(
        cls,
        limit: Optional[int] = None
    ) -> List['PaymentMethod']:
        """Devuelve los métodos visibles al público, ordenados.

        Filtra por ``active=True`` y excluye los códigos estructurales/pivote,
        manteniendo el orden de ``display_order``. Es el punto único que deben
        usar todas las superficies públicas (actuales y futuras) para listar
        métodos, de modo que ocultar uno nuevo no requiera tocar cada vista.

        Args:
            limit: Máximo de resultados a devolver (None = todos).

        Returns:
            Lista de PaymentMethod públicos ordenados por ``display_order``.
        """
        activos = (
            cls.query
            .filter_by(active=True)
            .order_by(cls.display_order.asc())
            .all()
        )
        visibles = [
            pm for pm in activos
            if (pm.code or '').upper() not in cls.CODIGOS_NO_PUBLICOS
        ]
        if limit is not None:
            return visibles[:limit]
        return visibles

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'active': self.active,
            'visible_publico': self.es_visible_publico,
            'display_order': self.display_order,
            'datos_receptor': self.datos_receptor,
            'value_type': self.value_type,
            'usd_value': float(self.usd_value) if self.usd_value else None,
            'usd_formula': self.usd_formula
        }

    def calculate_usd_value(self):
        """
        Calcula el valor en USD basado en el tipo de valor
        Este método es usado por todas las monedas
        """
        if self.value_type == 'manual':
            return float(self.usd_value) if self.usd_value else 1.0
        elif self.value_type == 'formula' and self.usd_formula:
            try:
                return float(eval(self.usd_formula))
            except:
                return 1.0
        return 1.0
