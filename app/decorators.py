"""
Control de acceso por rol del panel.

Centraliza la autorización por rol:
- ADMIN: acceso total al panel ``/dashboard``.
- OPERATOR: solo la sección de pagos ``/dashboard/pagos``.

Se ofrece tanto un guard para usar en ``before_request`` (``require_roles``)
como decoradores de ruta (``admin_required``, ``operator_or_admin_required``).
"""
from functools import wraps
from typing import Optional

from flask import flash, redirect, request, url_for
from flask_login import current_user

from app.models.operator import OperatorRole


def home_endpoint_for_role(role: Optional[OperatorRole]) -> str:
    """
    Endpoint de inicio según el rol del operador.

    Args:
        role: Rol del operador autenticado.

    Returns:
        Nombre del endpoint al que dirigir al operador. Los administradores
        van al panel; los operadores, a pagos; cualquier otro caso
        (p. ej. viewer, aún no contemplado en el modelo activo) se cierra
        sesión de forma segura para evitar bucles de redirección.
    """
    if role == OperatorRole.ADMIN:
        return 'dashboard.index'
    if role == OperatorRole.OPERATOR:
        return 'pagos.index'
    return 'auth.logout'


def require_roles(*roles: OperatorRole):
    """
    Guard de autorización por rol para usar en un ``before_request``.

    Comprueba autenticación y rol del usuario actual.

    Args:
        *roles: Roles autorizados a acceder.

    Returns:
        Una redirección (Response) si se deniega el acceso, o ``None`` si se
        permite (en cuyo caso la petición continúa con normalidad).
    """
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.path))

    if current_user.role not in roles:
        flash('No tienes permiso para acceder a esa sección.', 'error')
        return redirect(url_for(home_endpoint_for_role(current_user.role)))

    return None


def role_required(*roles: OperatorRole):
    """
    Decorador de ruta que exige uno de los roles indicados.

    Args:
        *roles: Roles autorizados.

    Returns:
        El decorador que envuelve la vista.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            denied = require_roles(*roles)
            if denied is not None:
                return denied
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorador de ruta: solo ADMIN."""
    return role_required(OperatorRole.ADMIN)(view_func)


def operator_or_admin_required(view_func):
    """Decorador de ruta: ADMIN u OPERATOR (sección de pagos)."""
    return role_required(OperatorRole.ADMIN, OperatorRole.OPERATOR)(view_func)

def rate_limit(name: str, session_rules=(), ip_rules=()):
    """
    Limitar la tasa de peticiones a un endpoint público.

    Aplica doble llave: por sesión del visitante (``anon_id``) y por IP real
    (``CF-Connecting-IP``), para que borrar cookies no baste para saltárselo.

    Args:
        name: Identificador del endpoint (parte de la clave en Redis).
        session_rules: Iterable de (límite, ventana_segundos) por sesión.
        ip_rules: Iterable de (límite, ventana_segundos) por IP.

    Returns:
        El decorador que envuelve la vista. Responde 429 si se excede.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            from flask import jsonify, request, session
            from app.services.rate_limit_service import RateLimitService

            anon_id = session.get('chat_anon_id')
            if anon_id:
                for limite, ventana in session_rules:
                    key = f"rl:{name}:s:{anon_id}:{ventana}"
                    permitido, reintentar = RateLimitService.hit(key, limite, ventana)
                    if not permitido:
                        return _demasiadas_peticiones(reintentar)

            ip = RateLimitService.client_ip(request)
            for limite, ventana in ip_rules:
                key = f"rl:{name}:i:{ip}:{ventana}"
                permitido, reintentar = RateLimitService.hit(key, limite, ventana)
                if not permitido:
                    return _demasiadas_peticiones(reintentar)

            return view_func(*args, **kwargs)
        return wrapper
    return decorator


def _demasiadas_peticiones(reintentar: int):
    """Respuesta 429 estándar para los endpoints públicos."""
    from flask import jsonify
    respuesta = jsonify({
        'ok': False,
        'error': 'demasiadas_peticiones',
        'retry_after': reintentar,
    })
    respuesta.status_code = 429
    respuesta.headers['Retry-After'] = str(reintentar)
    return respuesta

