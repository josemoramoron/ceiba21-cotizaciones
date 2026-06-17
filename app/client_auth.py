"""
Sesión y autorización de clientes web.

Los operadores usan Flask-Login (su user_loader carga Operator). Como Operator
y WebUser comparten la forma de get_id(), no pueden compartir el mismo
user_loader sin colisionar. Por eso los clientes usan autenticación basada en
la sesión de servidor: se guarda el id del WebUser en session['client_user_id'].
"""
from functools import wraps
from typing import Optional

from flask import g, redirect, request, session, url_for

from app.models import db

SESSION_KEY = 'client_user_id'


def login_client(web_user) -> None:
    """Iniciar sesión de cliente guardando su id en la sesión."""
    session[SESSION_KEY] = web_user.id
    session.permanent = True
    g._current_client = web_user


def logout_client() -> None:
    """Cerrar la sesión de cliente."""
    session.pop(SESSION_KEY, None)
    g.pop('_current_client', None)


def current_client():
    """
    Obtener el WebUser autenticado en esta petición, o None.

    El resultado se cachea en ``g`` para no repetir consultas dentro de una
    misma petición.

    Returns:
        El WebUser autenticado, o None si no hay cliente en sesión.
    """
    if SESSION_KEY not in session:
        return None

    if not hasattr(g, '_current_client'):
        from app.models.web_user import WebUser
        g._current_client = db.session.get(WebUser, session[SESSION_KEY])

    return g._current_client


def client_login_required(view_func):
    """Decorador: exige cliente autenticado; si no, redirige al login."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if current_client() is None:
            return redirect(url_for('cuenta.login', next=request.path))
        return view_func(*args, **kwargs)
    return wrapper
