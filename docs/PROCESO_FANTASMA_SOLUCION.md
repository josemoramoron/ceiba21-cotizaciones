# Solución al Problema de Procesos Gunicorn Fantasmas

**Fecha del Incidente:** 04 de Mayo de 2026  
**Sistema Afectado:** Ceiba21 Flask Application  
**Severidad:** Alta - Servicio caído completamente

---

## 🚨 Descripción del Problema

El servicio ceiba21 estuvo en un bucle de reintentos fallidos (5,203+ intentos) con el siguiente error:

```
[ERROR] connection to ('127.0.0.1', 5000) failed: [Errno 98] Address already in use
```

El servicio systemd no podía iniciar porque el puerto 5000 estaba ocupado por procesos gunicorn "fantasmas" que corrían fuera del control de systemd.

---

## 🔍 Diagnóstico

### Síntomas Observados

1. **Servicio systemd en estado `activating (auto-restart)`**
2. **Error continuo:** `Address already in use` en puerto 5000
3. **Procesos gunicorn antiguos** ejecutándose desde el 3 de mayo
4. **PostgreSQL y Redis** operativos (no eran el problema)

### Investigación

Al revisar los procesos activos, se encontraron 4 procesos gunicorn daemon:

```bash
webmaster@raspberrypi $ ps aux | grep gunicorn
webmaster  94089  0.0  0.2  36416 20208 ?  S  May03  0:05 gunicorn --daemon wsgi:app
webmaster  94091  0.0  1.2 129760 104000 ? S  May03  0:03 gunicorn --daemon wsgi:app
webmaster  94092  0.0  1.2 127184 101584 ? S  May03  0:03 gunicorn --daemon wsgi:app
webmaster  94093  0.0  1.1 125744 97344 ?  S  May03  0:03 gunicorn --daemon wsgi:app
```

---

## 🎯 Causa Raíz

El análisis del historial de bash (`~/.bash_history`) reveló la causa:

### Comandos Ejecutados Manualmente

Se encontraron múltiples ejecuciones de comandos con el flag `--daemon`:

```bash
gunicorn --workers 3 --bind 127.0.0.1:5000 --daemon wsgi:app
```

### ¿Por qué es problemático?

1. **Desacople del terminal:** Los procesos daemon no dependen de la sesión que los creó
2. **Sin control de systemd:** Systemd no puede gestionar procesos iniciados manualmente
3. **Persistencia indefinida:** Los procesos permanecen activos incluso después de cerrar sesión
4. **Conflicto de puerto:** Ocupan el puerto 5000, bloqueando el servicio oficial

---

## ✅ Solución Aplicada

### Paso 1: Detener el Servicio Systemd
```bash
sudo systemctl stop ceiba21
```

### Paso 2: Eliminar Procesos Fantasmas
```bash
kill -9 94089 94091 94092 94093
```

### Paso 3: Verificar Puerto Libre
```bash
lsof -i :5000  # Debe estar vacío
```

### Paso 4: Reiniciar Servicio
```bash
sudo systemctl start ceiba21
```

### Paso 5: Verificar Estado
```bash
systemctl status ceiba21
curl -I http://localhost:5000/
```

---

## 📊 Resultado

✅ **Servicio ceiba21:** ACTIVO y funcionando  
✅ **Puerto 5000:** Liberado y disponible  
✅ **Workers gunicorn:** 3 workers + 1 master bajo control de systemd  
✅ **Respuesta HTTP:** 200 OK  

---

## 🛡️ Prevención - Mejores Prácticas

### ❌ NO HACER

```bash
# ❌ Nunca ejecutar gunicorn manualmente con --daemon
gunicorn --workers 3 --bind 127.0.0.1:5000 --daemon wsgi:app

# ❌ No matar procesos sin detener systemd primero
kill -9 <pid>
```

### ✅ HACER

```bash
# ✅ Usar systemd para gestionar el servicio
sudo systemctl restart ceiba21
sudo systemctl stop ceiba21
sudo systemctl start ceiba21
sudo systemctl status ceiba21

# ✅ Ver logs del servicio
journalctl -u ceiba21 -f

# ✅ Usar el script de reinicio seguro (recomendado)
sudo ./scripts/safe_restart.sh
```

---

## 🔧 Script de Reinicio Seguro

Se creó un script automatizado que garantiza un reinicio limpio:

**Ubicación:** `scripts/safe_restart.sh`

### Características

- ✅ Detiene el servicio systemd correctamente
- ✅ Identifica y elimina procesos gunicorn residuales
- ✅ Verifica que el puerto 5000 esté libre
- ✅ Reinicia el servicio vía systemd
- ✅ Valida que el servicio esté activo
- ✅ Prueba la respuesta HTTP
- ✅ Muestra información detallada de cada paso

### Uso

```bash
sudo ./scripts/safe_restart.sh
```

---

## 📝 Configuración Correcta

### Archivo systemd (`/etc/systemd/system/ceiba21.service`)

```ini
[Unit]
Description=Ceiba21 Flask Application
After=network.target

[Service]
User=webmaster
Group=www-data
WorkingDirectory=/var/www/cotizaciones
Environment="PATH=/var/www/cotizaciones/venv/bin"
ExecStart=/var/www/cotizaciones/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Nota importante:** El ExecStart NO incluye el flag `--daemon` porque systemd ya maneja la daemonización.

---

## 🎓 Lecciones Aprendidas

1. **Centralizar la gestión de servicios:** Usar systemd como única fuente de control
2. **Evitar comandos manuales con --daemon:** Pueden crear procesos huérfanos
3. **Documentar procedimientos:** Tener scripts estandarizados previene errores
4. **Monitoreo proactivo:** Detectar problemas antes de que se agraven
5. **Automatización:** Scripts que garantizan operaciones consistentes y seguras

---

## 📚 Referencias

- **Gunicorn Documentation:** [Deploy Gunicorn](https://docs.gunicorn.org/en/stable/deploy.html)
- **Systemd Service Units:** [systemd.service](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- **Script de Reinicio:** `/var/www/cotizaciones/scripts/safe_restart.sh`

---

## 📞 Contacto

Para reportar problemas similares o sugerencias de mejora, contactar al equipo de desarrollo.

---

**Última actualización:** 04 de Mayo de 2026  
**Mantenido por:** Equipo Ceiba21
