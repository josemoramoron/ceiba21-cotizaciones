"""
Dashboard de operadores para gestionar órdenes.
Permite ver, tomar, completar y rechazar órdenes del bot.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.order_service import OrderService
from app.models.order import Order, OrderStatus
from app.models.operator import Operator
from datetime import datetime

operator_bp = Blueprint('operator', __name__, url_prefix='/operator')


@operator_bp.route('/orders')
@login_required
def orders():
    """
    Dashboard principal: Lista de órdenes.
    
    Muestra todas las órdenes pendientes y en proceso.
    """
    # Obtener filtros
    status_filter = request.args.get('status', 'pending')
    channel_filter = request.args.get('channel', 'all')
    
    # Query base
    query = Order.query
    
    # Filtro por estado
    if status_filter == 'pending':
        query = query.filter_by(status=OrderStatus.PENDING)
    elif status_filter == 'in_process':
        query = query.filter_by(status=OrderStatus.IN_PROCESS)
    elif status_filter == 'completed':
        query = query.filter_by(status=OrderStatus.COMPLETED)
    elif status_filter == 'all':
        query = query.filter(Order.status.in_([
            OrderStatus.PENDING,
            OrderStatus.IN_PROCESS,
            OrderStatus.COMPLETED,
            OrderStatus.CANCELLED
        ]))
    
    # Filtro por canal
    if channel_filter != 'all':
        query = query.filter_by(channel=channel_filter)
    
    # Ordenar por fecha (más recientes primero)
    orders = query.order_by(Order.created_at.desc()).limit(100).all()
    
    # Estadísticas del día
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = {
        'pending': Order.query.filter_by(status=OrderStatus.PENDING).count(),
        'completed_today': Order.query.filter(
            Order.status == OrderStatus.COMPLETED,
            Order.completed_at >= today
        ).count(),
        'in_process': Order.query.filter_by(status=OrderStatus.IN_PROCESS).count(),
    }
    
    return render_template(
        'operator/orders.html',
        orders=orders,
        stats=stats,
        status_filter=status_filter,
        channel_filter=channel_filter
    )


@operator_bp.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    """
    Vista detallada de una orden.
    
    Muestra:
    - Datos completos de la orden
    - Comprobante de pago
    - Datos del cliente
    - Acciones disponibles
    """
    order = Order.query.get_or_404(order_id)
    
    return render_template(
        'operator/order_detail.html',
        order=order
    )


@operator_bp.route('/api/orders/<int:order_id>/take', methods=['POST'])
@login_required
def take_order(order_id):
    """
    API: Tomar una orden (asignarla al operador actual).
    """
    try:
        success, message, order = OrderService.assign_order(order_id, current_user.id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'order': {
                    'id': order.id,
                    'reference': order.reference,
                    'status': order.status.value
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al tomar orden: {str(e)}'
        }), 500


@operator_bp.route('/api/orders/<int:order_id>/complete', methods=['POST'])
@login_required
def complete_order(order_id):
    """
    API: Marcar orden como completada.
    
    Body (opcional):
    {
        "operator_proof_url": "URL del comprobante del operador",
        "notes": "Notas adicionales"
    }
    """
    try:
        data = request.get_json() or {}
        operator_proof_url = data.get('operator_proof_url')
        notes = data.get('notes')
        
        success, message, order = OrderService.complete_order(
            order_id=order_id,
            operator_id=current_user.id,
            operator_proof_url=operator_proof_url,
            notes=notes
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'order': {
                    'id': order.id,
                    'reference': order.reference,
                    'status': order.status.value
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al completar orden: {str(e)}'
        }), 500


@operator_bp.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """
    API: Cancelar orden.
    
    Body (requerido):
    {
        "reason": "Motivo de cancelación"
    }
    """
    try:
        data = request.get_json() or {}
        reason = data.get('reason', '').strip()
        
        if not reason:
            return jsonify({
                'success': False,
                'message': 'Debes proporcionar un motivo de cancelación'
            }), 400
        
        success, message, order = OrderService.cancel_order(
            order_id=order_id,
            reason=reason,
            operator_id=current_user.id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'order': {
                    'id': order.id,
                    'reference': order.reference,
                    'status': order.status.value
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al cancelar orden: {str(e)}'
        }), 500
