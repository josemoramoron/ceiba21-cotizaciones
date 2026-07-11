"""
Panel de chat para operadores (dashboard).

Permite ver las conversaciones apiladas, seguir el hilo en vivo, intervenir
manualmente y pausar/reanudar el bot (por conversación y de forma global).
Acceso restringido a administradores.
"""
from flask import Blueprint, render_template, jsonify, request
from flask_login import current_user

from app.decorators import require_roles
from app.models.operator import OperatorRole
from app.services.chat_service import ChatService
from app.services.system_config_service import SystemConfigService

chat_admin_bp = Blueprint('chat_admin', __name__, url_prefix='/dashboard/chat')


@chat_admin_bp.before_request
def _require_admin():
    """El panel de chat es exclusivo de administradores."""
    return require_roles(OperatorRole.ADMIN)


@chat_admin_bp.route('/')
def index():
    """Vista principal: lista de conversaciones + hilo."""
    return render_template(
        'chat/index.html',
        bot_paused_global=SystemConfigService.get_webchat_bot_paused(),
    )


@chat_admin_bp.route('/api/conversaciones')
def api_conversaciones():
    """Listado de conversaciones (polling)."""
    return jsonify({
        'ok': True,
        'bot_paused_global': SystemConfigService.get_webchat_bot_paused(),
        'conversations': ChatService.list_conversations(),
    })


@chat_admin_bp.route('/api/<int:conversation_id>/mensajes')
def api_mensajes(conversation_id: int):
    """Mensajes de una conversación (hilo completo o solo los nuevos)."""
    after_id = request.args.get('after', 0, type=int)
    if after_id:
        from app.models.chat import ChatMessage
        msgs = [m.to_dict() for m in ChatMessage.get_since(conversation_id, after_id)]
    else:
        msgs = ChatService.history(conversation_id)
        ChatService.mark_read_by_operator(conversation_id)
    return jsonify({'ok': True, 'messages': msgs})


@chat_admin_bp.route('/api/<int:conversation_id>/responder', methods=['POST'])
def api_responder(conversation_id: int):
    """Enviar una respuesta manual del operador."""
    data = request.get_json(silent=True) or {}
    msg = ChatService.operator_reply(
        conversation_id=conversation_id,
        operator_id=current_user.id,
        text=data.get('texto', ''),
    )
    if msg is None:
        return jsonify({'ok': False, 'error': 'mensaje_invalido'}), 400
    return jsonify({'ok': True, 'message': msg.to_dict()})


@chat_admin_bp.route('/api/<int:conversation_id>/pausa', methods=['POST'])
def api_pausa(conversation_id: int):
    """Pausar/reanudar el bot en una conversación concreta."""
    data = request.get_json(silent=True) or {}
    paused = bool(data.get('paused', True))
    if not ChatService.set_bot_paused(conversation_id, paused):
        return jsonify({'ok': False, 'error': 'no_encontrada'}), 404
    return jsonify({'ok': True, 'paused': paused})


@chat_admin_bp.route('/api/pausa-global', methods=['POST'])
def api_pausa_global():
    """Pausar/reanudar el bot para TODAS las conversaciones."""
    data = request.get_json(silent=True) or {}
    paused = bool(data.get('paused', True))
    SystemConfigService.set_webchat_bot_paused(paused)
    return jsonify({'ok': True, 'paused': paused})
