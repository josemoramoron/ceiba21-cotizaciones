"""
Tests de BlacklistService.

Usa la BD real de dev (ceiba21_dev). Todo dato de prueba usa identificadores
con marca TST* y se limpia en cada finally. operator_id se deja en None en
casi todos los tests: blocked_by_operator_id es nullable y no hace falta un
Operator real para probar la lógica del servicio.

Fuera de alcance en este archivo (documentado, no probado aquí):
- run_fraud_check=True (llama a FraudCheckService, API externa).
- La cascada real de _cancel_pending_orders sobre OrderService/Transaction;
  solo se prueba el caso "usuario sin órdenes pendientes" (no-op seguro),
  que es el que se ejercita al crear un reporte ligado a un User de prueba.
"""
import pytest

from app import create_app
from app.models import db
from app.models.user import User
from app.models.blacklist import (
    BlacklistEntry, BlacklistAppeal,
    BlacklistType, BlacklistCategory, BlacklistStatus, AppealStatus
)
from app.services.blacklist_service import BlacklistService


@pytest.fixture(autouse=True)
def app_context():
    """Contexto de app para cada test (acceso a la BD de dev)."""
    app = create_app()
    app.config['TESTING'] = True
    # :5433 porque en esta laptop el cluster nativo de Postgres no está en
    # el puerto default 5432 (ocupado por el contenedor Docker de FVA).
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'postgresql://webmaster:postgres123@localhost:5433/ceiba21_dev'
    )
    with app.app_context():
        yield


def _borrar_entry(entry_id):
    """Limpieza común: borra apelaciones + el BlacklistEntry de prueba."""
    if entry_id is None:
        return
    BlacklistAppeal.query.filter_by(blacklist_id=entry_id).delete()
    BlacklistEntry.query.filter_by(id=entry_id).delete()
    db.session.commit()


def _borrar_user(user_id):
    """Limpieza común: borra el User de prueba."""
    if user_id is None:
        return
    User.query.filter_by(id=user_id).delete()
    db.session.commit()


def _crear_entry(**kwargs):
    """Atajo: create_report() con defaults razonables, falla fuerte si
    la creación no funciona (para no ensuciar fixtures de otros tests)."""
    defaults = {
        'operator_id': None,
        'reason': 'Motivo de prueba TST',
    }
    defaults.update(kwargs)
    ok, msg, entry = BlacklistService.create_report(**defaults)
    assert ok, f"Setup falló creando entry de prueba: {msg}"
    return entry


class TestCreateReportPreventivo:
    """create_report() sin user_id (bloqueo preventivo)."""

    def test_sin_identificadores_da_error(self):
        ok, msg, entry = BlacklistService.create_report(
            operator_id=None, reason='Sin identificadores TST'
        )
        assert ok is False
        assert entry is None
        assert 'identificador' in msg

    def test_duplicado_activo_da_error(self):
        entry = _crear_entry(reason='Original TST', phone='+58414TST0002')
        try:
            ok, msg, entry2 = BlacklistService.create_report(
                operator_id=None, reason='Duplicado TST', phone='+58414TST0002'
            )
            assert ok is False
            assert entry2 is None
            assert 'Ya existe un reporte activo' in msg
        finally:
            _borrar_entry(entry.id)

    def test_categoria_o_tipo_invalido_da_error(self):
        ok, msg, entry = BlacklistService.create_report(
            operator_id=None, reason='Categoria invalida TST',
            phone='+58414TST0004', category='NO_EXISTE'
        )
        assert ok is False
        assert entry is None
        assert 'inválida' in msg

    def test_temporal_sin_expiracion_da_error(self):
        ok, msg, entry = BlacklistService.create_report(
            operator_id=None, reason='Temporal sin fecha TST',
            phone='+58414TST0005', block_type='TEMPORARY'
        )
        assert ok is False
        assert entry is None
        assert 'expiración' in msg

    def test_creacion_exitosa_guarda_evidencia_como_json(self):
        entry = _crear_entry(
            reason='Creacion exitosa TST',
            phone='+58414TST0006', dni='TSTDNI0006',
            evidence_urls=['http://x.test/1', 'http://x.test/2']
        )
        try:
            assert entry.status == BlacklistStatus.ACTIVE
            assert entry.block_type == BlacklistType.PERMANENT  # default
            assert entry.category == BlacklistCategory.OTHER  # default
            import json
            assert json.loads(entry.evidence_urls) == ['http://x.test/1', 'http://x.test/2']
        finally:
            _borrar_entry(entry.id)


class TestCreateReportConUsuario:
    """create_report() con user_id: enriquecimiento + bloqueo del usuario."""

    def test_usuario_inexistente_da_error(self):
        ok, msg, entry = BlacklistService.create_report(
            operator_id=None, reason='Usuario inexistente TST', user_id=-999
        )
        assert ok is False
        assert entry is None
        assert 'no encontrado' in msg

    def test_bloquea_al_usuario_sin_ordenes_pendientes(self):
        user = User(telegram_id=910000001, first_name='TST', last_name='Usuario Blacklist')
        user.save()
        entry = None
        try:
            assert user.is_blocked is False
            entry = _crear_entry(reason='Bloqueo de usuario TST', user_id=user.id)
            # Enriquecido desde el usuario: toma su telegram_id.
            assert entry.telegram_id == 910000001
            db.session.refresh(user)
            assert user.is_blocked is True
            assert user.is_active is False
        finally:
            _borrar_entry(entry.id if entry else None)
            _borrar_user(user.id)


class TestUpdateStatus:
    def test_reporte_inexistente_da_error(self):
        ok, msg = BlacklistService.update_status(
            blacklist_id=-1, new_status='REVOKED', operator_id=None, reason='x'
        )
        assert ok is False
        assert msg == "Reporte no encontrado"

    def test_estado_invalido_da_error(self):
        entry = _crear_entry(reason='Estado invalido TST', phone='+58414TST0007')
        try:
            ok, msg = BlacklistService.update_status(
                blacklist_id=entry.id, new_status='NO_EXISTE', operator_id=None
            )
            assert ok is False
            assert 'Estado inválido' in msg
        finally:
            _borrar_entry(entry.id)

    def test_revocar_sin_razon_da_error(self):
        entry = _crear_entry(reason='Revocar sin razon TST', phone='+58414TST0008')
        try:
            ok, msg = BlacklistService.update_status(
                blacklist_id=entry.id, new_status='REVOKED', operator_id=None, reason=None
            )
            assert ok is False
            assert 'razón' in msg
        finally:
            db.session.rollback()  # descarta el status=REVOKED en memoria sin commitear
            _borrar_entry(entry.id)

    def test_revocar_preventivo_con_razon(self):
        entry = _crear_entry(reason='Revocar preventivo TST', phone='+58414TST0009')
        try:
            ok, msg = BlacklistService.update_status(
                blacklist_id=entry.id, new_status='REVOKED', operator_id=None,
                reason='Resuelto TST'
            )
            assert ok is True
            assert msg == "Estatus actualizado de active a REVOKED"
            fresh = db.session.get(BlacklistEntry, entry.id)
            assert fresh.status == BlacklistStatus.REVOKED
            assert fresh.unblock_reason == 'Resuelto TST'
            assert fresh.unblocked_at is not None
        finally:
            _borrar_entry(entry.id)

    def test_revocar_reactiva_al_usuario_sin_otros_bloqueos(self):
        user = User(telegram_id=910000002, first_name='TST', last_name='Reactivar')
        user.save()
        entry = None
        try:
            entry = _crear_entry(reason='Reactivar usuario TST', user_id=user.id)
            db.session.refresh(user)
            assert user.is_blocked is True

            ok, _ = BlacklistService.update_status(
                blacklist_id=entry.id, new_status='REVOKED', operator_id=None,
                reason='Desbloqueo TST'
            )
            assert ok is True
            db.session.refresh(user)
            assert user.is_blocked is False
            assert user.is_active is True
        finally:
            _borrar_entry(entry.id if entry else None)
            _borrar_user(user.id)

    def test_revocar_no_reactiva_si_hay_otro_bloqueo_activo(self):
        user = User(telegram_id=910000003, first_name='TST', last_name='DobleBloqueo')
        user.save()
        entry1 = None
        entry2 = None
        try:
            entry1 = _crear_entry(reason='Primer bloqueo TST', user_id=user.id)
            db.session.refresh(user)
            assert user.is_blocked is True

            # Segundo bloqueo del mismo usuario, insertado directo (create_report
            # rechazaría esto como duplicado por compartir telegram_id).
            entry2 = BlacklistEntry(
                user_id=user.id, block_type=BlacklistType.PERMANENT,
                category=BlacklistCategory.OTHER, status=BlacklistStatus.ACTIVE,
                reason='Segundo bloqueo TST', reporter_name='ceiba21'
            )
            entry2.save()

            ok, _ = BlacklistService.update_status(
                blacklist_id=entry1.id, new_status='REVOKED', operator_id=None,
                reason='Desbloqueo parcial TST'
            )
            assert ok is True
            db.session.refresh(user)
            # Sigue bloqueado: entry2 sigue activo.
            assert user.is_blocked is True
        finally:
            _borrar_entry(entry1.id if entry1 else None)
            _borrar_entry(entry2.id if entry2 else None)
            _borrar_user(user.id)

    def test_cambia_tipo_de_bloqueo_y_expiracion(self):
        from datetime import timedelta
        from app.utils.fecha import utcnow_naive
        entry = _crear_entry(reason='Cambiar tipo TST', phone='+58414TST0010')
        try:
            nueva_fecha = utcnow_naive() + timedelta(days=5)
            ok, _ = BlacklistService.update_status(
                blacklist_id=entry.id, new_status='ACTIVE', operator_id=None,
                new_block_type='TEMPORARY', new_expires_at=nueva_fecha
            )
            assert ok is True
            fresh = db.session.get(BlacklistEntry, entry.id)
            assert fresh.block_type == BlacklistType.TEMPORARY
            assert fresh.expires_at is not None
        finally:
            _borrar_entry(entry.id)

    def test_tipo_de_bloqueo_invalido_da_error(self):
        entry = _crear_entry(reason='Tipo invalido TST', phone='+58414TST0011')
        try:
            ok, msg = BlacklistService.update_status(
                blacklist_id=entry.id, new_status='ACTIVE', operator_id=None,
                new_block_type='NO_EXISTE'
            )
            assert ok is False
            assert 'Tipo de bloqueo inválido' in msg
        finally:
            _borrar_entry(entry.id)


class TestDeleteReport:
    def test_delega_en_update_status_revoked(self):
        entry = _crear_entry(reason='Delete report TST', phone='+58414TST0012')
        try:
            ok, _ = BlacklistService.delete_report(blacklist_id=entry.id, operator_id=None)
            assert ok is True
            fresh = db.session.get(BlacklistEntry, entry.id)
            assert fresh.status == BlacklistStatus.REVOKED
            assert fresh.unblock_reason == 'Reporte eliminado por operador'
        finally:
            _borrar_entry(entry.id)


class TestUpdateReport:
    def test_reporte_inexistente_da_error(self):
        ok, msg = BlacklistService.update_report(blacklist_id=-1, operator_id=None, reason='x')
        assert ok is False
        assert msg == "Reporte no encontrado"

    def test_solo_actualiza_campos_editables(self):
        entry = _crear_entry(reason='Original TST', phone='+58414TST0013')
        try:
            ok, msg = BlacklistService.update_report(
                blacklist_id=entry.id, operator_id=None,
                reason='Nuevo motivo TST',
                status='REVOKED',  # no es editable por este método: se ignora
                campo_que_no_existe='x'
            )
            assert ok is True
            assert '1 campos modificados' in msg
            fresh = db.session.get(BlacklistEntry, entry.id)
            assert fresh.reason == 'Nuevo motivo TST'
            assert fresh.status == BlacklistStatus.ACTIVE  # no lo tocó
        finally:
            _borrar_entry(entry.id)


class TestSearch:
    def test_por_report_id(self):
        entry = _crear_entry(reason='Buscar por id TST', phone='+58414TST0014')
        try:
            resultado = BlacklistService.search(report_id=entry.id)
            assert len(resultado) == 1
            assert resultado[0].id == entry.id
        finally:
            _borrar_entry(entry.id)

    def test_por_texto_en_reason(self):
        entry = _crear_entry(reason='Marca unica TSTBUSCAMARCA aqui', phone='+58414TST0015')
        try:
            resultado = BlacklistService.search(query='TSTBUSCAMARCA')
            assert any(e.id == entry.id for e in resultado)
        finally:
            _borrar_entry(entry.id)

    def test_por_categoria(self):
        entry = _crear_entry(reason='Buscar categoria TST', phone='+58414TST0016', category='FRAUD')
        try:
            resultado = BlacklistService.search(category='FRAUD', limit=1000)
            assert any(e.id == entry.id for e in resultado)
        finally:
            _borrar_entry(entry.id)

    def test_default_excluye_revocados(self):
        activo = _crear_entry(reason='Sigue activo TST', phone='+58414TST0017')
        revocado = _crear_entry(reason='Sera revocado TST', phone='+58414TST0018')
        try:
            BlacklistService.delete_report(blacklist_id=revocado.id, operator_id=None)
            resultado = BlacklistService.search(limit=1000)  # sin filtros -> default ACTIVE
            ids = [e.id for e in resultado]
            assert activo.id in ids
            assert revocado.id not in ids
        finally:
            _borrar_entry(activo.id)
            _borrar_entry(revocado.id)


class TestGetAllActive:
    def test_incluye_reporte_activo_de_prueba(self):
        entry = _crear_entry(reason='Get all active TST', phone='+58414TST0019')
        try:
            activos = BlacklistService.get_all_active(limit=1000)
            assert any(e.id == entry.id for e in activos)
        finally:
            _borrar_entry(entry.id)


class TestCheckUserBlacklisted:
    def test_usuario_con_bloqueo_activo(self):
        user = User(telegram_id=910000004, first_name='TST', last_name='CheckBlacklist')
        user.save()
        entry = None
        try:
            entry = _crear_entry(reason='Check user blacklisted TST', user_id=user.id)
            blacklisted, reason = BlacklistService.check_user_blacklisted(user.id)
            assert blacklisted is True
            assert reason == 'Check user blacklisted TST'
        finally:
            _borrar_entry(entry.id if entry else None)
            _borrar_user(user.id)

    def test_usuario_sin_bloqueo(self):
        blacklisted, reason = BlacklistService.check_user_blacklisted(-999)
        assert blacklisted is False
        assert reason is None

    def test_bloqueo_temporal_expirado_no_cuenta(self):
        from datetime import timedelta
        from app.utils.fecha import utcnow_naive
        user = User(telegram_id=910000005, first_name='TST', last_name='Expirado')
        user.save()
        entry = None
        try:
            entry = BlacklistEntry(
                user_id=user.id, block_type=BlacklistType.TEMPORARY,
                category=BlacklistCategory.OTHER, status=BlacklistStatus.ACTIVE,
                reason='Expirado TST', reporter_name='ceiba21',
                expires_at=utcnow_naive() - timedelta(days=1)
            )
            entry.save()
            blacklisted, reason = BlacklistService.check_user_blacklisted(user.id)
            assert blacklisted is False
            assert reason is None
        finally:
            _borrar_entry(entry.id if entry else None)
            _borrar_user(user.id)


class TestCheckIdentifiersBlacklisted:
    def test_encuentra_por_telefono(self):
        entry = _crear_entry(reason='Check identifiers TST', phone='+58414TST0020')
        try:
            blacklisted, encontrado = BlacklistService.check_identifiers_blacklisted(
                phone='+58414TST0020'
            )
            assert blacklisted is True
            assert encontrado.id == entry.id
        finally:
            _borrar_entry(entry.id)

    def test_sin_identificadores_da_false(self):
        blacklisted, encontrado = BlacklistService.check_identifiers_blacklisted()
        assert blacklisted is False
        assert encontrado is None


class TestSubmitAppeal:
    def test_reporte_inexistente_da_error(self):
        ok, msg, appeal = BlacklistService.submit_appeal(
            blacklist_id=-1, appellant_name='TST', appellant_email='tst@test.local',
            appeal_text='x'
        )
        assert ok is False
        assert appeal is None
        assert 'no encontrado' in msg

    def test_creacion_exitosa_pasa_entry_a_appealed(self):
        entry = _crear_entry(reason='Submit appeal TST', phone='+58414TST0021')
        try:
            ok, msg, appeal = BlacklistService.submit_appeal(
                blacklist_id=entry.id, appellant_name='Juan TST',
                appellant_email='juantst@test.local', appeal_text='Fue un error TST'
            )
            assert ok is True
            assert appeal is not None
            fresh = db.session.get(BlacklistEntry, entry.id)
            assert fresh.status == BlacklistStatus.APPEALED
        finally:
            _borrar_entry(entry.id)

    def test_apelacion_duplicada_pendiente_da_error(self):
        entry = _crear_entry(reason='Appeal duplicada TST', phone='+58414TST0022')
        try:
            BlacklistService.submit_appeal(
                blacklist_id=entry.id, appellant_name='TST', appellant_email='tst@test.local',
                appeal_text='Primera TST'
            )
            ok, msg, appeal = BlacklistService.submit_appeal(
                blacklist_id=entry.id, appellant_name='TST', appellant_email='tst@test.local',
                appeal_text='Segunda TST'
            )
            assert ok is False
            assert appeal is None
            assert 'pendiente' in msg
        finally:
            _borrar_entry(entry.id)


class TestReviewAppeal:
    def _crear_entry_con_appeal(self, marca):
        entry = _crear_entry(reason=f'Review appeal {marca} TST', phone=f'+58414TST{marca}')
        _, _, appeal = BlacklistService.submit_appeal(
            blacklist_id=entry.id, appellant_name='TST', appellant_email='tst@test.local',
            appeal_text='Texto TST'
        )
        return entry, appeal

    def test_apelacion_inexistente_da_error(self):
        ok, msg = BlacklistService.review_appeal(
            appeal_id=-1, operator_id=None, decision='approved', decision_reason='x'
        )
        assert ok is False
        assert msg == "Apelación no encontrada"

    def test_decision_invalida_da_error(self):
        entry, appeal = self._crear_entry_con_appeal('0023')
        try:
            ok, msg = BlacklistService.review_appeal(
                appeal_id=appeal.id, operator_id=None, decision='tal_vez',
                decision_reason='x'
            )
            assert ok is False
            assert 'inválida' in msg
        finally:
            _borrar_entry(entry.id)

    def test_ya_revisada_da_error(self):
        entry, appeal = self._crear_entry_con_appeal('0024')
        try:
            BlacklistService.review_appeal(
                appeal_id=appeal.id, operator_id=None, decision='rejected',
                decision_reason='Primera revision TST'
            )
            ok, msg = BlacklistService.review_appeal(
                appeal_id=appeal.id, operator_id=None, decision='approved',
                decision_reason='Segunda revision TST'
            )
            assert ok is False
            assert 'ya fue revisada' in msg
        finally:
            _borrar_entry(entry.id)

    def test_aprobada_revoca_el_bloqueo(self):
        entry, appeal = self._crear_entry_con_appeal('0025')
        try:
            ok, _ = BlacklistService.review_appeal(
                appeal_id=appeal.id, operator_id=None, decision='approved',
                decision_reason='Aceptada TST'
            )
            assert ok is True
            fresh = db.session.get(BlacklistEntry, entry.id)
            assert fresh.status == BlacklistStatus.REVOKED
        finally:
            _borrar_entry(entry.id)

    def test_rechazada_vuelve_a_activo(self):
        entry, appeal = self._crear_entry_con_appeal('0026')
        try:
            ok, _ = BlacklistService.review_appeal(
                appeal_id=appeal.id, operator_id=None, decision='rejected',
                decision_reason='Rechazada TST'
            )
            assert ok is True
            fresh = db.session.get(BlacklistEntry, entry.id)
            assert fresh.status == BlacklistStatus.ACTIVE
        finally:
            _borrar_entry(entry.id)


class TestGetPendingAppeals:
    def test_incluye_pendiente_y_excluye_revisada(self):
        entry = _crear_entry(reason='Pending appeals TST', phone='+58414TST0027')
        try:
            _, _, appeal = BlacklistService.submit_appeal(
                blacklist_id=entry.id, appellant_name='TST', appellant_email='tst@test.local',
                appeal_text='x'
            )
            pendientes = BlacklistService.get_pending_appeals()
            assert any(a.id == appeal.id for a in pendientes)

            BlacklistService.review_appeal(
                appeal_id=appeal.id, operator_id=None, decision='rejected',
                decision_reason='Resuelta TST'
            )
            pendientes = BlacklistService.get_pending_appeals()
            assert not any(a.id == appeal.id for a in pendientes)
        finally:
            _borrar_entry(entry.id)


class TestGetStatistics:
    def test_refleja_altas_de_reportes_activos(self):
        antes = BlacklistService.get_statistics()
        e1 = _crear_entry(reason='Stats 1 TST', phone='+58414TST0028', category='FRAUD')
        e2 = _crear_entry(reason='Stats 2 TST', phone='+58414TST0029', category='FRAUD')
        try:
            despues = BlacklistService.get_statistics()
            assert despues['total'] == antes['total'] + 2
            assert despues['active'] == antes['active'] + 2
            assert despues['by_category'].get('fraud', 0) == antes['by_category'].get('fraud', 0) + 2
        finally:
            _borrar_entry(e1.id)
            _borrar_entry(e2.id)
