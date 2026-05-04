#!/bin/bash

################################################################################
# Script de Reinicio Seguro - Ceiba21
# 
# Este script garantiza un reinicio limpio del servicio ceiba21, eliminando
# cualquier proceso gunicorn residual que pueda estar ocupando el puerto 5000.
#
# Uso: sudo ./scripts/safe_restart.sh
################################################################################

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Sin color

# Banner
echo -e "${BLUE}"
echo "════════════════════════════════════════════════════════"
echo "       REINICIO SEGURO DEL SERVICIO CEIBA21"
echo "════════════════════════════════════════════════════════"
echo -e "${NC}"

# Verificar que se ejecuta como root o con sudo
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ Este script debe ejecutarse como root o con sudo${NC}"
   echo "   Uso: sudo ./scripts/safe_restart.sh"
   exit 1
fi

echo -e "${YELLOW}📋 Paso 1: Deteniendo servicio systemd...${NC}"
systemctl stop ceiba21 2>/dev/null || echo "   Servicio ya estaba detenido"
sleep 2
echo -e "${GREEN}   ✓ Servicio systemd detenido${NC}"

echo ""
echo -e "${YELLOW}🔍 Paso 2: Buscando procesos gunicorn residuales...${NC}"
GUNICORN_PIDS=$(ps aux | grep -E "[g]unicorn.*wsgi:app" | awk '{print $2}')

if [ -z "$GUNICORN_PIDS" ]; then
    echo -e "${GREEN}   ✓ No se encontraron procesos residuales${NC}"
else
    echo -e "${YELLOW}   Encontrados procesos: $GUNICORN_PIDS${NC}"
    echo -e "${YELLOW}🧹 Paso 3: Eliminando procesos residuales...${NC}"
    for pid in $GUNICORN_PIDS; do
        kill -9 $pid 2>/dev/null && echo "      → PID $pid eliminado"
    done
    sleep 2
    echo -e "${GREEN}   ✓ Procesos residuales eliminados${NC}"
fi

echo ""
echo -e "${YELLOW}🔌 Paso 4: Verificando puerto 5000...${NC}"
PORT_CHECK=$(lsof -i :5000 2>/dev/null || echo "")
if [ -z "$PORT_CHECK" ]; then
    echo -e "${GREEN}   ✓ Puerto 5000 está libre${NC}"
else
    echo -e "${RED}   ⚠ Puerto 5000 todavía ocupado:${NC}"
    echo "$PORT_CHECK"
    exit 1
fi

echo ""
echo -e "${YELLOW}🚀 Paso 5: Iniciando servicio ceiba21...${NC}"
systemctl start ceiba21
sleep 3
echo -e "${GREEN}   ✓ Servicio iniciado${NC}"

echo ""
echo -e "${YELLOW}🏥 Paso 6: Verificando estado del servicio...${NC}"
if systemctl is-active --quiet ceiba21; then
    echo -e "${GREEN}   ✓ Servicio ceiba21 está ACTIVO${NC}"
    
    # Mostrar información de los workers
    echo ""
    echo -e "${BLUE}📊 Procesos gunicorn activos:${NC}"
    ps aux | grep -E "[g]unicorn.*wsgi:app" | awk '{print "   → PID " $2 " | CPU: " $3 "% | MEM: " $4 "%"}'
    
    # Test HTTP
    echo ""
    echo -e "${YELLOW}🌐 Paso 7: Probando respuesta HTTP...${NC}"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ 2>&1)
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}   ✓ Servidor responde correctamente (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "${YELLOW}   ⚠ Respuesta HTTP: $HTTP_CODE${NC}"
    fi
else
    echo -e "${RED}   ❌ El servicio NO está activo${NC}"
    echo ""
    echo "📋 Últimas líneas del log:"
    journalctl -u ceiba21 -n 20 --no-pager
    exit 1
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}        ✅ REINICIO COMPLETADO EXITOSAMENTE${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}💡 Tip: Para ver los logs en tiempo real:${NC}"
echo -e "   journalctl -u ceiba21 -f"
echo ""

exit 0
