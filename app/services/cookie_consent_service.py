"""
Servicio de consentimiento de cookies.

Centraliza el formato, la lectura y la escritura de la cookie de
consentimiento, de modo que rutas y templates no manipulen su estructura
directamente.
"""
import json
from typing import Any, Dict
from urllib.parse import quote, unquote

from flask import current_app

from app.services.base_service import BaseService


class CookieConsentService(BaseService):
    """
    Gestiona el consentimiento de cookies del visitante.

    El consentimiento se guarda en una cookie propia (estrictamente necesaria,
    por lo que no requiere consentimiento previo) con el formato URL-encoded::

        {"v": "<version>", "c": {"necessary": true, "preferences": bool, "analytics": bool}}

    Categorías:
    - necessary: siempre activa (sesión, seguridad). No se puede desactivar.
    - preferences: recordar ajustes del visitante (idioma, tema, etc.).
    - analytics: medición de uso.
    """

    # Categorías opcionales (necessary es implícita y siempre True)
    OPTIONAL_CATEGORIES = ('preferences', 'analytics')

    @classmethod
    def get_client_config(cls) -> Dict[str, Any]:
        """
        Obtener la configuración de la cookie de consentimiento.

        Returns:
            Dict con name, version y max_age_days desde la config de la app.
        """
        return {
            'name': current_app.config.get('COOKIE_CONSENT_NAME', 'ceiba21_consent'),
            'version': str(current_app.config.get('COOKIE_CONSENT_VERSION', '1')),
            'max_age_days': int(current_app.config.get('COOKIE_CONSENT_MAX_AGE_DAYS', 180)),
        }

    @classmethod
    def default_categories(cls) -> Dict[str, bool]:
        """
        Categorías por defecto (sin consentimiento dado): solo las necesarias.

        Returns:
            Dict de categorías con sus valores por defecto.
        """
        categories = {cat: False for cat in cls.OPTIONAL_CATEGORIES}
        categories['necessary'] = True
        return categories

    @classmethod
    def normalize_categories(cls, raw: Any) -> Dict[str, bool]:
        """
        Normalizar categorías recibidas a un conjunto conocido.

        Fuerza 'necessary' a True e ignora claves desconocidas.

        Args:
            raw: Dict potencialmente arbitrario con categorías.

        Returns:
            Dict de categorías saneado.
        """
        categories = cls.default_categories()
        if isinstance(raw, dict):
            for cat in cls.OPTIONAL_CATEGORIES:
                categories[cat] = bool(raw.get(cat, False))
        categories['necessary'] = True
        return categories

    @classmethod
    def get_consent(cls, request) -> Dict[str, Any]:
        """
        Leer el estado de consentimiento desde la cookie de la petición.

        Args:
            request: Petición Flask actual.

        Returns:
            Dict con 'given' (bool), 'version' (str) y 'categories' (dict).
            Si no hay cookie o la versión cambió, 'given' es False.
        """
        cfg = cls.get_client_config()
        raw = request.cookies.get(cfg['name'])

        if not raw:
            return {'given': False, 'version': cfg['version'],
                    'categories': cls.default_categories()}

        try:
            data = json.loads(unquote(raw))
        except (ValueError, TypeError):
            return {'given': False, 'version': cfg['version'],
                    'categories': cls.default_categories()}

        version = str(data.get('v', ''))
        categories = cls.normalize_categories(data.get('c'))

        # Si la versión de la política cambió, se vuelve a pedir consentimiento.
        if version != cfg['version']:
            return {'given': False, 'version': cfg['version'], 'categories': categories}

        return {'given': True, 'version': version, 'categories': categories}

    @classmethod
    def has_category(cls, request, category: str) -> bool:
        """
        Indicar si una categoría de cookies fue consentida.

        Args:
            request: Petición Flask actual.
            category: Nombre de la categoría.

        Returns:
            True si la categoría está activa (necessary siempre True).
        """
        if category == 'necessary':
            return True
        consent = cls.get_consent(request)
        return bool(consent['given'] and consent['categories'].get(category, False))

    @classmethod
    def _build_cookie_value(cls, categories: Dict[str, bool], version: str) -> str:
        """
        Construir el valor URL-encoded de la cookie de consentimiento.

        Args:
            categories: Categorías saneadas.
            version: Versión de la política.

        Returns:
            Valor listo para Set-Cookie.
        """
        payload = json.dumps({'v': version, 'c': categories}, separators=(',', ':'))
        return quote(payload)

    @classmethod
    def apply_consent_cookie(cls, response, categories: Any):
        """
        Escribir la cookie de consentimiento en la respuesta.

        La cookie NO es HttpOnly (el JS del banner la lee) y es Secure solo en
        producción (HTTPS). Se registra el consentimiento para auditoría.

        Args:
            response: Respuesta Flask a la que añadir la cookie.
            categories: Categorías elegidas por el usuario.

        Returns:
            La misma respuesta, con la cookie añadida.
        """
        cfg = cls.get_client_config()
        normalized = cls.normalize_categories(categories)
        value = cls._build_cookie_value(normalized, cfg['version'])
        secure = bool(current_app.config.get('SESSION_COOKIE_SECURE', False))

        response.set_cookie(
            cfg['name'],
            value,
            max_age=cfg['max_age_days'] * 24 * 60 * 60,
            secure=secure,
            httponly=False,   # el banner (JS) necesita leerla
            samesite='Lax',
            path='/',
        )
        cls.log_info(f"Consentimiento de cookies registrado: {normalized}")
        return response
