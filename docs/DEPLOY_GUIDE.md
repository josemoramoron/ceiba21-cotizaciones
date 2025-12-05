# 🚀 GUÍA DE DESPLIEGUE A PRODUCCIÓN

## 📋 RESUMEN

Como trabajas directamente en producción (`/var/www/cotizaciones`), todos los cambios ya están aplicados localmente. Solo necesitas:

1. **Reiniciar el servidor** para aplicar cambios
2. **Verificar** que todo funcione correctamente

---

## 🔄 REINICIAR SERVIDOR

### **Opción 1: Si usas Flask desarrollo (puerto 5001)**

```bash
# Detener servidor actual
# Presiona Ctrl+C en la terminal donde corre

# Reiniciar
cd /var/www/cotizaciones
source venv/bin/activate
flask run --host=0.0.0.0 --port=5001
```

### **Opción 2: Si usas Gunicorn**

```bash
# Buscar proceso
ps aux | grep gunicorn

# Matar proceso viejo
pkill -f gunicorn

# Reiniciar
cd /var/www/cotizaciones
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:80 wsgi:app --daemon
```

### **Opción 3: Si usas systemd**

```bash
# Ver servicios disponibles
systemctl list-units --type=service | grep -E "flask|gunicorn|ceiba"

# Reiniciar (cambia 'nombre-servicio' por el real)
sudo systemctl restart nombre-servicio

# Ver estado
sudo systemctl status nombre-servicio
```

### **Opción 4: Si usas supervisor**

```bash
# Ver servicios
sudo supervisorctl status

# Reiniciar (cambia 'ceiba21' por el nombre real)
sudo supervisorctl restart ceiba21
```

---

## ✅ VERIFICACIÓN POST-DESPLIEGUE

### **1. Verificar que el servidor arrancó**

```bash
# Ver procesos Python
ps aux | grep python

# Ver puertos abiertos
ss -tulnp | grep -E "80|443|5000|5001"

# Ver logs (si existen)
tail -f logs/app.log
```

### **2. Probar desde navegador**

```
http://TU_DOMINIO/auth/login
```

o

```
http://TU_IP:5001/auth/login
```

### **3. Verificar funcionalidades nuevas**

- ✅ Login funciona
- ✅ Dashboard carga
- ✅ **NUEVO:** Panel de control del bot en `/dashboard/telegram`
- ✅ **NUEVO:** Botones Iniciar/Detener/Reiniciar bot
- ✅ **NUEVO:** Estadísticas del bot
- ✅ **NUEVO:** API `/api/bot/status` y `/api/bot/stats`

### **4. Verificar logs**

```bash
# Ver errores recientes
tail -50 logs/app.log | grep ERROR

# Monitorear en tiempo real
tail -f logs/app.log
```

---

## 🐛 SI ALGO FALLA

### **Problema: Servidor no inicia**

```bash
# Ver logs detallados
python wsgi.py
# Esto mostrará el error exacto
```

### **Problema: Error 500**

```bash
# Ver logs
tail -100 logs/app.log

# Verificar permisos
ls -la /var/www/cotizaciones
```

### **Problema: Panel del bot no aparece**

```bash
# Limpiar cache del navegador
Ctrl + Shift + R

# Verificar que JavaScript se cargó
# En consola del navegador (F12), buscar:
# "GET /static/js/bot_control.js"
```

---

## 📦 BACKUP (RECOMENDADO)

Antes de reiniciar, haz backup de la BD:

```bash
# Backup de PostgreSQL
pg_dump -U postgres nombre_bd > backup_$(date +%Y%m%d_%H%M%S).sql

# O especificando host
pg_dump -h localhost -U postgres -d nombre_bd -f backup.sql
```

---

## 🔐 CONFIGURACIÓN SSL (PRODUCCIÓN)

Si usas un dominio con HTTPS, asegúrate de tener:

### **Con Nginx:**

```nginx
server {
    listen 443 ssl;
    server_name tu-dominio.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📝 NOTAS IMPORTANTES

1. **Puerto 5001 es para desarrollo**
   - Usa puerto 80/443 en producción con Gunicorn+Nginx

2. **Flask `flask run` NO es para producción**
   - Usa Gunicorn o uWSGI

3. **Configuración recomendada para producción:**
   ```bash
   gunicorn -w 4 \
            -b 127.0.0.1:5000 \
            --access-logfile logs/access.log \
            --error-logfile logs/error.log \
            --daemon \
            wsgi:app
   ```

4. **Para auto-restart con systemd:**
   - Crea `/etc/systemd/system/ceiba21.service`
   - Habilita: `sudo systemctl enable ceiba21`

---

## 🎯 PRÓXIMOS PASOS

Una vez desplegado y verificado:

- ✅ Probar panel de control del bot
- ✅ Verificar que estadísticas funcionan
- ⏭️ Continuar con **FASE B: Bot Conversacional**

---

## 📞 SOPORTE

Si necesitas ayuda:
1. Copia el error completo de logs
2. Copia la salida de `ps aux | grep python`
3. Comparte el contenido de `.env` (sin contraseñas)
