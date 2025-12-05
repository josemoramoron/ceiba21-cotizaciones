"""
Servicio de cache con Redis.
Maneja cache de tasas, cotizaciones y datos frecuentes.
"""
from app.services.base_service import BaseService
from app import cache
from typing import Optional, Any
from functools import wraps


def get_redis_client():
    """Obtener redis_client dinámicamente"""
    import app as app_module
    return app_module.redis_client


class CacheService(BaseService):
    """
    Servicio para gestión centralizada de cache con Redis.
    
    Responsabilidades:
    - Cache de cotizaciones y tasas
    - Invalidación de cache
    - Gestión de TTL (Time To Live)
    """
    
    # TTL predeterminados (en segundos)
    TTL_QUOTES = 300      # 5 minutos para cotizaciones
    TTL_RATES = 300       # 5 minutos para tasas
    TTL_STATS = 60        # 1 minuto para estadísticas
    TTL_CALCULATOR = 120  # 2 minutos para calculadora
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """
        Obtener valor desde cache.
        
        Args:
            key: Clave del cache
            
        Returns:
            Valor en cache o None
        """
        try:
            redis_client = get_redis_client()
            return redis_client.get(key)
        except Exception as e:
            cls.log_error(f"Error al obtener cache {key}", e)
            return None
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Guardar valor en cache.
        
        Args:
            key: Clave del cache
            value: Valor a guardar
            ttl: Tiempo de vida en segundos (None = sin expiración)
            
        Returns:
            bool: True si se guardó exitosamente
        """
        try:
            redis_client = get_redis_client()
            if ttl:
                redis_client.setex(key, ttl, value)
            else:
                redis_client.set(key, value)
            return True
        except Exception as e:
            cls.log_error(f"Error al guardar cache {key}", e)
            return False
    
    @classmethod
    def delete(cls, key: str) -> bool:
        """
        Eliminar clave del cache.
        
        Args:
            key: Clave a eliminar
            
        Returns:
            bool: True si se eliminó
        """
        try:
            redis_client = get_redis_client()
            redis_client.delete(key)
            return True
        except Exception as e:
            cls.log_error(f"Error al eliminar cache {key}", e)
            return False
    
    @classmethod
    def clear_all(cls) -> bool:
        """
        Limpiar todo el cache.
        
        Returns:
            bool: True si se limpió exitosamente
        """
        try:
            cache.clear()
            return True
        except Exception as e:
            cls.log_error("Error al limpiar cache", e)
            return False
    
    @classmethod
    def invalidate_quotes_cache(cls) -> bool:
        """
        Invalidar cache de cotizaciones.
        Llamar cuando se actualizan tasas desde dashboard.
        
        Returns:
            bool: True si se invalidó
        """
        try:
            redis_client = get_redis_client()
            
            # Eliminar cache de flask-caching
            cache.delete('all_quotes')
            cache.delete('active_quotes')
            
            # Eliminar keys de Redis con patrón
            for key in redis_client.scan_iter("quote:*"):
                redis_client.delete(key)
            
            for key in redis_client.scan_iter("calc:*"):
                redis_client.delete(key)
            
            cls.log_info("Cache de cotizaciones invalidado")
            return True
        except Exception as e:
            cls.log_error("Error al invalidar cache de cotizaciones", e)
            return False
    
    @classmethod
    def get_or_set(cls, key: str, callback, ttl: int = 300) -> Any:
        """
        Obtener desde cache o ejecutar callback y guardar.
        
        Args:
            key: Clave del cache
            callback: Función a ejecutar si no hay cache
            ttl: Tiempo de vida
            
        Returns:
            Valor desde cache o del callback
        """
        # Buscar en cache
        cached = cls.get(key)
        if cached is not None:
            return cached
        
        # Ejecutar callback
        value = callback()
        
        # Guardar en cache
        cls.set(key, value, ttl)
        
        return value
    
    @staticmethod
    def cached(timeout=300, key_prefix='view'):
        """
        Decorador para cachear resultados de funciones.
        
        Args:
            timeout: Tiempo de vida en segundos
            key_prefix: Prefijo para la clave
            
        Returns:
            Decorador
            
        Example:
            @CacheService.cached(timeout=300, key_prefix='quotes')
            def get_all_quotes():
                return Quote.query.all()
        """
        return cache.cached(timeout=timeout, key_prefix=key_prefix)
