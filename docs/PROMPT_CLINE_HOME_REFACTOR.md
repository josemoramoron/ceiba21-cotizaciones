# Prompt Profesional para Cline — Refactor Frontend Home
**Proyecto:** Ceiba21-Cotizaciones  
**Stack:** Flask 3.1 + PostgreSQL + SQLAlchemy + Tailwind CSS + Python 3.13  
**Fecha:** Mayo 2026

---

## ✅ PROMPT DEPURADO (cómo debería haberse pedido desde el inicio)

```
Necesito modificar la página de inicio (home) del sitio público. 
Lee primero estos archivos antes de escribir cualquier código:

- app/routes/public.py
- app/templates/public/home.html
- app/templates/public_base.html
- app/services/quote_service.py

### CAMBIOS REQUERIDOS

#### 1. Navbar fija al hacer scroll
Archivo: app/templates/public_base.html
- Agregar position: sticky; top: 0; z-index: 100; al elemento <nav>
- Usar clase específica .site-nav en lugar del selector genérico nav {}
  para no afectar otros elementos del DOM

#### 2. Card "Resumen de Cotizaciones" con datos reales
Archivos: app/routes/public.py + app/templates/public/home.html

En app/routes/public.py, modificar la función home() para:
- Consultar QuoteService.get_quotes_matrix()
- Filtrar los métodos: paypal, zelle, usdt, zinli, wise
- Construir una lista hero_quotes con estructura PLANA (ver regla Jinja2)
- Pasar hero_quotes al template

Estructura correcta del objeto (datos planos, sin diccionarios anidados):
  row = {
      'name': pm['name'],   # string
      'code': pm['code'],   # string
      'ves':  float,        # valor en bolívares
      'cop':  float,        # valor en pesos colombianos
  }

En app/templates/public/home.html:
- Renombrar el card de "Cotizaciones en Tiempo Real" a "Resumen de Cotizaciones"
- Mostrar columnas: Método | Bs (VES) | $ (COP)
- Usar notación de punto en Jinja2: {{ q.ves }}, {{ q.cop }}
- El card debe ser visible tanto en desktop como en móvil (quitar hidden md:block)
- Agregar botón "Compartir" que copie las cotizaciones como texto

#### 3. Barra de navegación fija en móvil (solo responsive)
Archivo: app/templates/public_base.html
- Agregar una barra fija en el borde inferior SOLO en móvil (md:hidden)
- Dos botones: "Ver Cotizaciones" y "Calculadora"
- Iconos Font Awesome con color #F7D917
- Agregar padding inferior al body para que el contenido no quede tapado

#### 4. Refactor CSS — eliminar conflictos con Tailwind
Archivo: app/templates/public_base.html

PROBLEMA: Existen reglas CSS con selectores genéricos y !important que
sobreescriben las clases de Tailwind en toda la página:
  nav { background-color: white !important; }   ← mata fondos de secciones
  body { background-color: white !important; }  ← impide fondos oscuros
  nav a { color: #1A1A1A !important; }          ← afecta links de todo el DOM

SOLUCIÓN:
- Reemplazar nav {} por .site-nav {} (clase específica)
- Eliminar body { background-color: white !important }
- Eliminar Bootstrap 5 del base.html del dashboard (duplica con Tailwind)
- Mover los colores Ceiba21 a la config de Tailwind:
  window.tailwind = { config: { theme: { extend: { colors: {
      'ceiba-yellow': '#F7D917',
      'ceiba-black':  '#1A1A1A'
  }}}}}

#### 5. Corrección de bug JS
Archivo: app/templates/public_base.html
- Existe un error: document.getElementById('mobile-menu-btn') 
  El ID real en el HTML es 'menuToggle', no 'mobile-menu-btn'
- Corregir a: document.getElementById('menuToggle')

### REGLAS DE ARQUITECTURA A RESPETAR
- Routes solo orquestan: reciben request → llaman service → retornan template
- Services contienen toda la lógica de negocio
- Templates NO construyen datos, solo muestran lo que reciben del route
- NO mezclar lógica Python en templates Jinja2

### REGLA CRÍTICA JINJA2 — DICCIONARIOS
En Jinja2, NUNCA acceder a claves de diccionario con corchetes desde el template:
  ❌ {{ q.values['VES'] }}     → Error: ambigüedad con método values()
  ❌ {% if q.values.get('VES', 0) > 0 %}  → Error: .get() no existe en Jinja2
  ✅ {{ q.ves }}               → Correcto: atributo plano
  ✅ {{ q.values.VES }}        → Correcto si es necesario anidar

La solución es construir los datos PLANOS en el route (Python),
no en el template (Jinja2).

### NO HACER
- No usar Bootstrap si ya existe Tailwind — generan conflictos
- No usar selectores CSS genéricos (nav, body, a) con !important
- No construir diccionarios anidados que se accedan desde el template
- No duplicar reglas CSS (hover-row aparecía dos veces)
```

---

## 📚 Lecciones aprendidas — Errores comunes documentados

### Error 1: Selector CSS genérico con !important
**Síntoma:** Toda la página pierde estilos, Tailwind no aplica, fondos oscuros desaparecen.  
**Causa:** `nav { background-color: white !important }` en el `<style>` global sobreescribe **cualquier** elemento `<nav>` del DOM, incluidas secciones con fondo negro.  
**Solución:** Siempre usar clases específicas: `.site-nav {}` en lugar de `nav {}`.

### Error 2: Quirks Mode por DOCTYPE roto
**Síntoma:** El navegador renderiza sin CSS moderno, Tailwind no carga (solo 1 request en Red).  
**Causa:** Cualquier carácter o línea en blanco **antes** de `<!DOCTYPE html>` activa Quirks Mode.  
**Solución:** Verificar que `<!DOCTYPE html>` sea la primera línea absoluta del archivo.

### Error 3: Acceso a diccionarios en Jinja2 con corchetes
**Síntoma:** `UndefinedError: 'builtin_function_or_method object' has no attribute 'VES'`  
**Causa:** `q.values['VES']` en Jinja2 se interpreta como llamar el método `.values()` de Python, no como acceso a clave.  
**Solución:** Pasar datos planos desde el route. Usar notación de punto `q.ves`.

### Error 4: .get() de Python en templates Jinja2
**Síntoma:** `UndefinedError: 'builtin_function_or_method object' has no attribute 'get'`  
**Causa:** Jinja2 no es Python puro. `.get()` es un método Python que no existe en el contexto de Jinja2.  
**Solución:** Usar el operador `| default(0)` de Jinja2, o mejor aún, construir los datos con defaults en el route.

### Error 5: ID de elemento JS incorrecto
**Síntoma:** `TypeError: Cannot read properties of null (reading 'addEventListener')`  
**Causa:** `document.getElementById('mobile-menu-btn')` pero el elemento tiene `id="menuToggle"`.  
**Solución:** Siempre verificar que el ID en el JS coincida exactamente con el ID en el HTML. Usar `?.addEventListener` para evitar crashes si el elemento no existe.

### Error 6: Bootstrap + Tailwind en el mismo archivo
**Síntoma:** Estilos inconsistentes, clases que no aplican como se espera.  
**Causa:** Bootstrap tiene su propio sistema de grilla y reset CSS que interfiere con Tailwind.  
**Solución:** Elegir uno. En este proyecto Tailwind es el estándar — Bootstrap fue eliminado del dashboard.

---

## 🏗️ Funcionalidades implementadas en esta sesión

### 1. `app/routes/public.py` — home() con datos reales
```python
@public_bp.route('/')
def home():
    matrix = QuoteService.get_quotes_matrix()
    HERO_METHODS = ['paypal', 'zelle', 'usdt', 'zinli', 'wise']
    hero_quotes = []
    for pm in matrix['payment_methods']:
        if pm['code'].lower() not in HERO_METHODS:
            continue
        row = {
            'name': pm['name'],
            'code': pm['code'],
            'ves':  matrix['quotes'].get(pm['code'], {}).get('VES', {}).get('value', 0),
            'cop':  matrix['quotes'].get(pm['code'], {}).get('COP', {}).get('value', 0),
        }
        hero_quotes.append(row)
    order = {code: i for i, code in enumerate(HERO_METHODS)}
    hero_quotes.sort(key=lambda x: order.get(x['code'].lower(), 99))
    return render_template('public/home.html', hero_quotes=hero_quotes)
```

### 2. `app/templates/public_base.html` — cambios estructurales
- ✅ Navbar sticky con clase `.site-nav`
- ✅ Barra móvil fija en borde inferior (md:hidden)
- ✅ CSS reorganizado sin selectores genéricos peligrosos
- ✅ Colores Ceiba21 en config de Tailwind
- ✅ Bug JS corregido (mobile-menu-btn → menuToggle)
- ✅ Bootstrap eliminado

### 3. `app/templates/base.html` (dashboard) — cambios
- ✅ Bootstrap eliminado (CSS + JS)
- ✅ Navbar del dashboard con colores Ceiba21 (#1A1A1A + #F7D917)
- ✅ Sidebar con hover amarillo en lugar de morado
- ✅ Navbar sticky

### 4. `app/templates/public/home.html` — cambios
- ✅ Card renombrado a "Resumen de Cotizaciones"
- ✅ Datos reales desde BD (PayPal, Zelle, USDT, Zinli, Wise)
- ✅ Columnas: Bs (VES) y $ (COP)
- ✅ Card visible en móvil Y desktop
- ✅ Botón "Compartir" — copia texto formateado al portapapeles
- ✅ Fallback para navegadores sin Clipboard API
- ✅ Botones "Ver Cotizaciones" y "Calcular" ocultos en móvil (reemplazados por barra fija)

---

## 📐 Patrón de prompt recomendado para Cline

### Estructura base
```
## Contexto
[descripción breve del módulo a modificar]

## Lee primero
[lista de archivos a leer antes de escribir código]

## Cambios requeridos
### Archivo: [ruta exacta]
- [cambio específico y medible]
- [otro cambio]

## Estructura de datos esperada
[ejemplo concreto del objeto/diccionario que debe fluir entre capas]

## Restricciones
- [qué NO hacer]
- [qué tecnología NO usar]

## Cómo probarlo
[comando o URL para verificar que funcionó]
```

### Principios de un buen prompt para Cline
1. **Dar contexto de arquitectura** — Cline necesita saber la capa en la que trabaja (route/service/template)
2. **Especificar archivos exactos** — nunca decir "el template de inicio", decir `app/templates/public/home.html`
3. **Mostrar la estructura de datos esperada** — un ejemplo del objeto que viaja entre capas elimina ambigüedad
4. **Declarar restricciones explícitas** — "no usar Bootstrap", "no usar !important en selectores genéricos"
5. **Un cambio por prompt cuando sea posible** — los cambios multi-archivo son difíciles de depurar
6. **Incluir cómo probarlo** — `flask run` + URL + qué debería verse
7. **Hacer checkpoint git antes** — `git commit -m "checkpoint antes de X"` como paso 0 explícito

---

*Documento generado con Claude — Mayo 2026*
