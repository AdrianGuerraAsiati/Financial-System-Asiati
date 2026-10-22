"""Conexión OAuth de Google Sheets desde navegador; tokens cifrados y solo lectura.

Cartera utiliza esta credencial cuando está conectada, en lugar de las ADC
personales del operador de la instancia. Google Cloud OAuth requiere una
configuración inicial de client_id/secret/redirección hecha por TI.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import requests
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.auditoria.service import registrar_auditoria
from app.core.auth.dependencias import Acceso, requiere, usuario_vigente
from app.core.db import Base
from app.core.session import crear_session, obtener_session
from app.core.usuarios.model import Usuario
from app.core.empresas import Empresa
from app.core.permisos import permisos_efectivos

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
CALLBACK_PATH = "/api/v1/integrations/google-sheets/oauth/callback"
TTL_ESTADO = timedelta(minutes=10)
router = APIRouter(prefix="/integrations/google-sheets", tags=["integrations"])


class ConexionGoogleSheets(Base):
    __tablename__ = "google_sheets_oauth_conexiones"

    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"), primary_key=True)
    refresh_token_cifrado: Mapped[str] = mapped_column(Text, nullable=False)
    autorizado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EstadoOAuthGoogleSheets(Base):
    __tablename__ = "google_sheets_oauth_estados"

    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


def _config() -> tuple[str, str, str]:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    parsed = urlparse(redirect_uri)
    if (
        not client_id or not client_secret
        or parsed.scheme != "https"
        or parsed.path != CALLBACK_PATH
        or parsed.query or parsed.fragment or not parsed.netloc
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "La conexión con Google debe activarla TI una sola vez. "
                "Falta configurar el cliente OAuth y su URL HTTPS de retorno."
            ),
        )
    return client_id, client_secret, redirect_uri


def _fernet() -> Fernet:
    # Dominio criptográfico separado del JWT: nunca se persiste el token en claro.
    secret = os.getenv("GOOGLE_OAUTH_TOKEN_KEY") or os.getenv("JWT_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="La clave de cifrado OAuth no está configurada.")
    key = hashlib.sha256(b"asiati.google-sheets.oauth.refresh.v1:" + secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _hash_estado(state: str) -> str:
    return hashlib.sha256(state.encode("ascii")).hexdigest()


def _pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode().rstrip("=")


def construir_url_google(*, client_id: str, redirect_uri: str, state: str, verifier: str) -> str:
    """Genera consentimiento offline con scope mínimo y PKCE S256."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SHEETS_SCOPE,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": _pkce_challenge(verifier),
        "code_challenge_method": "S256",
    }
    return AUTHORIZE_URL + "?" + urlencode(params)


def _origin_valido(request: Request) -> None:
    """Evita cambios de conexión provocados por otro sitio mediante cookies."""
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    if not origin or urlparse(origin).netloc != host or urlparse(origin).scheme != "https":
        raise HTTPException(status_code=403, detail="Solicitud desde un origen no autorizado.")


def _empresa_query(empresa_id: int) -> int:
    return empresa_id


ver_cartera = requiere("cartera.ver", empresa_de=_empresa_query)
administrar = requiere("google_sheets.conectar")


def obtener_sesion_oauth_cartera(empresa_id: int) -> AuthorizedSession | None:
    """Prioriza token corporativo asociado a empresa; None permite legado ADC."""
    with crear_session() as session:
        conexion = session.get(ConexionGoogleSheets, empresa_id)
        if conexion is None:
            return None
        try:
            refresh_token = _fernet().decrypt(conexion.refresh_token_cifrado.encode()).decode()
        except InvalidToken as exc:
            raise HTTPException(
                status_code=503,
                detail="La conexión de Google Sheets requiere nueva autorización en Cartera.",
            ) from exc
    client_id, client_secret, _ = _config()
    credenciales = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        scopes=[SHEETS_SCOPE],
    )
    return AuthorizedSession(credenciales)


@router.get("/conexion")
def estado_conexion(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    conexion = session.get(ConexionGoogleSheets, empresa_id)
    try:
        _config()
        configurado = True
    except HTTPException:
        configurado = False
    return {
        "empresa_id": empresa_id,
        "conectada": conexion is not None,
        "oauth_configurado": configurado,
        "solo_lectura": True,
        "modo": "OAUTH_WEB" if conexion is not None else "ADC_LEGADO",
        "actualizado_en": conexion.actualizado_en.isoformat() if conexion is not None else None,
    }


@router.post("/conexion/iniciar")
def iniciar_conexion(
    request: Request,
    empresa_id: int,
    acceso: Acceso = Depends(administrar),
    session: Session = Depends(obtener_session),
) -> dict[str, str]:
    _origin_valido(request)
    client_id, _, redirect_uri = _config()
    _fernet()
    if session.get(Empresa, empresa_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")
    if os.getenv("CARTERA_SHEETS_EMPRESA_ID", "").strip() != str(empresa_id):
        raise HTTPException(status_code=409, detail="La fuente de Cartera no está configurada para esta empresa.")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    registro = EstadoOAuthGoogleSheets(
        state_hash=_hash_estado(state),
        empresa_id=empresa_id,
        usuario_id=acceso.usuario.id,
        code_verifier=verifier,
        vence_en=datetime.now(timezone.utc) + TTL_ESTADO,
    )
    session.add(registro)
    session.commit()
    return {
        "url": construir_url_google(
            client_id=client_id, redirect_uri=redirect_uri, state=state, verifier=verifier,
        )
    }


@router.get("/oauth/callback")
def oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    usuario: Usuario = Depends(usuario_vigente),
    session: Session = Depends(obtener_session),
) -> RedirectResponse:
    if error:
        return RedirectResponse("/?google_sheets=denegada", status_code=303)
    if not code or not state or len(state) > 200 or not state.isascii():
        raise HTTPException(status_code=400, detail="Respuesta de autorización incompleta.")
    registro = session.scalar(
        select(EstadoOAuthGoogleSheets)
        .where(EstadoOAuthGoogleSheets.state_hash == _hash_estado(state))
        .with_for_update()
    )
    if registro is None or registro.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="La autorización no corresponde a esta sesión.")
    if registro.vence_en < datetime.now(timezone.utc):
        session.delete(registro)
        session.commit()
        raise HTTPException(status_code=400, detail="La autorización caducó. Inicia de nuevo.")
    if "google_sheets.conectar" not in permisos_efectivos(usuario.rol):
        raise HTTPException(status_code=403, detail="Sin permiso para conectar Google Sheets.")
    empresa_id, verifier = registro.empresa_id, registro.code_verifier
    session.delete(registro)
    session.commit()  # nonce de un solo uso incluso si Google falla

    client_id, client_secret, redirect_uri = _config()
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return RedirectResponse("/?google_sheets=error", status_code=303)
    concedidos = set(payload.get("scope", "").split())
    if SHEETS_SCOPE not in concedidos:
        return RedirectResponse("/?google_sheets=permisos", status_code=303)
    refresh_token = payload.get("refresh_token")
    if not refresh_token or not isinstance(refresh_token, str):
        return RedirectResponse("/?google_sheets=sin_refresh", status_code=303)

    # No se guarda la conexión hasta demostrar acceso a la hoja ya configurada.
    spreadsheet_id = os.getenv("CARTERA_SHEETS_SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        return RedirectResponse("/?google_sheets=sin_hoja", status_code=303)
    credenciales = Credentials(
        token=payload["access_token"],
        refresh_token=refresh_token,
        token_uri=TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        scopes=[SHEETS_SCOPE],
    )
    try:
        respuesta = AuthorizedSession(credenciales).get(
            "https://sheets.googleapis.com/v4/spreadsheets/" + spreadsheet_id,
            params={"fields": "spreadsheetId"},
            timeout=15,
        )
        respuesta.raise_for_status()
    except (requests.RequestException, KeyError):
        return RedirectResponse("/?google_sheets=sin_acceso", status_code=303)

    cifrado = _fernet().encrypt(refresh_token.encode()).decode()
    conexion = session.get(ConexionGoogleSheets, empresa_id)
    if conexion is None:
        conexion = ConexionGoogleSheets(
            empresa_id=empresa_id,
            refresh_token_cifrado=cifrado,
            autorizado_por=usuario.id,
        )
        session.add(conexion)
    else:
        conexion.refresh_token_cifrado = cifrado
        conexion.autorizado_por = usuario.id
        conexion.actualizado_en = datetime.now(timezone.utc)
    registrar_auditoria(
        session, usuario_id=usuario.id, empresa_id=empresa_id,
        accion="google_sheets.oauth_conectado", entidad="google_sheets_oauth_conexion",
        entidad_id=empresa_id, despues={"solo_lectura": True},
    )
    session.commit()
    return RedirectResponse("/?google_sheets=conectada", status_code=303)


@router.get("/conexion/probar")
def probar_conexion(
    empresa_id: int,
    _acceso: Acceso = Depends(administrar),
) -> dict[str, object]:
    conexion = obtener_sesion_oauth_cartera(empresa_id)
    if conexion is None:
        raise HTTPException(status_code=409, detail="Primero conecta Google Sheets.")
    spreadsheet_id = os.getenv("CARTERA_SHEETS_SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        raise HTTPException(status_code=503, detail="La hoja de Cartera no está configurada.")
    try:
        respuesta = conexion.get(
            "https://sheets.googleapis.com/v4/spreadsheets/" + spreadsheet_id,
            params={"fields": "spreadsheetId"},
            timeout=15,
        )
        respuesta.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="Google rechazó el acceso. Usa Reconectar Google Sheets.") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="La autorización caducó. Usa Reconectar Google Sheets.") from exc
    return {"ok": True, "solo_lectura": True}


@router.post("/conexion/desconectar")
def desconectar(
    request: Request,
    empresa_id: int,
    acceso: Acceso = Depends(administrar),
    session: Session = Depends(obtener_session),
) -> dict[str, bool]:
    _origin_valido(request)
    conexion = session.get(ConexionGoogleSheets, empresa_id)
    if conexion is not None:
        session.delete(conexion)
        registrar_auditoria(
            session, usuario_id=acceso.usuario.id, empresa_id=empresa_id,
            accion="google_sheets.oauth_desconectado", entidad="google_sheets_oauth_conexion",
            entidad_id=empresa_id, antes={"solo_lectura": True},
        )
        session.commit()
    return {"conectada": False}
