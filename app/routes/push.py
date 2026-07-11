"""
Web Push: clave pública VAPID, suscripción y envío de prueba.

Soporta clientes logueados (suscripción atada al WebUser) y visitantes anónimos
(atada al anon_id del chat en la sesión). Las rutas de API responden 401/400
JSON, nunca redirigen (para no enmascarar el fallo al llamarlas por fetch).
"""
import uuid

from flask import Blueprint, jsonify, request, current_app, session

from app.client_auth import current_client
from app.models.push_subscription import PushSubscription
from app.services.push_service import PushService

push_bp = Blueprint('push', __name__, url_prefix='/push')

ANON_KEY = 'chat_anon_id'


def _ensure_anon_id() -> str:
    """Id anónimo estable en la sesión (compartido con el chat)."""
    aid = session.get(ANON_KEY)
    if not aid:
        aid = uuid.uuid4().hex
        session[ANON_KEY] = aid
        session.permanent = True
    return aid


@push_bp.route('/vapid-public-key')
def vapid_public_key():
    """Clave pública VAPID para que el navegador se suscriba."""
    return jsonify({'publicKey': current_app.config.get('VAPID_PUBLIC_KEY')})


@push_bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Guardar la suscripción Web Push (logueado o anónimo)."""
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    keys = data.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return jsonify({'ok': False, 'error': 'suscripcion_invalida'}), 400

    client = current_client()
    web_user_id = client.id if client else None
    anon_id = None if client else _ensure_anon_id()

    sub = PushSubscription.upsert(
        endpoint=endpoint, p256dh=p256dh, auth=auth,
        web_user_id=web_user_id, anon_id=anon_id,
        user_agent=request.headers.get('User-Agent', '')[:255],
    )
    if sub is None or sub.id is None:
        return jsonify({'ok': False, 'error': 'no_guardado'}), 500

    return jsonify({'ok': True})


@push_bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Desactivar una suscripción por su endpoint."""
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.deactivate_by_endpoint(endpoint)
    return jsonify({'ok': True})


@push_bp.route('/test', methods=['POST'])
def test():
    """Enviar una notificación de prueba al propio destinatario."""
    client = current_client()
    if client:
        subs = PushSubscription.get_active_for_user(client.id)
        sent = PushService.send_to_user(
            client.id, 'Ceiba21', '🔔 Notificaciones activadas correctamente.',
            '/cuenta')
    else:
        anon_id = session.get(ANON_KEY)
        subs = PushSubscription.get_active_for_anon(anon_id) if anon_id else []
        sent = PushService.send_to_anon(
            anon_id, 'Ceiba21', '🔔 Notificaciones activadas correctamente.',
            '/') if anon_id else 0

    return jsonify({'ok': sent > 0, 'subs': len(subs), 'sent': sent})
