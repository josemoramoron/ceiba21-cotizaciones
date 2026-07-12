"""
Límite de tasa (rate limiting) sobre Redis.

Contadores atómicos con ventana fija: ``INCR`` + ``EXPIRE``. Se usa para
proteger los endpoints públicos del chat, que no requieren autenticación.

Política ante fallo de Redis: **fail-open** (se permite la petición y se
registra el error). Es preferible un chat abierto a un chat caído.
"""
from typing import Tuple

from flask import Request

from app.services.base_service import BaseService
from app.services.cache_service import get_redis_client


class RateLimitService(BaseService):
    """Contadores de límite de tasa en Redis."""

    @staticmethod
    def client_ip(request: Request) -> str:
        """
        IP real del visitante.

        Detrás del Cloudflare Tunnel, ``remote_addr`` es siempre 127.0.0.1, así
        que la IP real llega en la cabecera ``CF-Connecting-IP``.
        """
        return (
            request.headers.get('CF-Connecting-IP')
            or request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            or request.remote_addr
            or 'desconocida'
        )

    @classmethod
    def hit(cls, key: str, limit: int, window: int) -> Tuple[bool, int]:
        """
        Registrar un acceso y decidir si se permite.

        Args:
            key: Clave del contador (identifica sujeto + endpoint + ventana).
            limit: Máximo de accesos permitidos dentro de la ventana.
            window: Duración de la ventana, en segundos.

        Returns:
            Tupla (permitido, segundos_para_reintentar).
        """
        try:
            redis_client = get_redis_client()
            actual = redis_client.incr(key)

            if actual == 1:
                redis_client.expire(key, window)

            if actual > limit:
                ttl = redis_client.ttl(key)
                return False, max(int(ttl or window), 1)

            return True, 0

        except Exception as exc:
            cls.log_error(f"Rate limit no disponible ({key}), se permite", exc)
            return True, 0
