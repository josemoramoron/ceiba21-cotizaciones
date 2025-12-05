"""
Endpoints API para controlar el bot de Telegram desde el dashboard.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.bot_service import BotService
from app.services.auth_service import AuthService

bot_control_bp = Blueprint('bot_control', __name__, url_prefix='/api/bot')


@bot_control_bp.route('/start', methods=['POST'])
@login_required
def start_bot():
    """
    Iniciar el bot de Telegram.
    
    Requiere permisos de ADMIN.
    """
    # Verificar permisos
    if not AuthService.check_permission(current_user.id, 'manage_bot'):
        return jsonify({
            'success': False,
            'message': 'No tienes permisos para controlar el bot'
        }), 403
    
    # Iniciar bot
    success, message = BotService.start_bot()
    
    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 400


@bot_control_bp.route('/stop', methods=['POST'])
@login_required
def stop_bot():
    """
    Detener el bot de Telegram.
    
    Requiere permisos de ADMIN.
    """
    # Verificar permisos
    if not AuthService.check_permission(current_user.id, 'manage_bot'):
        return jsonify({
            'success': False,
            'message': 'No tienes permisos para controlar el bot'
        }), 403
    
    # Detener bot
    success, message = BotService.stop_bot()
    
    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 400


@bot_control_bp.route('/restart', methods=['POST'])
@login_required
def restart_bot():
    """
    Reiniciar el bot de Telegram.
    
    Requiere permisos de ADMIN.
    """
    # Verificar permisos
    if not AuthService.check_permission(current_user.id, 'manage_bot'):
        return jsonify({
            'success': False,
            'message': 'No tienes permisos para controlar el bot'
        }), 403
    
    # Reiniciar bot
    success, message = BotService.restart_bot()
    
    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 400


@bot_control_bp.route('/status', methods=['GET'])
@login_required
def bot_status():
    """
    Obtener estado actual del bot.
    
    Accesible para todos los operadores autenticados.
    """
    status = BotService.get_status()
    return jsonify(status), 200


@bot_control_bp.route('/stats', methods=['GET'])
@login_required
def bot_stats():
    """
    Obtener estadísticas del bot.
    
    Accesible para todos los operadores autenticados.
    """
    stats = BotService.get_stats()
    return jsonify(stats), 200
