"""
Rutas principales de la aplicación
"""
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Página principal"""
    return '''
    <h1>🚀 Ceiba21 - Sistema de Cotizaciones</h1>
    <p>✅ Estructura modular funcionando</p>
    <ul>
        <li><a href="/dashboard">Dashboard</a> (próximamente)</li>
        <li><a href="/api/quotes">API Cotizaciones</a> (próximamente)</li>
    </ul>
    '''

@main_bp.route('/health')
def health():
    """Endpoint de salud"""
    return {'status': 'ok', 'message': 'Sistema funcionando'}
