#!/usr/bin/env python3
"""
Convertir logos SVG a PNG de alta calidad
"""
import cairosvg
from pathlib import Path

logos = [
    'app/static/img/logos/logo-telegram-channel.svg',
    'app/static/img/logos/logo-bot-avatar.svg',
    'app/static/img/logos/logo-web-horizontal.svg',
    'app/static/img/logos/logo-web-vertical.svg',
    'app/static/img/favicon.svg'
]

for svg_path in logos:
    svg_file = Path(svg_path)
    
    if not svg_file.exists():
        print(f"⚠️  No existe: {svg_path}")
        continue
    
    # PNG de alta resolución (para redes sociales)
    png_path = svg_file.with_suffix('.png')
    
    try:
        cairosvg.svg2png(
            url=str(svg_file),
            write_to=str(png_path),
            output_width=1024,  # Alta resolución
            output_height=1024
        )
        print(f"✅ Convertido: {png_path}")
    except Exception as e:
        print(f"❌ Error en {svg_path}: {e}")

# Favicon especial (16x16, 32x32, 48x48)
favicon_svg = Path('app/static/img/favicon.svg')
if favicon_svg.exists():
    for size in [16, 32, 48, 64]:
        favicon_png = Path(f'app/static/img/favicon-{size}.png')
        cairosvg.svg2png(
            url=str(favicon_svg),
            write_to=str(favicon_png),
            output_width=size,
            output_height=size
        )
        print(f"✅ Favicon {size}x{size}: {favicon_png}")

print("\n🎉 ¡Conversión completada!")
