"""Altas, bajas y aprobación de cobertura; nunca cierra un período."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.core.periodos import Periodo
from app.core.auditoria import registrar_auditoria
from .esperadas import WalletEsperada
from .plataforma.integracion import catalogo_de_empresa


class CatalogoCongeladoError(ValueError):
    pass


class WalletCatalogoAprobacion(Base):
    __tablename__ = "wallets_catalogo_aprobaciones"
    __table_args__ = (
        ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_aprobacion_periodo_empresa", ondelete="RESTRICT"),
        UniqueConstraint("periodo_id", name="uq_wallets_aprobacion_periodo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False)
    aprobado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    aprobado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    wallets_snapshot: Mapped[list] = mapped_column(JSON, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)


def validar_identidad(tipo: str, identidad: str | None) -> tuple[str, str]:
    if tipo not in {"wiilog", "tienda", "pagos"}:
        raise ValueError("Tipo de wallet inválido.")
    ident = (identidad or "").strip().lower()
    if tipo == "wiilog":
        if ident:
            raise ValueError("Wiilog no acepta identidad explícita en el catálogo.")
    elif not ident or len(ident) > 320:
        raise ValueError("Identidad de wallet obligatoria (máximo 320 caracteres).")
    return tipo, ident


def periodo_bloqueado(session: Session, empresa_id: int, periodo_id: int) -> Periodo:
    periodo = session.scalar(select(Periodo).where(
        Periodo.id == periodo_id, Periodo.empresa_id == empresa_id
    ).with_for_update())
    if periodo is None:
        raise LookupError("El período no pertenece a la empresa indicada.")
    if periodo.cerrado:
        raise CatalogoCongeladoError("El período está cerrado.")
    return periodo


def _aprobacion(session: Session, periodo_id: int) -> WalletCatalogoAprobacion | None:
    return session.scalar(select(WalletCatalogoAprobacion).where(
        WalletCatalogoAprobacion.periodo_id == periodo_id
    ))


def _filas(session: Session, periodo_id: int) -> list[WalletEsperada]:
    return list(session.scalars(select(WalletEsperada).where(
        WalletEsperada.periodo_id == periodo_id
    ).order_by(WalletEsperada.tipo_wallet, WalletEsperada.identidad_wallet)))


def catalogo(session: Session, *, empresa_id: int, periodo_id: int) -> dict:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise LookupError("El período no pertenece a la empresa indicada.")
    aprobacion = _aprobacion(session, periodo_id)
    return {
        "empresa_id": empresa_id, "periodo_id": periodo_id,
        "aprobado": aprobacion is not None,
        "aprobado_at": aprobacion.aprobado_at if aprobacion else None,
        "aprobado_por": aprobacion.aprobado_por if aprobacion else None,
        "wallets": [
            {"id": r.id, "tipo_wallet": r.tipo_wallet, "identidad_wallet": r.identidad_wallet,
             "vigente_desde": r.vigente_desde, "vigente_hasta": r.vigente_hasta}
            for r in _filas(session, periodo_id)
        ],
    }


def agregar(session: Session, *, empresa_id: int, periodo_id: int, usuario_id: int,
            tipo_wallet: str, identidad_wallet: str | None, ip: str | None = None,
            vigente_desde: date | None = None, vigente_hasta: date | None = None) -> WalletEsperada:
    tipo, identidad = validar_identidad(tipo_wallet, identidad_wallet)
    if vigente_desde is not None and vigente_hasta is not None and vigente_desde > vigente_hasta:
        raise ValueError("La fecha inicial de vigencia no puede superar la final.")
    periodo_bloqueado(session, empresa_id, periodo_id)
    if _aprobacion(session, periodo_id):
        raise CatalogoCongeladoError("Catálogo aprobado: no se puede modificar.")
    configuradas = catalogo_de_empresa(session, empresa_id)
    if tipo == "wiilog":
        permitida = configuradas["wiilog"]
    else:
        grupo = "tiendas" if tipo == "tienda" else "pagos"
        permitida = any(
            w["usuario_email"].strip().lower() == identidad
            for w in configuradas[grupo]
        )
    if not permitida:
        raise ValueError("La wallet no está parametrizada para la empresa indicada.")
    if session.scalar(select(WalletEsperada.id).where(
        WalletEsperada.periodo_id == periodo_id, WalletEsperada.tipo_wallet == tipo,
        WalletEsperada.identidad_wallet == identidad
    )) is not None:
        raise ValueError("La wallet ya está declarada para este período.")
    item = WalletEsperada(empresa_id=empresa_id, periodo_id=periodo_id,
                          tipo_wallet=tipo, identidad_wallet=identidad, registrado_por=usuario_id,
                          vigente_desde=vigente_desde, vigente_hasta=vigente_hasta)
    session.add(item)
    session.flush()
    registrar_auditoria(session, usuario_id=usuario_id, accion="WALLET_CATALOGO_AGREGAR",
        entidad="wallets_esperadas", entidad_id=item.id, empresa_id=empresa_id,
        despues={"periodo_id": periodo_id, "tipo_wallet": tipo, "identidad_wallet": identidad}, ip=ip)
    return item


def quitar(session: Session, *, empresa_id: int, periodo_id: int, item_id: int,
           usuario_id: int, motivo: str, ip: str | None = None) -> None:
    periodo_bloqueado(session, empresa_id, periodo_id)
    if _aprobacion(session, periodo_id):
        raise CatalogoCongeladoError("Catálogo aprobado: no se puede modificar.")
    if not motivo.strip():
        raise ValueError("La baja requiere motivo.")
    item = session.scalar(select(WalletEsperada).where(
        WalletEsperada.id == item_id, WalletEsperada.periodo_id == periodo_id,
        WalletEsperada.empresa_id == empresa_id
    ))
    if item is None:
        raise LookupError("Wallet esperada no encontrada.")
    registrar_auditoria(session, usuario_id=usuario_id, accion="WALLET_CATALOGO_QUITAR",
        entidad="wallets_esperadas", entidad_id=item.id, empresa_id=empresa_id,
        antes={"periodo_id": periodo_id, "tipo_wallet": item.tipo_wallet,
               "identidad_wallet": item.identidad_wallet, "motivo": motivo.strip()}, ip=ip)
    session.delete(item)


def aprobar(session: Session, *, empresa_id: int, periodo_id: int, usuario_id: int,
            motivo: str, ip: str | None = None) -> WalletCatalogoAprobacion:
    periodo = periodo_bloqueado(session, empresa_id, periodo_id)
    if _aprobacion(session, periodo_id):
        raise CatalogoCongeladoError("Catálogo ya aprobado.")
    if not motivo.strip():
        raise ValueError("La aprobación requiere justificación.")
    filas = _filas(session, periodo_id)
    if not filas:
        raise ValueError("No se puede aprobar un catálogo vacío.")
    # Segregación antes de evaluar vigencias.
    if any(f.registrado_por == usuario_id for f in filas):
        raise ValueError("El aprobador no puede aprobar wallets que registró.")
    if any(f.vigente_desde is None or f.vigente_hasta is None or
           f.vigente_desde > periodo.fecha_inicio or f.vigente_hasta < periodo.fecha_fin for f in filas):
        raise ValueError("Cada wallet debe acreditar vigencia durante todo el período antes de aprobar.")
    snapshot = [
        {"tipo_wallet": f.tipo_wallet, "identidad_wallet": f.identidad_wallet, "id": f.id,
         "vigente_desde": f.vigente_desde.isoformat(), "vigente_hasta": f.vigente_hasta.isoformat()}
        for f in filas
    ]
    aprobacion = WalletCatalogoAprobacion(
        empresa_id=empresa_id, periodo_id=periodo_id, aprobado_por=usuario_id,
        wallets_snapshot=snapshot, motivo=motivo.strip())
    session.add(aprobacion)
    session.flush()
    registrar_auditoria(session, usuario_id=usuario_id, accion="WALLET_CATALOGO_APROBAR",
        entidad="wallets_catalogo_aprobaciones", entidad_id=aprobacion.id, empresa_id=empresa_id,
        despues={"periodo_id": periodo_id, "wallets": snapshot, "motivo": motivo.strip()}, ip=ip)
    return aprobacion
