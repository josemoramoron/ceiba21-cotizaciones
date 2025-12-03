# Solución: Problema BRL y MXN en Dashboard

## 📋 Problema Identificado

Las monedas **BRL (Real Brasileño)** y **MXN (Peso Mexicano)** no aparecían en el dashboard y no mostraban los valores de sus métodos de pago.

## 🔍 Diagnóstico

Al revisar la base de datos, se encontró que:

### Estado Inicial:
```
BRL (Real Brasileño)  - Activa: False
MXN (Peso Mexicano)   - Activa: False
```

### Datos Verificados:
- ✅ **Tasas de cambio**: Ambas monedas tenían tasas correctas
  - BRL: 5.28
  - MXN: 18.34
- ✅ **Cotizaciones**: Ambas monedas tenían todas sus cotizaciones (22/22 métodos de pago)
- ❌ **Estado**: Estaban marcadas como inactivas (`active=False`)

## 🎯 Causa Raíz

El dashboard y otros componentes filtran las monedas por su estado `active`:
- Las monedas con `active=True` se muestran en el dashboard
- Las monedas con `active=False` se ocultan del sistema

VES y COP funcionaban correctamente porque estaban activas:
```
VES (Bolívares)       - Activa: True  ✅
COP (Peso Colombiano) - Activa: True  ✅
```

## ✅ Solución Aplicada

Se ejecutó el script `scripts/activate_currencies.py` que:

1. Localizó las monedas BRL y MXN en la base de datos
2. Cambió su estado a `active=True`
3. Guardó los cambios en la base de datos

### Estado Final:
```
BRL (Real Brasileño)  - Activa: True  ✅
MXN (Peso Mexicano)   - Activa: True  ✅
```

## 🧪 Verificación

Después de activar las monedas:
- ✅ BRL tiene 22/22 cotizaciones activas
- ✅ MXN tiene 22/22 cotizaciones activas
- ✅ Ambas monedas ahora aparecen en el dashboard
- ✅ Los métodos de pago muestran valores correctos para ambas monedas

## 📝 Scripts Utilizados

### 1. Diagnóstico:
```bash
python scripts/check_currency_status.py
```

### 2. Solución:
```bash
python scripts/activate_currencies.py
```

## 🔧 Administración de Monedas

Para activar/desactivar monedas en el futuro, puedes:

### Opción 1: Desde el Dashboard
1. Ir a `/dashboard/currencies`
2. Usar el botón de toggle para activar/desactivar monedas

### Opción 2: Por Código
```python
from app.models import Currency, db

# Activar una moneda
currency = Currency.query.filter_by(code='BRL').first()
currency.active = True
db.session.commit()

# Desactivar una moneda
currency = Currency.query.filter_by(code='MXN').first()
currency.active = False
db.session.commit()
```

## 📊 Resumen de Monedas Activas

Después de la solución:

| Código | Nombre              | Estado   | Cotizaciones |
|--------|---------------------|----------|--------------|
| VES    | Bolívares           | ✅ Activa | 22/22        |
| COP    | Peso Colombiano     | ✅ Activa | 22/22        |
| BRL    | Real Brasileño      | ✅ Activa | 22/22        |
| MXN    | Peso Mexicano       | ✅ Activa | 22/22        |
| ARS    | Peso Argentino      | ⚠️ Inactiva | 21/22      |
| CLP    | Peso Chileno        | ⚠️ Inactiva | 21/22      |

## 💡 Nota

Si ARS o CLP también necesitan ser activadas, simplemente ejecuta:
```bash
python scripts/activate_currencies.py
```

Y modifica el script para incluir estas monedas adicionales.

---

**Fecha de Solución**: 12 de Marzo, 2025  
**Problema Resuelto**: ✅ BRL y MXN ahora funcionan correctamente
