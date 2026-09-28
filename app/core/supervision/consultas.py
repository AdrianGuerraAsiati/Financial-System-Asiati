"""Tablero de supervisión (ROLES_Y_PERMISOS.md §5).

Todo sale de tablas existentes: periodos, fuentes, cargas, hallazgos, auditoria
e ingresos. No hay contadores aparte. El filtro por empresas visibles se aplica
aquí, en cada consulta.
"""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from app.core.auditoria import Auditoria
from app.core.auth.model import Ingreso
from app.core.cargas import Carga
from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.hallazgos import Hallazgo
from app.core.periodos import Periodo
from app.core.usuarios import Usuario, UsuarioEmpresa


DIAS_INGRESOS = 30


def estado_conciliaciones(
    session: Session,
    *,
    empresas_visibles: frozenset[int] | None,
    empresa_id: int | None = None,
) -> list[dict[str, object]]:
    consulta = (
        select(Periodo, Empresa.nombre)
        .join(Empresa, Empresa.id == Periodo.empresa_id)
        .order_by(Periodo.fecha_inicio.desc(), Periodo.id.desc())
    )
    if empresas_visibles is not None:
        consulta = consulta.where(Periodo.empresa_id.in_(empresas_visibles))
    if empresa_id is not None:
        consulta = consulta.where(Periodo.empresa_id == empresa_id)
    periodos = session.execute(consulta).all()
    if not periodos:
        return []

    periodo_ids = [periodo.id for periodo, _ in periodos]
    empresa_ids = {periodo.empresa_id for periodo, _ in periodos}

    fuentes_por_empresa: dict[int, list[Fuente]] = {}
    for fuente in session.scalars(
        select(Fuente).where(Fuente.empresa_id.in_(empresa_ids)).order_by(Fuente.id)
    ):
        fuentes_por_empresa.setdefault(fuente.empresa_id, []).append(fuente)

    cargadas = set(
        session.execute(
            select(Carga.periodo_id, Carga.fuente_id)
            .where(Carga.periodo_id.in_(periodo_ids))
            .distinct()
        ).all()
    )

    abiertos = Hallazgo.resuelto.is_(False)
    conteos = {
        fila.periodo_id: fila
        for fila in session.execute(
            select(
                Hallazgo.periodo_id,
                func.count().filter(abiertos).label("abiertos"),
                func.count().filter(and_(abiertos, Hallazgo.critico)).label("criticos"),
                func.count().filter(Hallazgo.estado == "escalado").label("escalados"),
            )
            .where(Hallazgo.periodo_id.in_(periodo_ids))
            .group_by(Hallazgo.periodo_id)
        )
    }

    resultado = []
    for periodo, empresa_nombre in periodos:
        conteo = conteos.get(periodo.id)
        resultado.append(
            {
                "empresa_id": periodo.empresa_id,
                "empresa": empresa_nombre,
                "periodo_id": periodo.id,
                "fecha_inicio": periodo.fecha_inicio.isoformat(),
                "fecha_fin": periodo.fecha_fin.isoformat(),
                "cerrado": periodo.cerrado,
                # "ejecutada" = hay carga de la fuente en el período: hoy la carga
                # solo se registra al ejecutar el motor.
                "fuentes": [
                    {
                        "fuente_id": fuente.id,
                        "fuente": fuente.nombre,
                        "estado": (
                            "cerrada"
                            if periodo.cerrado
                            else "ejecutada"
                            if (periodo.id, fuente.id) in cargadas
                            else "pendiente"
                        ),
                    }
                    for fuente in fuentes_por_empresa.get(periodo.empresa_id, [])
                ],
                "hallazgos_abiertos": conteo.abiertos if conteo else 0,
                "hallazgos_criticos_abiertos": conteo.criticos if conteo else 0,
                "hallazgos_escalados": conteo.escalados if conteo else 0,
                # TODO(negocio): definir cómo se calcula el score de una conciliación
                # y el monto en pesos de los hallazgos abiertos (los hallazgos del
                # núcleo no guardan monto; hoy solo está en la evidencia de Wiilog).
                "score": None,
            }
        )
    return resultado


def _usuarios_de_empresas(empresas_visibles: frozenset[int]):
    return exists().where(
        UsuarioEmpresa.usuario_id == Usuario.id,
        UsuarioEmpresa.empresa_id.in_(empresas_visibles),
    )


def ultimos_ingresos(
    session: Session,
    *,
    empresas_visibles: frozenset[int] | None,
) -> list[dict[str, object]]:
    desde = datetime.now(timezone.utc) - timedelta(days=DIAS_INGRESOS)
    consulta = (
        select(Ingreso, Usuario.nombre, Usuario.rol)
        .outerjoin(Usuario, Usuario.id == Ingreso.usuario_id)
        .where(Ingreso.creado_at >= desde)
        .order_by(Ingreso.creado_at.desc(), Ingreso.id.desc())
    )
    if empresas_visibles is not None:
        # Con alcance asignado solo se ven los usuarios que comparten empresa;
        # los intentos con correos desconocidos solo los ve quien ve todo.
        consulta = consulta.where(_usuarios_de_empresas(empresas_visibles))
    return [
        {
            "usuario_id": ingreso.usuario_id,
            "nombre": nombre,
            "rol": rol,
            "email_intentado": ingreso.email_intentado,
            "exito": ingreso.exito,
            "ip": ingreso.ip,
            "creado_at": ingreso.creado_at.isoformat(),
        }
        for ingreso, nombre, rol in session.execute(consulta)
    ]


def acciones_por_usuario(
    session: Session,
    *,
    empresas_visibles: frozenset[int] | None,
    usuario_id: int | None = None,
    empresa_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[dict[str, object]]:
    consulta = (
        select(
            Auditoria.usuario_id,
            Usuario.nombre,
            Usuario.rol,
            Auditoria.accion,
            func.count().label("cantidad"),
        )
        .join(Usuario, Usuario.id == Auditoria.usuario_id)
        .group_by(Auditoria.usuario_id, Usuario.nombre, Usuario.rol, Auditoria.accion)
        .order_by(Auditoria.usuario_id, Auditoria.accion)
    )
    if empresas_visibles is not None:
        consulta = consulta.where(Auditoria.empresa_id.in_(empresas_visibles))
    if usuario_id is not None:
        consulta = consulta.where(Auditoria.usuario_id == usuario_id)
    if empresa_id is not None:
        consulta = consulta.where(Auditoria.empresa_id == empresa_id)
    if desde is not None:
        consulta = consulta.where(
            Auditoria.creado_at >= datetime.combine(desde, time.min, timezone.utc)
        )
    if hasta is not None:
        consulta = consulta.where(
            Auditoria.creado_at
            < datetime.combine(hasta + timedelta(days=1), time.min, timezone.utc)
        )
    return [
        {
            "usuario_id": fila.usuario_id,
            "nombre": fila.nombre,
            "rol": fila.rol,
            "accion": fila.accion,
            "cantidad": fila.cantidad,
        }
        for fila in session.execute(consulta)
    ]
