"""
Rutas del módulo SMS (Blueprint /dashboard/sms).

Solo orquestación: las rutas llaman a SmsService y renderizan templates.
Toda la lógica de negocio vive en app/services/sms_service.py.

Acceso restringido a ADMIN (igual que el resto de /dashboard) vía before_request.
"""
from flask import (
    Blueprint, render_template, request, jsonify, flash, redirect, url_for
)

from app.routes.auth import login_required
from app.decorators import require_roles
from app.models.operator import OperatorRole
from app.models.sim_slot import SimSlot
from app.services.sms_service import SmsService

sms_bp = Blueprint('sms', __name__, url_prefix='/dashboard/sms')

# Total de slots del board físico (board de 20 SIMs).
TOTAL_SIM_SLOTS = 20


@sms_bp.before_request
def _require_admin():
    """Restringe el módulo SMS a administradores.

    Excepción: los webhooks del gateway Android no llevan sesión, por lo que
    se excluyen del guard. Su seguridad se basa en que solo son alcanzables
    desde la red local / túnel, no en la sesión del panel.
    """
    if request.endpoint in ('sms.webhook_incoming', 'sms.webhook_status'):
        return None
    return require_roles(OperatorRole.ADMIN)


@sms_bp.route('/')
@login_required
def index():
    """Dashboard SMS: estado del gateway, contadores y actividad reciente."""
    SmsService.ensure_slots(TOTAL_SIM_SLOTS)
    health, _ = SmsService.get_gateway_health()
    from app.models.sms_message import SmsMessage
    slots = SimSlot.get_ordered()
    return render_template(
        'sms/index.html',
        health=health,
        unread=SmsMessage.count_unread(),
        recent_inbound=SmsMessage.get_inbound().limit(8).all(),
        recent_outbound=SmsMessage.get_outbound().limit(5).all(),
        slots=slots,
        slots_map={s.slot_number: s for s in slots},
        active_slot=SmsService.get_active_slot(),
    )


@sms_bp.route('/enviar', methods=['GET', 'POST'])
@login_required
def send():
    """Formulario de envío de SMS y procesamiento del POST."""
    slots = SimSlot.get_active_ordered()
    if request.method == 'POST':
        phones = [
            p.strip() for p in request.form.get('phones', '').split(',')
            if p.strip()
        ]
        text = request.form.get('text', '').strip()
        sim_slot = request.form.get('sim_slot', type=int)

        if not phones or not text:
            flash('Número y mensaje son obligatorios.', 'error')
            return render_template('sms/send.html', slots=slots)

        _, error = SmsService.send_sms(phones, text, sim_slot)
        if error:
            flash(f'Error al enviar: {error}', 'error')
        else:
            flash(f'✅ Enviado a {len(phones)} número(s)', 'success')
            return redirect(url_for('sms.history'))

    return render_template('sms/send.html', slots=slots)


@sms_bp.route('/inbox')
@login_required
def inbox():
    """Bandeja de entrada paginada; marca los entrantes como leídos."""
    page = request.args.get('page', 1, type=int)
    from app.models.sms_message import SmsMessage
    messages = SmsMessage.get_inbound().paginate(
        page=page, per_page=25, error_out=False
    )
    SmsService.mark_inbound_read()
    slots = {s.slot_number: s for s in SimSlot.get_ordered()}
    return render_template('sms/inbox.html', messages=messages, slots=slots)


@sms_bp.route('/historial')
@login_required
def history():
    """Historial de mensajes enviados, paginado."""
    page = request.args.get('page', 1, type=int)
    from app.models.sms_message import SmsMessage
    messages = SmsMessage.get_outbound().paginate(
        page=page, per_page=25, error_out=False
    )
    slots = {s.slot_number: s for s in SimSlot.get_ordered()}
    return render_template('sms/history.html', messages=messages, slots=slots)


@sms_bp.route('/sims')
@login_required
def sims():
    """Gestión de slots SIM del board."""
    SmsService.ensure_slots(TOTAL_SIM_SLOTS)
    return render_template(
        'sms/sims.html',
        slots=SimSlot.get_ordered(),
        active_slot=SmsService.get_active_slot(),
        total=TOTAL_SIM_SLOTS,
    )


@sms_bp.route('/sims/<int:slot>/editar', methods=['POST'])
@login_required
def sim_edit(slot):
    """Actualiza la metadata de un slot SIM."""
    sim = SimSlot.get_by_slot(slot)
    if sim is None:
        flash('Slot no encontrado.', 'error')
        return redirect(url_for('sms.sims'))

    sim.label = request.form.get('label') or sim.label
    sim.phone_number = request.form.get('phone_number') or None
    sim.operator = request.form.get('operator') or None
    sim.country = request.form.get('country') or None
    sim.color = request.form.get('color') or sim.color
    sim.notes = request.form.get('notes') or None
    sim.active = 'active' in request.form
    sim.save()

    flash(f'✅ SIM del slot {slot} actualizada', 'success')
    return redirect(url_for('sms.sims'))


# ── API JSON (consumida por la propia interfaz y por otros módulos) ──────────

@sms_bp.route('/api/sims/<int:slot>/activar', methods=['POST'])
@login_required
def api_activate_slot(slot):
    """Fija el slot SIM activo. Devuelve JSON para el front."""
    try:
        sim = SmsService.set_active_slot(slot)
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 404
    return jsonify({'ok': True, 'slot': slot, 'label': sim.display_name})


@sms_bp.route('/api/unread')
@login_required
def api_unread():
    """Contador de no leídos (polling ligero desde el navegador)."""
    from app.models.sms_message import SmsMessage
    return jsonify({'unread': SmsMessage.count_unread()})


@sms_bp.route('/api/health')
@login_required
def api_health():
    """Estado del gateway Android (para el indicador de la interfaz)."""
    health, error = SmsService.get_gateway_health()
    if error:
        return jsonify({'online': False, 'error': error}), 200
    return jsonify({'online': True, 'model': health.get('model', '')}), 200


# ── Webhooks (llamados por la app Android del gateway) ───────────────────────
# NOTA: estos NO llevan login — el gateway no tiene sesión. Van fuera del
# guard de admin porque el before_request redirige; ver registro en __init__.

@sms_bp.route('/webhook/incoming', methods=['POST'])
def webhook_incoming():
    """Recibe SMS entrantes desde el gateway Android."""
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({'error': 'sin datos'}), 400
    SmsService.ingest_incoming(payload)
    return jsonify({'status': 'ok'}), 200


@sms_bp.route('/webhook/status', methods=['POST'])
def webhook_status():
    """Recibe actualizaciones de estado de entrega desde el gateway."""
    payload = request.get_json(silent=True) or {}
    SmsService.update_delivery_status(
        payload.get('id'), payload.get('state')
    )
    return jsonify({'status': 'ok'}), 200
