"""
Conciliación automática de pagos con órdenes.

Replica la heurística que usa el operador humano: **método + monto + nombre del
titular**, con la hora como desempate. La referencia de transacción NO se usa
como señal principal porque no es fiable (en PayPal el ID del remitente y el del
receptor difieren; en Zelle la referencia ni siquiera llega al correo).

Se compara el importe **BRUTO** del pago contra ``order.amount_usd`` (lo que el
cliente dijo que iba a enviar). Así la comisión —variable según sea F&F, G&S o
tarjeta— no afecta la comparación: el bruto es lo que el cliente tecleó.

Ante la duda, NUNCA se adivina: si hay dos candidatos parejos, el pago se marca
para revisión manual.
"""
import re
import unicodedata
from datetime import timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from app.services.base_service import BaseService
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus

# Filtros duros
VENTANA_ORDENES_DIAS = 7      # antigüedad máxima de la orden candidata
VENTANA_PAGO_HORAS = 24       # separación máxima entre el pago y la orden
TOLERANCIA_DE_MAS = Decimal('1.00')   # el cliente puede redondear hacia arriba
TOLERANCIA_EXACTA = Decimal('0.01')

# Puntajes
PUNTOS_MONTO_EXACTO = 45
PUNTOS_MONTO_DE_MAS = 35
PUNTOS_NOMBRE_ALTO = 35
PUNTOS_NOMBRE_MEDIO = 20
PUNTOS_TIEMPO_CERCANO = 20    # dentro de 2 horas
PUNTOS_TIEMPO_LEJANO = 10     # dentro de 24 horas
PUNTOS_REFERENCIA = 100       # si el cliente escribió la referencia en el memo

UMBRAL_VINCULACION = 80
MARGEN_EMPATE = 10            # si dos candidatos difieren menos: revisión manual


class ReconciliationService(BaseService):
    """Casa pagos entrantes con órdenes pendientes."""

    # ── Normalización y comparación de nombres ─────────────────────────────

    @staticmethod
    def _normalizar(nombre: str) -> str:
        """Quitar acentos, signos y mayúsculas para poder comparar nombres."""
        if not nombre:
            return ''
        sin_acentos = ''.join(
            c for c in unicodedata.normalize('NFD', nombre)
            if unicodedata.category(c) != 'Mn'
        )
        limpio = re.sub(r'[^a-z ]', ' ', sin_acentos.lower())
        return ' '.join(limpio.split())

    @classmethod
    def similitud_nombres(cls, uno: str, otro: str) -> float:
        """
        Similitud entre dos nombres, de 0 a 1.

        Compara también los nombres con las palabras ordenadas, para que
        "Mora Jose" y "Jose Mora" se reconozcan como la misma persona.
        """
        a, b = cls._normalizar(uno), cls._normalizar(otro)
        if not a or not b:
            return 0.0

        directa = SequenceMatcher(None, a, b).ratio()
        ordenada = SequenceMatcher(
            None, ' '.join(sorted(a.split())), ' '.join(sorted(b.split()))
        ).ratio()
        return max(directa, ordenada)

    # ── Puntaje de un candidato ────────────────────────────────────────────

    @classmethod
    def _puntuar_monto(cls, pago: Payment, orden: Order) -> Tuple[int, str]:
        """
        Puntuar la coincidencia de importes.

        Se compara el BRUTO del pago (lo que el cliente envió) contra el
        amount_usd de la orden (lo que dijo que enviaría). La comisión no entra
        en la comparación porque es variable (F&F, G&S, tarjeta).
        """
        bruto = Decimal(str(pago.importe_bruto or 0))
        esperado = Decimal(str(orden.amount_usd or 0))
        diferencia = bruto - esperado

        if abs(diferencia) <= TOLERANCIA_EXACTA:
            return PUNTOS_MONTO_EXACTO, 'monto exacto'

        if Decimal('0') < diferencia <= TOLERANCIA_DE_MAS:
            return PUNTOS_MONTO_DE_MAS, f'envió ${diferencia:.2f} de más'

        return 0, ''

    @classmethod
    def _puntuar_nombre(cls, pago: Payment, orden: Order) -> Tuple[int, str]:
        """Puntuar el parecido entre el pagador y el titular de la orden."""
        similitud = cls.similitud_nombres(
            pago.pagador_nombre or '', orden.client_holder or ''
        )
        if similitud >= 0.85:
            return PUNTOS_NOMBRE_ALTO, 'nombre coincide'
        if similitud >= 0.65:
            return PUNTOS_NOMBRE_MEDIO, 'nombre parecido'
        return 0, ''

    @classmethod
    def _puntuar_tiempo(cls, pago: Payment, orden: Order) -> Tuple[int, str]:
        """Puntuar la cercanía temporal entre el pago y la orden."""
        if not pago.fecha_pago or not orden.created_at:
            return 0, ''

        distancia = abs(pago.fecha_pago - orden.created_at)
        if distancia <= timedelta(hours=2):
            return PUNTOS_TIEMPO_CERCANO, 'misma franja horaria'
        if distancia <= timedelta(hours=VENTANA_PAGO_HORAS):
            return PUNTOS_TIEMPO_LEJANO, 'mismo día'
        return 0, ''

    @classmethod
    def _puntuar_referencia(cls, pago: Payment, orden: Order) -> Tuple[int, str]:
        """Bonus: el cliente escribió la referencia de la orden en el memo."""
        texto = f"{pago.memo or ''} {pago.notas or ''}".upper()
        if orden.reference and orden.reference.upper() in texto:
            return PUNTOS_REFERENCIA, 'referencia en el memo'
        return 0, ''

    @classmethod
    def puntuar(cls, pago: Payment, orden: Order) -> Tuple[int, List[str]]:
        """
        Puntaje total de un par (pago, orden) y los motivos que lo sustentan.

        Returns:
            Tupla (puntaje, lista de motivos legibles).
        """
        total, motivos = 0, []

        for puntuador in (cls._puntuar_monto, cls._puntuar_nombre,
                          cls._puntuar_tiempo, cls._puntuar_referencia):
            puntos, motivo = puntuador(pago, orden)
            total += puntos
            if motivo:
                motivos.append(motivo)

        return total, motivos

    # ── Búsqueda de candidatos y vinculación ───────────────────────────────

    @staticmethod
    def _metodo_de_orden(orden: Order) -> str:
        """Código normalizado del método con el que paga el cliente."""
        metodo = orden.payment_method_from
        return (metodo.code or metodo.name or '').lower() if metodo else ''

    @staticmethod
    def _dentro_de_ventana(pago: Payment, orden: Order) -> bool:
        """True si el pago cae dentro de la ventana temporal de la orden."""
        if not pago.fecha_pago or not orden.created_at:
            return False
        distancia = abs(pago.fecha_pago - orden.created_at)
        return distancia <= timedelta(hours=VENTANA_PAGO_HORAS)

    @classmethod
    def buscar_candidatos(cls, pago: Payment) -> List[dict]:
        """
        Órdenes que podrían corresponder a un pago, ordenadas por puntaje.

        Filtros duros: mismo método, orden en PENDING (con comprobante subido),
        de los últimos días y con el pago dentro de la ventana temporal.

        Returns:
            Lista de dicts con la orden, su puntaje y los motivos.
        """
        from app.models import db  # noqa: F401  (asegura el registro de modelos)

        desde = pago.fecha_pago - timedelta(days=VENTANA_ORDENES_DIAS) \
            if pago.fecha_pago else None

        consulta = Order.query.filter(Order.status == OrderStatus.PENDING)
        if desde is not None:
            consulta = consulta.filter(Order.created_at >= desde)

        candidatos = []
        for orden in consulta.all():
            if cls._metodo_de_orden(orden) != (pago.metodo or '').lower():
                continue

            # Filtro DURO de ventana temporal: un pago fuera de las 24 h de la
            # orden no es candidato, por mucho que coincidan monto y nombre.
            if not cls._dentro_de_ventana(pago, orden):
                continue

            puntos, motivos = cls.puntuar(pago, orden)
            if puntos <= 0:
                continue

            candidatos.append({
                'order': orden,
                'reference': orden.reference,
                'score': puntos,
                'motivos': motivos,
            })

        return sorted(candidatos, key=lambda c: c['score'], reverse=True)

    @classmethod
    def vincular(cls, pago: Payment, orden: Order,
                 automatico: bool = True) -> bool:
        """Vincular un pago a una orden (sin cambiar el estado de la orden)."""
        pago.order_id = orden.id
        pago.set_dato_extra('conciliacion', 'automatica' if automatico else 'manual')
        if not pago.save():
            cls.log_error(f"No se pudo vincular el pago {pago.id}")
            return False

        cls.log_info(
            f"Pago {pago.id} vinculado a la orden {orden.reference} "
            f"({'auto' if automatico else 'manual'})"
        )
        return True

    @classmethod
    def conciliar(cls, pago: Payment) -> Optional[dict]:
        """
        Intentar conciliar un pago recién ingresado.

        Vincula solo si hay un candidato claro. Si dos candidatos están
        empatados, marca el pago para revisión: con dinero de por medio, ante la
        duda no se adivina.

        Returns:
            Dict con el resultado ('vinculado' / 'revision' / 'sin_candidatos').
        """
        if pago.order_id:
            return {'resultado': 'ya_conciliado'}

        candidatos = cls.buscar_candidatos(pago)
        if not candidatos:
            return {'resultado': 'sin_candidatos'}

        mejor = candidatos[0]
        if mejor['score'] < UMBRAL_VINCULACION:
            return {'resultado': 'sin_candidatos', 'mejor_score': mejor['score']}

        # ¿Hay un segundo candidato demasiado parecido? -> no adivinar
        if len(candidatos) > 1:
            segundo = candidatos[1]
            if (mejor['score'] - segundo['score']) < MARGEN_EMPATE:
                cls._marcar_revision(pago, candidatos[:3])
                return {
                    'resultado': 'revision',
                    'candidatos': [c['reference'] for c in candidatos[:3]],
                }

        if cls.vincular(pago, mejor['order']):
            return {
                'resultado': 'vinculado',
                'reference': mejor['reference'],
                'score': mejor['score'],
                'motivos': mejor['motivos'],
            }
        return {'resultado': 'error'}

    @classmethod
    def _marcar_revision(cls, pago: Payment, candidatos: List[dict]) -> None:
        """Dejar el pago en revisión manual, con los candidatos empatados."""
        pago.estado = PaymentStatus.REVISION
        pago.set_dato_extra(
            'conciliacion_candidatos',
            [{'reference': c['reference'], 'score': c['score']} for c in candidatos]
        )
        pago.save()
        cls.log_info(
            f"Pago {pago.id} en revisión: candidatos empatados "
            f"({[c['reference'] for c in candidatos]})"
        )

    @classmethod
    def buscar_pago_para_orden(cls, orden: Order) -> Optional[Payment]:
        """
        Buscar un pago ya recibido que corresponda a una orden recién creada.

        Cubre el caso real de que el cliente pague ANTES de terminar el flujo
        del bot (o de que el correo llegue primero).
        """
        desde = orden.created_at - timedelta(hours=VENTANA_PAGO_HORAS)

        pagos = (
            Payment.query
            .filter(Payment.order_id.is_(None))
            .filter(Payment.fecha_pago >= desde)
            .all()
        )

        mejor, mejor_score = None, 0
        for pago in pagos:
            if cls._metodo_de_orden(orden) != (pago.metodo or '').lower():
                continue
            if not cls._dentro_de_ventana(pago, orden):
                continue
            puntos, _ = cls.puntuar(pago, orden)
            if puntos > mejor_score:
                mejor, mejor_score = pago, puntos

        if mejor is not None and mejor_score >= UMBRAL_VINCULACION:
            cls.vincular(mejor, orden)
            return mejor
        return None

    @classmethod
    def marcar_pagado(cls, orden: Order) -> bool:
        """
        Marcar como PAGADO el pago vinculado a una orden completada.

        Cierra el ciclo: al pagarle al cliente desde el chat, el pago deja de
        estar pendiente en /dashboard/pagos sin tocar dos paneles.
        """
        pago = Payment.query.filter_by(order_id=orden.id).first()
        if pago is None:
            return False

        pago.estado = PaymentStatus.PAGADO
        if not pago.save():
            return False

        cls.log_info(f"Pago {pago.id} marcado como PAGADO (orden {orden.reference})")
        return True
