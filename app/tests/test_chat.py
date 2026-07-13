"""
Tests del chat web: conversaciones, mensajes, pausa del bot y comprobantes.

Los tests usan el bot en PAUSA para ser deterministas (si el bot respondiera,
dependeríamos del estado conversacional en Redis).
"""
import io

import pytest

from app.models.chat import ChatConversation, ChatMessage
from app.services.chat_service import ChatService
from app.services.system_config_service import SystemConfigService


@pytest.fixture
def bot_en_pausa(db):
    """Pausa global del bot durante el test, restaurando el valor previo."""
    previo = SystemConfigService.get_webchat_bot_paused()
    SystemConfigService.set_webchat_bot_paused(True)
    yield
    SystemConfigService.set_webchat_bot_paused(previo)


@pytest.fixture
def limpiar_chat(db):
    """Borra las conversaciones creadas por el test al terminar."""
    creadas = []
    yield creadas
    for conv in creadas:
        ChatMessage.query.filter_by(conversation_id=conv.id).delete()
        db.session.delete(conv)
    db.session.commit()


class TestMensajesDelCliente:
    """Alta de mensajes desde el widget."""

    def test_guarda_mensaje_y_crea_conversacion(self, db, bot_en_pausa,
                                                limpiar_chat):
        """Un mensaje nuevo crea la conversación y su User de canal webchat."""
        conv, msg = ChatService.post_client_message(
            anon_id='test_anon_001', web_user=None, text='hola'
        )
        limpiar_chat.append(conv)

        assert conv is not None
        assert msg.body == 'hola'
        assert msg.sender == 'client'
        assert conv.user_id is not None  # se creó el User webchat
        assert conv.unread_for_operator == 1

    def test_guarda_la_etiqueta_no_el_callback(self, db, bot_en_pausa,
                                               limpiar_chat):
        """Al pulsar un botón se guarda 'Bolívares', no 'currency:1'."""
        conv, msg = ChatService.post_client_message(
            anon_id='test_anon_002', web_user=None,
            text='currency:1', label='Bolívares'
        )
        limpiar_chat.append(conv)

        assert msg.body == 'Bolívares'
        assert 'currency:1' not in msg.body

    def test_mensaje_vacio_no_crea_nada(self, db, bot_en_pausa):
        """Un mensaje en blanco se rechaza."""
        conv, msg = ChatService.post_client_message(
            anon_id='test_anon_003', web_user=None, text='   '
        )
        assert conv is None and msg is None

    def test_reutiliza_la_conversacion_del_visitante(self, db, bot_en_pausa,
                                                     limpiar_chat):
        """Dos mensajes del mismo anon_id van a la misma conversación."""
        conv1, _ = ChatService.post_client_message(
            anon_id='test_anon_004', web_user=None, text='uno')
        conv2, _ = ChatService.post_client_message(
            anon_id='test_anon_004', web_user=None, text='dos')
        limpiar_chat.append(conv1)

        assert conv1.id == conv2.id
        assert conv2.unread_for_operator == 2


class TestPausaDelBot:
    """El bot solo habla si no hay pausa global NI pausa por conversación."""

    def test_pausa_global_manda(self, db, bot_en_pausa, limpiar_chat):
        """Con pausa global, el bot calla aunque la conversación esté activa."""
        conv, _ = ChatService.post_client_message(
            anon_id='test_anon_005', web_user=None, text='hola')
        limpiar_chat.append(conv)

        conv.bot_paused = False
        conv.save()

        assert ChatService.is_bot_active_for(conv) is False

    def test_pausa_por_conversacion(self, db, limpiar_chat):
        """Sin pausa global, la pausa local sigue silenciando al bot."""
        previo = SystemConfigService.get_webchat_bot_paused()
        SystemConfigService.set_webchat_bot_paused(True)
        conv, _ = ChatService.post_client_message(
            anon_id='test_anon_006', web_user=None, text='hola')
        limpiar_chat.append(conv)

        SystemConfigService.set_webchat_bot_paused(False)
        conv.bot_paused = True
        conv.save()
        assert ChatService.is_bot_active_for(conv) is False

        SystemConfigService.set_webchat_bot_paused(previo)


class TestPolling:
    """El widget solo recibe lo que no escribió él mismo."""

    def test_nuevos_excluye_los_del_cliente(self, db, bot_en_pausa,
                                            limpiar_chat):
        """get_new_for_client no devuelve los mensajes del propio cliente."""
        conv, msg = ChatService.post_client_message(
            anon_id='test_anon_007', web_user=None, text='hola')
        limpiar_chat.append(conv)

        nuevos = ChatService.get_new_for_client(conv.id, 0)
        assert all(m['sender'] != 'client' for m in nuevos)

    def test_historial_incluye_todo(self, db, bot_en_pausa, limpiar_chat):
        """El historial sí trae los mensajes del cliente."""
        conv, _ = ChatService.post_client_message(
            anon_id='test_anon_008', web_user=None, text='hola')
        limpiar_chat.append(conv)

        historial = ChatService.history(conv.id)
        assert len(historial) == 1
        assert historial[0]['body'] == 'hola'


class TestComprobantes:
    """Validación de los archivos subidos por el cliente."""

    def test_rechaza_extension_no_permitida(self, db):
        """Un .exe no se acepta."""
        archivo = io.BytesIO(b'contenido')
        archivo.filename = 'virus.exe'

        from werkzeug.datastructures import FileStorage
        fs = FileStorage(stream=io.BytesIO(b'x' * 100), filename='virus.exe')

        ok, mensaje, url = ChatService._save_proof_file(fs, 'TEST-001')
        assert ok is False
        assert url is None

    def test_rechaza_archivo_grande(self, db):
        """Un archivo de más de 5 MB se rechaza."""
        from werkzeug.datastructures import FileStorage
        grande = io.BytesIO(b'x' * (6 * 1024 * 1024))
        fs = FileStorage(stream=grande, filename='comprobante.jpg')

        ok, mensaje, url = ChatService._save_proof_file(fs, 'TEST-002')
        assert ok is False
        assert '5 MB' in mensaje

    def test_rechaza_archivo_vacio(self, db):
        """Un archivo de 0 bytes se rechaza."""
        from werkzeug.datastructures import FileStorage
        fs = FileStorage(stream=io.BytesIO(b''), filename='vacio.png')

        ok, mensaje, url = ChatService._save_proof_file(fs, 'TEST-003')
        assert ok is False


class TestRutasDelChat:
    """Endpoints públicos del widget."""

    def test_mensaje_requiere_texto(self, client):
        """Sin texto, responde 400."""
        r = client.post('/chat/mensaje', json={'texto': ''})
        assert r.status_code == 400

    def test_nuevos_sin_sesion_devuelve_vacio(self, client):
        """Un visitante sin conversación no recibe mensajes."""
        r = client.get('/chat/nuevos')
        assert r.status_code == 200
        assert r.get_json()['messages'] == []

    def test_panel_de_operador_exige_admin(self, client):
        """El panel del chat no es público."""
        r = client.get('/dashboard/chat/', follow_redirects=False)
        assert r.status_code in (301, 302, 401, 403)
