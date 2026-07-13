"""
Tests del formateo de mensajes por canal.

Lo crítico aquí es la seguridad: el texto del bot interpola datos que escribe el
usuario (nombre, banco, titular), así que el formateador web NO debe dejar pasar
HTML ejecutable.
"""
from app.bot.formatters import (
    WebFormatter, PlainFormatter, TelegramFormatter, formatter_for
)


class TestWebFormatter:
    """El chat web conserva el énfasis pero neutraliza el HTML peligroso."""

    def test_conserva_negritas(self):
        """Las etiquetas de formato del bot se mantienen."""
        assert WebFormatter.format('<b>Datos verificados</b>') == \
            '<b>Datos verificados</b>'

    def test_conserva_cursivas_y_codigo(self):
        """El resto de etiquetas permitidas también sobrevive."""
        resultado = WebFormatter.format('<i>hola</i> <code>ABC</code>')
        assert '<i>hola</i>' in resultado
        assert '<code>ABC</code>' in resultado

    def test_neutraliza_script(self):
        """Un <script> inyectado queda escapado, nunca ejecutable."""
        resultado = WebFormatter.format("Titular: <script>alert('x')</script>")
        assert '<script>' not in resultado
        assert '&lt;script&gt;' in resultado

    def test_neutraliza_atributos_peligrosos(self):
        """Los vectores por atributo (onerror) también se escapan."""
        resultado = WebFormatter.format('<img src=x onerror=alert(1)>')
        assert '<img' not in resultado
        assert '&lt;img' in resultado

    def test_escapa_ampersand(self):
        """El texto normal con & se escapa correctamente."""
        assert '&amp;' in WebFormatter.format('Banco & Cía')

    def test_texto_vacio(self):
        """Un texto vacío no revienta."""
        assert WebFormatter.format('') == ''
        assert WebFormatter.format(None) == ''


class TestPlainFormatter:
    """El canal plano elimina todo el marcado."""

    def test_elimina_etiquetas(self):
        assert PlainFormatter.format('<b>Hola</b> mundo') == 'Hola mundo'


class TestTelegramFormatter:
    """Telegram recibe el HTML tal cual."""

    def test_pasa_sin_cambios(self):
        assert TelegramFormatter.format('<b>Hola</b>') == '<b>Hola</b>'


class TestFormatterFor:
    """La fábrica devuelve el formateador correcto por canal."""

    def test_canales_conocidos(self):
        assert formatter_for('telegram') is TelegramFormatter
        assert formatter_for('web') is WebFormatter
        assert formatter_for('webchat') is WebFormatter

    def test_canal_desconocido_cae_en_plano(self):
        """Un canal sin formateador propio no debe filtrar HTML."""
        assert formatter_for('whatsapp') is PlainFormatter
        assert formatter_for('') is PlainFormatter
