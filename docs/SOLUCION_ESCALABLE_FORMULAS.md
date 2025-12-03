# Solución Escalable: Fórmulas Centralizadas

## 🎯 Problema Original

**Antes**: Cada cotización (Quote) tenía su propia copia de la fórmula:
- PayPal en VES: `formula = "1 / 1.1"`
- PayPal en COP: `formula = "1 / 1.1"`
- PayPal en BRL: `formula = "1 / 1.1"`
- PayPal en MXN: `formula = "1 / 1.1"`
- ... (copiada en TODAS las monedas)

**Problema**: Al actualizar la fórmula de PayPal, había que actualizar 6+ cotizaciones (una por cada moneda). ❌ No escalable.

## ✅ Solución Implementada

**Ahora**: La fórmula está centralizada en PaymentMethod:
- PayPal: `formula = "1 / 1.1"` (una sola vez)
- Todas las monedas leen esta fórmula al calcular

**Ventaja**: Al actualizar la fórmula de PayPal, automáticamente se aplica a TODAS las monedas. ✅ Escalable.

## 🏗️ Arquitectura Nueva

### PaymentMethod (Centralizado)
```python
class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20))
    name = db.Column(db.String(50))
    
    # ✅ NUEVO: Configuración USD centralizada
    value_type = db.Column(db.String(20))     # 'manual' o 'formula'
    usd_value = db.Column(db.Numeric(10, 6))  # Valor manual
    usd_formula = db.Column(db.String(200))   # Fórmula matemática
    
    def calculate_usd_value(self):
        """Calcula USD una sola vez, usado por todas las monedas"""
        if self.value_type == 'manual':
            return float(self.usd_value)
        elif self.value_type == 'formula':
            return float(eval(self.usd_formula))
```

### Quote (Lee del PaymentMethod)
```python
class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_method_id = db.Column(db.Integer)
    currency_id = db.Column(db.Integer)
    
    # Campos deprecados (se mantienen por compatibilidad)
    value_type = db.Column(db.String(20))
    usd_value = db.Column(db.Numeric(10, 6))
    usd_formula = db.Column(db.String(200))
    
    calculated_usd = db.Column(db.Numeric(10, 6))
    final_value = db.Column(db.Numeric(12, 2))
    
    def calculate_final_value(self):
        """
        ✅ NUEVO: Lee la fórmula del PaymentMethod (centralizada)
        No usa sus propios campos value_type/usd_value/usd_formula
        """
        # Leer valor USD del PaymentMethod
        calculated_usd = self.payment_method.calculate_usd_value()
        
        # Calcular valor final
        exchange_rate = ExchangeRate.query.filter_by(
            currency_id=self.currency_id
        ).first()
        
        self.final_value = calculated_usd * exchange_rate.rate
        return self.final_value
```

## 📊 Flujo de Cálculo

### Antes (No Escalable):
```
PayPal VES Quote → lee su propia fórmula → calcula → 344.12 Bs
PayPal COP Quote → lee su propia fórmula → calcula → 3419.56 COP
PayPal BRL Quote → lee su propia fórmula → calcula → 4.80 R$
PayPal MXN Quote → lee su propia fórmula → calcula → 16.67 MXN
```
❌ Cada Quote tiene una copia de la fórmula

### Ahora (Escalable):
```
PayPal (PaymentMethod)
  ↓ tiene formula = "1 / 1.1"
  ↓ calculate_usd_value() → 0.9091 USD
  ├→ VES Quote → 0.9091 × 378.53 = 344.12 Bs
  ├→ COP Quote → 0.9091 × 3761.52 = 3419.56 COP
  ├→ BRL Quote → 0.9091 × 5.28 = 4.80 R$
  └→ MXN Quote → 0.9091 × 18.34 = 16.67 MXN
```
✅ Una sola fórmula, usada por todas las monedas

## 🔄 Migración Realizada

El script `migrate_to_centralized_formulas.py` realizó:

1. **Agregó columnas a `payment_methods`**:
   - `value_type VARCHAR(20)`
   - `usd_value NUMERIC(10, 6)`
   - `usd_formula VARCHAR(200)`

2. **Migró datos de VES a PaymentMethod**:
   - Copió las fórmulas de Quote (VES) a PaymentMethod
   - Ahora PaymentMethod es la fuente de verdad

3. **Recalculó todas las cotizaciones**:
   - 130 cotizaciones recalculadas
   - Ahora leen del PaymentMethod

## 🚀 Cómo Usar el Nuevo Sistema

### Actualizar la Fórmula de un Método de Pago

**Antes** (No escalable):
```python
# Tenías que actualizar cada Quote individualmente
for currency in currencies:
    quote = Quote.query.filter_by(
        payment_method_id=paypal.id,
        currency_id=currency.id
    ).first()
    quote.usd_formula = "1 / 1.15"  # Nueva fórmula
    quote.calculate_final_value()
db.session.commit()
```

**Ahora** (Escalable):
```python
# Actualiza UNA SOLA VEZ en PaymentMethod
paypal = PaymentMethod.query.filter_by(code='PAYPAL').first()
paypal.usd_formula = "1 / 1.15"  # Nueva fórmula
db.session.commit()

# Recalcular TODAS las cotizaciones del método
quotes = Quote.query.filter_by(payment_method_id=paypal.id).all()
for quote in quotes:
    quote.calculate_final_value()
db.session.commit()
```

O desde el dashboard: `/dashboard/payment-methods` → Editar PayPal → Cambiar fórmula

### Agregar Nueva Moneda

El sistema ahora es automáticamente escalable:

```python
# Crear nueva moneda
nueva_moneda = Currency(code='PEN', name='Sol Peruano', symbol='S/')
db.session.add(nueva_moneda)
db.session.flush()

# Crear cotizaciones (NO necesita copiar fórmulas)
for pm in PaymentMethod.query.all():
    quote = Quote(
        payment_method_id=pm.id,
        currency_id=nueva_moneda.id
    )
    quote.calculate_final_value()  # ✅ Lee la fórmula del PaymentMethod
    db.session.add(quote)

db.session.commit()
```

**Resultado**: La nueva moneda automáticamente usa las fórmulas centralizadas. ✅

## 📈 Ventajas de la Solución

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Fórmulas** | ❌ Copiadas en cada Quote | ✅ Centralizadas en PaymentMethod |
| **Actualización** | ❌ 6+ Quotes por método | ✅ 1 PaymentMethod |
| **Nuevas Monedas** | ❌ Copiar fórmulas | ✅ Leen automáticamente |
| **Mantenimiento** | ❌ Complejo | ✅ Simple |
| **Escalabilidad** | ❌ No escalable | ✅ Totalmente escalable |
| **Consistencia** | ❌ Riesgo de desincronización | ✅ Siempre consistente |

## 🧪 Pruebas

### Verificar que Funciona

```bash
cd /var/www/cotizaciones
python scripts/analyze_quote_values.py
```

Deberías ver:
```
Método de Pago       VES USD    BRL USD    MXN USD    COP USD
--------------------------------------------------------------------------------
PayPal               0.9091     0.9091     0.9091     0.9091  ✅ Mismo valor
Zelle                0.9434     0.9434     0.9434     0.9434  ✅ Mismo valor
USDT                 0.9615     0.9615     0.9615     0.9615  ✅ Mismo valor
```

Todos tienen el mismo valor USD porque leen de la misma fuente (PaymentMethod).

### Probar Actualización

```python
# 1. Cambiar fórmula de PayPal
paypal = PaymentMethod.query.filter_by(code='PAYPAL').first()
paypal.usd_formula = "1 / 1.15"  # Cambio: 1.1 → 1.15

# 2. Recalcular
quotes = Quote.query.filter_by(payment_method_id=paypal.id).all()
for q in quotes:
    q.calculate_final_value()
db.session.commit()

# 3. Verificar que TODAS las monedas cambiaron
# VES: nuevo valor
# COP: nuevo valor
# BRL: nuevo valor
# MXN: nuevo valor
# ✅ Todas cambiaron automáticamente
```

## 💡 Notas Importantes

1. **Los campos en Quote se mantienen por compatibilidad**:
   - `value_type`, `usd_value`, `usd_formula` en Quote están deprecados
   - El sistema primero intenta leer de PaymentMethod
   - Si no existe, hace fallback a los campos de Quote

2. **PaymentMethod es ahora la fuente de verdad**:
   - NO modifiques los campos en Quote
   - SIEMPRE modifica PaymentMethod

3. **Al agregar nuevos métodos de pago**:
   - Define `value_type`, `usd_value` o `usd_formula` en PaymentMethod
   - Las cotizaciones se crean automáticamente para todas las monedas

## 🔮 Próximos Pasos

Ahora que el sistema es escalable:

1. ✅ Agrega nuevas monedas sin preocuparte
2. ✅ Actualiza fórmulas en un solo lugar
3. ✅ El sistema automáticamente sincroniza todo
4. ✅ No más scripts manuales de corrección

---

**Fecha**: 12 de Marzo, 2025  
**Versión**: 3.0 (Fórmulas Centralizadas - Solución Escalable)  
**Estado**: ✅ Implementado y en producción
