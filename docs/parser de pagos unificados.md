# Resumen de sesión — Ceiba21 · Ingesta de pagos y dashboard

**Fecha:** 12 de junio de 2026
**Foco:** estabilizar el pipeline de ingesta de pagos por IMAP (PayPal, Zelle, Wise, Binance), reconstruir la tabla `payments` y pulir el dashboard de pagos.

---

## 1. Reconstrucción de la tabla de pagos

- Se decidió **limpiar y reimportar** la tabla `payments` desde cero.
- Riesgos discutidos antes de borrar:
  - Los **pagos manuales** no se recuperan (no hay correo que reimportar).
  - La importación **solo lee el INBOX**: cualquier correo **archivado o borrado** en Gmail no vuelve.
- Procedimiento seguro: backup previo (`~/backup_database.sh`) → borrado vía contexto de la app (`Payment.query.delete()`) → reimport por **CLI** (`importar_historico.py`).
- **Resultado:** tabla reconstruida con **7.530 pagos, 0 manuales**, dedup-safe. El último barrido desde 10-jun dio "2 nuevos, 54 duplicados" (al día).

---

## 2. Robustez del pipeline IMAP (`app/services/gmail_service.py`)

Varios fallos encontrados y corregidos, en orden:

| Problema | Causa | Fix |
|---|---|---|
| `LookupError: unknown encoding: unknown-8bit` | Un header con charset MIME no estándar | `try/except LookupError` → fallback a `utf-8` tolerante en `_decode_header_value` |
| El marcado apuntaba al correo equivocado | Se usaban **números de secuencia** IMAP (se corren si entra correo nuevo) | Migración completa a **UID** en `search` / `fetch` / `store` (7 puntos) |
| Cuelgues sin cortar (timeout) | El `timeout` de `IMAP4_SSL()` solo cubre el connect en Py3.13 | `self._connection.socket().settimeout(IMAP_TIMEOUT)` tras conectar |
| Un correo trabado tumbaba todo el import | El `except` del bucle no capturaba `OSError` | Se añadió `OSError` al `except` por-correo en el histórico |
| Timeout marcando correo por correo | `mark_as_read` reconecta (login completo) por cada correo | `mark_multiple_as_read` (una conexión, un `STORE` en lote) |

---

## 3. Patrón de ejecución (lección reforzada)

- **Operaciones masivas IMAP van por CLI, nunca por HTTP**: el botón/endpoint corre bajo Gunicorn con timeout de 120 s y muere a mitad. El backfill grande va por terminal.
- Para sobrevivir caídas de SSH durante un import largo: `nohup ... &` (o `tmux`), no en primer plano (un `client_loop: send disconnect` mata el proceso atado a la sesión).
- La ingesta periódica corre por **cron** con `run_ingesta.py`.

---

## 4. Blindaje del botón "importar desde" (`payments_unified.py` + `unified_ingestion_service.py`)

- Rechazo de rangos de más de **7 días** atrás (responde con el comando CLI exacto a usar).
- Tope de **50 correos** más recientes por corrida HTTP (`limite` añadido a `procesar_desde_fecha`).
- **Marcado en lote** en `procesar_desde_fecha` (el cambio que finalmente eliminó el `WORKER TIMEOUT`: antes marcaba uno por uno con reconexión completa).

---

## 5. Diagnóstico Binance

- Existen **dos tipos** de correo de Binance:
  - **"Pago recibido"** (Binance Pay P2P) → el parser lo reclama pero fallaba la extracción del monto.
  - **"Depósito completado"** (USDT on-chain) → el parser **ni lo reconoce** (su asunto no matchea los marcadores).
- **Decisión:** por ahora **no** parsear los depósitos on-chain; lo que Binance captura hoy es suficiente.
- Aclaración de logs: `Correo no reconocido por ningún parser` (Binance) es **inofensivo** y esperado — distinto de `No se pudo extraer importe Binance` (ese sí es un parser que reclamó el correo pero no sacó el monto).

---

## 6. Diagnóstico PayPal — pago de "Vale Andre Ruiz"

- El parser **sí** procesa ese correo: `_limpiar_monto` maneja correctamente la **coma decimal europea** y los espacios no-rompibles (`\xa0`) — `$40,00 → 40.0`, comisión `$2,46 → 2.46`, total `$37,54 → 37.54`.
- El pago **estaba en la BD**: `Payment #987 | paypal | Vale Andre Ruiz | 40.00 USD | procesado | 2026-06-11 23:44:57`.
- El problema **no era el parser ni la ingesta**, sino el **ordenamiento del listado**.

---

## 7. Fix de ordenamiento del listado (`payments_unified.py`)

- Antes: `order_by(Payment.id.desc())`.
- Ahora: `order_by(Payment.fecha_pago.desc().nullslast(), Payment.id.desc())`.
- Razón: tras el import masivo, los `id` (y `created_at`) se asignaron por **orden de llegada del IMAP**, no por fecha. Un pago reciente (11-jun) quedó con `id` bajo (#987) y aparecía enterrado. `fecha_pago` es el campo correcto para cronología real. Validado: compila a `ORDER BY fecha_pago DESC NULLS LAST, id DESC`.

---

## 8. Página de servicios y título

- Se creó `app/templates/public/servicios.html` (resolvió el `TemplateNotFound: public/servicios.html` → 500 en `/servicios`).
- El título "Nuestros Servicios" quedaba **invisible en tema oscuro** (usaba `text-gray-900` fijo). Se cambió a `style="color: var(--color-text)"` (variable adaptativa de `style.css`), respetando `.clinerules`.

---

## 9. Pulidos menores

- Input "importar desde" por defecto en la **fecha de hoy** (`index()` pasa `hoy`, el template usa `value="{{ hoy }}"`) — *preparado*.
- (Antes de la compactación, en esta misma sesión): ingesta manual desde el dashboard, conversor de monedas (cross-rate), fix en `currency_service` (`initialize_for_trading`), y el paquete `app/utils` (`formato_eu` + filtro Jinja `eu`).

---

## Estado de despliegue

- **Desplegado y verificado:** reconstrucción de la tabla (7.530), fixes IMAP (charset / UID / timeout socket / OSError / marcado en lote), blindaje del import, ordenamiento por `fecha_pago`, `servicios.html` + título adaptativo.
- **Preparado, pendiente de aplicar:** fecha de hoy en el input "importar desde"; cron a 3 min.
- **Discutido y pausado por decisión:** el refactor de "retomar desde el último parseado".

---

## Decisión pendiente: resiliencia ante correos abiertos a mano

- **Problema:** la ingesta periódica busca solo `UNSEEN`. Si un correo se abre a mano en Gmail, deja de ser "no leído" y el barrido lo salta → se pierde.
- **Workaround disponible hoy:** **marcar el correo como no leído** de nuevo → entra en la siguiente corrida (el dedup garantiza que no se duplique si ya estaba).
- **Dato clave:** el botón "importar desde" ya hace lo de la **Opción A** (lee leídos + no leídos por fecha, con dedup), solo que manual.

| Aspecto | Actual (hoy) | Opción A — ventana + dedup | Opción B — cursor por UID |
|---|---|---|---|
| Criterio IMAP | `UNSEEN FROM …` | `SINCE fecha FROM …` (leídos y no leídos) | `UID último+1:* FROM …` |
| Cómo sabe qué procesó | Flag leído/no leído de Gmail | Dedup en la BD | Cursor del último UID |
| ¿Pierde abiertos a mano? | **Sí** | No (dentro de la ventana) | No |
| Tráfico IMAP | Mínimo | Alto (re-baja ~2 días por corrida) | Mínimo |
| Estado nuevo / infra | Ninguno | Ninguno (reusa la tabla) | Cursor en Redis o tabla |
| Complejidad | — | Baja | Media/alta (UIDVALIDITY, bootstrap) |

- **Recomendación dejada sobre la mesa:** Opción A para resolverlo ya; Opción B como optimización futura si el tráfico IMAP molesta.
- **Decisión actual:** dejar como está por el momento.

---

## Aprendizajes técnicos clave (para referencia / `.clinerules`)

- En IMAP, usar **UID** y nunca números de secuencia para `fetch`/`store` (las secuencias se corren si entra correo durante el barrido).
- El `timeout` de `IMAP4_SSL()` solo cubre el connect en Py3.13; hay que setearlo también en el **socket** para que aplique a `fetch`/`search`/`store`.
- **Marcar en lote** (una conexión) — nunca reconectar por correo (login completo por iteración = timeout garantizado en lotes grandes).
- El **flag leído/no leído de Gmail no es un buen "cursor" de procesamiento** (lo puede cambiar cualquier cliente); el **dedup por `message_id`/`transaction_id`** es la red de seguridad real.
- Decodificación de headers **tolerante a charset desconocido** (`unknown-8bit` → fallback utf-8).
- Ordenar listados por la **fecha de negocio** (`fecha_pago`), no por `id`/`created_at`, que tras un import masivo no reflejan la cronología.
- `_limpiar_monto` ya maneja **coma decimal europea** + `\xa0`; el formato es-CO de PayPal no requiere cambios.
- Operaciones IMAP en bloque → **CLI/cron**, no HTTP; usar `nohup`/`tmux` para sobrevivir caídas de SSH.

---

## Pendientes / próximos pasos (cuando convenga)

- Aplicar (si se desea) la fecha-de-hoy en el input y el cron a 3 min (con `flock` si se va por Opción A).
- Decidir Opción A vs B para la resiliencia ante correos abiertos a mano.
- Laterales mencionados a lo largo de la sesión: capa 3 del conversor (override por par + cross-rate al calculador para EUR), badge/filtro "Manuales", aplicar el filtro `eu` en `detalle_pago.html` y cotizaciones, verificar que contabilidad reciba todos los métodos, `DROP TABLE paypal_payments` legacy a futuro.
