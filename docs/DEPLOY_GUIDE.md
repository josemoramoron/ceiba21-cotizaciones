# 🚀 GUÍA DE DESPLIEGUE Y BUENAS PRÁCTICAS

## 📋 TU CONFIGURACIÓN ACTUAL

### **Sistema: systemd + gunicorn**

```
systemd (ceiba21.service)
    ↓ supervisa y controla
gunicorn (3 workers en puerto 5000)
    ↓ ejecuta
Flask Application (wsgi.py)
```

**systemd** es tu "supervisor":
- ✅ Inicia gunicorn automáticamente al arrancar el servidor
- ✅ Reinicia gunicorn si crashea
- ✅ Gestiona logs centralizados
- ✅ Permite control fácil con `systemctl`

**gunicorn** es tu "servidor de aplicación":
- ✅ Ejecuta tu código Python
- ✅ Maneja múltiples requests simultáneos (3 workers)
- ✅ Escucha en `127.0.0.1:5000`
- ✅ Optimizado para producción

---

## 🎯 BUENAS PRÁCTICAS: DESARROLLO VS PRODUCCIÓN

### **🛠️ MODO DESARROLLO (Puerto 5001)**

**Cuándo usar:**
- Al desarrollar nuevas features
- Para probar cambios rápidamente
- Cuando necesitas debugging
- Para ver errores detallados

**Cómo iniciar:**

```bash
cd /var/www/cotizaciones
source venv/bin/activate
flask run --host=0.0.0.0 --port=5001
```

**Ventajas:**
- ✅ Auto-reload al cambiar código
- ✅ Mensajes de error detallados
- ✅ Fácil de detener (Ctrl+C)
- ✅ No interfiere con producción

**Desventajas:**
- ❌ Solo 1 request a la vez (lento)
- ❌ NO es seguro para producción
- ❌ Sin auto-restart si crashea

**Acceso:**
```
http://192.168.8.158:5001
```

---

### **🚀 MODO PRODUCCIÓN (Puerto 5000 → 80 via Nginx)**

**Cuándo usar:**
- Sistema "en vivo" con usuarios reales
- Después de probar en desarrollo
- Para máximo rendimiento
- Cuando necesitas estabilidad

**Cómo gestionar:**

```bash
# Reiniciar después de cambios
sudo systemctl restart ceiba21

# Ver estado
sudo systemctl status ceiba21

# Detener temporalmente
sudo systemctl stop ceiba21

# Iniciar
sudo systemctl start ceiba21

# Ver logs en tiempo real
sudo journalctl -u ceiba21 -f

# Ver logs de errores
sudo journalctl -u ceiba21 | grep ERROR
```

**Ventajas:**
- ✅ Múltiples workers (maneja muchos users)
- ✅ Auto-reinicio si crashea
- ✅ Logs centralizados
- ✅ Inicia automáticamente al bootear
- ✅ Seguro y optimizado

**Acceso:**
```
http://ceiba21.com
```

---

## 📝 WORKFLOWS RECOMENDADOS

### **Workflow 1: Desarrollo → Producción (Recomendado)**

```bash
# 1. DESARROLLO
# Terminal 1: Iniciar servidor dev
cd /var/www/cotizaciones
source venv/bin/activate
flask run --host=0.0.0.0 --port=5001

# Desarrollar, probar, hacer cambios
# Acceder: http://192.168.8.158:5001

# 2. CUANDO ESTÉ LISTO
# Detener dev (Ctrl+C)

# 3. COMMIT
git add .
git commit -m "feat: nueva funcionalidad"
git push origin master

# 4. DEPLOY A PRODUCCIÓN
sudo systemctl restart ceiba21

# 5. VERIFICAR
# Acceder: http://ceiba21.com
```

---

### **Workflow 2: Testing rápido en mismo servidor**

```bash
# 1. Detener producción temporalmente
sudo systemctl stop ceiba21

# 2. Probar en modo desarrollo
flask run --host=0.0.0.0 --port=5000

# 3. Hacer pruebas

# 4. Detener (Ctrl+C)

# 5. Volver a producción
sudo systemctl start ceiba21
```

---

## 🔄 DESPLIEGUE DE CAMBIOS

### **Proceso Completo**

```bash
# 1. BACKUP DE BASE DE DATOS (recomendado)
pg_dump -U postgres ceiba21_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. VER QUÉ CAMBIOS HAY
git status
git log --oneline -5

# 3. REINICIAR SERVICIO
sudo systemctl restart ceiba21

# 4. VERIFICAR QUE INICIÓ CORRECTAMENTE
sudo systemctl status ceiba21

# 5. VER LOGS
sudo journalctl -u ceiba21 -n 50

# 6. PROBAR EN NAVEGADOR
# Acceder a http://ceiba21.com
```

---

## ✅ VERIFICACIÓN POST-DESPLIEGUE

### **1. Verificar que el servicio arrancó**

```bash
# Estado del servicio
sudo systemctl status ceiba21

# Debe mostrar:
# Active: active (running)
# 4 procesos (1 maestro + 3 workers)
```

### **2. Verificar procesos**

```bash
ps aux | grep gunicorn

# Deberías ver algo como:
# webmast+ 729409 ... gunicorn (maestro)
# webmast+ 729411 ... gunicorn (worker 1)
# webmast+ 729412 ... gunicorn (worker 2)
# webmast+ 729413 ... gunicorn (worker 3)
```

### **3. Verificar puertos**

```bash
ss -tulnp | grep 5000

# Debería mostrar gunicorn escuchando en 127.0.0.1:5000
```

### **4. Probar desde navegador**

- ✅ http://ceiba21.com/auth/login
- ✅ Login funciona
- ✅ Dashboard carga
- ✅ **Panel de control del bot** en `/dashboard/telegram`
- ✅ Estadísticas actualizadas
- ✅ Sin errores en consola del navegador (F12)

### **5. Verificar logs**

```bash
# Ver últimos 50 logs
sudo journalctl -u ceiba21 -n 50

# Buscar errores
sudo journalctl -u ceiba21 | grep -i error

# Monitorear en tiempo real
sudo journalctl -u ceiba21 -f
```

---

## ⚠️ ERRORES COMUNES Y SOLUCIONES

### **Problema: Múltiples procesos gunicorn**

**Síntoma:**
```bash
ps aux | grep gunicorn
# Muestra 10+ procesos, algunos muy viejos
```

**Causa:** Iniciaste gunicorn manualmente y luego usaste systemd.

**Solución:**
```bash
# Matar TODOS los gunicorn
pkill -f gunicorn

# Reiniciar SOLO con systemd
sudo systemctl restart ceiba21
```

**Prevención:** ❌ NUNCA ejecutes `gunicorn ...` manualmente. ✅ SIEMPRE usa `systemctl`.

---

### **Problema: Puerto en uso**

**Síntoma:**
```
Address already in use
```

**Solución:**
```bash
# Ver qué usa el puerto
ss -tulnp | grep :5000

# Matar proceso
kill -9 [PID]

# O reiniciar servicio
sudo systemctl restart ceiba21
```

---

### **Problema: Cambios no se aplican**

**Síntoma:** Modificaste código pero no ves los cambios.

**Causa:** Python NO auto-reloada en producción.

**Solución:**
```bash
# SIEMPRE reinicia después de cambios
sudo systemctl restart ceiba21
```

---

### **Problema: Error 500**

**Solución:**
```bash
# Ver logs detallados
sudo journalctl -u ceiba21 -n 100

# Ver stack trace completo
sudo journalctl -u ceiba21 | grep -A 20 "ERROR"

# Probar manualmente para ver error
cd /var/www/cotizaciones
source venv/bin/activate
python wsgi.py
```

---

### **Problema: Panel del bot no aparece**

**Solución:**
```bash
# 1. Limpiar cache del navegador
Ctrl + Shift + R

# 2. Verificar que JavaScript se cargó
# Abrir consola (F12) y buscar:
# "GET /static/js/bot_control.js 200"

# 3. Ver errores de JavaScript
# En consola del navegador buscar errores en rojo
```

---

## 📦 CONFIGURACIÓN DEL SERVICIO

### **Archivo: `/etc/systemd/system/ceiba21.service`**

```ini
[Unit]
Description=Ceiba21 Flask Application
After=network.target

[Service]
User=webmaster
WorkingDirectory=/var/www/cotizaciones
Environment="PATH=/var/www/cotizaciones/venv/bin"
ExecStart=/var/www/cotizaciones/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### **Para modificar el servicio:**

```bash
# Editar archivo
sudo nano /etc/systemd/system/ceiba21.service

# Recargar configuración
sudo systemctl daemon-reload

# Reiniciar servicio
sudo systemctl restart ceiba21
```

---

## 🔧 COMANDOS ÚTILES

### **Gestión del Servicio**

```bash
# Reiniciar (después de cambios)
sudo systemctl restart ceiba21

# Ver estado
sudo systemctl status ceiba21

# Detener
sudo systemctl stop ceiba21

# Iniciar
sudo systemctl start ceiba21

# Habilitar auto-inicio al bootear
sudo systemctl enable ceiba21

# Deshabilitar auto-inicio
sudo systemctl disable ceiba21
```

### **Logs**

```bash
# Ver logs en tiempo real
sudo journalctl -u ceiba21 -f

# Ver últimos 50 logs
sudo journalctl -u ceiba21 -n 50

# Ver logs desde hoy
sudo journalctl -u ceiba21 --since today

# Ver solo errores
sudo journalctl -u ceiba21 -p err

# Ver logs con timestamps
sudo journalctl -u ceiba21 -o short-precise
```

### **Debugging**

```bash
# Ver procesos Python
ps aux | grep python

# Ver puertos abiertos
ss -tulnp | grep -E "80|443|5000|5001"

# Ver uso de memoria
free -h

# Ver uso de disco
df -h
```

---

## 🔐 CONFIGURACIÓN NGINX (Proxy Reverso)

Si usas Nginx para servir en puerto 80/443:

```nginx
server {
    listen 80;
    server_name ceiba21.com www.ceiba21.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /var/www/cotizaciones/app/static;
        expires 30d;
    }
}
```

**Recargar Nginx:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🛡️ SEGURIDAD Y OPTIMIZACIÓN

### **Recomendaciones de Producción**

1. **Usar HTTPS (SSL/TLS)**
   ```bash
   sudo certbot --nginx -d ceiba21.com
   ```

2. **Configurar firewall**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **Logs rotación**
   ```bash
   sudo nano /etc/logrotate.d/ceiba21
   ```

4. **Monitoreo**
   - Configurar alertas si el servicio falla
   - Monitorear uso de recursos

5. **Backups automáticos**
   ```bash
   # Cron job para backup diario de BD
   0 2 * * * pg_dump ceiba21_db > /backups/db_$(date +\%Y\%m\%d).sql
   ```

---

## 📊 DIFERENCIAS CLAVE

| Aspecto | Desarrollo | Producción |
|---------|-----------|------------|
| **Comando** | `flask run` | `systemctl restart ceiba21` |
| **Puerto** | 5001 | 5000 (interno) → 80 (público) |
| **Workers** | 1 | 3 |
| **Auto-reload** | ✅ Sí | ❌ No |
| **Performance** | Lento | Rápido |
| **Debugging** | Detallado | Limitado |
| **Logs** | Terminal | journalctl |
| **Auto-restart** | ❌ No | ✅ Sí |
| **Producción** | ❌ NUNCA | ✅ Siempre |

---

## 🎯 CHECKLIST DE DESPLIEGUE

Antes de reiniciar en producción:

- [ ] Código testeado en desarrollo (puerto 5001)
- [ ] Backup de base de datos realizado
- [ ] Git commit y push hechos
- [ ] README actualizado (si aplica)
- [ ] No hay cambios sin commitear
- [ ] Reiniciar servicio: `sudo systemctl restart ceiba21`
- [ ] Verificar estado: `sudo systemctl status ceiba21`
- [ ] Probar en navegador
- [ ] Verificar logs: `sudo journalctl -u ceiba21 -n 50`
- [ ] Panel del bot funciona
- [ ] Sin errores en consola
- [ ] Funcionamiento OK ✅

---

## 🆘 ROLLBACK DE EMERGENCIA

Si algo sale mal después del deploy:

```bash
# 1. Volver al commit anterior
git log --oneline -5  # Ver commits
git reset --hard [commit-hash-anterior]

# 2. Reiniciar servicio
sudo systemctl restart ceiba21

# 3. Verificar
sudo systemctl status ceiba21
```

---

## 📞 SOPORTE

Si necesitas ayuda:

1. **Ver estado del servicio:**
   ```bash
   sudo systemctl status ceiba21
   ```

2. **Ver logs completos:**
   ```bash
   sudo journalctl -u ceiba21 -n 200
   ```

3. **Ver procesos:**
   ```bash
   ps aux | grep gunicorn
   ```

4. **Compartir:**
   - Salida de los comandos anteriores
   - Error completo del navegador (F12)
   - Contenido de `.env` (sin contraseñas)

---

## 🎓 RESUMEN DE COMANDOS MÁS USADOS

```bash
# Desarrollo
flask run --host=0.0.0.0 --port=5001

# Producción
sudo systemctl restart ceiba21
sudo systemctl status ceiba21
sudo journalctl -u ceiba21 -f

# Ver qué está corriendo
ps aux | grep gunicorn
ss -tulnp | grep 5000

# Emergencia (limpiar todo)
pkill -f gunicorn
sudo systemctl restart ceiba21
```

---

## ✅ PRÓXIMOS PASOS

Una vez desplegado y verificado:

1. ✅ Probar panel de control del bot
2. ✅ Verificar que estadísticas funcionan
3. ✅ Confirmar que todo carga sin errores
4. ⏭️ Continuar con **FASE B: Bot Conversacional**

**¡Sistema listo para producción!** 🚀
