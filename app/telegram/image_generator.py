"""
Generador de imágenes para publicaciones de Telegram
Crea imágenes profesionales con las cotizaciones del día
"""
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os

class TelegramImageGenerator:
    """Genera imágenes para publicar en Telegram"""
    
    def __init__(self):
        self.width = 1080
        self.height = 1080
        self.bg_color = (26, 26, 26)  # Negro Ceiba21
        self.yellow = (247, 217, 23)  # Amarillo Ceiba21
        self.white = (255, 255, 255)
        self.gray = (180, 188, 197)
        
    def generate_quotes_image(self, quotes_data, custom_image_path=None):
        """
        Genera imagen de cotizaciones
        
        Args:
            quotes_data: Lista de diccionarios con {name, rate}
            custom_image_path: Ruta opcional de imagen publicitaria personalizada
        
        Returns:
            str: Ruta de la imagen generada
        """
        # Crear lienzo
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Si hay imagen personalizada, usarla como fondo superior
        if custom_image_path and os.path.exists(custom_image_path):
            try:
                custom_img = Image.open(custom_image_path)
                custom_img = custom_img.resize((1080, 400))
                img.paste(custom_img, (0, 0))
                start_y = 420
            except Exception as e:
                print(f"Error cargando imagen personalizada: {e}")
                start_y = 100
        else:
            start_y = 100
            
        # Logo/Título (si no hay imagen personalizada)
        if not custom_image_path:
            try:
                # Intentar cargar logo
                logo_path = 'app/static/img/favicon.svg'
                # Como SVG es complejo, dibujamos el texto
                font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 80)
                draw.text((self.width//2, 60), 'CEIBA21', fill=self.yellow, 
                         font=font_title, anchor='mm')
            except:
                # Fallback si no hay fuente
                draw.text((self.width//2, 60), 'CEIBA21', fill=self.yellow, anchor='mm')
        
        # Fecha y hora
        try:
            font_date = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
        except:
            font_date = ImageFont.load_default()
            
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((self.width//2, 140), now, 
                 fill=self.gray, font=font_date, anchor='mm')
        
        # Título de cotizaciones
        try:
            font_subtitle = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 48)
        except:
            font_subtitle = ImageFont.load_default()
            
        draw.text((self.width//2, start_y + 80), 'MEJORES TASAS DEL MERCADO', 
                 fill=self.white, font=font_subtitle, anchor='mm')
        
        # Línea decorativa
        line_y = start_y + 130
        draw.rectangle([(200, line_y), (880, line_y + 4)], fill=self.yellow)
        
        # Cotizaciones (máximo 6)
        try:
            font_quote = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 42)
            font_rate = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 46)
        except:
            font_quote = font_rate = ImageFont.load_default()
        
        quote_y = line_y + 60
        max_quotes = min(6, len(quotes_data))
        
        for i, quote in enumerate(quotes_data[:max_quotes]):
            # Fondo de tarjeta
            card_y = quote_y + (i * 100)
            draw.rectangle([(150, card_y), (930, card_y + 80)], 
                          fill=(45, 45, 45), outline=self.yellow, width=3)
            
            # Nombre del método (sin emoji)
            draw.text((180, card_y + 40), quote['name'], 
                     fill=self.white, font=font_quote, anchor='lm')
            
            # Tasa (sin signo $)
            currency_symbol = quote.get('currency', 'USD')
            draw.text((900, card_y + 40), f"{quote['rate']:.2f} {currency_symbol}", 
                     fill=self.yellow, font=font_rate, anchor='rm')
        
        # Footer con branding
        footer_y = self.height - 100
        try:
            font_footer = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 36)
        except:
            font_footer = ImageFont.load_default()
            
        draw.text((self.width//2, footer_y), 'La mejor tasa del mercado', 
                 fill=self.yellow, font=font_footer, anchor='mm')
        draw.text((self.width//2, footer_y + 50), 'Contáctanos: ceiba21.com', 
                 fill=self.gray, font=font_footer, anchor='mm')
        
        # Guardar imagen
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'app/static/img/telegram_posts/cotizaciones_{timestamp}.png'
        img.save(output_path, 'PNG', quality=95)
        
        return output_path
    
    def validate_custom_image(self, file_path):
        """Valida que la imagen personalizada sea correcta"""
        try:
            img = Image.open(file_path)
            # Verificar dimensiones razonables
            if img.width < 500 or img.height < 300:
                return False, "Imagen muy pequeña (mínimo 500x300px)"
            return True, "OK"
        except Exception as e:
            return False, f"Error: {str(e)}"
