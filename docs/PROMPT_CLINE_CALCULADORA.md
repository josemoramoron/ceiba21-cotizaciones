# Prompt Cline — Refactor Calculadora PayPal
**Fecha**: Mayo 2026  
**Archivo afectado**: `app/templates/public/calculadora.html`  
**Capa**: View (Jinja2 / HTML + JS)  
**Tipo de cambio**: Mejora UX — sin impacto en backend

---

## Contexto

La calculadora de comisiones PayPal (`/calculadora`) tenía dos contenedores
independientes lado a lado (grid 2 columnas): uno para **Recibir Pago** y otro
para **Enviar Pago**.

Se realizaron tres mejoras exclusivamente en la capa **View**, respetando la
arquitectura MVC del proyecto (Routes → Services → Models):

---

## Cambios realizados

### 1. Unificación en un solo contenedor con tabs

**Problema**: Dos tarjetas separadas consumían mucho espacio horizontal y
obligaban al usuario a comparar visualmente entre columnas.

**Solución**: Un único contenedor `max-w-xl` centrado con dos pestañas en el
header:
- `↓ Recibir Pago` (activo por defecto)
- `↑ Enviar Pago`

Cada tab muestra su panel correspondiente con animación `fadeSlideIn`.
Un indicador deslizante amarillo (`#F7D917`) marca el tab activo.

**Archivos modificados**:
- `app/templates/public/calculadora.html` — único archivo tocado

**Archivos NO modificados** (correcta separación MVC):
- `app/routes/public.py` — sin cambios
- `app/services/calculator_service.py` — sin cambios
- `app/models/` — sin cambios

---

### 2. Selector de moneda con opción default neutra

**Problema**: El `<select>` iniciaba en `USD - Dólar`, dando por sentada una
elección del usuario sin que este la hubiera hecho.

**Solución**: Primera opción deshabilitada:
```html
<option value="" disabled selected>— Seleccionar moneda —</option>
```

Esto obliga al usuario a elegir conscientemente y desencadena el flujo correcto
de visibilidad del botón WhatsApp (ver cambio 3).

**Impacto en JS**: Las funciones `calculateReceive()` y `calculateSend()`
ahora evalúan tres estados posibles del selector:

| Valor del select | Conversión | Botón WA |
|---|---|---|
| `""` (sin selección) | oculta | oculto |
| `"USD"` | oculta | visible |
| Otra moneda (`VES`, `BRL`…) | visible | visible |

---

### 3. Botón "Hablar con un asesor" con aparición condicional

**Problema**: No existía un canal directo desde la calculadora hacia el equipo
de Ceiba21.

**Solución**: Botón verde WhatsApp que:
1. **Está oculto** mientras no se seleccione moneda (`max-height: 0; opacity: 0`)
2. **Aparece con animación suave** (`max-height` + `opacity` transition) al
   elegir cualquier moneda
3. **Construye dinámicamente** el mensaje con los resultados del panel activo:

```
Hola 👋 Quiero consultar sobre la siguiente operación:

📥 *Recibir Pago PayPal*
━━━━━━━━━━━━━━━━━━
Monto enviado:    $106.03
Comisión PayPal:  $6.03
Recibes neto:     $100.00

💱 *Conversión a VES*
Cotización:  630.59
Monto VES:   63.059,00

¿Me pueden ayudar? 🙏
```

El mensaje se pasa via `encodeURIComponent` al parámetro `text=` de la API
de WhatsApp: `https://api.whatsapp.com/send/?phone=NUMERO&text=...`

**Número configurable**: Variable `WA_NUMBER` en el bloque `<script>` del
template — una sola línea a editar cuando se cambie el número.

---

## Lógica JS relevante (capa View)

Toda la lógica vive en el `<script>` del template. No se crearon endpoints
nuevos ni se tocó ningún service. Las funciones clave:

```javascript
switchTab(tab)         // Alterna entre 'receive' y 'send'
calculateReceive()     // Calcula comisiones + controla visibilidad WA
calculateSend()        // Ídem para modo envío
openWhatsApp(mode)     // Construye URL con mensaje y abre nueva pestaña
```

---

## Cómo probar localmente

```bash
# 1. Activar entorno virtual
venv\Scripts\activate

# 2. Correr la app
flask run

# 3. Navegar a:
http://localhost:5000/calculadora

# Verificar:
# ✅ Los tabs conmutan correctamente
# ✅ El selector inicia en "— Seleccionar moneda —"
# ✅ El botón WA está oculto hasta elegir moneda
# ✅ Al elegir moneda, el botón aparece con animación
# ✅ Al pulsar el botón, WhatsApp abre con el mensaje pre-llenado
# ✅ El mensaje incluye conversión si la moneda no es USD
```

---

## Deploy

```bash
git add app/templates/public/calculadora.html
git commit -m "feat: calculadora unificada con tabs, selector neutro y botón WhatsApp asesor"
git push origin master
ssh ceiba21-local-webmaster "/var/www/cotizaciones/deploy.sh"
```

---

## Notas para Cline

- Este cambio es **solo de presentación** — no requiere migraciones ni
  nuevas dependencias
- Si en el futuro se quiere que el número de WhatsApp venga de la BD,
  el punto de entrada es `app/services/` (crear un `contact_service.py`
  o agregarlo a `notification_service.py`) y pasarlo al template desde
  `app/routes/public.py` como variable de contexto
- El patrón de tabs podría reutilizarse en otras páginas públicas
  siguiendo la misma estructura CSS + `switchTab()`
