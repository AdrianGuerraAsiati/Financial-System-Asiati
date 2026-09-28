from dataclasses import dataclass

from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


@dataclass(frozen=True)
class CasoValidacionCartera:
    codigo: str
    cantidad: int
    valor: float
    registros: tuple[RegistroCarteraEnCamino, ...]


def validar_cartera_en_camino(
    registros: list[RegistroCarteraEnCamino] | tuple[RegistroCarteraEnCamino, ...],
) -> tuple[CasoValidacionCartera, ...]:
    """Preserva las validaciones de calidad existentes del tablero de Cartera en Camino."""
    casos: list[CasoValidacionCartera] = []

    sin_oc = tuple(
        registro
        for registro in registros
        if not registro.oc
        and (
            registro.valor
            or registro.valor_anticipo
            or registro.valor_financiado
        )
    )
    if sin_oc:
        casos.append(
            CasoValidacionCartera(
                codigo="sin_numero_oc",
                cantidad=len(sin_oc),
                valor=sum(registro.valor for registro in sin_oc),
                registros=sin_oc,
            )
        )

    vistos: set[tuple[str, str, str, str, str]] = set()
    repetidas: list[RegistroCarteraEnCamino] = []

    for registro in registros:
        clave = (
            registro.oc,
            registro.sku,
            registro.documento_transporte,
            registro.producto,
            f"{registro.valor:.2f}",
        )
        if clave in vistos:
            repetidas.append(registro)
        else:
            vistos.add(clave)

    if repetidas:
        repetidas_tuple = tuple(repetidas)
        casos.append(
            CasoValidacionCartera(
                codigo="linea_repetida",
                cantidad=len(repetidas_tuple),
                valor=sum(registro.valor for registro in repetidas_tuple),
                registros=repetidas_tuple,
            )
        )

    descuadres = tuple(
        registro
        for registro in registros
        if abs(
            registro.valor
            - registro.valor_anticipo
            - registro.valor_financiado
        )
        > 0.01
    )
    if descuadres:
        casos.append(
            CasoValidacionCartera(
                codigo="valor_oci_descuadra",
                cantidad=len(descuadres),
                valor=sum(
                    registro.valor
                    - registro.valor_anticipo
                    - registro.valor_financiado
                    for registro in descuadres
                ),
                registros=descuadres,
            )
        )

    valor_cero_con_componentes = tuple(
        registro
        for registro in registros
        if not registro.valor
        and (
            registro.valor_anticipo
            or registro.valor_financiado
        )
    )
    if valor_cero_con_componentes:
        casos.append(
            CasoValidacionCartera(
                codigo="valor_oci_cero_con_componentes",
                cantidad=len(valor_cero_con_componentes),
                valor=sum(
                    registro.valor_anticipo + registro.valor_financiado
                    for registro in valor_cero_con_componentes
                ),
                registros=valor_cero_con_componentes,
            )
        )

    return tuple(casos)
