# Integración del módulo SMS en Ceiba21

Este paquete añade mensajería SMS a Ceiba21 como un módulo más, respetando
la arquitectura Routes → Services → Models y reutilizando PostgreSQL, Gunicorn,
systemd, Redis, Tailwind y el túnel Cloudflare existentes. **No crea procesos,
bases de datos ni servicios nuevos.**

## Archivos nuevos (copiar tal cual)

```
app/models/sim_slot.py
app/models/sms_message.py
app/services/sms_service.py
app/routes/sms.py
app/templates/sms/index.html
app/templates/sms/send.html
app/templates/sms/inbox.html
app/templates/sms/history.html
app/templates/sms/sims.html
app/templates/sms/_status_badge.html
app/templates/sms/_pagination.html
scripts/init_sms.py
```

## Ediciones a archivos existentes (5 cambios)

### 1. `app/models/__init__.py`
Tras las importaciones de modelos, añadir:
```python
# Módulo SMS
from app.models.sim_slot import SimSlot
from app.models.sms_message import SmsMessage, SmsDirection, SmsStatus
```
Y en `__all__` agregar: `'SimSlot', 'SmsMessage', 'SmsDirection', 'SmsStatus',`

### 2. `app/services/__init__.py`
Añadir:
```python
from app.services.sms_service import SmsService
```
Y en `__all__`: `'SmsService',`

### 3. `app/services/system_config_service.py`
Añadir estos métodos dentro de la clase `SystemConfigService` (usan el patrón
tipado existente, sin tocar SystemConfig directamente desde fuera):

```python
    # ── Slot SIM activo del módulo SMS ─────────────────────────────────────
    _KEY_SMS_ACTIVE_SLOT = 'sms_active_sim_slot'
    _SMS_SLOT_DESCRIPTION = 'Número de slot SIM activo en el board multi-SIM.'

    @classmethod
    def get_sms_active_slot(cls):
        """Devuelve el número de slot SIM activo, o None si no se ha fijado.

        Returns:
            int con el slot activo, o None.
        """
        raw = SystemConfig.get_value(cls._KEY_SMS_ACTIVE_SLOT)
        try:
            return int(raw) if raw is not None else None
        except (ValueError, TypeError):
            return None

    @classmethod
    def set_sms_active_slot(cls, slot_number: int) -> bool:
        """Persiste el slot SIM activo.

        Args:
            slot_number: Número de slot del board.

        Returns:
            True si se guardó correctamente.
        """
        return SystemConfig.set_value(
            key=cls._KEY_SMS_ACTIVE_SLOT,
            value=int(slot_number),
            description=cls._SMS_SLOT_DESCRIPTION,
        )
```

### 4. `app/__init__.py`
En el bloque de registro de blueprints, añadir el import y el registro:
```python
    from app.routes.sms import sms_bp
    ...
    app.register_blueprint(sms_bp)
```

### 5. `app/templates/base.html`
En el sidebar (dentro del bloque `{% if ... role.value == 'admin' %}`), añadir
el enlace junto a los demás, p. ej. después de "Pagos":
```html
                <a href="{{ url_for('sms.index') }}"
                   class="sidebar-link flex items-center space-x-3 px-4 py-3 rounded-lg
                   {% if request.endpoint and request.endpoint.startswith('sms.') %}active{% endif %}">
                    <i class="fas fa-comment-sms w-4" style="color:var(--color-primary);"></i><span>SMS</span>
                </a>
```

## Variables de entorno (.env de producción)

Añadir al `.env` de `/var/www/cotizaciones`:
```env
SMS_GATEWAY_IP=192.168.20.16
SMS_GATEWAY_PORT=8080
SMS_GATEWAY_USER=sms
SMS_GATEWAY_PASSWORD=HytDyRHl
```

## Despliegue

```bash
# 1. Aplicar archivos (Cline) y commit
git add -A && git commit -m "feat: módulo SMS integrado (gateway Android multi-SIM)"
git push origin master

# 2. Deploy normal de Ceiba21
ssh ceiba21-local-webmaster "/var/www/cotizaciones/deploy.sh"

# 3. Crear tablas SMS y sembrar slots (una sola vez)
ssh ceiba21-local-webmaster "cd /var/www/cotizaciones && source venv/bin/activate && python scripts/init_sms.py"

# 4. Tests
python -m pytest app\tests\ -v
```

## Webhook (en la app del teléfono)

- URL: `https://ceiba21.com/dashboard/sms/webhook/incoming`
- Evento: `sms:received`

Los webhooks están exentos del guard de admin (el gateway no tiene sesión);
su seguridad se basa en ser alcanzables solo vía la red local / túnel.

## Notas de arquitectura

- **Notificaciones:** polling ligero (`/api/unread` cada 15s, `/api/health`
  cada 30s) en lugar de SSE, porque SSE con estado en memoria no funciona con
  los 3 workers de Gunicorn de producción. El polling es compatible multi-worker.
- **Sin migración de esquema destructiva:** solo `CREATE TABLE` de tablas nuevas
  (`sms_messages`, `sms_sim_slots`), nada de `ALTER TABLE` sobre tablas vivas.
- **URL final:** el módulo vive en `ceiba21.com/dashboard/sms` — no requiere
  subdominio nuevo ni configuración extra de Cloudflare/Nginx.
