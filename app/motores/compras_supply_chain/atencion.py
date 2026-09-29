from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Iterable

from .agrupacion import agrupar_ocs
from .dominio import LineaCompra


@dataclass(frozen=True)
class MuestraAtencion:
    pais: str
    hoja_fuente: str
    fila_fuente: int
    numero_oc: str
    estado: str
    evidencia: str

    def como_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PuntoAtencion:
    codigo: str
    titulo: str
    categoria: str
    descripcion: str
    cantidad: int
    muestras: tuple[MuestraAtencion, ...]

    def como_dict(self) -> dict[str, object]:
        return {
            "codigo": self.codigo,
            "titulo": self.titulo,
            "categoria": self.categoria,
            "descripcion": self.descripcion,
            "cantidad": self.cantidad,
            "muestras": [muestra.como_dict() for muestra in self.muestras],
        }


def _fecha_fuente(valor: str) -> date | None:
    texto = str(valor or "").strip()
    if not texto:
        return None

    # Formatos explícitos observables/esperables. Un valor no interpretable
    # se reporta por separado; nunca se adivina una fecha.
    candidatos = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    )
    for formato in candidatos:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _muestra(
    linea: LineaCompra,
    *,
    evidencia: str,
) -> MuestraAtencion:
    return MuestraAtencion(
        pais=linea.pais,
        hoja_fuente=linea.hoja_fuente,
        fila_fuente=linea.fila_fuente,
        numero_oc=linea.numero_oc,
        estado=linea.estado_normalizado,
        evidencia=evidencia,
    )


def evaluar_puntos_atencion(
    lineas: Iterable[LineaCompra],
    *,
    hoy: date | None = None,
    max_muestras: int = 5,
) -> tuple[PuntoAtencion, ...]:
    hoy = hoy or date.today()
    lineas_lista = tuple(lineas)
    resultados: list[PuntoAtencion] = []

    def agregar_lineas(
        *,
        codigo: str,
        titulo: str,
        categoria: str,
        descripcion: str,
        seleccion: list[tuple[LineaCompra, str]],
    ) -> None:
        if not seleccion:
            return
        resultados.append(
            PuntoAtencion(
                codigo=codigo,
                titulo=titulo,
                categoria=categoria,
                descripcion=descripcion,
                cantidad=len(seleccion),
                muestras=tuple(
                    _muestra(linea, evidencia=evidencia)
                    for linea, evidencia in seleccion[:max_muestras]
                ),
            )
        )

    enviadas = [
        linea
        for linea in lineas_lista
        if linea.estado_normalizado == "ENVIADO A DESTINO"
    ]
    agregar_lineas(
        codigo="ENVIADA_SIN_DOCUMENTO",
        titulo="Enviada sin documento de transporte",
        categoria="DOCUMENTACION",
        descripcion=(
            "Línea en ENVIADO A DESTINO sin documento de transporte diligenciado."
        ),
        seleccion=[
            (linea, "DOCUMENTO DE TRANSPORTE vacío")
            for linea in enviadas
            if not linea.documento_transporte.strip()
        ],
    )
    agregar_lineas(
        codigo="ENVIADA_SIN_ETD",
        titulo="Enviada sin ETD",
        categoria="FECHAS",
        descripcion="Línea en ENVIADO A DESTINO sin ETD diligenciada.",
        seleccion=[
            (linea, "ETD vacía")
            for linea in enviadas
            if not linea.etd.strip()
        ],
    )
    agregar_lineas(
        codigo="ENVIADA_SIN_ETA",
        titulo="Enviada sin ETA",
        categoria="FECHAS",
        descripcion="Línea en ENVIADO A DESTINO sin ETA diligenciada.",
        seleccion=[
            (linea, "ETA vacía")
            for linea in enviadas
            if not linea.eta.strip()
        ],
    )

    eta_vencida: list[tuple[LineaCompra, str]] = []
    eta_no_interpretable: list[tuple[LineaCompra, str]] = []
    for linea in lineas_lista:
        if (
            not linea.eta.strip()
            or linea.fecha_entrega_bodega_destino.strip()
            or linea.etapa_logistica == "RECIBIDO"
            or linea.situacion_operativa == "ANULADA"
        ):
            continue
        eta = _fecha_fuente(linea.eta)
        if eta is None:
            eta_no_interpretable.append((linea, f"ETA origen: {linea.eta}"))
        elif eta < hoy:
            eta_vencida.append(
                (
                    linea,
                    f"ETA {eta.isoformat()} < {hoy.isoformat()} y sin entrega",
                )
            )

    agregar_lineas(
        codigo="ETA_VENCIDA_SIN_ENTREGA",
        titulo="ETA vencida sin entrega registrada",
        categoria="FECHAS",
        descripcion=(
            "ETA anterior a hoy, sin fecha de entrega a bodega y sin etapa RECIBIDO."
        ),
        seleccion=eta_vencida,
    )
    agregar_lineas(
        codigo="ETA_NO_INTERPRETABLE",
        titulo="ETA no interpretable",
        categoria="CALIDAD_FECHA",
        descripcion=(
            "La ETA tiene contenido, pero no coincide con los formatos de fecha "
            "soportados. No se usa para decidir vencimiento."
        ),
        seleccion=eta_no_interpretable,
    )

    entrega_estado_abierto = [
        (
            linea,
            f"Entrega origen: {linea.fecha_entrega_bodega_destino}; "
            f"etapa: {linea.etapa_logistica}",
        )
        for linea in lineas_lista
        if linea.fecha_entrega_bodega_destino.strip()
        and linea.etapa_logistica not in {"RECIBIDO", "SIN_ETAPA"}
    ]
    agregar_lineas(
        codigo="ENTREGA_CON_ESTADO_ABIERTO",
        titulo="Entrega registrada con estado abierto",
        categoria="CONSISTENCIA",
        descripcion=(
            "Existe fecha de entrega a bodega, pero la etapa normalizada aún no "
            "es RECIBIDO. La plataforma solo señala la inconsistencia."
        ),
        seleccion=entrega_estado_abierto,
    )

    ocs = tuple(oc for oc in agrupar_ocs(lineas_lista) if oc.oc_identificada)

    def agregar_ocs(
        *,
        codigo: str,
        titulo: str,
        descripcion: str,
        seleccion: list[tuple[object, str]],
    ) -> None:
        if not seleccion:
            return
        muestras = []
        for oc, evidencia in seleccion[:max_muestras]:
            # ResumenOC siempre tiene estos atributos; se evita acoplar la
            # dataclass de muestra a una fila específica que sería arbitraria.
            muestras.append(
                MuestraAtencion(
                    pais=oc.pais,
                    hoja_fuente="AGRUPACION_OC",
                    fila_fuente=0,
                    numero_oc=oc.numero_oc,
                    estado=" / ".join(oc.estados),
                    evidencia=evidencia,
                )
            )
        resultados.append(
            PuntoAtencion(
                codigo=codigo,
                titulo=titulo,
                categoria="COMPOSICION_OC",
                descripcion=descripcion,
                cantidad=len(seleccion),
                muestras=tuple(muestras),
            )
        )

    agregar_ocs(
        codigo="OC_ESTADOS_MIXTOS",
        titulo="OC con varios estados",
        descripcion=(
            "La OC contiene líneas en más de un estado fuente. No se asigna un "
            "estado agregado automáticamente."
        ),
        seleccion=[
            (oc, ", ".join(oc.estados))
            for oc in ocs
            if oc.estado_mixto
        ],
    )
    agregar_ocs(
        codigo="OC_PROVEEDORES_MULTIPLES",
        titulo="OC con varios proveedores",
        descripcion="La OC contiene líneas asociadas a más de un proveedor.",
        seleccion=[
            (oc, ", ".join(oc.proveedores))
            for oc in ocs
            if oc.proveedor_mixto
        ],
    )
    agregar_ocs(
        codigo="OC_TRANSPORTES_MULTIPLES",
        titulo="OC con varios modos de transporte",
        descripcion=(
            "La OC contiene líneas asociadas a más de un modo de transporte."
        ),
        seleccion=[
            (oc, ", ".join(oc.modos_transporte))
            for oc in ocs
            if oc.transporte_mixto
        ],
    )

    return tuple(resultados)
