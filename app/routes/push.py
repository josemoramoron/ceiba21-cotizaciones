"""
Web Push: clave pública VAPID, suscripción y envío de prueba.

Las suscripciones se asocian al cliente (WebUser) autenticado por sesión.
Las rutas de API responden 401 JSON (no redirigen) cuando no hay cliente, para
no enmascarar el fallo de autenticación al ser llamadas por fetch().
"""
from flask import Blueprint, jsonify, request, current_app

from app.client_auth import current_client
from app.models.push_subscription import PushSubscription
from app.services.push_service import PushService

push_bp = Blueprint('push', __name__, url_prefix='/push')


@push_bp.route('/vapid-public-key')
def vapid_public_key():
    """Clave pública VAPID para que el navegador se suscriba."""
    return jsonify({'publicKey': current_app.config.get('VAPID_PUBLIC_KEY')})


@push_bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Guardar la suscripción Web Push del cliente actual."""
    client = current_client()
    if client is None:
        return jsonify({'ok': False, 'error': 'no_autenticado'}), 401

    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    keys = data.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return jsonify({'ok': False, 'error': 'suscripcion_invalida'}), 400

    sub = PushSubscription.upsert(
        web_user_id=client.id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=request.headers.get('User-Agent', '')[:255],
    )
    if sub is None or sub.id is None:
        return jsonify({'ok': False, 'error': 'no_guardado'}), 500

    return jsonify({'ok': True, 'id': sub.id})


@push_bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Desactivar una suscripción por su endpoint."""
    if current_client() is None:
        return jsonify({'ok': False, 'error': 'no_autenticado'}), 401

    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.deactivate_by_endpoint(endpoint)
    return jsonify({'ok': True})


@push_bp.route('/test', methods=['POST'])
def test():
    """Enviar una notificación de prueba al propio cliente."""
    client = current_client()
    if client is None:
        return jsonify({'ok': False, 'error': 'no_autenticado'}), 401

    subs = PushSubscription.get_active_for_user(client.id)
    sent = PushService.send_to_user(
        web_user_id=client.id,
        title='Ceiba21',
        body='🔔 Notificaciones activadas correctamente.',
        url='/cuenta',
    )
    return jsonify({'ok': sent > 0, 'subs': len(subs), 'sent': sent})
