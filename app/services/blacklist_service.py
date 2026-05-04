"""
Servicio de Blacklist - Gestión de clientes bloqueados.

RESPONSABILIDADES:
- CRUD de reportes de blacklist
- Búsqueda avanzada
- Gestión de apelaciones
- Validaciones y verificaciones
"""
from app.services.base_service import BaseService
from app.models.blacklist import (
    BlacklistEntry, BlacklistAppeal,
    BlacklistType, BlacklistCategory, BlacklistStatus, AppealStatus
)
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models import db
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import or_
import json


class BlacklistService(BaseService):
    """
    Servicio para gestión completa de blacklist.
    """
    
    # ==========================================
    # CRUD BLACKLIST
    # ==========================================
    
    @classmethod
    def create_report(cls,
                     operator_id: int,
                     reason: str,
                     category: str = 'OTHER',
                     block_type: str = 'PERMANENT',
                     severity: int = 3,
                     user_id: Optional[int] = None,
                     telegram_id: Optional[int] = None,
                     phone: Optional[str] = None,
                     email: Optional[str] = None,
                     dni: Optional[str] = None,
                     full_name: Optional[str] = None,
                     detailed_notes: Optional[str] = None,
                     evidence_urls: Optional[List[str]] = None,
                     order_references: Optional[str] = None,
                     expires_at: Optional[datetime] = None,
                     run_fraud_check: bool = False,
                     country: Optional[str] = None,
                     state: Optional[str] = None,
                     transaction_type: Optional[str] = None,
                     bank_info: Optional[str] = None,
                     additional_info: Optional[str] = None,
                     photo_url: Optional[str] = None,
                     scam_links: Optional[str] = None,
                     reporter_name: Optional[str] = 'ceiba21') -> Tuple[bool, str, Optional[BlacklistEntry]]:
        """
        Crear nuevo reporte de blacklist.
        
        Permite bloqueo preventivo sin user_id (por datos identificatorios).
        
        Args:
            operator_id: ID del operador que crea el reporte
            reason: Razón del bloqueo (requerido)
            category: Categoría del bloqueo
            block_type: Tipo de bloqueo (PERMANENT, TEMPORARY, SUSPENDED)
            severity: Severidad 1-5
            user_id: ID del usuario (opcional)
            telegram_id: ID de Telegram (opcional)
            phone: Teléfono (opcional)
            email: Email (opcional)
            dni: DNI/Cédula (opcional)
            full_name: Nombre completo (opcional)
            detailed_notes: Notas adicionales
            evidence_urls: Lista de URLs de evidencia
            order_references: Referencias de órdenes relacionadas
            expires_at: Fecha de expiración (solo para TEMPORARY)
            run_fraud_check: Si ejecutar verificación de fraude
            
        Returns:
            (success, message, blacklist_entry)
        """
        try:
            # Validar que al menos un identificador exista
            if not any([user_id, telegram_id, phone, email, dni]):
                return False, "Debes proporcionar al menos un identificador (user_id, telegram_id, phone, email o dni)", None
            
            # Si hay user_id, obtener datos del usuario
            if user_id:
                user = User.find_by_id(user_id)
                if not user:
                    return False, f"Usuario con ID {user_id} no encontrado", None
                
                # Completar datos faltantes del usuario
                telegram_id = telegram_id or user.telegram_id
                phone = phone or user.phone
                email = email or user.email
                full_name = full_name or user.get_display_name()
            
            # Verificar duplicados
            existing = cls._check_duplicates(telegram_id, phone, email, dni)
            if existing:
                return False, f"Ya existe un reporte activo (ID: {existing.id}): {existing.reason}", None
            
            # Ejecutar fraud check si está habilitado
            fraud_result = None
            risk_score = 0
            if run_fraud_check:
                try:
                    from app.services.fraud_check_service import FraudCheckService
                    fraud_result = FraudCheckService.check_all(
                        telegram_id=telegram_id,
                        phone=phone,
                        email=email
                    )
                    risk_score = fraud_result.get('risk_score', 0)
                except Exception as e:
                    cls.log_error('fraud_check_failed', {'error': str(e)})
            
            # Validar tipo de bloqueo
            try:
                block_type_enum = BlacklistType[block_type.upper()]
                category_enum = BlacklistCategory[category.upper()]
            except KeyError as e:
                return False, f"Tipo de bloqueo o categoría inválida: {str(e)}", None
            
            # Si es temporal, debe tener fecha de expiración
            if block_type_enum == BlacklistType.TEMPORARY and not expires_at:
                return False, "Los bloqueos temporales deben tener una fecha de expiración", None
            
            # Crear entrada
            entry = BlacklistEntry(
                user_id=user_id,
                telegram_id=telegram_id,
                phone=phone,
                email=email,
                dni=dni,
                full_name=full_name,
                block_type=block_type_enum,
                category=category_enum,
                status=BlacklistStatus.ACTIVE,
                reason=reason,
                detailed_notes=detailed_notes,
                blocked_by_operator_id=operator_id,
                expires_at=expires_at,
                severity=severity,
                evidence_urls=json.dumps(evidence_urls) if evidence_urls else None,
                order_references=order_references,
                fraud_check_result=fraud_result,
                risk_score=risk_score,
                country=country,
                state=state,
                transaction_type=transaction_type,
                bank_info=bank_info,
                additional_info=additional_info,
                photo_url=photo_url,
                scam_links=scam_links,
                reporter_name=reporter_name
            )
            
            if not entry.save():
                return False, "Error al guardar el reporte en la base de datos", None
            
            # Si hay user_id, actualizar usuario
            if user_id:
                user = User.find_by_id(user_id)
                user.is_blocked = True
                user.is_active = False
                user.save()
                
                # Cancelar órdenes pendientes
                cls._cancel_pending_orders(user_id, f"Usuario bloqueado: {reason}")
            
            cls.log_action('blacklist_created', {
                'entry_id': entry.id,
                'operator_id': operator_id,
                'category': category,
                'user_id': user_id
            })
            
            return True, "Reporte creado exitosamente", entry
            
        except Exception as e:
            cls.log_error('create_report_failed', {'error': str(e)})
            return False, f"Error al crear reporte: {str(e)}", None
    
    @classmethod
    def update_status(cls,
                     blacklist_id: int,
                     new_status: str,
                     operator_id: int,
                     reason: Optional[str] = None,
                     new_block_type: Optional[str] = None,
                     new_expires_at: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Actualizar estatus de un reporte.
        
        Permite cambiar:
        - ACTIVE → EXPIRED
        - ACTIVE → REVOKED (desbloquear)
        - TEMPORARY ↔ PERMANENT
        - SUSPENDED → ACTIVE
        etc.
        
        Args:
            blacklist_id: ID del reporte
            new_status: Nuevo estado
            operator_id: ID del operador
            reason: Razón del cambio (requerido para REVOKED)
            new_block_type: Nuevo tipo de bloqueo (opcional)
            new_expires_at: Nueva fecha de expiración (opcional)
            
        Returns:
            (success, message)
        """
        try:
            entry = BlacklistEntry.find_by_id(blacklist_id)
            if not entry:
                return False, "Reporte no encontrado"
            
            old_status = entry.status
            
            # Validar nuevo estado
            try:
                new_status_enum = BlacklistStatus[new_status.upper()]
            except KeyError:
                return False, f"Estado inválido: {new_status}"
            
            entry.status = new_status_enum
            
            # Si se está desbloqueando
            if new_status_enum == BlacklistStatus.REVOKED:
                if not reason:
                    return False, "Debes proporcionar una razón para desbloquear"
                
                entry.unblocked_at = datetime.utcnow()
                entry.unblocked_by_operator_id = operator_id
                entry.unblock_reason = reason
                
                # Actualizar usuario si existe
                if entry.user_id:
                    user = User.find_by_id(entry.user_id)
                    # Verificar que no tenga otros bloqueos activos
                    other_blocks = cls._has_other_active_blocks(entry.user_id, blacklist_id)
                    if not other_blocks:
                        user.is_blocked = False
                        user.is_active = True
                        user.save()
            
            # Si se cambia tipo de bloqueo
            if new_block_type:
                try:
                    entry.block_type = BlacklistType[new_block_type.upper()]
                    if new_expires_at:
                        entry.expires_at = new_expires_at
                except KeyError:
                    return False, f"Tipo de bloqueo inválido: {new_block_type}"
            
            if not entry.save():
                return False, "Error al actualizar el reporte"
            
            cls.log_action('blacklist_status_updated', {
                'entry_id': blacklist_id,
                'old_status': old_status.value,
                'new_status': new_status,
                'operator_id': operator_id
            })
            
            return True, f"Estatus actualizado de {old_status.value} a {new_status}"
            
        except Exception as e:
            cls.log_error('update_status_failed', {'error': str(e)})
            return False, f"Error al actualizar estatus: {str(e)}"
    
    @classmethod
    def update_report(cls,
                     blacklist_id: int,
                     operator_id: int,
                     **kwargs) -> Tuple[bool, str]:
        """
        Actualizar campos de un reporte.
        
        Args:
            blacklist_id: ID del reporte
            operator_id: ID del operador
            **kwargs: Campos a actualizar
            
        Returns:
            (success, message)
        """
        try:
            entry = BlacklistEntry.find_by_id(blacklist_id)
            if not entry:
                return False, "Reporte no encontrado"
            
            # Campos editables
            editable_fields = [
                'reason', 'detailed_notes', 'severity', 
                'evidence_urls', 'order_references', 'full_name'
            ]
            
            updated_fields = []
            for field, value in kwargs.items():
                if field in editable_fields and value is not None:
                    setattr(entry, field, value)
                    updated_fields.append(field)
            
            if not entry.save():
                return False, "Error al actualizar el reporte"
            
            cls.log_action('blacklist_updated', {
                'entry_id': blacklist_id,
                'operator_id': operator_id,
                'fields': updated_fields
            })
            
            return True, f"Reporte actualizado ({len(updated_fields)} campos modificados)"
            
        except Exception as e:
            cls.log_error('update_report_failed', {'error': str(e)})
            return False, f"Error al actualizar reporte: {str(e)}"
    
    @classmethod
    def delete_report(cls,
                     blacklist_id: int,
                     operator_id: int) -> Tuple[bool, str]:
        """
        Eliminar un reporte (soft delete - cambiar a REVOKED).
        
        Args:
            blacklist_id: ID del reporte
            operator_id: ID del operador
            
        Returns:
            (success, message)
        """
        return cls.update_status(
            blacklist_id=blacklist_id,
            new_status='REVOKED',
            operator_id=operator_id,
            reason='Reporte eliminado por operador'
        )
    
    # ==========================================
    # BÚSQUEDA Y CONSULTA
    # ==========================================
    
    @classmethod
    def search(cls,
              query: Optional[str] = None,
              telegram_id: Optional[int] = None,
              phone: Optional[str] = None,
              email: Optional[str] = None,
              dni: Optional[str] = None,
              report_id: Optional[int] = None,
              category: Optional[str] = None,
              status: Optional[str] = None,
              min_severity: Optional[int] = None,
              limit: int = 100) -> List[BlacklistEntry]:
        """
        Búsqueda avanzada con múltiples filtros.
        
        Args:
            query: Búsqueda de texto general
            telegram_id: Filtrar por Telegram ID
            phone: Filtrar por teléfono
            email: Filtrar por email
            dni: Filtrar por DNI
            report_id: Buscar por ID específico
            category: Filtrar por categoría
            status: Filtrar por estado
            min_severity: Severidad mínima
            limit: Máximo de resultados
            
        Returns:
            Lista de BlacklistEntry
        """
        try:
            filters = []
            
            # Búsqueda por ID de reporte
            if report_id:
                entry = BlacklistEntry.find_by_id(report_id)
                return [entry] if entry else []
            
            # Búsqueda por identificadores específicos
            if telegram_id:
                filters.append(BlacklistEntry.telegram_id == telegram_id)
            
            if phone:
                filters.append(BlacklistEntry.phone.like(f'%{phone}%'))
            
            if email:
                filters.append(BlacklistEntry.email.like(f'%{email}%'))
            
            if dni:
                filters.append(BlacklistEntry.dni.like(f'%{dni}%'))
            
            # Búsqueda por texto general
            if query:
                filters.append(
                    or_(
                        BlacklistEntry.reason.ilike(f'%{query}%'),
                        BlacklistEntry.detailed_notes.ilike(f'%{query}%'),
                        BlacklistEntry.full_name.ilike(f'%{query}%')
                    )
                )
            
            # Filtros adicionales
            if category:
                try:
                    filters.append(BlacklistEntry.category == BlacklistCategory[category.upper()])
                except KeyError:
                    pass
            
            if status:
                try:
                    filters.append(BlacklistEntry.status == BlacklistStatus[status.upper()])
                except KeyError:
                    pass
            
            if min_severity:
                filters.append(BlacklistEntry.severity >= min_severity)
            
            # Si no hay filtros, retornar todos los activos
            if not filters:
                filters.append(BlacklistEntry.status == BlacklistStatus.ACTIVE)
            
            return BlacklistEntry.query.filter(*filters).order_by(
                BlacklistEntry.blocked_at.desc()
            ).limit(limit).all()
            
        except Exception as e:
            cls.log_error('search_failed', {'error': str(e)})
            return []
    
    @classmethod
    def get_all_active(cls, limit: int = 100) -> List[BlacklistEntry]:
        """Obtener todos los reportes activos"""
        return BlacklistEntry.query.filter_by(
            status=BlacklistStatus.ACTIVE
        ).order_by(BlacklistEntry.blocked_at.desc()).limit(limit).all()
    
    @classmethod
    def check_user_blacklisted(cls, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Verificar si un usuario está en blacklist.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            (is_blacklisted, reason)
        """
        try:
            active_block = BlacklistEntry.query.filter(
                BlacklistEntry.user_id == user_id,
                BlacklistEntry.status == BlacklistStatus.ACTIVE
            ).first()
            
            if active_block and active_block.is_active_block():
                return True, active_block.reason
            
            return False, None
            
        except Exception as e:
            cls.log_error('check_blacklist_failed', {'error': str(e)})
            return False, None
    
    @classmethod
    def check_identifiers_blacklisted(cls,
                                     telegram_id: Optional[int] = None,
                                     phone: Optional[str] = None,
                                     email: Optional[str] = None,
                                     dni: Optional[str] = None) -> Tuple[bool, Optional[BlacklistEntry]]:
        """
        Verificar si algún identificador está en blacklist.
        
        Returns:
            (is_blacklisted, blacklist_entry)
        """
        try:
            or_conditions = []
            
            if telegram_id:
                or_conditions.append(BlacklistEntry.telegram_id == telegram_id)
            if phone:
                or_conditions.append(BlacklistEntry.phone == phone)
            if email:
                or_conditions.append(BlacklistEntry.email == email)
            if dni:
                or_conditions.append(BlacklistEntry.dni == dni)
            
            if not or_conditions:
                return False, None
            
            entry = BlacklistEntry.query.filter(
                BlacklistEntry.status == BlacklistStatus.ACTIVE,
                or_(*or_conditions)
            ).first()
            
            if entry and entry.is_active_block():
                return True, entry
            
            return False, None
            
        except Exception as e:
            cls.log_error('check_identifiers_failed', {'error': str(e)})
            return False, None
    
    # ==========================================
    # APELACIONES
    # ==========================================
    
    @classmethod
    def submit_appeal(cls,
                     blacklist_id: int,
                     appellant_name: str,
                     appellant_email: str,
                     appeal_text: str,
                     appellant_phone: Optional[str] = None,
                     additional_evidence: Optional[List[str]] = None,
                     ip_address: Optional[str] = None,
                     user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[BlacklistAppeal]]:
        """
        Enviar apelación desde formulario público.
        
        Args:
            blacklist_id: ID del reporte de blacklist
            appellant_name: Nombre del apelante
            appellant_email: Email del apelante
            appeal_text: Texto de la apelación
            appellant_phone: Teléfono (opcional)
            additional_evidence: Lista de URLs de evidencia
            ip_address: IP del apelante
            user_agent: User agent del navegador
            
        Returns:
            (success, message, appeal)
        """
        try:
            entry = BlacklistEntry.find_by_id(blacklist_id)
            if not entry:
                return False, "Reporte de blacklist no encontrado", None
            
            # Verificar que no tenga apelación pendiente
            pending = BlacklistAppeal.query.filter_by(
                blacklist_id=blacklist_id,
                status=AppealStatus.PENDING
            ).first()
            
            if pending:
                return False, "Ya existe una apelación pendiente para este reporte", None
            
            # Crear apelación
            appeal = BlacklistAppeal(
                blacklist_id=blacklist_id,
                appellant_name=appellant_name,
                appellant_email=appellant_email,
                appellant_phone=appellant_phone,
                appeal_text=appeal_text,
                additional_evidence=','.join(additional_evidence) if additional_evidence else None,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if not appeal.save():
                return False, "Error al guardar la apelación", None
            
            # Actualizar estado del blacklist
            entry.status = BlacklistStatus.APPEALED
            entry.save()
            
            # Notificar a administradores
            try:
                from app.services.notification_service import NotificationService
                NotificationService.notify_admins(
                    f"Nueva apelación recibida\nReporte: {entry.id}\nApelante: {appellant_name}"
                )
            except:
                pass
            
            cls.log_action('appeal_submitted', {
                'appeal_id': appeal.id,
                'blacklist_id': blacklist_id
            })
            
            return True, "Apelación enviada exitosamente. Te contactaremos pronto.", appeal
            
        except Exception as e:
            cls.log_error('submit_appeal_failed', {'error': str(e)})
            return False, f"Error al enviar apelación: {str(e)}", None
    
    @classmethod
    def review_appeal(cls,
                     appeal_id: int,
                     operator_id: int,
                     decision: str,  # 'approved', 'rejected'
                     decision_reason: str,
                     review_notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Revisar y decidir sobre una apelación.
        
        Args:
            appeal_id: ID de la apelación
            operator_id: ID del operador que revisa
            decision: 'approved' o 'rejected'
            decision_reason: Razón de la decisión
            review_notes: Notas internas (opcional)
            
        Returns:
            (success, message)
        """
        try:
            appeal = BlacklistAppeal.find_by_id(appeal_id)
            if not appeal:
                return False, "Apelación no encontrada"
            
            if appeal.status != AppealStatus.PENDING:
                return False, f"Esta apelación ya fue revisada (estado: {appeal.status.value})"
            
            # Validar decisión
            if decision not in ['approved', 'rejected']:
                return False, "Decisión inválida. Debe ser 'approved' o 'rejected'"
            
            # Actualizar apelación
            appeal.status = AppealStatus.APPROVED if decision == 'approved' else AppealStatus.REJECTED
            appeal.reviewed_at = datetime.utcnow()
            appeal.reviewed_by_operator_id = operator_id
            appeal.decision = decision
            appeal.decision_reason = decision_reason
            appeal.review_notes = review_notes
            
            if not appeal.save():
                return False, "Error al guardar la revisión"
            
            # Si se aprueba, desbloquear
            if decision == 'approved':
                success, msg = cls.update_status(
                    blacklist_id=appeal.blacklist_id,
                    new_status='REVOKED',
                    operator_id=operator_id,
                    reason=f"Apelación aprobada: {decision_reason}"
                )
                if not success:
                    return False, f"Apelación aprobada pero error al desbloquear: {msg}"
            else:
                # Si se rechaza, volver a ACTIVE
                entry = appeal.blacklist_entry
                entry.status = BlacklistStatus.ACTIVE
                entry.save()
            
            cls.log_action('appeal_reviewed', {
                'appeal_id': appeal_id,
                'decision': decision,
                'operator_id': operator_id
            })
            
            return True, f"Apelación {decision}. El usuario ha sido notificado."
            
        except Exception as e:
            cls.log_error('review_appeal_failed', {'error': str(e)})
            return False, f"Error al revisar apelación: {str(e)}"
    
    @classmethod
    def get_pending_appeals(cls) -> List[BlacklistAppeal]:
        """Obtener todas las apelaciones pendientes"""
        return BlacklistAppeal.query.filter_by(
            status=AppealStatus.PENDING
        ).order_by(BlacklistAppeal.submitted_at.desc()).all()
    
    # ==========================================
    # ESTADÍSTICAS
    # ==========================================
    
    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Obtener estadísticas de blacklist"""
        try:
            total = BlacklistEntry.query.count()
            active = BlacklistEntry.query.filter_by(status=BlacklistStatus.ACTIVE).count()
            appealed = BlacklistEntry.query.filter_by(status=BlacklistStatus.APPEALED).count()
            revoked = BlacklistEntry.query.filter_by(status=BlacklistStatus.REVOKED).count()
            
            # Por categoría
            by_category = {}
            for category in BlacklistCategory:
                count = BlacklistEntry.query.filter_by(
                    category=category,
                    status=BlacklistStatus.ACTIVE
                ).count()
                if count > 0:
                    by_category[category.value] = count
            
            # Apelaciones
            pending_appeals = BlacklistAppeal.query.filter_by(
                status=AppealStatus.PENDING
            ).count()
            
            return {
                'total': total,
                'active': active,
                'appealed': appealed,
                'revoked': revoked,
                'by_category': by_category,
                'pending_appeals': pending_appeals
            }
            
        except Exception as e:
            cls.log_error('get_statistics_failed', {'error': str(e)})
            return {}
    
    # ==========================================
    # UTILIDADES PRIVADAS
    # ==========================================
    
    @classmethod
    def _check_duplicates(cls,
                         telegram_id: Optional[int],
                         phone: Optional[str],
                         email: Optional[str],
                         dni: Optional[str]) -> Optional[BlacklistEntry]:
        """Verificar si ya existe un reporte activo con estos datos"""
        try:
            or_conditions = []
            
            if telegram_id:
                or_conditions.append(BlacklistEntry.telegram_id == telegram_id)
            if phone:
                or_conditions.append(BlacklistEntry.phone == phone)
            if email:
                or_conditions.append(BlacklistEntry.email == email)
            if dni:
                or_conditions.append(BlacklistEntry.dni == dni)
            
            if not or_conditions:
                return None
            
            return BlacklistEntry.query.filter(
                BlacklistEntry.status == BlacklistStatus.ACTIVE,
                or_(*or_conditions)
            ).first()
            
        except Exception as e:
            cls.log_error('check_duplicates_failed', {'error': str(e)})
            return None
    
    @classmethod
    def _has_other_active_blocks(cls, user_id: int, exclude_id: int) -> bool:
        """Verificar si usuario tiene otros bloqueos activos"""
        try:
            count = BlacklistEntry.query.filter(
                BlacklistEntry.user_id == user_id,
                BlacklistEntry.id != exclude_id,
                BlacklistEntry.status == BlacklistStatus.ACTIVE
            ).count()
            
            return count > 0
            
        except Exception as e:
            cls.log_error('check_other_blocks_failed', {'error': str(e)})
            return False
    
    @classmethod
    def _cancel_pending_orders(cls, user_id: int, reason: str):
        """Cancelar todas las órdenes pendientes del usuario"""
        try:
            from app.services.order_service import OrderService
            
            pending_orders = Order.query.filter(
                Order.user_id == user_id,
                Order.status.in_([OrderStatus.DRAFT, OrderStatus.PENDING, OrderStatus.IN_PROCESS])
            ).all()
            
            for order in pending_orders:
                try:
                    OrderService.cancel_order(
                        order_id=order.id,
                        reason=reason,
                        operator_id=None
                    )
                except:
                    pass
                    
        except Exception as e:
            cls.log_error('cancel_pending_orders_failed', {'error': str(e)})