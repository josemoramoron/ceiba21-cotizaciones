# FASE 6: CONTABILIDAD AUTOMÁTICA Y REPORTES

## 📋 CONTEXTO

Sistema de órdenes Ceiba21 - Ya completamos Fases 1, 2, 3, 4 y 5.

### Estado completado:
- ✅ **Fase 1:** Modelos (BaseModel, User, Operator, Order, Transaction, Message, WebUser)
- ✅ **Fase 2:** Servicios (OrderService, CalculatorService, AuthService, NotificationService)
- ✅ **Fase 3:** Canales (BaseChannel, TelegramChannel, WhatsAppChannel, WebChatChannel, ChannelFactory)
- ✅ **Fase 4:** Bot conversacional de Telegram (FSM completa, comandos admin/operador)
- ✅ **Fase 5:** Dashboard de operadores (unificado, WebSockets, chat en vivo)

### Objetivo de esta fase:
Crear un sistema completo de contabilidad automática que registre todas las transacciones financieras sin intervención manual, y genere reportes detallados para toma de decisiones.

---

## 🎯 CONCEPTO CLAVE: CONTABILIDAD AUTOMÁTICA

### Problema que resolvemos:

**❌ Sin contabilidad automática:**
```
1. Orden completada
2. Operador debe:
   - Abrir Excel manualmente
   - Registrar ingreso de USD
   - Registrar comisión ganada
   - Registrar pago en moneda local
   - Calcular balance
   - Actualizar reportes
→ Errores humanos, datos inconsistentes, lentitud
```

**✅ Con contabilidad automática:**
```
1. Orden completada
2. Sistema automáticamente:
   - Genera 3 transacciones (INCOME, FEE, EXPENSE)
   - Actualiza estadísticas en tiempo real
   - Calcula métricas financieras
   - Genera reportes actualizados
→ Cero errores, datos consistentes, instantáneo
```

---

## 💰 MODELO DE TRANSACCIONES

### Recordatorio del modelo Transaction:

Cada orden COMPLETADA genera **3 transacciones automáticas**:

```python
# Ejemplo: Orden de $100 USD por PayPal → 28,808.65 Bs

# 1. INCOME (ingreso)
Transaction(
    type=INCOME,
    amount=100.00,
    currency_code='USD',
    payment_method='PayPal',
    description='Recibido de @juanperez vía PayPal'
)

# 2. FEE (ganancia de Ceiba21)
Transaction(
    type=FEE,
    amount=5.70,
    currency_code='USD',
    payment_method='PayPal',
    description='Comisión PayPal'
)

# 3. EXPENSE (pago al cliente)
Transaction(
    type=EXPENSE,
    amount=28808.65,
    currency_code='VES',
    payment_method='Banco Venezuela',
    description='Pagado a @juanperez vía Banco Venezuela'
)
```

**Balance neto:** Fee ($5.70 USD) = Ganancia de Ceiba21

---

## 📊 ARQUITECTURA DE CONTABILIDAD

```
┌─────────────────────────────────────────────────┐
│         ORDEN COMPLETADA (Fase 5)               │
│  Operador marca orden como COMPLETED            │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│    OrderService.complete_order()                │
│    1. Cambiar estado → COMPLETED                │
│    2. ⚡ Transaction.create_from_order(order)   │
│    3. Actualizar estadísticas                   │
│    4. Notificar cliente                         │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│    TABLA: transactions (PostgreSQL)             │
│  • 3 registros nuevos por orden                 │
│  • Timestamps automáticos                       │
│  • Vinculados a order_id                        │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│    AccountingService                            │
│  • Calcular balances por moneda                 │
│  • Calcular ganancias totales                   │
│  • Generar reportes por período                 │
│  • Exportar a Excel/PDF                         │
│  • Enviar reportes automáticos por email       │
└─────────────────────────────────────────────────┘
```

---

## 🎨 MOCKUP DEL DASHBOARD CONTABLE

```
┌────────────────────────────────────────────────────────────────────┐
│ Ceiba21 - Contabilidad                     👤 Admin ▼    [📅 Hoy]  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ 📊 RESUMEN FINANCIERO HOY                                         │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │                                                              │ │
│ │  💰 INGRESOS USD         💸 EGRESOS           📈 GANANCIAS   │ │
│ │  $2,450.00              VES: 747,375 Bs      $131.85        │ │
│ │  (25 órdenes)           COP: 4,120,000       (5.38%)        │ │
│ │                         CLP: 0                               │ │
│ │                         ARS: 0                               │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                    │
│ 📅 PERÍODO: [Hoy ▼] [Esta semana] [Este mes] [Personalizado]     │
│                                                                    │
│ ┌─────────────────────┐  ┌──────────────────────────────────────┐│
│ │ GANANCIAS POR DÍA   │  │ DISTRIBUCIÓN POR MÉTODO              ││
│ │                     │  │                                      ││
│ │   $150              │  │  PayPal    : $98.50 (74.7%)         ││
│ │   $120 ●            │  │  Zelle     : $28.35 (21.5%)         ││
│ │   $100  ●           │  │  USDT      : $5.00  (3.8%)          ││
│ │    $80   ● ●        │  │                                      ││
│ │    $60    ●  ●      │  │  [Gráfico de pie]                    ││
│ │    $40     ●   ●    │  │                                      ││
│ │    $20       ●   ● ●│  │                                      ││
│ │     $0 ─────────────│  │                                      ││
│ │      L M M J V S D  │  │                                      ││
│ └─────────────────────┘  └──────────────────────────────────────┘│
│                                                                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                    │
│ 📋 TRANSACCIONES RECIENTES                                        │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ FECHA     TIPO      MONTO           MÉTODO         ORDEN     │ │
│ ├──────────────────────────────────────────────────────────────┤ │
│ │ 15:42    💵 INCOME  $100.00 USD     PayPal         ORD-003   │ │
│ │ 15:42    📈 FEE     $5.70 USD       PayPal         ORD-003   │ │
│ │ 15:42    💸 EXPENSE 30,550.00 Bs    Bco Venezuela  ORD-003   │ │
│ │ 15:20    💵 INCOME  $50.00 USD      Zelle          ORD-002   │ │
│ │ 15:20    📈 FEE     $0.00 USD       Zelle          ORD-002   │ │
│ │ 15:20    💸 EXPENSE 15,275.00 Bs    Bco Mercantil  ORD-002   │ │
│ │ 14:58    💵 INCOME  $250.00 USD     PayPal         ORD-001   │ │
│ │ 14:58    📈 FEE     $14.25 USD      PayPal         ORD-001   │ │
│ │ 14:58    💸 EXPENSE 76,375.00 Bs    Bco Venezuela  ORD-001   │ │
│ │                                                              │ │
│ │                                    [Ver todas] [Exportar 📥]  │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                    │
│ ⚡ ACCIONES:                                                       │
│ [📥 Exportar Excel] [📄 Generar PDF] [📧 Enviar reporte email]   │
│ [🔄 Recalcular todo] [⚙️ Configurar alertas]                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 FUNCIONALIDADES

### 1. Generación automática de transacciones

**Ya implementado en Fase 2 (OrderService):**

```python
# app/services/order_service.py

@classmethod
def complete_order(cls, order_id, operator_id, operator_proof_url=None):
    """
    Al marcar orden como completada, genera transacciones automáticamente.
    """
    # ... código existente ...
    
    # Cambiar estado
    order.transition_to(OrderStatus.COMPLETED, operator=operator)
    
    # ⚡ AUTOMATIZACIÓN: Generar transacciones contables
    Transaction.create_from_order(order)
    
    # ... resto del código ...
```

**Método create_from_order ya existe en Transaction model:**

```python
# app/models/transaction.py

@classmethod
def create_from_order(cls, order):
    """
    Crear 3 transacciones desde una orden completada.
    
    Este método YA ESTÁ IMPLEMENTADO en Fase 1.
    Aquí solo documentamos para contexto.
    """
    transactions = []
    
    # 1. INCOME
    income = cls(
        order_id=order.id,
        type=TransactionType.INCOME,
        amount=order.amount_usd,
        currency_code='USD',
        payment_method_id=order.payment_method_from_id,
        description=f"Recibido de {order.user.get_display_name()} vía {order.payment_method_from.name}",
        is_verified=False
    )
    transactions.append(income)
    
    # 2. FEE
    fee = cls(
        order_id=order.id,
        type=TransactionType.FEE,
        amount=order.fee_usd,
        currency_code='USD',
        payment_method_id=order.payment_method_from_id,
        description=f"Comisión {order.payment_method_from.name}",
        is_verified=True
    )
    transactions.append(fee)
    
    # 3. EXPENSE
    expense = cls(
        order_id=order.id,
        type=TransactionType.EXPENSE,
        amount=order.amount_local,
        currency_code=order.currency.code,
        payment_method_id=order.payment_method_to_id,
        description=f"Pagado a {order.user.get_display_name()} vía {order.payment_method_to.name}",
        is_verified=False
    )
    transactions.append(expense)
    
    # Guardar todas
    for t in transactions:
        t.save()
    
    return transactions
```

✅ **Esta funcionalidad YA está lista.** Solo necesitamos la interfaz visual.

---

### 2. AccountingService - Reportes y cálculos

**Nuevo servicio a crear:**

```python
# app/services/accounting_service.py

from app.services.base_service import BaseService
from app.models.transaction import Transaction, TransactionType
from datetime import datetime, timedelta
from sqlalchemy import func
from decimal import Decimal

class AccountingService(BaseService):
    """
    Servicio para contabilidad y reportes financieros.
    
    RESPONSABILIDADES:
    - Calcular balances por moneda
    - Calcular ganancias totales
    - Generar reportes por período
    - Exportar a Excel/PDF
    - Métricas financieras
    """
    
    # ==========================================
    # BALANCES Y TOTALES
    # ==========================================
    
    @classmethod
    def get_balance_summary(cls, start_date=None, end_date=None):
        """
        Resumen financiero del período.
        
        RETORNA:
        {
            'total_income_usd': 2450.00,
            'total_fees_usd': 131.85,
            'total_expenses': {
                'VES': 747375.00,
                'COP': 4120000.00,
                'CLP': 0.00,
                'ARS': 0.00
            },
            'net_profit_usd': 131.85,
            'order_count': 25,
            'average_fee_percentage': 5.38
        }
        """
        # Establecer fechas por defecto (hoy)
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        # Consultar transacciones del período
        transactions = Transaction.query.filter(
            Transaction.created_at.between(start_date, end_date)
        ).all()
        
        summary = {
            'total_income_usd': Decimal('0.00'),
            'total_fees_usd': Decimal('0.00'),
            'total_expenses': {},
            'net_profit_usd': Decimal('0.00'),
            'order_count': 0,
            'average_fee_percentage': Decimal('0.00')
        }
        
        # Procesar transacciones
        order_ids = set()
        
        for t in transactions:
            if t.type == TransactionType.INCOME and t.currency_code == 'USD':
                summary['total_income_usd'] += t.amount
                order_ids.add(t.order_id)
            
            elif t.type == TransactionType.FEE:
                summary['total_fees_usd'] += t.amount
            
            elif t.type == TransactionType.EXPENSE:
                if t.currency_code not in summary['total_expenses']:
                    summary['total_expenses'][t.currency_code] = Decimal('0.00')
                summary['total_expenses'][t.currency_code] += t.amount
        
        # Calcular métricas
        summary['net_profit_usd'] = summary['total_fees_usd']
        summary['order_count'] = len(order_ids)
        
        if summary['total_income_usd'] > 0:
            summary['average_fee_percentage'] = (
                summary['total_fees_usd'] / summary['total_income_usd'] * 100
            ).quantize(Decimal('0.01'))
        
        return summary
    
    # ==========================================
    # SERIES TEMPORALES
    # ==========================================
    
    @classmethod
    def get_daily_fees(cls, days=7):
        """
        Ganancias (fees) por día de los últimos N días.
        
        RETORNA:
        [
            {'date': '2024-12-01', 'fees': 45.80},
            {'date': '2024-12-02', 'fees': 62.15},
            ...
        ]
        
        USO: Para gráficos de tendencia
        """
        start_date = datetime.now() - timedelta(days=days)
        
        results = db.session.query(
            func.date(Transaction.created_at).label('date'),
            func.sum(Transaction.amount).label('total_fees')
        ).filter(
            Transaction.type == TransactionType.FEE,
            Transaction.created_at >= start_date
        ).group_by('date').order_by('date').all()
        
        return [
            {
                'date': result.date.isoformat(),
                'fees': float(result.total_fees)
            }
            for result in results
        ]
    
    @classmethod
    def get_hourly_distribution(cls, date=None):
        """
        Distribución de órdenes por hora del día.
        
        RETORNA:
        [
            {'hour': 9, 'count': 2},
            {'hour': 10, 'count': 5},
            ...
        ]
        
        USO: Identificar horas pico
        """
        if not date:
            date = datetime.now().date()
        
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        
        results = db.session.query(
            func.extract('hour', Transaction.created_at).label('hour'),
            func.count(func.distinct(Transaction.order_id)).label('order_count')
        ).filter(
            Transaction.type == TransactionType.FEE,
            Transaction.created_at.between(start, end)
        ).group_by('hour').order_by('hour').all()
        
        return [
            {'hour': int(result.hour), 'count': result.order_count}
            for result in results
        ]
    
    # ==========================================
    # DISTRIBUCIONES
    # ==========================================
    
    @classmethod
    def get_fees_by_payment_method(cls, start_date=None, end_date=None):
        """
        Ganancias por método de pago.
        
        RETORNA:
        [
            {'method': 'PayPal', 'fees': 98.50, 'percentage': 74.7},
            {'method': 'Zelle', 'fees': 28.35, 'percentage': 21.5},
            {'method': 'USDT', 'fees': 5.00, 'percentage': 3.8}
        ]
        
        USO: Gráfico de pie
        """
        # Establecer fechas
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        results = db.session.query(
            PaymentMethod.name,
            func.sum(Transaction.amount).label('total_fees')
        ).join(
            PaymentMethod, Transaction.payment_method_id == PaymentMethod.id
        ).filter(
            Transaction.type == TransactionType.FEE,
            Transaction.created_at.between(start_date, end_date)
        ).group_by(PaymentMethod.name).all()
        
        # Calcular total para porcentajes
        total_fees = sum(r.total_fees for r in results)
        
        distribution = []
        for result in results:
            percentage = (float(result.total_fees) / float(total_fees) * 100) if total_fees > 0 else 0
            distribution.append({
                'method': result.name,
                'fees': float(result.total_fees),
                'percentage': round(percentage, 1)
            })
        
        # Ordenar por monto descendente
        distribution.sort(key=lambda x: x['fees'], reverse=True)
        
        return distribution
    
    @classmethod
    def get_orders_by_currency(cls, start_date=None, end_date=None):
        """
        Órdenes por moneda destino.
        
        RETORNA:
        [
            {'currency': 'VES', 'count': 18, 'percentage': 72.0},
            {'currency': 'COP', 'count': 7, 'percentage': 28.0}
        ]
        """
        from app.models.order import Order
        
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        results = db.session.query(
            Currency.code,
            func.count(Order.id).label('order_count')
        ).join(
            Currency, Order.currency_id == Currency.id
        ).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.completed_at.between(start_date, end_date)
        ).group_by(Currency.code).all()
        
        total_orders = sum(r.order_count for r in results)
        
        distribution = []
        for result in results:
            percentage = (result.order_count / total_orders * 100) if total_orders > 0 else 0
            distribution.append({
                'currency': result.code,
                'count': result.order_count,
                'percentage': round(percentage, 1)
            })
        
        distribution.sort(key=lambda x: x['count'], reverse=True)
        
        return distribution
    
    # ==========================================
    # EXPORTACIÓN
    # ==========================================
    
    @classmethod
    def export_to_excel(cls, start_date, end_date, filename='reporte_contable.xlsx'):
        """
        Exportar transacciones a Excel.
        
        SHEETS:
        1. Resumen
        2. Ingresos
        3. Gastos
        4. Ganancias
        5. Gráficos
        """
        import pandas as pd
        from openpyxl import Workbook
        from openpyxl.chart import PieChart, BarChart, Reference
        
        # Obtener transacciones
        transactions = Transaction.query.filter(
            Transaction.created_at.between(start_date, end_date)
        ).order_by(Transaction.created_at.desc()).all()
        
        # Crear Excel con múltiples hojas
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            
            # 1. Hoja de resumen
            summary = cls.get_balance_summary(start_date, end_date)
            df_summary = pd.DataFrame([{
                'Métrica': k,
                'Valor': str(v)
            } for k, v in summary.items()])
            df_summary.to_excel(writer, sheet_name='Resumen', index=False)
            
            # 2. Hoja de ingresos
            incomes = [t for t in transactions if t.type == TransactionType.INCOME]
            df_incomes = pd.DataFrame([{
                'Fecha': t.created_at.strftime('%Y-%m-%d %H:%M'),
                'Orden': t.order.reference if t.order else 'N/A',
                'Monto': float(t.amount),
                'Moneda': t.currency_code,
                'Método': t.payment_method.name if t.payment_method else 'N/A',
                'Descripción': t.description
            } for t in incomes])
            df_incomes.to_excel(writer, sheet_name='Ingresos', index=False)
            
            # 3. Hoja de gastos
            expenses = [t for t in transactions if t.type == TransactionType.EXPENSE]
            df_expenses = pd.DataFrame([{
                'Fecha': t.created_at.strftime('%Y-%m-%d %H:%M'),
                'Orden': t.order.reference if t.order else 'N/A',
                'Monto': float(t.amount),
                'Moneda': t.currency_code,
                'Método': t.payment_method.name if t.payment_method else 'N/A',
                'Descripción': t.description
            } for t in expenses])
            df_expenses.to_excel(writer, sheet_name='Gastos', index=False)
            
            # 4. Hoja de ganancias
            fees = [t for t in transactions if t.type == TransactionType.FEE]
            df_fees = pd.DataFrame([{
                'Fecha': t.created_at.strftime('%Y-%m-%d %H:%M'),
                'Orden': t.order.reference if t.order else 'N/A',
                'Monto': float(t.amount),
                'Método': t.payment_method.name if t.payment_method else 'N/A',
                'Orden Monto': float(t.order.amount_usd) if t.order else 0,
                'Porcentaje': f"{(float(t.amount) / float(t.order.amount_usd) * 100):.2f}%" if t.order and t.order.amount_usd > 0 else '0%'
            } for t in fees])
            df_fees.to_excel(writer, sheet_name='Ganancias', index=False)
        
        cls.log_action('excel_exported', {
            'filename': filename,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'transaction_count': len(transactions)
        })
        
        return filename
    
    @classmethod
    def export_to_pdf(cls, start_date, end_date, filename='reporte_contable.pdf'):
        """
        Generar reporte PDF profesional.
        
        SECCIONES:
        1. Portada con logo y período
        2. Resumen ejecutivo
        3. Tabla de transacciones
        4. Gráficos
        5. Conclusiones
        """
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        
        # Crear PDF
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # 1. Portada
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a73e8'),
            spaceAfter=30,
            alignment=1  # Centrado
        )
        
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph('Ceiba21', title_style))
        story.append(Paragraph('Reporte Contable', styles['Heading2']))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(
            f'Período: {start_date.strftime("%d/%m/%Y")} - {end_date.strftime("%d/%m/%Y")}',
            styles['Normal']
        ))
        story.append(PageBreak())
        
        # 2. Resumen ejecutivo
        story.append(Paragraph('Resumen Ejecutivo', styles['Heading1']))
        story.append(Spacer(1, 0.2*inch))
        
        summary = cls.get_balance_summary(start_date, end_date)
        
        summary_data = [
            ['Métrica', 'Valor'],
            ['Ingresos totales (USD)', f"${summary['total_income_usd']:.2f}"],
            ['Ganancias totales (USD)', f"${summary['total_fees_usd']:.2f}"],
            ['Número de órdenes', str(summary['order_count'])],
            ['Fee promedio', f"{summary['average_fee_percentage']:.2f}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(PageBreak())
        
        # 3. Transacciones detalladas
        story.append(Paragraph('Transacciones Detalladas', styles['Heading1']))
        story.append(Spacer(1, 0.2*inch))
        
        transactions = Transaction.query.filter(
            Transaction.created_at.between(start_date, end_date)
        ).order_by(Transaction.created_at.desc()).limit(50).all()
        
        trans_data = [['Fecha', 'Tipo', 'Monto', 'Método', 'Orden']]
        
        for t in transactions:
            trans_data.append([
                t.created_at.strftime('%d/%m %H:%M'),
                t.type.value,
                f"{t.amount:.2f} {t.currency_code}",
                t.payment_method.name if t.payment_method else 'N/A',
                t.order.reference if t.order else 'N/A'
            ])
        
        trans_table = Table(trans_data, colWidths=[1.2*inch, 1*inch, 1.5*inch, 1.5*inch, 1.3*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ]))
        
        story.append(trans_table)
        
        # Construir PDF
        doc.build(story)
        
        cls.log_action('pdf_exported', {
            'filename': filename,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
        return filename
    
    # ==========================================
    # REPORTES AUTOMÁTICOS POR EMAIL
    # ==========================================
    
    @classmethod
    def send_daily_report(cls, recipient_email):
        """
        Enviar reporte diario por email.
        
        CONTENIDO:
        - Resumen del día
        - Top 5 órdenes
        - Ganancias vs ayer
        - Adjunto: Excel con detalle completo
        """
        from datetime import date
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        
        # Generar Excel
        filename = f'reporte_{today.isoformat()}.xlsx'
        cls.export_to_excel(start, end, filename)
        
        # Obtener resumen
        summary = cls.get_balance_summary(start, end)
        
        # Crear email HTML
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #1a73e8; color: white; padding: 20px; }}
                .summary {{ margin: 20px 0; }}
                .metric {{ background-color: #f5f5f5; padding: 10px; margin: 10px 0; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Ceiba21 - Reporte Diario</h1>
                <p>{today.strftime('%d de %B, %Y')}</p>
            </div>
            
            <div class="summary">
                <h2>Resumen del Día</h2>
                
                <div class="metric">
                    <strong>💰 Ingresos:</strong> ${summary['total_income_usd']:.2f} USD
                </div>
                
                <div class="metric">
                    <strong>📈 Ganancias:</strong> ${summary['total_fees_usd']:.2f} USD ({summary['average_fee_percentage']:.2f}%)
                </div>
                
                <div class="metric">
                    <strong>📦 Órdenes completadas:</strong> {summary['order_count']}
                </div>
                
                <div class="metric">
                    <strong>💸 Egresos:</strong><br>
                    {'<br>'.join([f"{k}: {v:,.2f}" for k, v in summary['total_expenses'].items()])}
                </div>
            </div>
            
            <div class="footer">
                <p>Este es un reporte automático generado por el sistema Ceiba21.</p>
                <p>El archivo adjunto contiene el detalle completo de transacciones.</p>
            </div>
        </body>
        </html>
        """
        
        # Enviar email
        msg = MIMEMultipart()
        msg['From'] = 'noreply@ceiba21.com'
        msg['To'] = recipient_email
        msg['Subject'] = f'Ceiba21 - Reporte Diario {today.strftime("%d/%m/%Y")}'
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Adjuntar Excel
        with open(filename, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(part)
        
        # Enviar (usar el sistema de email existente)
        # TODO: Usar el mismo SMTP configurado para alertas
        
        cls.log_action('daily_report_sent', {
            'recipient': recipient_email,
            'date': today.isoformat()
        })
        
        return True
    
    # ==========================================
    # MÉTRICAS Y ANALYTICS
    # ==========================================
    
    @classmethod
    def get_kpis(cls, start_date=None, end_date=None):
        """
        Key Performance Indicators.
        
        RETORNA:
        {
            'total_revenue': 2450.00,
            'total_profit': 131.85,
            'profit_margin': 5.38,
            'average_order_value': 98.00,
            'orders_per_day': 25,
            'top_payment_method': 'PayPal',
            'top_currency': 'VES',
            'growth_vs_previous_period': 12.5
        }
        """
        # Implementar cálculo de KPIs
        # ...
        pass
    
    @classmethod
    def get_growth_metrics(cls, period='month'):
        """
        Métricas de crecimiento.
        
        COMPARA:
        - Período actual vs período anterior
        - Growth rate (%)
        
        USO: Dashboard ejecutivo
        """
        # Implementar métricas de crecimiento
        # ...
        pass
```

---

### 3. Dashboard contable (Vista web)

```python
# app/routes/accounting.py

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from app.services.accounting_service import AccountingService
from app.services.auth_service import AuthService
from datetime import datetime, timedelta

accounting_bp = Blueprint('accounting', __name__, url_prefix='/accounting')

@accounting_bp.route('/dashboard')
@login_required
@AuthService.require_permission('view_reports')
def dashboard():
    """
    Dashboard contable principal.
    
    Muestra:
    - Resumen financiero
    - Gráficos de tendencias
    - Transacciones recientes
    """
    # Obtener período (por defecto: hoy)
    period = request.args.get('period', 'today')
    
    if period == 'today':
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now()
    elif period == 'week':
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
    elif period == 'month':
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
    else:
        # Período personalizado
        start_date = datetime.strptime(request.args.get('start'), '%Y-%m-%d')
        end_date = datetime.strptime(request.args.get('end'), '%Y-%m-%d')
    
    # Obtener datos
    summary = AccountingService.get_balance_summary(start_date, end_date)
    daily_fees = AccountingService.get_daily_fees(days=7)
    fees_by_method = AccountingService.get_fees_by_payment_method(start_date, end_date)
    orders_by_currency = AccountingService.get_orders_by_currency(start_date, end_date)
    
    # Transacciones recientes
    recent_transactions = Transaction.query.filter(
        Transaction.created_at.between(start_date, end_date)
    ).order_by(Transaction.created_at.desc()).limit(20).all()
    
    return render_template(
        'accounting/dashboard.html',
        summary=summary,
        daily_fees=daily_fees,
        fees_by_method=fees_by_method,
        orders_by_currency=orders_by_currency,
        recent_transactions=recent_transactions,
        period=period,
        start_date=start_date,
        end_date=end_date
    )

@accounting_bp.route('/export/excel')
@login_required
@AuthService.require_permission('export_data')
def export_excel():
    """
    Exportar a Excel.
    
    GET /accounting/export/excel?start=2024-12-01&end=2024-12-31
    """
    start_date = datetime.strptime(request.args.get('start'), '%Y-%m-%d')
    end_date = datetime.strptime(request.args.get('end'), '%Y-%m-%d')
    
    filename = AccountingService.export_to_excel(start_date, end_date)
    
    return send_file(
        filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'reporte_ceiba21_{start_date.strftime("%Y%m%d")}_a_{end_date.strftime("%Y%m%d")}.xlsx'
    )

@accounting_bp.route('/export/pdf')
@login_required
@AuthService.require_permission('export_data')
def export_pdf():
    """
    Exportar a PDF.
    """
    start_date = datetime.strptime(request.args.get('start'), '%Y-%m-%d')
    end_date = datetime.strptime(request.args.get('end'), '%Y-%m-%d')
    
    filename = AccountingService.export_to_pdf(start_date, end_date)
    
    return send_file(
        filename,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'reporte_ceiba21_{start_date.strftime("%Y%m%d")}_a_{end_date.strftime("%Y%m%d")}.pdf'
    )

@accounting_bp.route('/send-report', methods=['POST'])
@login_required
@AuthService.require_permission('send_reports')
def send_report():
    """
    Enviar reporte por email.
    
    POST /accounting/send-report
    Body: {"email": "admin@ceiba21.com", "period": "today"}
    """
    email = request.json.get('email')
    period = request.json.get('period', 'today')
    
    try:
        if period == 'today':
            AccountingService.send_daily_report(email)
        else:
            # Implementar para otros períodos
            pass
        
        return jsonify({
            'success': True,
            'message': f'Reporte enviado a {email}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@accounting_bp.route('/api/summary')
@login_required
def api_summary():
    """
    API endpoint para obtener resumen (AJAX).
    
    GET /accounting/api/summary?start=2024-12-01&end=2024-12-31
    """
    start_date = datetime.strptime(request.args.get('start'), '%Y-%m-%d')
    end_date = datetime.strptime(request.args.get('end'), '%Y-%m-%d')
    
    summary = AccountingService.get_balance_summary(start_date, end_date)
    
    # Convertir Decimals a float para JSON
    summary['total_income_usd'] = float(summary['total_income_usd'])
    summary['total_fees_usd'] = float(summary['total_fees_usd'])
    summary['net_profit_usd'] = float(summary['net_profit_usd'])
    summary['average_fee_percentage'] = float(summary['average_fee_percentage'])
    summary['total_expenses'] = {k: float(v) for k, v in summary['total_expenses'].items()}
    
    return jsonify(summary)

@accounting_bp.route('/api/daily-fees')
@login_required
def api_daily_fees():
    """
    API endpoint para gráfico de fees diarios.
    
    GET /accounting/api/daily-fees?days=7
    """
    days = int(request.args.get('days', 7))
    data = AccountingService.get_daily_fees(days)
    
    return jsonify(data)

@accounting_bp.route('/api/fees-by-method')
@login_required
def api_fees_by_method():
    """
    API endpoint para distribución por método.
    """
    start_date = datetime.strptime(request.args.get('start'), '%Y-%m-%d')
    end_date = datetime.strptime(request.args.get('end'), '%Y-%m-%d')
    
    data = AccountingService.get_fees_by_payment_method(start_date, end_date)
    
    return jsonify(data)
```

---

### 4. Alertas automáticas

```python
# app/services/alert_service.py

from app.services.base_service import BaseService
from app.services.accounting_service import AccountingService
from datetime import datetime, timedelta

class AlertService(BaseService):
    """
    Servicio para alertas automáticas.
    
    ALERTAS:
    - Volumen diario bajo
    - Fee promedio bajo
    - Muchas órdenes canceladas
    - Balance negativo en alguna moneda
    """
    
    @classmethod
    def check_daily_volume_alert(cls):
        """
        Verificar si el volumen del día está por debajo del promedio.
        
        UMBRAL: Si volumen < 70% del promedio semanal
        """
        # Volumen de hoy
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_summary = AccountingService.get_balance_summary(today_start, datetime.now())
        today_volume = float(today_summary['total_income_usd'])
        
        # Promedio de últimos 7 días
        week_start = datetime.now() - timedelta(days=7)
        week_summary = AccountingService.get_balance_summary(week_start, datetime.now())
        week_volume = float(week_summary['total_income_usd'])
        daily_average = week_volume / 7
        
        # Verificar umbral
        if today_volume < (daily_average * 0.7):
            cls._send_alert(
                title='📉 Volumen Bajo',
                message=f'El volumen de hoy (${today_volume:.2f}) está por debajo del promedio (${daily_average:.2f})',
                priority='medium'
            )
    
    @classmethod
    def check_low_fee_percentage(cls):
        """
        Verificar si el fee promedio está bajo.
        
        UMBRAL: Si fee < 4%
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        summary = AccountingService.get_balance_summary(today_start, datetime.now())
        
        avg_fee = float(summary['average_fee_percentage'])
        
        if avg_fee < 4.0 and summary['order_count'] > 5:
            cls._send_alert(
                title='⚠️ Fee Promedio Bajo',
                message=f'El fee promedio de hoy es {avg_fee:.2f}% (esperado: ~5.4%)',
                priority='high'
            )
    
    @classmethod
    def check_high_cancellation_rate(cls):
        """
        Verificar si hay muchas órdenes canceladas.
        
        UMBRAL: Si cancelaciones > 20% de órdenes totales
        """
        from app.models.order import Order, OrderStatus
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_orders = Order.query.filter(Order.created_at >= today_start).count()
        cancelled_orders = Order.query.filter(
            Order.created_at >= today_start,
            Order.status == OrderStatus.CANCELLED
        ).count()
        
        if total_orders > 0:
            cancellation_rate = (cancelled_orders / total_orders) * 100
            
            if cancellation_rate > 20:
                cls._send_alert(
                    title='🚨 Tasa de Cancelación Alta',
                    message=f'{cancelled_orders} de {total_orders} órdenes canceladas hoy ({cancellation_rate:.1f}%)',
                    priority='high'
                )
    
    @classmethod
    def _send_alert(cls, title, message, priority='medium'):
        """
        Enviar alerta por múltiples canales.
        
        CANALES:
        - Email a admin
        - Notificación en dashboard
        - Mensaje en Telegram (opcional)
        """
        import subprocess
        
        # Email
        subprocess.run([
            'mail',
            '-s', title,
            'ceiba21.oficial@gmail.com'
        ], input=message.encode())
        
        # Log
        cls.log_action('alert_sent', {
            'title': title,
            'message': message,
            'priority': priority
        })
```

---

### 5. Cron jobs para reportes automáticos

```python
# scripts/daily_accounting_tasks.py

"""
Script para ejecutar tareas contables diarias.

CRON: Ejecutar todos los días a las 23:59
"""

from app import create_app
from app.services.accounting_service import AccountingService
from app.services.alert_service import AlertService

def main():
    app = create_app()
    
    with app.app_context():
        # 1. Enviar reporte diario
        AccountingService.send_daily_report('ceiba21.oficial@gmail.com')
        
        # 2. Verificar alertas
        AlertService.check_daily_volume_alert()
        AlertService.check_low_fee_percentage()
        AlertService.check_high_cancellation_rate()
        
        print("✅ Tareas contables diarias completadas")

if __name__ == '__main__':
    main()
```

**Configurar crontab:**

```bash
# Editar crontab
crontab -e

# Agregar línea:
59 23 * * * cd /var/www/cotizaciones && /var/www/cotizaciones/venv/bin/python scripts/daily_accounting_tasks.py >> /var/www/cotizaciones/logs/accounting.log 2>&1
```

---

## 📁 ARCHIVOS A CREAR

```
app/services/
├── accounting_service.py      # ⭐ Principal
└── alert_service.py            # Alertas automáticas

app/routes/
└── accounting.py               # Dashboard contable

app/templates/
└── accounting/
    ├── dashboard.html          # Vista principal
    ├── transactions.html       # Lista detallada
    └── reports.html            # Configuración de reportes

app/static/
├── css/
│   └── accounting.css          # Estilos específicos
│
└── js/
    └── accounting_charts.js    # Gráficos con Chart.js

scripts/
└── daily_accounting_tasks.py  # Tareas automáticas
```

---

## 📝 ARCHIVOS A MODIFICAR

- `requirements.txt` (agregar pandas, openpyxl, reportlab, etc.)
- `app/__init__.py` (registrar blueprint accounting)
- `app/services/order_service.py` (ya tiene Transaction.create_from_order, verificar que funciona)

---

## 🔧 DEPENDENCIAS NECESARIAS

Agregar a `requirements.txt`:

```txt
# Exportación Excel
pandas==2.1.4
openpyxl==3.1.2
xlsxwriter==3.1.9

# Exportación PDF
reportlab==4.0.7

# Gráficos
matplotlib==3.8.2

# Scheduling (opcional, alternativa a cron)
apscheduler==3.10.4
```

---

## 📊 TEMPLATES HTML

### Dashboard contable

```html
<!-- app/templates/accounting/dashboard.html -->

{% extends "operator/base.html" %}

{% block content %}
<div class="p-6">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-gray-900">Contabilidad</h1>
        
        <!-- Selector de período -->
        <div class="flex space-x-2">
            <button class="px-4 py-2 bg-blue-500 text-white rounded" data-period="today">
                Hoy
            </button>
            <button class="px-4 py-2 bg-gray-200 rounded" data-period="week">
                Esta Semana
            </button>
            <button class="px-4 py-2 bg-gray-200 rounded" data-period="month">
                Este Mes
            </button>
            <button class="px-4 py-2 bg-gray-200 rounded" data-period="custom">
                Personalizado
            </button>
        </div>
    </div>
    
    <!-- Resumen financiero -->
    <div class="grid grid-cols-3 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow p-6">
            <h3 class="text-sm font-medium text-gray-500 mb-2">💰 Ingresos USD</h3>
            <p class="text-3xl font-bold text-gray-900">${{ "%.2f"|format(summary.total_income_usd) }}</p>
            <p class="text-sm text-gray-600 mt-2">{{ summary.order_count }} órdenes</p>
        </div>
        
        <div class="bg-white rounded-lg shadow p-6">
            <h3 class="text-sm font-medium text-gray-500 mb-2">💸 Egresos</h3>
            {% for currency, amount in summary.total_expenses.items() %}
            <p class="text-xl font-bold text-gray-900">{{ currency }}: {{ "{:,.2f}"|format(amount) }}</p>
            {% endfor %}
        </div>
        
        <div class="bg-white rounded-lg shadow p-6">
            <h3 class="text-sm font-medium text-gray-500 mb-2">📈 Ganancias USD</h3>
            <p class="text-3xl font-bold text-green-600">${{ "%.2f"|format(summary.total_fees_usd) }}</p>
            <p class="text-sm text-gray-600 mt-2">{{ "%.2f"|format(summary.average_fee_percentage) }}% promedio</p>
        </div>
    </div>
    
    <!-- Gráficos -->
    <div class="grid grid-cols-2 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow p-6">
            <h3 class="text-lg font-bold mb-4">Ganancias por Día</h3>
            <canvas id="daily-fees-chart"></canvas>
        </div>
        
        <div class="bg-white rounded-lg shadow p-6">
            <h3 class="text-lg font-bold mb-4">Distribución por Método</h3>
            <canvas id="fees-by-method-chart"></canvas>
        </div>
    </div>
    
    <!-- Transacciones recientes -->
    <div class="bg-white rounded-lg shadow">
        <div class="p-6 border-b border-gray-200">
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-bold">Transacciones Recientes</h3>
                <div class="space-x-2">
                    <button onclick="exportExcel()" class="px-4 py-2 bg-green-600 text-white rounded">
                        📥 Exportar Excel
                    </button>
                    <button onclick="exportPDF()" class="px-4 py-2 bg-red-600 text-white rounded">
                        📄 Generar PDF
                    </button>
                </div>
            </div>
        </div>
        
        <table class="min-w-full">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Monto</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Método</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Orden</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                {% for t in recent_transactions %}
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {{ t.created_at.strftime('%H:%M') }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        {% if t.type.value == 'income' %}
                        <span class="px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800">
                            💵 INCOME
                        </span>
                        {% elif t.type.value == 'fee' %}
                        <span class="px-2 py-1 text-xs font-semibold rounded bg-green-100 text-green-800">
                            📈 FEE
                        </span>
                        {% else %}
                        <span class="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">
                            💸 EXPENSE
                        </span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {{ "{:,.2f}"|format(t.amount) }} {{ t.currency_code }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {{ t.payment_method.name if t.payment_method else 'N/A' }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-blue-600">
                        <a href="{{ url_for('operator.order_detail', order_id=t.order_id) }}">
                            {{ t.order.reference if t.order else 'N/A' }}
                        </a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="{{ url_for('static', filename='js/accounting_charts.js') }}"></script>
<script>
// Datos para gráficos
const dailyFeesData = {{ daily_fees|tojson }};
const feesByMethodData = {{ fees_by_method|tojson }};

// Inicializar gráficos
initCharts(dailyFeesData, feesByMethodData);

// Funciones de exportación
function exportExcel() {
    const start = '{{ start_date.strftime("%Y-%m-%d") }}';
    const end = '{{ end_date.strftime("%Y-%m-%d") }}';
    window.location.href = `/accounting/export/excel?start=${start}&end=${end}`;
}

function exportPDF() {
    const start = '{{ start_date.strftime("%Y-%m-%d") }}';
    const end = '{{ end_date.strftime("%Y-%m-%d") }}';
    window.location.href = `/accounting/export/pdf?start=${start}&end=${end}`;
}
</script>
{% endblock %}
```

---

### JavaScript para gráficos

```javascript
// app/static/js/accounting_charts.js

function initCharts(dailyFeesData, feesByMethodData) {
    // Gráfico de línea: Ganancias por día
    const ctxLine = document.getElementById('daily-fees-chart').getContext('2d');
    new Chart(ctxLine, {
        type: 'line',
        data: {
            labels: dailyFeesData.map(d => {
                const date = new Date(d.date);
                return date.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric' });
            }),
            datasets: [{
                label: 'Ganancias USD',
                data: dailyFeesData.map(d => d.fees),
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '$' + context.parsed.y.toFixed(2) + ' USD';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value;
                        }
                    }
                }
            }
        }
    });
    
    // Gráfico de pie: Distribución por método
    const ctxPie = document.getElementById('fees-by-method-chart').getContext('2d');
    new Chart(ctxPie, {
        type: 'pie',
        data: {
            labels: feesByMethodData.map(d => d.method),
            datasets: [{
                data: feesByMethodData.map(d => d.fees),
                backgroundColor: [
                    'rgb(255, 99, 132)',
                    'rgb(54, 162, 235)',
                    'rgb(255, 205, 86)',
                    'rgb(75, 192, 192)',
                    'rgb(153, 102, 255)'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const percentage = feesByMethodData[context.dataIndex].percentage;
                            return label + ': $' + value.toFixed(2) + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}
```

---

## 🧪 TESTING

### Tests de AccountingService

```python
# tests/test_accounting_service.py

import pytest
from datetime import datetime, timedelta
from app.services.accounting_service import AccountingService
from app.models.order import Order, OrderStatus
from app.models.transaction import Transaction

def test_get_balance_summary(db_session):
    """Test cálculo de resumen financiero"""
    # Crear orden de prueba
    order = create_test_order(amount_usd=100, fee_usd=5.70)
    order.status = OrderStatus.COMPLETED
    order.save()
    
    # Generar transacciones
    Transaction.create_from_order(order)
    
    # Obtener resumen
    summary = AccountingService.get_balance_summary()
    
    assert summary['total_income_usd'] == 100.00
    assert summary['total_fees_usd'] == 5.70
    assert summary['order_count'] == 1

def test_export_to_excel(db_session, tmp_path):
    """Test exportación a Excel"""
    # Crear órdenes de prueba
    create_test_orders(count=5)
    
    # Exportar
    filename = AccountingService.export_to_excel(
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now(),
        filename=str(tmp_path / 'test.xlsx')
    )
    
    # Verificar que se creó el archivo
    assert os.path.exists(filename)

def test_daily_fees(db_session):
    """Test serie temporal de fees"""
    # Crear órdenes en diferentes días
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        order = create_test_order(created_at=date)
        order.status = OrderStatus.COMPLETED
        order.save()
        Transaction.create_from_order(order)
    
    # Obtener fees diarios
    daily_fees = AccountingService.get_daily_fees(days=7)
    
    assert len(daily_fees) == 7
    assert all('date' in d and 'fees' in d for d in daily_fees)
```

---

## 🎯 CHECKLIST DE IMPLEMENTACIÓN

### Fase 6a: AccountingService base (Día 1)

- [ ] Crear `app/services/accounting_service.py`
- [ ] Implementar `get_balance_summary()`
- [ ] Implementar `get_daily_fees()`
- [ ] Implementar `get_fees_by_payment_method()`
- [ ] Implementar `get_orders_by_currency()`
- [ ] Testing: Métodos de cálculo funcionan

### Fase 6b: Exportación Excel (Día 2)

- [ ] Instalar pandas, openpyxl
- [ ] Implementar `export_to_excel()`
- [ ] Crear múltiples hojas (resumen, ingresos, gastos, ganancias)
- [ ] Testing: Excel se genera correctamente

### Fase 6c: Exportación PDF (Día 2-3)

- [ ] Instalar reportlab
- [ ] Implementar `export_to_pdf()`
- [ ] Diseño profesional con logo y gráficos
- [ ] Testing: PDF se ve bien

### Fase 6d: Dashboard contable (Día 3-4)

- [ ] Crear `app/routes/accounting.py`
- [ ] Template `accounting/dashboard.html`
- [ ] Integrar Chart.js
- [ ] Selectores de período
- [ ] Testing: Dashboard muestra datos correctos

### Fase 6e: API endpoints (Día 4)

- [ ] Endpoint `/api/summary`
- [ ] Endpoint `/api/daily-fees`
- [ ] Endpoint `/api/fees-by-method`
- [ ] Endpoint `/export/excel`
- [ ] Endpoint `/export/pdf`
- [ ] Testing: Endpoints funcionan

### Fase 6f: Reportes automáticos (Día 5)

- [ ] Implementar `send_daily_report()`
- [ ] Crear script `daily_accounting_tasks.py`
- [ ] Configurar crontab
- [ ] Testing: Email llega correctamente

### Fase 6g: Sistema de alertas (Día 5)

- [ ] Crear `app/services/alert_service.py`
- [ ] Implementar alertas: volumen bajo, fee bajo, cancelaciones altas
- [ ] Integrar en cron job diario
- [ ] Testing: Alertas se disparan correctamente

### Fase 6h: Testing completo (Día 6)

- [ ] Tests unitarios de AccountingService
- [ ] Tests de exportación
- [ ] Tests de alertas
- [ ] Testing en producción

### Fase 6i: Documentación

- [ ] Documentar uso del dashboard
- [ ] Documentar exportación de reportes
- [ ] Documentar configuración de alertas

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### 1. Performance

- ✅ Caché de métricas en Redis (5 minutos)
- ✅ Índices en BD (transaction.created_at, transaction.type)
- ✅ Pagination en lista de transacciones
- ✅ Generación de PDF/Excel en background (Celery, futuro)

### 2. Precisión numérica

- ✅ Usar Decimal para todos los cálculos monetarios
- ✅ NUNCA usar float para dinero
- ✅ Redondear correctamente (2 decimales para USD, 2 para locales)

### 3. Seguridad

- ✅ Solo ADMIN puede ver dashboard contable
- ✅ Solo ADMIN puede exportar datos
- ✅ Logs de auditoría en exportaciones

### 4. Escalabilidad

- ✅ Archivos Excel/PDF grandes → guardar en disco, no enviar directo
- ✅ Usar worker background para reportes pesados (Celery)
- ✅ Limpieza automática de archivos antiguos (>30 días)

---

## ✅ CRITERIOS DE ÉXITO

Al finalizar la Fase 6, el sistema debe:

1. ✅ Generar transacciones automáticamente al completar orden
2. ✅ Dashboard contable muestra resumen financiero en tiempo real
3. ✅ Gráficos de tendencias funcionan correctamente
4. ✅ Exportar a Excel con múltiples hojas
5. ✅ Generar PDF profesional con logo y tablas
6. ✅ Enviar reporte diario automático por email
7. ✅ Alertas de volumen bajo, fee bajo, cancelaciones altas
8. ✅ Todos los cálculos son precisos (Decimal)
9. ✅ Permisos respetados (solo ADMIN ve contabilidad)
10. ✅ Métricas históricas disponibles (7, 30, 90 días)

---

## 🎬 PRÓXIMOS PASOS (FASE 7 - OPCIONAL)

Después de completar la Fase 6, funcionalidades opcionales:

**FASE 7: Registro de usuarios web**
- Usuarios pueden registrarse en ceiba21.com
- Dashboard de usuario (ver sus órdenes)
- Verificación de email
- Recuperación de contraseña

**FASE 8: WebChat en vivo**
- Chat en vivo en sitio web sin depender de Telegram/WhatsApp
- Widget flotante
- WebSocket para tiempo real

**FASE 9: WhatsApp Bot**
- Bot de WhatsApp (igual que Telegram)
- Twilio API

**FASE 10: App móvil**
- App nativa con Flutter
- Push notifications
- Biometría para login

---

**Autor:** Jose (Ceiba21)  
**Asistente:** Claude (Anthropic)  
**Fecha:** Diciembre 2024  
**Versión:** 1.0
