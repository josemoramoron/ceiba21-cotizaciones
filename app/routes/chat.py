"""
Endpoints del chat web para el cliente (widget de la burbuja flotante).

Autenticación no requerida: el visitante puede ser anónimo (se le asigna un
``anon_id`` estable en la sesión) o un cliente logueado (WebUser).
"""
import uuid

from flask import Blueprint, jsonify, request, session

from app.client_auth import current_client
from app.services.chat_service import ChatService
from app.models.chat import ChatConversation

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

ANON_KEY = 'chat_anon_id'


def _anon_id() -> str:
    """Id de sesión anónima estable del visitante (se crea si no existe)."""
    aid = session.get(ANON_KEY)
    if not aid:
        aid = uuid.uuid4().hex
        session[ANON_KEY] = aid
        session.permanent = True
    return aid


@chat_bp.route('/mensaje', methods=['POST'])
def mensaje():
    """Recibir un mensaje del cliente."""
    data = request.get_json(silent=True) or {}
    text = data.get('texto') or data.get('text') or ''
    conv, msg = ChatService.post_client_message(
        anon_id=_anon_id(),
        web_user=current_client(),
        text=text,
        country=ChatService.country_from_request(request),
        label=data.get('etiqueta'),
    )
    if conv is None:
        return jsonify({'ok': False, 'error': 'mensaje_vacio'}), 400
    return jsonify({
        'ok': True,
        'conversation_id': conv.id,
        'message': msg.to_dict(),
        # Respuesta inmediata del bot (vacío si está en pausa: atiende un humano)
        'bot_messages': ChatService.get_new_for_client(conv.id, msg.id),
    })


@chat_bp.route('/nuevos', methods=['GET'])
def nuevos():
    """Polling: mensajes de operador/bot nuevos para el cliente."""
    anon_id = session.get(ANON_KEY)
    if not anon_id:
        return jsonify({'ok': True, 'messages': []})
    conv = ChatConversation.get_for_anon(anon_id)
    if conv is None:
        return jsonify({'ok': True, 'messages': []})
    after_id = request.args.get('after', 0, type=int)
    return jsonify({
        'ok': True,
        'conversation_id': conv.id,
        'messages': ChatService.get_new_for_client(conv.id, after_id),
        'typing': ChatService.is_typing(conv.id, 'operator'),
    })


@chat_bp.route('/historial', methods=['GET'])
def historial():
    """Cargar el hilo completo al abrir el widget."""
    anon_id = session.get(ANON_KEY)
    if not anon_id:
        return jsonify({'ok': True, 'messages': []})
    conv = ChatConversation.get_for_anon(anon_id)
    if conv is None:
        return jsonify({'ok': True, 'messages': []})
    return jsonify({
        'ok': True,
        'conversation_id': conv.id,
        'messages': ChatService.history(conv.id),
    })


@chat_bp.route('/typing', methods=['POST'])
def typing():
    """El cliente está escribiendo (estado efímero, visible para el operador)."""
    anon_id = session.get(ANON_KEY)
    if not anon_id:
        return jsonify({'ok': True})
    conv = ChatConversation.get_for_anon(anon_id)
    if conv is not None:
        ChatService.set_typing(conv.id, 'client')
    return jsonify({'ok': True})

@chat_bp.route('/comprobante', methods=['POST'])
def comprobante():
    """Recibir el comprobante de pago (imagen o PDF) desde el widget."""
    archivo = request.files.get('archivo')
    if archivo is None or not archivo.filename:
        return jsonify({'ok': False, 'error': 'No se envió ningún archivo'}), 400

    conv, msg, error = ChatService.post_client_proof(
        anon_id=_anon_id(),
        web_user=current_client(),
        file_storage=archivo,
        country=ChatService.country_from_request(request),
    )
    if error:
        return jsonify({'ok': False, 'error': error}), 400

    return jsonify({
        'ok': True,
        'conversation_id': conv.id,
        'message': msg.to_dict(),
        'bot_messages': ChatService.get_new_for_client(conv.id, msg.id),
    })

