# 🚫 SISTEMA DE BLACKLIST - GUÍA DE IMPLEMENTACIÓN

## ✅ LO QUE YA ESTÁ IMPLEMENTADO

### 1. Modelos (100% Completo)
- ✅ `app/models/blacklist.py`
  - `BlacklistEntry`: Modelo principal de bloqueos
  - `BlacklistAppeal`: Modelo de apelaciones
  - Todos los Enums necesarios

### 2. Servicios (100% Completo)
- ✅ `app/services/blacklist_service.py`
  - CRUD completo de reportes
  - Búsqueda avanzada
  - Gestión de apelaciones
  - Estadísticas
  
- ✅ `app/services/fraud_check_service.py`
  - Verificación de teléfonos (Numverify/Twilio)
  - Verificación de emails
  - Check de Telegram IDs
  - Cálculo de risk score

### 3. Scripts (100% Completo)
- ✅ `scripts/create_blacklist_tables.py`: Para crear las tablas

---

## 📋 LO QUE FALTA POR IMPLEMENTAR

### 1. Rutas del Dashboard (PRÓXIMO PASO)

Crear `app/routes/blacklist.py` con:

```python
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.blacklist_service import BlacklistService
from app.models.blacklist import BlacklistEntry, BlacklistCategory, BlacklistType, BlacklistStatus

blacklist_bp = Blueprint('blacklist', __name__, url_prefix='/blacklist')

# RUTAS PRINCIPALES
@blacklist_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal de blacklist"""
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

@blacklist_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_report():
    """Crear nuevo reporte"""
    if request.method == 'POST':
        data = request.form
        
        success, message, entry = BlacklistService.create_report(
            operator_id=current_user.id,
            reason=data.get('reason'),
            category=data.get('category', 'OTHER'),
            block_type=data.get('block_type', 'PERMANENT'),
            severity=int(data.get('severity', 3)),
            user_id=data.get('user_id') or None,
            telegram_id=data.get('telegram_id') or None,
            phone=data.get('phone') or None,
            email=data.get('email') or None,
            dni=data.get('dni') or None,
            full_name=data.get('full_name') or None,
            detailed_notes=data.get('detailed_notes'),
            order_references=data.get('order_references'),
            run_fraud_check=data.get('run_fraud_check') == 'on'
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('blacklist.dashboard'))
        else:
            flash(message, 'error')
    
    return render_template(
        'blacklist/create_report.html',
        categories=BlacklistCategory,
        types=BlacklistType
    )

@blacklist_bp.route('/search')
@login_required
def search():
    """Búsqueda avanzada"""
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

@blacklist_bp.route('/<int:blacklist_id>')
@login_required
def view_report(blacklist_id):
    """Ver detalle de reporte"""
    entry = BlacklistEntry.find_by_id(blacklist_id)
    if not entry:
        flash('Reporte no encontrado', 'error')
        return redirect(url_for('blacklist.dashboard'))
    
    return render_template('blacklist/report_detail.html', entry=entry)

@blacklist_bp.route('/<int:blacklist_id>/update-status', methods=['POST'])
@login_required
def update_status(blacklist_id):
    """Actualizar estatus"""
    success, message = BlacklistService.update_status(
        blacklist_id=blacklist_id,
        new_status=request.form.get('status'),
        operator_id=current_user.id,
        reason=request.form.get('reason')
    )
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('blacklist.view_report', blacklist_id=blacklist_id))

# APELACIONES
@blacklist_bp.route('/appeals')
@login_required
def appeals_list():
    """Lista de apelaciones"""
    appeals = BlacklistService.get_pending_appeals()
    return render_template('blacklist/appeals_list.html', appeals=appeals)

@blacklist_bp.route('/appeals/<int:appeal_id>/review', methods=['POST'])
@login_required
def review_appeal(appeal_id):
    """Revisar apelación"""
    success, message = BlacklistService.review_appeal(
        appeal_id=appeal_id,
        operator_id=current_user.id,
        decision=request.form.get('decision'),
        decision_reason=request.form.get('decision_reason'),
        review_notes=request.form.get('review_notes')
    )
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('blacklist.appeals_list'))
```

### 2. Templates HTML

Crear estos templates en `app/templates/blacklist/`:

#### `dashboard.html`
```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-6">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">🚫 Blacklist - Usuarios Bloqueados</h1>
        <a href="{{ url_for('blacklist.create_report') }}" 
           class="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700">
            + Nuevo Reporte
        </a>
    </div>

    <!-- Estadísticas -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white p-4 rounded-lg shadow">
            <div class="text-gray-600">Total Reportes</div>
            <div class="text-3xl font-bold">{{ stats.total }}</div>
        </div>
        <div class="bg-red-50 p-4 rounded-lg shadow">
            <div class="text-red-600">Activos</div>
            <div class="text-3xl font-bold text-red-600">{{ stats.active }}</div>
        </div>
        <div class="bg-yellow-50 p-4 rounded-lg shadow">
            <div class="text-yellow-600">Apelaciones Pendientes</div>
            <div class="text-3xl font-bold text-yellow-600">{{ stats.pending_appeals }}</div>
        </div>
        <div class="bg-green-50 p-4 rounded-lg shadow">
            <div class="text-green-600">Revocados</div>
            <div class="text-3xl font-bold text-green-600">{{ stats.revoked }}</div>
        </div>
    </div>

    <!-- Búsqueda -->
    <div class="bg-white p-4 rounded-lg shadow mb-6">
        <form action="{{ url_for('blacklist.search') }}" method="GET" class="grid grid-cols-1 md:grid-cols-5 gap-4">
            <input type="text" name="q" placeholder="Buscar..." class="border rounded px-3 py-2">
            <input type="text" name="telegram_id" placeholder="Telegram ID" class="border rounded px-3 py-2">
            <input type="text" name="phone" placeholder="Teléfono" class="border rounded px-3 py-2">
            <input type="text" name="email" placeholder="Email" class="border rounded px-3 py-2">
            <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                🔍 Buscar
            </button>
        </form>
    </div>

    <!-- Tabla de Reportes -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuario</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Razón</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoría</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severidad</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                {% for entry in reports %}
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm">#{{ entry.id }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {{ entry.get_display_name() }}
                    </td>
                    <td class="px-6 py-4 text-sm">{{ entry.reason[:50] }}...</td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                                     bg-red-100 text-red-800">
                            {{ entry.category.value }}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        {{ '🔴' * entry.severity }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        {{ entry.blocked_at.strftime('%d/%m/%Y') }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        <a href="{{ url_for('blacklist.view_report', blacklist_id=entry.id) }}" 
                           class="text-blue-600 hover:text-blue-900">Ver</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

#### `create_report.html`
```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-6 max-w-4xl">
    <h1 class="text-3xl font-bold mb-6">📝 Crear Nuevo Reporte de Blacklist</h1>

    <form method="POST" class="bg-white rounded-lg shadow p-6">
        <!-- Identificadores -->
        <div class="mb-6">
            <h2 class="text-xl font-semibold mb-4">Identificadores del Usuario</h2>
            <p class="text-sm text-gray-600 mb-4">
                Proporciona al menos un identificador. El sistema completará automáticamente los demás si el usuario existe.
            </p>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium mb-1">ID de Usuario</label>
                    <input type="number" name="user_id" class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Telegram ID</label>
                    <input type="number" name="telegram_id" class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Teléfono</label>
                    <input type="text" name="phone" class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Email</label>
                    <input type="email" name="email" class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">DNI/Cédula</label>
                    <input type="text" name="dni" class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Nombre Completo</label>
                    <input type="text" name="full_name" class="w-full border rounded px-3 py-2">
                </div>
            </div>
        </div>

        <!-- Detalles del Bloqueo -->
        <div class="mb-6">
            <h2 class="text-xl font-semibold mb-4">Detalles del Bloqueo</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div>
                    <label class="block text-sm font-medium mb-1">Categoría *</label>
                    <select name="category" required class="w-full border rounded px-3 py-2">
                        {% for cat in categories %}
                        <option value="{{ cat.value }}">{{ cat.value.replace('_', ' ').title() }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Tipo de Bloqueo *</label>
                    <select name="block_type" required class="w-full border rounded px-3 py-2">
                        <option value="PERMANENT">Permanente</option>
                        <option value="TEMPORARY">Temporal</option>
                        <option value="SUSPENDED">Suspendido</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Severidad (1-5) *</label>
                    <input type="number" name="severity" min="1" max="5" value="3" required 
                           class="w-full border rounded px-3 py-2">
                </div>
            </div>

            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Razón del Bloqueo *</label>
                <input type="text" name="reason" required maxlength="500" 
                       class="w-full border rounded px-3 py-2"
                       placeholder="Ej: Envió comprobante falso en orden ORD-20250101-001">
            </div>

            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Notas Detalladas</label>
                <textarea name="detailed_notes" rows="4" 
                          class="w-full border rounded px-3 py-2"
                          placeholder="Información adicional, contexto, etc."></textarea>
            </div>

            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Referencias de Órdenes</label>
                <input type="text" name="order_references" 
                       class="w-full border rounded px-3 py-2"
                       placeholder="ORD-20250101-001, ORD-20250101-002">
            </div>
        </div>

        <!-- Verificación de Fraude -->
        <div class="mb-6">
            <label class="flex items-center">
                <input type="checkbox" name="run_fraud_check" class="mr-2">
                <span class="text-sm font-medium">Ejecutar verificación de fraude (APIs externas)</span>
            </label>
        </div>

        <!-- Botones -->
        <div class="flex justify-end space-x-4">
            <a href="{{ url_for('blacklist.dashboard') }}" 
               class="px-6 py-2 border rounded hover:bg-gray-50">
                Cancelar
            </a>
            <button type="submit" 
                    class="px-6 py-2 bg-red-600 text-white rounded hover:bg-red-700">
                Crear Reporte
            </button>
        </div>
    </form>
</div>
{% endblock %}
```

### 3. Registrar Blueprint

En `app/routes/__init__.py`, agregar:

```python
from app.routes.blacklist import blacklist_bp

def register_blueprints(app):
    # ... blueprints existentes ...
    app.register_blueprint(blacklist_bp)
```

### 4. Agregar Botón en Navbar

En `app/templates/base.html`, agregar en el sidebar:

```html
<a href="{{ url_for('blacklist.dashboard') }}" 
   class="sidebar-link flex items-center space-x-3 px-4 py-3 rounded-lg transition">
    <i class="fas fa-ban"></i>
    <span>Blacklist</span>
</a>
```

---

## 🚀 PASOS PARA ACTIVAR

1. **Crear las tablas:**
   ```bash
   python scripts/create_blacklist_tables.py
   ```

2. **Crear las rutas** (copiar código de arriba a `app/routes/blacklist.py`)

3. **Crear los templates** (crear archivos en `app/templates/blacklist/`)

4. **Registrar el blueprint** (modificar `app/routes/__init__.py`)

5. **Agregar botón en navbar** (modificar `app/templates/base.html`)

6. **Reiniciar servidor:**
   ```bash
   sudo systemctl restart cotizaciones
   ```

7. **Probar:** Ir a https://ceiba21.com/blacklist/dashboard

---

## 📝 VARIABLES DE ENTORNO (Opcional)

Para las APIs de fraude, agregar a `.env`:

```bash
# Numverify (verificación de teléfonos)
NUMVERIFY_API_KEY=tu_api_key

# Twilio (alternativa para teléfonos)
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
```

---

## 🧪 TESTING

Puedes probar el servicio desde Python:

```python
from app import create_app
from app.services.blacklist_service import BlacklistService

app = create_app()
with app.app_context():
    # Crear reporte
    success, msg, entry = BlacklistService.create_report(
        operator_id=1,
        reason="Testing",
        telegram_id=123456789,
        category='SUSPICIOUS'
    )
    print(f"Success: {success}, Message: {msg}")
    
    # Buscar
    results = BlacklistService.search(telegram_id=123456789)
    print(f"Found: {len(results)} results")
```

---

## 📚 PRÓXIMOS PASOS SUGERIDOS

1. Implementar templates de apelaciones
2. Agregar exportación a CSV/Excel
3. Dashboard de estadísticas avanzadas
4. Integración con APIs de fraude (cuando tengas las keys)
5. Sistema de notificaciones por email
6. Logs de auditoría detallados

---

## 🐛 TROUBLESHOOTING

Si tienes errores al crear tablas:
```bash
# Ver qué tablas existen
python -c "from app import create_app, db; app=create_app(); app.app_context().push(); print(db.engine.table_names())"

# Recrear todo (¡cuidado, borra datos!)
# DROP TABLE blacklist_appeals, blacklist CASCADE;
```

---

¿Necesitas ayuda con algún paso? ¡Avísame!