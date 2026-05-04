"""
Servicio de Imágenes - Optimización y manejo de fotos.

RESPONSABILIDADES:
- Subida de imágenes
- Optimización automática
- Redimensionamiento
- Conversión a WebP
- Almacenamiento seguro
"""
from app.services.base_service import BaseService
from PIL import Image
import os
from werkzeug.utils import secure_filename
from typing import Tuple, Optional
import uuid
from datetime import datetime


class ImageService(BaseService):
    """
    Servicio para manejo de imágenes.
    """
    
    # Configuración
    UPLOAD_FOLDER = '/var/www/cotizaciones/app/static/uploads/blacklist'
    MAX_SIZE = (800, 800)  # Tamaño máximo en píxeles
    QUALITY = 85  # Calidad de compresión (1-100)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    @classmethod
    def allowed_file(cls, filename: str) -> bool:
        """Verificar si la extensión es permitida"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS
    
    @classmethod
    def optimize_and_save(cls, file, subfolder: str = '') -> Tuple[bool, str, Optional[str]]:
        """
        Optimizar y guardar imagen.
        
        Args:
            file: Archivo subido (FileStorage de Flask)
            subfolder: Subcarpeta opcional
            
        Returns:
            (success, message, url_relativa)
        """
        try:
            if not file or file.filename == '':
                return False, "No se proporcionó ningún archivo", None
            
            if not cls.allowed_file(file.filename):
                return False, "Tipo de archivo no permitido. Use: PNG, JPG, GIF o WebP", None
            
            # Crear carpeta si no existe
            upload_path = os.path.join(cls.UPLOAD_FOLDER, subfolder)
            os.makedirs(upload_path, exist_ok=True)
            
            # Generar nombre único
            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d')}.{ext}"
            filepath = os.path.join(upload_path, unique_filename)
            
            # Guardar archivo temporal
            file.save(filepath)
            
            # Abrir con PIL y optimizar
            with Image.open(filepath) as img:
                # Convertir RGBA a RGB si es necesario
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Redimensionar si es muy grande
                if img.size[0] > cls.MAX_SIZE[0] or img.size[1] > cls.MAX_SIZE[1]:
                    img.thumbnail(cls.MAX_SIZE, Image.Resampling.LANCZOS)
                
                # Convertir a WebP para mejor compresión
                webp_filename = unique_filename.rsplit('.', 1)[0] + '.webp'
                webp_filepath = os.path.join(upload_path, webp_filename)
                
                # Guardar optimizado
                img.save(webp_filepath, 'WEBP', quality=cls.QUALITY, optimize=True)
            
            # Eliminar archivo original si se convirtió a WebP
            if ext != 'webp':
                os.remove(filepath)
                final_filename = webp_filename
            else:
                final_filename = unique_filename
            
            # URL relativa para la BD
            relative_url = f"/static/uploads/blacklist/{subfolder}/{final_filename}".replace('//', '/')
            
            cls.log_action('image_uploaded', {
                'filename': final_filename,
                'path': relative_url
            })
            
            return True, "Imagen subida y optimizada exitosamente", relative_url
            
        except Exception as e:
            cls.log_error('image_upload_failed', str(e))
            return False, f"Error al procesar imagen: {str(e)}", None
    
    @classmethod
    def delete_image(cls, url: str) -> Tuple[bool, str]:
        """
        Eliminar imagen del servidor.
        
        Args:
            url: URL relativa de la imagen
            
        Returns:
            (success, message)
        """
        try:
            if not url:
                return True, "No hay imagen para eliminar"
            
            # Construir path absoluto
            # URL es tipo: /static/uploads/blacklist/foto.webp
            # Path debe ser: /var/www/cotizaciones/app/static/uploads/blacklist/foto.webp
            relative_path = url.replace('/static/', '')
            full_path = os.path.join('/var/www/cotizaciones/app/static', relative_path)
            
            if os.path.exists(full_path):
                os.remove(full_path)
                cls.log_action('image_deleted', {'path': url})
                return True, "Imagen eliminada"
            else:
                return False, "Imagen no encontrada"
                
        except Exception as e:
            cls.log_error('image_delete_failed', str(e))
            return False, f"Error al eliminar imagen: {str(e)}"
    
    @classmethod
    def get_file_size_mb(cls, filepath: str) -> float:
        """Obtener tamaño de archivo en MB"""
        try:
            return os.path.getsize(filepath) / (1024 * 1024)
        except:
            return 0.0