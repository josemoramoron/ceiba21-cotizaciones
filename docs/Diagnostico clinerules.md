# Diagnóstico de Buenas Prácticas — Ceiba21-Cotizaciones
**Proyecto:** Ceiba21-Cotizaciones  
**Referencia:** `.clinerules` del proyecto  
**Fecha:** Junio 2026  
**Origen:** Diagnóstico post-sesión `feat/paypal-gmail-ingesta-automatica`

---

## 1. Resumen Ejecutivo

Durante la implementación del sistema de ingesta automática de pagos PayPal se identificaron violaciones a las reglas definidas en `.clinerules`. Este documento consolida todos los hallazgos en dos categorías: **deuda técnica nueva** (introducida en la sesión de PayPal) y **deuda técnica preexistente** (anterior a esa sesión).

---

## 2. Reglas de `.clinerules` como Referencia

```
1. Python 3.13 con Type Hints en todas las funciones
2. PEP 8: snake_case para funciones/variables, PascalCase para clases
3. Docstrings en formato Google para funciones públicas
4. Funciones que superen 60 líneas → separar en módulo independiente
5. Nunca except: pass — capturar excepciones específicas
6. No mezclar lógica de negocio en routes — va en services/
7. Routes NUNCA llaman directamente a Models (siempre vía Services)
8. CSS: nunca !important para tema, colores via variables CSS
9. Templates: sin lógica Python, solo presentación
```

---

## 3. Deuda Técnica Nueva (sesión PayPal)

### 3.1 Funciones que superan 60 líneas

**Regla violada:** _"Si una función supera 60 líneas sepárala en un módulo independiente"_

| Archivo | Función | Líneas | Acción recomendada |
|---|---|---|---|
| `app/services/gmail_service.py` | `get_new_paypal_payments()` | 99 | Extraer `_fetch_email_by_uid()` y `_parse_raw_message()` como helpers privados |
| `app/services/paypal_parser_service.py` | `parse_email()` | 186 | Extraer `_parse_montos()`, `_parse_transaccion()`, `_parse_direccion()` como métodos privados |
| `app/services/payment_ingestion_service.py` | `procesar_nuevos_pagos()` | 93 | Extraer `_build_resultado()` como helper privado |
| `app/services/payment_ingestion_service.py` | `_procesar_correo()` | 102 | Extraer `_crear_pago_desde_datos()` como helper privado |

**Impacto:** Baja legibilidad, dificulta testing unitario, viola el principio de responsabilidad única.

---

### 3.2 `except Exception` genéricos

**Regla violada:** _"Nunca uses except: pass — captura excepciones específicas con respuestas claras"_

#### `app/services/gmail_service.py` — 6 instancias

```python
# ACTUAL (incorrecto):
except Exception as e:
    logger.error(f"Error conectando Gmail IMAP: {e}")

# CORRECTO:
except imaplib.IMAP4.error as e:
    logger.error(f"Error autenticando Gmail IMAP: {e}")
except ConnectionRefusedError as e:
    logger.error(f"No se pudo conectar al servidor IMAP: {e}")
except OSError as e:
    logger.error(f"Error de red conectando a Gmail: {e}")
```

Excepciones específicas a usar en `gmail_service.py`:
- `imaplib.IMAP4.error` — errores del protocolo IMAP
- `imaplib.IMAP4.abort` — conexión abortada
- `ConnectionRefusedError` — servidor no disponible
- `OSError` — errores de red/socket
- `email.errors.MessageParseError` — correo malformado

#### `app/services/payment_ingestion_service.py` — 6 instancias

```python
# ACTUAL (incorrecto):
except Exception as e:
    logger.error(f"Error en job de ingesta automática: {e}")

# CORRECTO:
except imaplib.IMAP4.error as e:
    logger.error(f"Error IMAP en ingesta: {e}")
except SQLAlchemyError as e:
    db.session.rollback()
    logger.error(f"Error BD en ingesta: {e}")
except ValueError as e:
    logger.warning(f"Datos inválidos en correo: {e}")
```

Excepciones específicas a usar en `payment_ingestion_service.py`:
- `sqlalchemy.exc.SQLAlchemyError` — errores de base de datos
- `sqlalchemy.exc.IntegrityError` — violaciones de unicidad
- `imaplib.IMAP4.error` — errores IMAP
- `ValueError` — datos del correo inválidos

#### `app/routes/payments.py` — 5 instancias

```python
# ACTUAL (incorrecto):
except Exception as e:
    db.session.rollback()
    logger.error(f"Error calculando pago {pago_id}: {e}")
    return jsonify({'error': str(e)}), 500

# CORRECTO:
except SQLAlchemyError as e:
    db.session.rollback()
    logger.error(f"Error BD calculando pago {pago_id}: {e}")
    return jsonify({'error': 'Error de base de datos'}), 500
except ValueError as e:
    logger.warning(f"Valor inválido en pago {pago_id}: {e}")
    return jsonify({'error': str(e)}), 400
```

---

### 3.3 Colores hardcoded en templates

**Regla violada:** _"Nunca hardcodear colores — siempre via variables CSS en :root"_

En `app/templates/payments/list.html` y `detail.html` hay 14 instancias de colores hardcodeados en atributos `style=`:

```html
<!-- ACTUAL (incorrecto): -->
<i class="fab fa-paypal" style="color:#003087;"></i>
<span style="background:#EDE9FE; color:#5B21B6;">G&S</span>
<span style="background:#E0F2FE; color:#0369A1;">F&F</span>

<!-- CORRECTO: agregar al :root del template o style.css -->
:root {
    --c-paypal-blue: #003087;
    --c-gs-bg: #EDE9FE;
    --c-gs-text: #5B21B6;
    --c-ff-bg: #E0F2FE;
    --c-ff-text: #0369A1;
}
```

**Nota:** El color `#003087` (azul PayPal) es un color de marca externo que puede justificarse como excepción documentada. El resto sí debe moverse a variables.

---

## 4. Deuda Técnica Preexistente

### 4.1 Routes llaman directamente a Models — `dashboard.py`

**Regla violada:** _"Routes NUNCA llaman directamente a Models (siempre vía Services)"_

En `app/routes/dashboard.py` se encontraron múltiples queries directas a modelos:

```python
# Línea 270 — VIOLA la regla:
operators = Operator.query.order_by(Operator.created_at.desc()).all()

# Línea 290:
existing = Operator.query.filter_by(username=username).first()

# Línea 317:
operator = Operator.query.get(operator_id)

# Líneas 478, 483, 489 — queries directas a Quote, PaymentMethod, Currency:
payment_methods = PaymentMethod.query.filter_by(active=True).all()
currency = Currency.query.filter_by(code=currency_code).first()
quote = Quote.query.filter_by(...).first()

# Líneas 552, 557, 558, 567, 584 — más queries directas:
currency_ves = Currency.query.filter_by(code='VES').first()
currency_cop = Currency.query.filter_by(code='COP').first()
quote = Quote.query.filter_by(...).first()
```

**Acción recomendada:** Mover estas queries a sus respectivos services:
- `OperatorService` (ya existe) — métodos `get_all()`, `get_by_username()`, `get_by_id()`
- `QuoteService` (ya existe) — método `get_quote_by_method_and_currency()`
- `CurrencyService` (ya existe) — método `get_by_code()`

---

### 4.2 Servicios con archivos muy largos

**Regla violada:** _"Si una función supera 60 líneas sepárala en un módulo independiente"_

Estos archivos existían antes de la sesión PayPal:

| Archivo | Líneas totales | Observación |
|---|---|---|
| `app/services/blacklist_service.py` | 787 | Varias funciones > 60 líneas |
| `app/services/accounting_service.py` | 537 | Algunas funciones > 60 líneas |

**Acción recomendada:** Auditar función por función y extraer helpers privados donde corresponda. No es urgente pero acumula deuda técnica.

---

## 5. Lo que SÍ cumple correctamente

Para tener balance en el diagnóstico:

✅ Separación Routes → Services → Models en todos los archivos nuevos  
✅ Type hints en todas las funciones de los servicios nuevos  
✅ Docstrings en formato Google en todos los servicios nuevos  
✅ Sin `!important` en CSS de los templates nuevos  
✅ Variables CSS (`var(--c-yellow)`, `var(--c-dark)`, etc.) usadas consistentemente  
✅ Sin lógica de negocio en routes  
✅ `calcular_pago_paypal_recibido()` correctamente en `CalculatorService`, no en el modelo  
✅ Modelo `PaypalPayment` sin lógica de negocio — solo `aplicar_calculo()` que guarda snapshot  
✅ PEP 8 cumplido en todos los archivos nuevos  
✅ `except: pass` nunca usado (aunque sí `except Exception` genérico)

---

## 6. Plan de Acción Priorizado

### Prioridad 1 — Alta (viola reglas directamente)

| # | Acción | Archivo | Esfuerzo |
|---|---|---|---|
| 1 | Dividir `parse_email()` en helpers privados | `paypal_parser_service.py` | Medio |
| 2 | Dividir `get_new_paypal_payments()` en helpers | `gmail_service.py` | Bajo |
| 3 | Dividir `procesar_nuevos_pagos()` y `_procesar_correo()` | `payment_ingestion_service.py` | Medio |
| 4 | Reemplazar `except Exception` por excepciones específicas | Los 3 archivos anteriores + route | Bajo |

### Prioridad 2 — Media (deuda preexistente)

| # | Acción | Archivo | Esfuerzo |
|---|---|---|---|
| 5 | Mover queries de `dashboard.py` a sus services | `routes/dashboard.py` | Alto |
| 6 | Mover variables CSS hardcodeadas a `:root` | `payments/list.html`, `detail.html` | Bajo |

### Prioridad 3 — Baja (mejora incremental)

| # | Acción | Archivo | Esfuerzo |
|---|---|---|---|
| 7 | Auditar funciones > 60 líneas en `blacklist_service.py` | `services/blacklist_service.py` | Alto |
| 8 | Auditar funciones > 60 líneas en `accounting_service.py` | `services/accounting_service.py` | Medio |

---

## 7. Contexto para el Chat de Trabajo

Al abordar estas mejoras en un chat nuevo, compartir:

1. Este documento como referencia
2. El archivo `.clinerules` del proyecto
3. Los archivos específicos a modificar según la prioridad elegida
4. El comando de tests para verificar que nada se rompe:
   ```bash
   python -m pytest app\tests\ -v
   ```

**Nota importante:** Antes de refactorizar cualquier función larga, verificar que los tests existentes cubren ese código. Si no hay tests, escribirlos primero.