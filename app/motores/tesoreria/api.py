"""API de facturas de compra y pagos manuales; no procesa recaudos de clientes."""
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auditoria.service import registrar_auditoria
from app.core.auth.dependencias import Acceso, requiere
from app.core.dimensiones.model import DimensionValor
from app.core.dimensiones.service import normalizar
from app.core.empresas import Empresa
from app.core.session import obtener_session
from app.motores.tesoreria.extraccion import extraer_ubl
from app.motores.tesoreria.model import FacturaCompra, PagoFactura
from app.motores.tesoreria.reglas import estado_factura
from app.motores.tesoreria.storage import leer_archivo, guardar, eliminar, descarga

router = APIRouter(prefix="/tesoreria", tags=["tesoreria"])


def _empresa(session: Session, acceso: Acceso, empresa_id: int) -> None:
    if (acceso.empresas_visibles is not None and empresa_id not in acceso.empresas_visibles
            or session.get(Empresa, empresa_id) is None):
        raise HTTPException(404, "Empresa no encontrada.")


def _factura(session: Session, acceso: Acceso, factura_id: int) -> FacturaCompra:
    f = session.get(FacturaCompra, factura_id)
    if f is None:
        raise HTTPException(404, "Factura no encontrada.")
    _empresa(session, acceso, f.empresa_id)
    return f


def _texto(valor: str | None, maximo: int, obligatorio: bool = False) -> str | None:
    t = " ".join((valor or "").split())
    if len(t) > maximo or (obligatorio and not t):
        raise HTTPException(422, f"Campo obligatorio o demasiado largo (máximo {maximo}).")
    return t or None


def _monto(valor: Decimal) -> Decimal:
    if (not valor.is_finite() or valor <= 0 or valor.as_tuple().exponent < -2
            or valor > Decimal("9999999999999999.99")):
        raise HTTPException(422, "El monto debe ser positivo, máximo 2 decimales y finito.")
    return valor.quantize(Decimal("0.01"))


def _dimension(session: Session, nombre: str, valor: str | None) -> str | None:
    if not valor:
        return None
    encontrado = session.scalar(select(DimensionValor).where(
        DimensionValor.dimension == nombre,
        DimensionValor.valor_normalizado == normalizar(valor),
        DimensionValor.activo.is_(True),
    ))
    if encontrado is None:
        raise HTTPException(422, f"Selecciona un valor activo de {nombre}.")
    return encontrado.valor


def _pagos(session: Session, factura_id: int) -> list[PagoFactura]:
    return list(session.scalars(select(PagoFactura).where(PagoFactura.factura_id == factura_id)
                                .order_by(PagoFactura.fecha, PagoFactura.id)))


def _json(session: Session, f: FacturaCompra, *, detalle: bool = False) -> dict:
    pagos = _pagos(session, f.id)
    resultado = {
        "id": f.id, "empresa_id": f.empresa_id, "numero": f.numero,
        "proveedor": f.proveedor, "fecha_emision": f.fecha_emision,
        "fecha_pago_oportuno": f.fecha_vencimiento,
        "fecha_pago_real": pagos[-1].fecha if pagos else None,
        "monto": format(f.monto, ".2f"), "moneda": f.moneda, "descripcion": f.descripcion,
        "ciudad": f.ciudad, "unidad_negocio": f.unidad_negocio, "categoria": f.categoria,
        "fijo_variable": f.fijo_variable, "cuenta_pago": f.cuenta_pago,
        "documento_contable": f.documento_contable, "archivo_nombre": f.archivo_nombre,
        "pagos_cantidad": len(pagos),
        **estado_factura(f.monto, [p.monto for p in pagos], f.fecha_vencimiento, date.today()),
    }
    if detalle:
        resultado["pagos"] = [
            {"id": p.id, "fecha": p.fecha, "monto": format(p.monto, ".2f"),
             "referencia": p.referencia, "soporte_nombre": p.soporte_nombre}
            for p in pagos
        ]
    return resultado


@router.get("/catalogos")
def catalogos(
    empresa_id: int, acceso: Acceso = Depends(requiere("tesoreria.ver")),
    session: Session = Depends(obtener_session),
) -> dict:
    _empresa(session, acceso, empresa_id)
    return {dimension: list(session.scalars(select(DimensionValor.valor).where(
        DimensionValor.dimension == dimension, DimensionValor.activo.is_(True)
    ).order_by(DimensionValor.valor))) for dimension in ("unidad_negocio", "categoria", "fijo_variable")}


@router.post("/extraer")
async def extraer(
    archivo: UploadFile = File(...),
    _acceso: Acceso = Depends(requiere("tesoreria.facturas.gestionar")),
) -> dict:
    contenido, _, extension, _ = await leer_archivo(archivo)
    if extension == ".xml":
        try:
            return extraer_ubl(contenido)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    return {"campos": {}, "advertencias": [
        "Para PDF e imagen la V1 requiere completar los campos manualmente.",
        "La extracción automática solo está disponible para XML UBL."
    ]}


@router.get("/facturas")
def listar(
    empresa_id: int, acceso: Acceso = Depends(requiere("tesoreria.ver")),
    session: Session = Depends(obtener_session),
) -> list[dict]:
    _empresa(session, acceso, empresa_id)
    facturas = session.scalars(select(FacturaCompra).where(FacturaCompra.empresa_id == empresa_id)
                              .order_by(FacturaCompra.id.desc()).limit(500))
    return [_json(session, f) for f in facturas]


@router.get("/facturas/{factura_id}")
def obtener(
    factura_id: int, acceso: Acceso = Depends(requiere("tesoreria.ver")),
    session: Session = Depends(obtener_session),
) -> dict:
    return _json(session, _factura(session, acceso, factura_id), detalle=True)


@router.post("/facturas", status_code=201)
async def crear(
    empresa_id: int = Form(...),
    numero: str = Form(...),
    proveedor: str = Form(...),
    monto: Decimal = Form(...),
    moneda: str = Form("COP"),
    descripcion: str = Form(...),
    fecha_emision: date | None = Form(None),
    fecha_vencimiento: date | None = Form(None),
    ciudad: str | None = Form(None),
    unidad_negocio: str | None = Form(None),
    categoria: str | None = Form(None),
    fijo_variable: str | None = Form(None),
    cuenta_pago: str | None = Form(None),
    documento_contable: str | None = Form(None),
    archivo: UploadFile = File(...),
    acceso: Acceso = Depends(requiere("tesoreria.facturas.gestionar")),
    session: Session = Depends(obtener_session),
) -> dict:
    _empresa(session, acceso, empresa_id)
    contenido, sha, sufijo, tipo = await leer_archivo(archivo)
    numero = _texto(numero, 120, True)
    proveedor = _texto(proveedor, 255, True)
    descripcion = _texto(descripcion, 1000, True)
    moneda = moneda.strip().upper()
    if moneda not in ("COP", "USD", "CLP"):
        raise HTTPException(422, "Moneda no admitida.")
    monto = _monto(monto)
    duplicado = session.scalar(select(FacturaCompra.id).where(
        FacturaCompra.empresa_id == empresa_id,
        or_(FacturaCompra.archivo_hash == sha,
            (FacturaCompra.numero_clave == normalizar(numero)) &
            (FacturaCompra.proveedor_clave == normalizar(proveedor))),
    ))
    if duplicado:
        raise HTTPException(409, "La factura o el documento ya están registrados.")
    factura = FacturaCompra(
        empresa_id=empresa_id, numero=numero, numero_clave=normalizar(numero),
        proveedor=proveedor, proveedor_clave=normalizar(proveedor),
        fecha_emision=fecha_emision, fecha_vencimiento=fecha_vencimiento,
        monto=monto, moneda=moneda, descripcion=descripcion,
        ciudad=_texto(ciudad, 100),
        unidad_negocio=_dimension(session, "unidad_negocio", _texto(unidad_negocio, 120)),
        categoria=_dimension(session, "categoria", _texto(categoria, 120)),
        fijo_variable=_dimension(session, "fijo_variable", _texto(fijo_variable, 120)),
        cuenta_pago=_texto(cuenta_pago, 200),
        documento_contable=_texto(documento_contable, 120),
        archivo_nombre=_texto(Path(archivo.filename or "").name, 255, True),
        archivo_hash=sha, archivo_tipo=tipo, archivo_ruta="pendiente",
        creado_por=acceso.usuario.id,
    )
    ruta = None
    try:
        session.add(factura)
        session.flush()
        ruta = guardar(empresa_id=empresa_id, factura_id=factura.id, contenido=contenido,
                       sha=sha, sufijo=sufijo)
        factura.archivo_ruta = ruta
        registrar_auditoria(session, usuario_id=acceso.usuario.id, empresa_id=empresa_id,
                            ip=acceso.ip, accion="tesoreria.factura.crear",
                            entidad="factura_compra", entidad_id=factura.id,
                            despues={"numero": numero, "proveedor": proveedor, "monto": str(monto),
                                     "fecha_vencimiento": str(fecha_vencimiento) if fecha_vencimiento else None})
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        eliminar(ruta)
        raise HTTPException(409, "Factura o archivo duplicado.") from exc
    except Exception:
        session.rollback()
        eliminar(ruta)
        raise
    return _json(session, factura, detalle=True)


@router.post("/facturas/{factura_id}/pagos", status_code=201)
async def pagar(
    factura_id: int,
    fecha: date = Form(...),
    monto: Decimal = Form(...),
    referencia: str | None = Form(None),
    comprobante: UploadFile = File(...),
    acceso: Acceso = Depends(requiere("tesoreria.pagos.registrar")),
    session: Session = Depends(obtener_session),
) -> dict:
    factura = session.scalar(select(FacturaCompra).where(FacturaCompra.id == factura_id).with_for_update())
    if factura is None:
        raise HTTPException(404, "Factura no encontrada.")
    _empresa(session, acceso, factura.empresa_id)
    contenido, sha, sufijo, tipo = await leer_archivo(comprobante, soporte=True)
    if session.scalar(select(PagoFactura.id).where(
        PagoFactura.factura_id == factura_id, PagoFactura.soporte_hash == sha)):
        raise HTTPException(409, "Este comprobante ya está registrado.")
    pagado = session.scalar(select(func.coalesce(func.sum(PagoFactura.monto), 0)).where(
        PagoFactura.factura_id == factura_id))
    monto = _monto(monto)
    if monto > factura.monto - pagado:
        raise HTTPException(422, "El monto supera el saldo pendiente.")
    pago = PagoFactura(factura_id=factura_id, fecha=fecha, monto=monto,
                      referencia=_texto(referencia, 120),
                      soporte_nombre=_texto(Path(comprobante.filename or "").name, 255, True),
                      soporte_hash=sha, soporte_tipo=tipo, soporte_ruta="pendiente",
                      registrado_por=acceso.usuario.id)
    ruta = None
    try:
        session.add(pago)
        session.flush()
        ruta = guardar(empresa_id=factura.empresa_id, factura_id=factura.id, contenido=contenido,
                       sha=sha, sufijo=sufijo, pago_id=pago.id)
        pago.soporte_ruta = ruta
        registrar_auditoria(session, usuario_id=acceso.usuario.id, empresa_id=factura.empresa_id,
                            ip=acceso.ip, accion="tesoreria.pago.registrar",
                            entidad="pago_factura", entidad_id=pago.id,
                            despues={"factura_id": factura.id, "monto": str(monto), "fecha": str(fecha),
                                     "soporte_hash": sha})
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        eliminar(ruta)
        raise HTTPException(409, "Comprobante duplicado.") from exc
    except Exception:
        session.rollback()
        eliminar(ruta)
        raise
    return _json(session, factura, detalle=True)


@router.get("/facturas/{factura_id}/documento")
def documento(factura_id: int, acceso: Acceso = Depends(requiere("tesoreria.ver")),
              session: Session = Depends(obtener_session)):
    f = _factura(session, acceso, factura_id)
    return descarga(f.archivo_ruta, f.archivo_tipo, f.archivo_nombre)


@router.get("/facturas/{factura_id}/pagos/{pago_id}/soporte")
def soporte(factura_id: int, pago_id: int,
            acceso: Acceso = Depends(requiere("tesoreria.ver")),
            session: Session = Depends(obtener_session)):
    f = _factura(session, acceso, factura_id)
    p = session.scalar(select(PagoFactura).where(PagoFactura.id == pago_id,
                                                 PagoFactura.factura_id == f.id))
    if p is None:
        raise HTTPException(404, "Comprobante no encontrado.")
    return descarga(p.soporte_ruta, p.soporte_tipo, p.soporte_nombre)
