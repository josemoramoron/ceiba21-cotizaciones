# Gestión de Monedas y Cotizaciones - Sistema POO

## 📋 Resumen de Cambios

Se ha implementado un sistema **Programación Orientada a Objetos (POO)** para gestionar automáticamente las cotizaciones de monedas y métodos de pago.

### ✅ Problema Resuelto

**ANTES:**
- Al agregar nuevas monedas (BRL, MXN), las cotizaciones de métodos de pago quedaban en 0
- Al modificar tasas de cambio, las cotizaciones NO se recalculaban automáticamente
- Proceso manual y propenso a errores

**AHORA:**
- Sistema automático que crea cotizaciones para todas las monedas nuevas
- Al modificar una tasa de cambio, TODAS las cotizaciones de esa moneda se recalculan automáticamente
- Arquitectura POO limpia y escalable

---

## 🏗️ Arquitectura POO

### 1. **Quote.calculate_final_value()**
```python
# En app/models/quote.py
def calculate_final_value(self):
    """
    Calcula automáticamente:
    1. Valor en USD (manual o fórmula)
    2. Valor final = USD × Tasa de cambio
    """
```

**Uso:**
```python
quote = Quote.query.get(quote_id)
quote.usd_value = 0.95
quote.calculate_final_value()  # Calcula automáticamente el valor final
db.session.commit()
```

---

### 2. **ExchangeRate.recalculate_quotes()**
```python
# En app/models/exchange_rate.py
def recalculate_quotes(self):
    """
    Recalcula TODAS las cotizaciones de esta moneda
    cuando se actualiza la tasa de cambio
    """
```

**Uso:**
```python
exchange_rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
exchange_rate.rate = 5.85  # Nueva tasa
num_quotes = exchange_rate.recalculate_quotes()  # Recalcula todo automáticamente
db.session.commit()
```

---

### 3. **Currency.initialize_for_trading()**
```python
# En app/models/currency.py
def initialize_for_trading(self, exchange_rate=None):
    """
    Inicializa completamente una moneda nueva:
    1. Crea la tasa de cambio (automática o manual)
    2. Crea cotizaciones para TODOS los métodos de pago
    
    Retorna: (success, message, details)
    """
```

**Uso:**
```python
# Crear nueva moneda
currency = Currency(code='EUR', name='Euro', symbol='€')
db.session.add(currency)
db.session.flush()

# Inicializar automáticamente
success, message, details = currency.initialize_for_trading(exchange_rate=0.92)
# Crea: ExchangeRate + 22 Quotes (una por cada método de pago)
```

---

### 4. **ExchangeRateService.update_rate()** (Mejorado)
```python
# En app/services/exchange_rate_service.py
@staticmethod
def update_rate(currency_code, new_rate):
    """
    Actualiza tasa y recalcula SOLO las cotizaciones de esa moneda (POO)
    Retorna: (exchange_rate, quotes_updated)
    """
```

**Uso:**
```python
from app.services.exchange_rate_service import ExchangeRateService

# Actualizar tasa de cambio
exchange_rate, quotes_updated = ExchangeRateService.update_rate('BRL', 5.85)
print(f"Se actualizaron {quotes_updated} cotizaciones automáticamente")
```

---

## 🚀 Cómo Agregar una Nueva Moneda

### Opción 1: Desde Python/Shell (Recomendado)
```python
from app import create_app, db
from app.models import Currency

app = create_app()
with app.app_context():
    # 1. Crear moneda
    nueva_moneda = Currency(
        code='PEN',
        name='Sol Peruano',
        symbol='S/',
        active=True,
        display_order=7
    )
    db.session.add(nueva_moneda)
    db.session.flush()
    
    # 2. Inicializar automáticamente (crea tasa + cotizaciones)
    success, message, details = nueva_moneda.initialize_for_trading(exchange_rate=3.75)
    
    if success:
        print(f"✅ {message}")
        print(f"   Tasa creada: {details['exchange_rate']['rate']}")
        print(f"   Cotizaciones creadas: {details['quotes_created']}")
    
    db.session.commit()
```

### Opción 2: Usando el Script de Arreglo
```bash
# El script detecta monedas sin cotizaciones y las arregla automáticamente
python scripts/fix_currencies.py
```

---

## 🔧 Mantenimiento

### Recalcular Todas las Cotizaciones de una Moneda
```python
from app.models import ExchangeRate

exchange_rate = ExchangeRate.query.filter_by(currency_id=currency_id).first()
quotes_updated = exchange_rate.recalculate_quotes()
db.session.commit()
print(f"Se recalcularon {quotes_updated} cotizaciones")
```

### Verificar Estado de una Moneda
```python
from app.models import Currency, ExchangeRate, Quote

currency = Currency.query.filter_by(code='BRL').first()

# Verificar tasa
exchange_rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
print(f"Tasa: {exchange_rate.rate if exchange_rate else 'NO EXISTE'}")

# Verificar cotizaciones
quotes = Quote.query.filter_by(currency_id=currency.id).all()
print(f"Cotizaciones: {len(quotes)}")
zero_quotes = [q for q in quotes if not q.final_value or q.final_value == 0]
print(f"En cero: {len(zero_quotes)}")
```

---

## 📊 Flujo Automático

```
Usuario modifica tasa de cambio en Dashboard
              ↓
  ExchangeRateService.update_rate()
              ↓
   exchange_rate.rate = new_value
              ↓
   exchange_rate.recalculate_quotes()  ← POO
              ↓
    Para cada Quote de esta moneda:
      → quote.calculate_final_value()  ← POO
              ↓
         db.session.commit()
              ↓
    ✅ Todas las cotizaciones actualizadas
```

---

## 🛠️ Scripts Disponibles

### `scripts/fix_currencies.py`
Arregla monedas existentes que tengan problemas:
- Sin tasa de cambio → Crea tasa automática
- Sin cotizaciones → Crea 22 cotizaciones
- Cotizaciones en 0 → Recalcula valores

```bash
python scripts/fix_currencies.py
```

**Salida esperada:**
```
============================================================
ARREGLANDO MONEDAS EXISTENTES
============================================================

📋 Procesando BRL (Real Brasileno)...
  ✅ Tasa de cambio: 1 USD = 5.2800 BRL
  📊 Cotizaciones existentes: 0
  🔧 Inicializando BRL...
  ✅ Moneda BRL inicializada: 22 cotizaciones creadas

============================================================
RESUMEN FINAL
============================================================
✅ BRL: Tasa=Sí, Cotizaciones=22, En cero=0
✅ MXN: Tasa=Sí, Cotizaciones=22, En cero=0
```

---

## 📝 Notas Técnicas

### Tasas por Defecto
Las tasas por defecto están en `Currency.get_default_rate_for_currency()`:
```python
default_rates = {
    'VES': 37.0,
    'COP': 4300.0,
    'CLP': 950.0,
    'ARS': 1000.0,
    'BRL': 5.85,
    'MXN': 17.50,
    'USD': 1.0,
    'EUR': 0.92,
    # ...
}
```

### Valor por Defecto USD para Nuevas Monedas
En `Currency.create_quotes_for_all_payment_methods()`:
```python
usd_value=0.92  # Valor por defecto para todas las monedas nuevas
```

---

## ✅ Estado Actual

Después de ejecutar el script de arreglo:

| Moneda | Tasa de Cambio | Cotizaciones | Estado |
|--------|---------------|--------------|---------|
| VES    | ✅ 378.53     | ✅ 22        | ✅ OK   |
| COP    | ✅ 3761.52    | ✅ 22        | ✅ OK   |
| ARS    | ✅ 1416.50    | ✅ 21        | ✅ OK   |
| **BRL** | ✅ 5.28      | ✅ **22**    | ✅ **ARREGLADO** |
| CLP    | ✅ 925.06     | ✅ 21        | ✅ OK   |
| **MXN** | ✅ 18.34     | ✅ **22**    | ✅ **ARREGLADO** |

---

## 🎯 Próximos Pasos

1. **Al agregar una nueva moneda:**
   ```python
   nueva_moneda.initialize_for_trading()
   ```

2. **Al modificar una tasa de cambio:**
   ```python
   ExchangeRateService.update_rate(code, new_rate)
   # Automáticamente recalcula todas las cotizaciones
   ```

3. **Si algo falla:**
   ```bash
   python scripts/fix_currencies.py
   ```

---

## 📚 Referencias

- **Modelos:** `app/models/currency.py`, `app/models/quote.py`, `app/models/exchange_rate.py`
- **Servicios:** `app/services/exchange_rate_service.py`
- **Scripts:** `scripts/fix_currencies.py`

---

*Documentación creada: 02/12/2025*
*Sistema POO implementado para gestión automática de cotizaciones*
