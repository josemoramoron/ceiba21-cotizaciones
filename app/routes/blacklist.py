"""
Rutas del Dashboard de Blacklist.

RESPONSABILIDADES:
- Dashboard principal con lista de reportes
- Crear nuevos reportes
- Búsqueda avanzada
- Ver detalles de reportes
- Actualizar estados
- Gestión de apelaciones
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.blacklist_service import BlacklistService
from app.services.image_service import ImageService
from app.models.blacklist import BlacklistEntry, BlacklistCategory, BlacklistType, BlacklistStatus
from datetime import datetime
from sqlalchemy import or_

blacklist_bp = Blueprint('blacklist', __name__, url_prefix='/blacklist')


# ==========================================
# DASHBOARD PRINCIPAL
# ==========================================

@blacklist_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard principal de blacklist.
    
    Muestra:
    - Estadísticas generales
    - Lista de reportes activos
    - Apelaciones pendientes
    """
    reports = BlacklistService.get_all_active(limit=50)
    stats = BlacklistService.get_statistics()
    pending_appeals = BlacklistService.get_pending_appeals()
    
    return render_template(
        'blacklist/dashboard.html',
        reports=reports,
        stats=stats,
        pending_appeals=pending_appeals,
        categories=BlacklistCategory,
        statuses=BlacklistStatus
    )


# ==========================================
# CREAR REPORTE
# ==========================================

@blacklist_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_report():
    """
    Crear nuevo reporte de blacklist.
    
    GET: Mostrar formulario
    POST: Crear reporte
    """
    if request.method == 'POST':
        data = request.form
        
        # Manejar upload de foto
        photo_url = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename:
                success, msg, url = ImageService.optimize_and_save(file)
                if success:
                    photo_url = url
                else:
                    flash(f'Error al subir foto: {msg}', 'warning')
        
        # Parsear fecha de expiración si es temporal
        expires_at = None
        if data.get('block_type') == 'TEMPORARY' and data.get('expires_at'):
            try:
                expires_at = datetime.strptime(data.get('expires_at'), '%Y-%m-%d')
            except:
                flash('Fecha de expiración inválida', 'error')
                return redirect(url_for('blacklist.create_report'))
        
        success, message, entry = BlacklistService.create_report(
            operator_id=current_user.id,
            reason=data.get('reason'),
            category=data.get('category', 'OTHER'),
            block_type=data.get('block_type', 'PERMANENT'),
            severity=int(data.get('severity', 3)),
            user_id=int(data.get('user_id')) if data.get('user_id') else None,
            telegram_id=int(data.get('telegram_id')) if data.get('telegram_id') else None,
            phone=data.get('phone') or None,
            email=data.get('email') or None,
            dni=data.get('dni') or None,
            full_name=data.get('full_name') or None,
            detailed_notes=data.get('detailed_notes'),
            order_references=data.get('order_references'),
            expires_at=expires_at,
            run_fraud_check=data.get('run_fraud_check') == 'on',
            country=data.get('country') or None,
            state=data.get('state') or None,
            transaction_type=data.get('transaction_type') or None,
            bank_info=data.get('bank_info') or None,
            additional_info=data.get('additional_info') or None,
            photo_url=photo_url,
            scam_links=data.get('scam_links') or None,
            reporter_name=data.get('reporter_name', 'ceiba21')
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('blacklist.view_report', blacklist_id=entry.id))
        else:
            flash(message, 'error')
    
    return render_template(
        'blacklist/create_report.html',
        categories=BlacklistCategory,
        types=BlacklistType
    )


# ==========================================
# BÚSQUEDA
# ==========================================

@blacklist_bp.route('/search')
@login_required
def search():
    """
    Búsqueda avanzada de reportes.
    
    Parámetros:
    - q: Texto general
    - telegram_id, phone, email, dni: Identificadores específicos
    - report_id: ID del reporte
    - category, status: Filtros
    """
    results = BlacklistService.search(
        query=request.args.get('q'),
        telegram_id=int(request.args.get('telegram_id')) if request.args.get('telegram_id') else None,
        phone=request.args.get('phone'),
        email=request.args.get('email'),
        dni=request.args.get('dni'),
        report_id=int(request.args.get('report_id')) if request.args.get('report_id') else None,
        category=request.args.get('category'),
        status=request.args.get('status')
    )
    
    return render_template(
        'blacklist/search_results.html',
        results=results,
        search_params=request.args
    )


# ==========================================
# VER DETALLES
# ==========================================

@blacklist_bp.route('/<int:blacklist_id>')
@login_required
def view_report(blacklist_id):
    """
    Ver detalles de un reporte.
    
    Muestra:
    - Información completa del reporte
    - Historial de cambios
    - Apelaciones relacionadas
    """
    entry = BlacklistEntry.find_by_id(blacklist_id)
    if not entry:
        flash('Reporte no encontrado', 'error')
        return redirect(url_for('blacklist.dashboard'))
    
    return render_template(
        'blacklist/report_detail.html',
        entry=entry,
        statuses=BlacklistStatus,
        types=BlacklistType
    )


# ==========================================
# ACTUALIZAR ESTADO
# ==========================================

@blacklist_bp.route('/<int:blacklist_id>/update-status', methods=['POST'])
@login_required
def update_status(blacklist_id):
    """
    Actualizar el estado de un reporte.
    
    Estados posibles:
    - ACTIVE
    - REVOKED (desbloquear)
    - EXPIRED
    """
    data = request.form
    
    success, message = BlacklistService.update_status(
        blacklist_id=blacklist_id,
        new_status=data.get('status'),
        operator_id=current_user.id,
        reason=data.get('reason')
    )
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('blacklist.view_report', blacklist_id=blacklist_id))


# ==========================================
# APELACIONES
# ==========================================

@blacklist_bp.route('/appeals')
@login_required
def appeals_list():
    """
    Lista de apelaciones pendientes.
    """
    appeals = BlacklistService.get_pending_appeals()
    
    return render_template(
        'blacklist/appeals_list.html',
        appeals=appeals
    )


@blacklist_bp.route('/appeals/<int:appeal_id>')
@login_required
def view_appeal(appeal_id):
    """
    Ver detalles de una apelación.
    """
    from app.models.blacklist import BlacklistAppeal
    appeal = BlacklistAppeal.find_by_id(appeal_id)
    
    if not appeal:
        flash('Apelación no encontrada', 'error')
        return redirect(url_for('blacklist.appeals_list'))
    
    return render_template(
        'blacklist/appeal_detail.html',
        appeal=appeal
    )


@blacklist_bp.route('/appeals/<int:appeal_id>/review', methods=['POST'])
@login_required
def review_appeal(appeal_id):
    """
    Revisar y decidir sobre una apelación.
    
    Decisiones:
    - approved: Aprobar y desbloquear
    - rejected: Rechazar y mantener bloqueo
    """
    data = request.form
    
    success, message = BlacklistService.review_appeal(
        appeal_id=appeal_id,
        operator_id=current_user.id,
        decision=data.get('decision'),
        decision_reason=data.get('decision_reason'),
        review_notes=data.get('review_notes')
    )
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('blacklist.appeals_list'))


# ==========================================
# API ENDPOINTS (JSON)
# ==========================================

@blacklist_bp.route('/api/check', methods=['POST'])
@login_required
def api_check_blacklist():
    """
    API: Verificar si un identificador está en blacklist.
    
    POST /blacklist/api/check
    Body: {
        "telegram_id": 123456789,
        "phone": "+58414...",
        "email": "email@example.com"
    }
    
    Returns: {
        "is_blacklisted": bool,
        "entry": {...} | null
    }
    """
    data = request.get_json()
    
    is_blacklisted, entry = BlacklistService.check_identifiers_blacklisted(
        telegram_id=data.get('telegram_id'),
        phone=data.get('phone'),
        email=data.get('email'),
        dni=data.get('dni')
    )
    
    return jsonify({
        'is_blacklisted': is_blacklisted,
        'entry': entry.to_dict() if entry else None
    })


@blacklist_bp.route('/api/stats')
@login_required
def api_stats():
    """
    API: Obtener estadísticas de blacklist.
    
    GET /blacklist/api/stats
    
    Returns: {
        "total": int,
        "active": int,
        ...
    }
    """
    stats = BlacklistService.get_statistics()
    return jsonify(stats)


# ==========================================
# EDICIÓN Y PERFIL
# ==========================================

@blacklist_bp.route('/<int:blacklist_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_report(blacklist_id):
    """Editar un reporte existente"""
    entry = BlacklistEntry.find_by_id(blacklist_id)
    if not entry:
        flash('Reporte no encontrado', 'error')
        return redirect(url_for('blacklist.dashboard'))
    
    if request.method == 'POST':
        data = request.form
        
        # Manejar nueva foto si se sube
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename:
                # Eliminar foto anterior si existe
                if entry.photo_url:
                    ImageService.delete_image(entry.photo_url)
                
                success, msg, url = ImageService.optimize_and_save(file)
                if success:
                    entry.photo_url = url
        
        # Actualizar campos
        entry.reason = data.get('reason', entry.reason)
        entry.detailed_notes = data.get('detailed_notes', entry.detailed_notes)
        entry.severity = int(data.get('severity', entry.severity))
        entry.full_name = data.get('full_name', entry.full_name)
        entry.country = data.get('country', entry.country)
        entry.state = data.get('state', entry.state)
        entry.transaction_type = data.get('transaction_type', entry.transaction_type)
        entry.bank_info = data.get('bank_info', entry.bank_info)
        entry.additional_info = data.get('additional_info', entry.additional_info)
        entry.scam_links = data.get('scam_links', entry.scam_links)
        entry.reporter_name = data.get('reporter_name', entry.reporter_name)
        
        # Registrar auditoría de edición
        entry.last_edited_at = datetime.utcnow()
        entry.last_edited_by_operator_id = current_user.id
        
        if entry.save():
            flash('Reporte actualizado exitosamente', 'success')
            return redirect(url_for('blacklist.view_report', blacklist_id=blacklist_id))
        else:
            flash('Error al actualizar reporte', 'error')
    
    return render_template(
        'blacklist/edit_report.html',
        entry=entry,
        categories=BlacklistCategory,
        types=BlacklistType
    )


@blacklist_bp.route('/profile/<identifier_type>/<identifier_value>')
@login_required
def user_profile(identifier_type, identifier_value):
    """
    Ver perfil completo con todos los reportes de un usuario.
    
    identifier_type: telegram_id, phone, email, dni
    identifier_value: el valor del identificador
    """
    # Buscar todos los reportes de este usuario
    filters = []
    
    if identifier_type == 'telegram_id':
        filters.append(BlacklistEntry.telegram_id == int(identifier_value))
    elif identifier_type == 'phone':
        filters.append(BlacklistEntry.phone == identifier_value)
    elif identifier_type == 'email':
        filters.append(BlacklistEntry.email == identifier_value)
    elif identifier_type == 'dni':
        filters.append(BlacklistEntry.dni == identifier_value)
    else:
        flash('Tipo de identificador inválido', 'error')
        return redirect(url_for('blacklist.dashboard'))
    
    # Obtener TODOS los reportes (activos, revocados, etc.)
    all_reports = BlacklistEntry.query.filter(
        or_(*filters)
    ).order_by(BlacklistEntry.blocked_at.desc()).all()
    
    if not all_reports:
        flash('No se encontraron reportes para este usuario', 'warning')
        return redirect(url_for('blacklist.dashboard'))
    
    # Estadísticas del usuario
    active_count = sum(1 for r in all_reports if r.status == BlacklistStatus.ACTIVE)
    revoked_count = sum(1 for r in all_reports if r.status == BlacklistStatus.REVOKED)
    
    return render_template(
        'blacklist/user_profile.html',
        reports=all_reports,
        identifier_type=identifier_type,
        identifier_value=identifier_value,
        active_count=active_count,
        revoked_count=revoked_count,
        statuses=BlacklistStatus
    )
