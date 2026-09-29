# Ceiba21 — Sidebar Tablet, Tipografía DejaVu Sans y Fix CSRF Calculadora

_Fecha del resumen: 29 de septiembre de 2026 · Última edición de código en este chat: 21 de septiembre de 2026_

## Contexto

Al arrancar esta sesión, la Fase 4 de pulido responsive del panel admin ya estaba deployada: `.dash-main{min-width:0}`, overflow-x en tablas, sidebar como drawer en tablet por ancho (`min-width:1024px`, commit `a73fb57`), addendum de `/dashboard/sms` (`287928a`) y el reemplazo de la tarjeta "Operadores" por "Pagos" (`e5fff8e`) — todo confirmado por Jose en dispositivos reales.

Cuatro hilos quedaron abiertos y se resolvieron en esta sesión:

1. **Sidebar en tablet grande**: Jose probó su Xiaomi Pad 6 Pro en landscape (1440×990px CSS) y el sidebar seguía estático, porque 1440px supera el umbral de 1024px fijado en el fix anterior. Pidió el criterio de "toda tablet", sin importar el ancho.
2. **Tipografía del sitio**: Jose vio una tipografía en unas capturas de pantalla de verificación que le gustó más que la que usa normalmente en Windows, y pidió aplicarla a todo el sitio (admin y público).
3. **Bloqueo de git**: los intentos de commit fallaban repetidamente con `.git/index.lock` / `HEAD.lock` — diagnosticado en un primer momento (de forma incorrecta) como un proceso de Windows reteniendo el archivo.
4. **Bug reportado por Jose**: al dejar la pestaña de la calculadora pública abierta un rato y luego ingresar un cálculo, aparecía un aviso rojo "No se pudo calcular en este momento" sin explicación, y Jose sospechaba que tenía que ver con CSRF.

## Cambios implementados

### 1. `app/templates/base.html` — sidebar estático solo con mouse/trackpad

**Problema**: la media query de sidebar estático usaba solo `min-width:1024px`, que no distingue una tablet grande en landscape (Xiaomi Pad 6 Pro 1440px, iPad Pro 12.9" 1366px) de una laptop real — ambas caen en el mismo rango de ancho.

**Solución**: se agregó `and (hover: hover) and (pointer: fine)` a la media query existente, de forma que el criterio real pase a ser "hay un mouse/trackpad fino como input primario" en vez de solo el ancho de pantalla. Verificado con Playwright (`has_touch`) en 8 combinaciones ancho×touch.

**Commit**: `8776131`

### 2. `app/static/css/tokens.css` + `app/static/fonts/DejaVuSans.woff2` / `DejaVuSans-Bold.woff2` — tipografía site-wide

**Problema**: Jose pidió aplicar en todo el sitio (admin y público) la tipografía vista en las capturas de verificación. Investigando, resultó ser DejaVu Sans (el `sans-serif` por defecto del entorno Linux/Chromium usado para generar esas capturas) — no la de eservicios.org/e-link (Inter + Plus Jakarta Sans), que se había evaluado primero como candidata.

**Solución**: nueva variable `--font-sans` con dos `@font-face` (400 y 700) apuntando a `.woff2` autohospedados (convertidos con `fonttools` desde los `.ttf` que ya estaban en el repo para las imágenes de Telegram), aplicada vía `body, body.font-sans { font-family: var(--font-sans); }` en `tokens.css` — el único CSS compartido entre `base.html` (admin) y `public_base.html` (público). Verificado visualmente en el dashboard admin y en la página pública de Cotizaciones.

**Commit**: `8776131` (mismo commit que el punto 1)

### 3. Diagnóstico del bloqueo de git (`.git/index.lock`, `.git/HEAD.lock`)

**Problema**: `git commit` fallaba repetidamente con "Unable to create index.lock: File exists". El diagnóstico inicial (un proceso de Windows como OneDrive, antivirus o VS Code reteniendo el archivo) resultó incorrecto.

**Causa real**: el puente remoto usado para editar el repo bloquea el borrado de archivos por defecto en carpetas conectadas, como medida de seguridad — por eso `mv` funcionaba pero `rm` fallaba con "Operation not permitted", y por eso git no podía limpiar sus propios locks ni sus objetos temporales internos.

**Solución**: se solicitó y obtuvo el permiso de borrado para la carpeta del repo (válido el resto de esa sesión). No fue necesario cerrar ningún proceso en Windows.

*(Hallazgo operativo de la sesión, no un cambio de código.)*

### 4. `app/templates/public/calculadora.html` — distinguir token CSRF vencido de error de red

**Problema**: al dejar la pestaña de la calculadora pública abierta más de una hora, el siguiente cálculo mostraba "No se pudo calcular en este momento." sin explicación. Investigando: el token CSRF vive en `<meta name="csrf-token">`, generado una sola vez al cargar la página; Flask-WTF lo expira solo (`WTF_CSRF_TIME_LIMIT`, default 3600s = 1h, sin override en este proyecto); y al vencer, responde una página HTML 400 (no hay `errorhandler` propio para `CSRFError`), lo que rompía el `.then(r => r.json())` del frontend y caía al `.catch()` genérico.

**Solución**: el `fetch()` ahora chequea `response.ok` antes de intentar `response.json()`. Si no es `ok`, se asume token vencido y se muestra un mensaje específico ("Esta pestaña llevaba un rato abierta y venció por seguridad. Recargá la página para seguir calculando.") junto con un botón **Recargar página** (nuevo elemento, oculto por defecto, controlado por un segundo parámetro `showReload` en `_showConvError()`). El error de red genuino (la promesa del fetch se rechaza directamente) sigue mostrando el mensaje genérico sin botón. Verificado con un harness Jinja2+Playwright simulando los 3 casos (token vencido, fallo de red, cálculo exitoso).

**Commit**: `67cef5f`

### 5. `.clinerules` (repo + copia en el proyecto de Claude) — nueva regla de ingeniería

**Problema**: sin una regla documentada, el mismo patrón de bug (token CSRF vencido sin manejo específico) podía repetirse en cualquier input público futuro basado en `fetch()`.

**Solución**: se agregó la sección "Reglas de inputs públicos con fetch() + CSRF", con el patrón obligatorio (chequear `response.ok` antes de `response.json()`, distinguir token vencido de fallo de red real, ofrecer siempre una salida clara con botón de recargar), citando la calculadora como implementación de referencia.

**Commit**: `1c69e0d`

## Decisiones de diseño

- **`hover`/`pointer` en vez de un breakpoint de ancho mayor**: ningún ancho fijo alcanza, porque tablets grandes en landscape se solapan con anchos de laptop reales. `(hover: hover) and (pointer: fine)` detecta la capacidad real del dispositivo (input táctil vs. mouse/trackpad), independiente del tamaño de pantalla.
- **Autohospedar DejaVu Sans en vez de Google Fonts CDN**: mismo motivo que la migración previa de Tailwind (CDN → build local) — `fonts.googleapis.com`/`fonts.gstatic.com` no son alcanzables desde algunas redes de la región. Se reutilizaron los `.ttf` ya empaquetados para las imágenes de Telegram en vez de traer una fuente nueva, minimizando el peso agregado al repo.
- **`body, body.font-sans` (selector doble) en vez de `!important`**: gana por especificidad CSS pura (0,1,1 contra el 0,1,0 del `.font-sans` de Tailwind), respetando la regla de `.clinerules` de nunca usar `!important` para resolver conflictos de estilos.
- **Chequear `response.ok` en vez de parsear el HTML de error para identificar el CSRF vencido específicamente**: no hay forma barata de distinguir un CSRF vencido de otro 4xx/5xx sin parsear la página de error completa. Se trata cualquier respuesta no-ok como "posible sesión vencida" — la peor consecuencia es un mensaje ligeramente impreciso en un caso raro, contra la alternativa de mantener el mensaje mudo que ya existía.
- **Fix en el frontend, sin `errorhandler` global de `CSRFError` en el backend**: un manejador global sería la solución arquitectónicamente "completa", pero implicaría decidir ahora el formato de respuesta JSON para ese error en *todos* los endpoints del proyecto — alcance mayor al pedido. El fix quedó acotado a una sola pantalla pública, sin tocar Services/Models.

## Prompt Cline generado

No aplica en esta sesión. Todos los cambios se aplicaron directamente sobre el repo de Jose a través del puente remoto, con scripts Python de lectura-modificación-escritura (con `assert` de verificación) y `git commit` directo — sin pasar por un prompt intermedio para Cline en VS Code, ya que por ahora Jose trabaja solo en Claude.ai.

## Estado final y próximos pasos

Tres commits generados en esta sesión, en orden: `8776131` (sidebar hover/pointer + tipografía DejaVu Sans), `67cef5f` (fix CSRF de la calculadora), `1c69e0d` (regla nueva en `.clinerules`).

**Pendiente inmediato**: Jose debe correr la suite de tests, hacer `git push origin master` y el deploy SSH de esos tres commits — a la fecha de este resumen todavía no se pushearon ni deployaron.

**Dato operativo para el futuro**: el bloqueo de "carpeta protegida contra borrado" del puente remoto puede repetirse en cualquier sesión futura que edite este repo vía el bridge; la solución conocida es pedir el permiso de borrado para la carpeta, no cerrar procesos de Windows.

**Mejoras futuras opcionales (no bloqueantes)**:

- Si se agregan más inputs públicos con `fetch()`, aplicar desde el diseño inicial el patrón ya documentado en `.clinerules`.
- Evaluar, bajo demanda, si conviene subir `WTF_CSRF_TIME_LIMIT` para páginas públicas de larga permanencia, además del manejo de UI ya aplicado — es una decisión de producto, no técnica.
- Sigue pendiente el rollout manual de `SMS_WEBHOOK_TOKEN` (heredado de fases anteriores, no tocado en esta sesión).
- Sigue abierta la entrevista del índice maestro global (legal Colombia/Venezuela + marketing), pausada por Jose para priorizar este trabajo técnico.

## Fechas

- **Última edición de código en este chat**: 21 de septiembre de 2026 (los tres commits `8776131`, `67cef5f`, `1c69e0d`).
- **Última edición de este documento**: 29 de septiembre de 2026 (fecha de creación de este resumen).
