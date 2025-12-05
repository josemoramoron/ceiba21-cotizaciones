/**
 * Control del Bot de Telegram desde el Dashboard
 * Actualización en tiempo real del estado y estadísticas
 */

class BotController {
    constructor() {
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusText = document.getElementById('status-text');
        this.statusDetails = document.getElementById('status-details');
        this.messagesCount = document.getElementById('messages-count');
        this.ordersCount = document.getElementById('orders-count');
        this.botUptime = document.getElementById('bot-uptime');
        
        this.btnStart = document.getElementById('btn-start-bot');
        this.btnStop = document.getElementById('btn-stop-bot');
        this.btnRestart = document.getElementById('btn-restart-bot');
        
        this.isUpdating = false;
        this.updateInterval = null;
        
        this.init();
    }
    
    init() {
        // Agregar eventos a botones
        this.btnStart.addEventListener('click', () => this.startBot());
        this.btnStop.addEventListener('click', () => this.stopBot());
        this.btnRestart.addEventListener('click', () => this.restartBot());
        
        // Actualizar estado inicial
        this.updateStatus();
        this.updateStats();
        
        // Iniciar polling cada 5 segundos
        this.startMonitoring();
    }
    
    async startBot() {
        if (this.isUpdating) return;
        
        this.isUpdating = true;
        this.btnStart.disabled = true;
        this.btnStart.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Iniciando...';
        
        try {
            const response = await fetch('/api/bot/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('✅ ' + data.message, 'success');
                await this.updateStatus();
            } else {
                this.showNotification('❌ ' + data.message, 'error');
            }
        } catch (error) {
            this.showNotification('❌ Error al iniciar bot: ' + error.message, 'error');
        } finally {
            this.isUpdating = false;
            this.btnStart.disabled = false;
            this.btnStart.innerHTML = '<i class="fas fa-play mr-2"></i>Iniciar Bot';
        }
    }
    
    async stopBot() {
        if (this.isUpdating) return;
        
        if (!confirm('¿Estás seguro de detener el bot?')) return;
        
        this.isUpdating = true;
        this.btnStop.disabled = true;
        this.btnStop.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Deteniendo...';
        
        try {
            const response = await fetch('/api/bot/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('✅ ' + data.message, 'success');
                await this.updateStatus();
            } else {
                this.showNotification('❌ ' + data.message, 'error');
            }
        } catch (error) {
            this.showNotification('❌ Error al detener bot: ' + error.message, 'error');
        } finally {
            this.isUpdating = false;
            this.btnStop.disabled = false;
            this.btnStop.innerHTML = '<i class="fas fa-stop mr-2"></i>Detener Bot';
        }
    }
    
    async restartBot() {
        if (this.isUpdating) return;
        
        if (!confirm('¿Reiniciar el bot?')) return;
        
        this.isUpdating = true;
        this.btnRestart.disabled = true;
        this.btnRestart.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Reiniciando...';
        
        try {
            const response = await fetch('/api/bot/restart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('✅ ' + data.message, 'success');
                await this.updateStatus();
            } else {
                this.showNotification('❌ ' + data.message, 'error');
            }
        } catch (error) {
            this.showNotification('❌ Error al reiniciar bot: ' + error.message, 'error');
        } finally {
            this.isUpdating = false;
            this.btnRestart.disabled = false;
            this.btnRestart.innerHTML = '<i class="fas fa-sync mr-2"></i>Reiniciar Bot';
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/bot/status');
            const data = await response.json();
            
            if (data.status === 'running') {
                this.statusIndicator.className = 'text-3xl mr-3 text-green-500';
                this.statusIndicator.textContent = '●';
                this.statusText.textContent = '✅ Bot en ejecución';
                this.statusDetails.textContent = `PID: ${data.pid} | Memoria: ${data.memory_mb} MB`;
                this.botUptime.textContent = data.uptime || '--';
                
                // Habilitar botón de detener, deshabilitar iniciar
                this.btnStart.disabled = true;
                this.btnStop.disabled = false;
                this.btnRestart.disabled = false;
            } else if (data.status === 'stopped') {
                this.statusIndicator.className = 'text-3xl mr-3 text-red-500';
                this.statusIndicator.textContent = '●';
                this.statusText.textContent = '⭕ Bot detenido';
                this.statusDetails.textContent = 'El bot no está corriendo';
                this.botUptime.textContent = '--';
                
                // Habilitar botón de iniciar, deshabilitar detener
                this.btnStart.disabled = false;
                this.btnStop.disabled = true;
                this.btnRestart.disabled = true;
            } else {
                this.statusIndicator.className = 'text-3xl mr-3 text-yellow-500';
                this.statusIndicator.textContent = '●';
                this.statusText.textContent = '⚠️ Estado desconocido';
                this.statusDetails.textContent = data.error || 'Error al verificar estado';
                this.botUptime.textContent = '--';
            }
        } catch (error) {
            console.error('Error al actualizar estado:', error);
            this.statusIndicator.className = 'text-3xl mr-3 text-gray-400';
            this.statusIndicator.textContent = '●';
            this.statusText.textContent = '❓ Error de conexión';
            this.statusDetails.textContent = 'No se pudo conectar al servidor';
        }
    }
    
    async updateStats() {
        try {
            const response = await fetch('/api/bot/stats');
            const data = await response.json();
            
            this.messagesCount.textContent = data.messages_today || 0;
            this.ordersCount.textContent = data.orders_active || 0;
        } catch (error) {
            console.error('Error al actualizar estadísticas:', error);
        }
    }
    
    startMonitoring() {
        // Actualizar cada 5 segundos
        this.updateInterval = setInterval(() => {
            this.updateStatus();
            this.updateStats();
        }, 5000);
    }
    
    stopMonitoring() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    showNotification(message, type = 'info') {
        // Crear elemento de notificación
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-6 py-4 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        } text-white font-semibold`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remover después de 3 segundos
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new BotController();
});
