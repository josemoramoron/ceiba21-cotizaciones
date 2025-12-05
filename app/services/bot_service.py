"""
Servicio para controlar el bot de Telegram.
Permite iniciar, detener y monitorear el proceso del bot.
"""
from app.services.base_service import BaseService
from typing import Dict, Any, Optional
import subprocess
import psutil
from datetime import datetime, timedelta


class BotService(BaseService):
    """
    Servicio para gestionar el proceso del bot de Telegram.
    
    RESPONSABILIDADES:
    - Iniciar/detener proceso del bot
    - Verificar estado del bot
    - Obtener estadísticas
    - Monitorear uptime
    """
    
    BOT_COMMAND = ['python', '-m', 'app.telegram.bot']
    BOT_PROCESS_NAME = 'app.telegram.bot'
    
    # ==========================================
    # CONTROL DEL PROCESO
    # ==========================================
    
    @classmethod
    def start_bot(cls) -> tuple[bool, str]:
        """
        Iniciar el bot de Telegram.
        
        Returns:
            (success, message)
        """
        try:
            # Verificar si ya está corriendo
            if cls.is_running():
                return False, "El bot ya está corriendo"
            
            # Iniciar proceso
            subprocess.Popen(
                cls.BOT_COMMAND,
                cwd='/var/www/cotizaciones',
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            cls.log_info("Bot de Telegram iniciado")
            return True, "Bot iniciado exitosamente"
            
        except Exception as e:
            cls.log_error("Error al iniciar bot", e)
            return False, f"Error al iniciar bot: {str(e)}"
    
    @classmethod
    def stop_bot(cls) -> tuple[bool, str]:
        """
        Detener el bot de Telegram.
        
        Returns:
            (success, message)
        """
        try:
            # Verificar si está corriendo
            if not cls.is_running():
                return False, "El bot no está corriendo"
            
            # Buscar y terminar proceso
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline') or []
                    if any(cls.BOT_PROCESS_NAME in str(cmd) for cmd in cmdline):
                        proc.terminate()
                        proc.wait(timeout=5)
                        cls.log_warning(f"Bot detenido (PID: {proc.pid})")
                        return True, "Bot detenido exitosamente"
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    pass
            
            return False, "No se pudo detener el bot"
            
        except Exception as e:
            cls.log_error("Error al detener bot", e)
            return False, f"Error al detener bot: {str(e)}"
    
    @classmethod
    def restart_bot(cls) -> tuple[bool, str]:
        """
        Reiniciar el bot de Telegram.
        
        Returns:
            (success, message)
        """
        # Detener
        if cls.is_running():
            success, message = cls.stop_bot()
            if not success:
                return False, f"Error al detener: {message}"
        
        # Esperar un momento
        import time
        time.sleep(1)
        
        # Iniciar
        success, message = cls.start_bot()
        if success:
            cls.log_info("Bot reiniciado exitosamente")
            return True, "Bot reiniciado exitosamente"
        else:
            return False, f"Error al iniciar: {message}"
    
    # ==========================================
    # ESTADO Y MONITOREO
    # ==========================================
    
    @classmethod
    def is_running(cls) -> bool:
        """
        Verificar si el bot está corriendo.
        
        Returns:
            True si está corriendo, False si no
        """
        try:
            for proc in psutil.process_iter(['cmdline']):
                cmdline = proc.info.get('cmdline') or []
                if any(cls.BOT_PROCESS_NAME in str(cmd) for cmd in cmdline):
                    return True
            return False
        except Exception:
            return False
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        Obtener estado completo del bot.
        
        Returns:
            {
                'status': 'running' | 'stopped',
                'pid': int | None,
                'uptime': str | None,
                'memory_mb': float | None
            }
        """
        try:
            for proc in psutil.process_iter(['pid', 'cmdline', 'create_time', 'memory_info']):
                cmdline = proc.info.get('cmdline') or []
                if any(cls.BOT_PROCESS_NAME in str(cmd) for cmd in cmdline):
                    # Bot está corriendo
                    create_time = proc.info.get('create_time')
                    uptime_seconds = datetime.now().timestamp() - create_time if create_time else 0
                    uptime = cls._format_uptime(uptime_seconds)
                    
                    memory_info = proc.info.get('memory_info')
                    memory_mb = memory_info.rss / (1024 * 1024) if memory_info else 0
                    
                    return {
                        'status': 'running',
                        'pid': proc.info.get('pid'),
                        'uptime': uptime,
                        'memory_mb': round(memory_mb, 2)
                    }
            
            # Bot no está corriendo
            return {
                'status': 'stopped',
                'pid': None,
                'uptime': None,
                'memory_mb': None
            }
            
        except Exception as e:
            cls.log_error("Error al obtener estado del bot", e)
            return {
                'status': 'error',
                'pid': None,
                'uptime': None,
                'memory_mb': None,
                'error': str(e)
            }
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """
        Obtener estadísticas del bot.
        
        Returns:
            {
                'messages_today': int,
                'orders_active': int,
                'users_active': int
            }
        """
        try:
            from app.models.message import Message
            from app.models.order import Order, OrderStatus
            from app.models.user import User
            from datetime import datetime
            
            # Mensajes de hoy
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            messages_today = Message.query.filter(
                Message.created_at >= today_start
            ).count()
            
            # Órdenes activas (no completadas ni canceladas)
            orders_active = Order.query.filter(
                Order.status.in_([
                    OrderStatus.PENDING,
                    OrderStatus.PROCESSING
                ])
            ).count()
            
            # Usuarios activos (con órdenes en últimos 7 días)
            week_ago = datetime.now() - timedelta(days=7)
            users_active = User.query.join(Order).filter(
                Order.created_at >= week_ago
            ).distinct().count()
            
            return {
                'messages_today': messages_today,
                'orders_active': orders_active,
                'users_active': users_active
            }
            
        except Exception as e:
            cls.log_error("Error al obtener estadísticas del bot", e)
            return {
                'messages_today': 0,
                'orders_active': 0,
                'users_active': 0
            }
    
    # ==========================================
    # UTILIDADES
    # ==========================================
    
    @classmethod
    def _format_uptime(cls, seconds: float) -> str:
        """
        Formatear uptime en formato legible.
        
        Args:
            seconds: Segundos de uptime
            
        Returns:
            String formateado (ej: "2h 30m", "45m", "3d 5h")
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        
        minutes = int(seconds / 60)
        if minutes < 60:
            return f"{minutes}m"
        
        hours = int(minutes / 60)
        remaining_minutes = minutes % 60
        if hours < 24:
            return f"{hours}h {remaining_minutes}m"
        
        days = int(hours / 24)
        remaining_hours = hours % 24
        return f"{days}d {remaining_hours}h"
