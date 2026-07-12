"""
Formateo de los mensajes del bot según el canal de destino.

El ``ConversationHandler`` produce un único texto con marcado HTML de Telegram
(``<b>``, ``<i>``...). Cada canal lo adapta:

- Telegram: lo usa tal cual.
- Web: subconjunto seguro de HTML (conserva el énfasis).
- Plano: sin marcado (SMS, WhatsApp, logs).
"""
import html as html_lib
import re

# Etiquetas de formato admitidas en el chat web.
_ETIQUETAS_WEB = ('b', 'strong', 'i', 'em', 'u', 's', 'code', 'pre')

_TAG_RE = re.compile(r'<[^>]+>')


class TelegramFormatter:
    """Telegram entiende el HTML tal cual lo produce el bot."""

    @staticmethod
    def format(text: str) -> str:
        """Devolver el texto sin cambios."""
        return text or ''


class PlainFormatter:
    """Texto sin marcado (SMS, WhatsApp, logs)."""

    @staticmethod
    def format(text: str) -> str:
        """Eliminar todas las etiquetas y desescapar las entidades."""
        if not text:
            return ''
        return html_lib.unescape(_TAG_RE.sub('', text)).strip()


class WebFormatter:
    """
    HTML seguro para el chat web.

    Estrategia: se escapa TODO el contenido y solo después se restauran las
    etiquetas de formato permitidas. Así, si un dato del usuario contiene
    ``<script>``, queda neutralizado; pero el ``<b>`` que emite el bot se
    conserva.
    """

    @staticmethod
    def format(text: str) -> str:
        """Convertir el HTML de Telegram en HTML seguro para el navegador."""
        if not text:
            return ''

        seguro = html_lib.escape(text)

        for etiqueta in _ETIQUETAS_WEB:
            seguro = seguro.replace(f'&lt;{etiqueta}&gt;', f'<{etiqueta}>')
            seguro = seguro.replace(f'&lt;/{etiqueta}&gt;', f'</{etiqueta}>')

        return seguro.strip()


def formatter_for(channel: str):
    """
    Formateador correspondiente a un canal.

    Args:
        channel: Canal de destino ('telegram', 'web', 'whatsapp', 'sms'...).

    Returns:
        La clase formateadora del canal (por defecto, texto plano).
    """
    return {
        'telegram': TelegramFormatter,
        'web': WebFormatter,
        'webchat': WebFormatter,
    }.get((channel or '').lower(), PlainFormatter)
