# PROMPT PARA CLINE - IMPLEMENTAR SOLUCIÓN

Hola Cline,

He identificado y resuelto el error del bot de Telegram. El problema era pasar objetos SQLAlchemy entre contextos async/sync.

## 📋 TU TAREA

Implementar la solución reemplazando 3 archivos con versiones corregidas.

## 📂 ARCHIVOS CORREGIDOS DISPONIBLES

Hay 3 archivos corregidos en `/mnt/user-data/outputs/`:

1. `CORREGIDO_conversation_handler.py`
2. `CORREGIDO_responses.py`
3. `CORREGIDO_bot.py`

## 🎯 PASOS A SEGUIR

### 1. Hacer backup de archivos actuales

```bash
cd /var/www/cotizaciones

# Backup
cp app/bot/conversation_handler.py app/bot/conversation_handler.py.backup
cp app/bot/responses.py app/bot/responses.py.backup
cp app/telegram/bot.py app/telegram/bot.py.backup
```

### 2. Copiar archivos corregidos

```bash
# Reemplazar conversation_handler.py
cp /mnt/user-data/outputs/CORREGIDO_conversation_handler.py app/bot/conversation_handler.py

# Reemplazar responses.py
cp /mnt/user-data/outputs/CORREGIDO_responses.py app/bot/responses.py

# Reemplazar bot.py
cp /mnt/user-data/outputs/CORREGIDO_bot.py app/telegram/bot.py
```

### 3. Verificar que Redis esté configurado en app/__init__.py

Asegúrate de que exista esto en `app/__init__.py`:

```python
import redis

# Cliente Redis global
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def create_app():
    app = Flask(__name__)
    # ... resto ...
    
    # Hacer redis_client accesible
    app.redis_client = redis_client
    
    return app
```

Si NO existe, agrégalo.

### 4. Limpiar cache y reiniciar

```bash
# Limpiar Redis
redis-cli FLUSHDB

# Limpiar cache Python
find /var/www/cotizaciones -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /var/www/cotizaciones -type f -name "*.pyc" -delete

# Reiniciar servicio
sudo systemctl restart ceiba21

# Ver logs en tiempo real
sudo journalctl -u ceiba21 -f
```

### 5. Probar el bot

Abre Telegram y prueba:

```
/start
```

Deberías ver el menú principal con botones. Click en "💱 Nueva operación" y verifica que muestra las monedas.

## 🔍 QUÉ CAMBIÓ

### En conversation_handler.py:

- Agregados métodos `_serialize_currency()`, `_serialize_payment_method()`, `_serialize_user()`
- TODOS los handlers ahora serializan objetos antes de retornar
- Retornan SOLO datos primitivos (dict, str, int)

### En responses.py:

- TODOS los métodos reciben datos primitivos, NO objetos SQLAlchemy
- `welcome_message(user_data: Dict)` en vez de `welcome_message(user: User)`
- Sin queries a BD en ningún método

### En bot.py:

- TODOS los handlers async usan `with app.app_context():`
- Queries + serialización dentro del contexto
- Uso de datos primitivos fuera del contexto

## ✅ CRITERIO DE ÉXITO

El bot funciona correctamente si:

1. `/start` muestra menú con botones ✅
2. Click "Nueva operación" muestra monedas ✅
3. Seleccionar moneda muestra métodos ✅
4. Sin errores en logs ✅

## ⚠️ SI HAY ERRORES

1. Comparte el error completo de los logs
2. Verifica que los 3 archivos se copiaron bien
3. Asegúrate de que redis_client está en app/__init__.py
4. Verifica que Redis está corriendo: `redis-cli ping`

## 📖 DOCUMENTACIÓN COMPLETA

Para entender la solución completa, lee:

- `/mnt/user-data/outputs/SOLUCION_BOT_TELEGRAM.md`
- `/mnt/user-data/outputs/INSTRUCCIONES_PARA_CLINE.md`

---

**POR FAVOR IMPLEMENTA ESTOS CAMBIOS Y REPORTA EL RESULTADO.**

Cuando termines, ejecuta `/start` en el bot de Telegram y dime si funciona o si hay errores en los logs.
