from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass

import httpx

from app.core.auth.config import ConfiguracionAuth


class CognitoError(RuntimeError):
    """Error base del proveedor Cognito."""


class CognitoCredencialesInvalidas(CognitoError):
    pass


class CognitoUsuarioNoConfirmado(CognitoError):
    pass


class CognitoUsuarioExiste(CognitoError):
    pass


class CognitoCodigoInvalido(CognitoError):
    pass


class CognitoPasswordInvalida(CognitoError):
    pass


class CognitoNoDisponible(CognitoError):
    pass


@dataclass(frozen=True)
class ResultadoCognito:
    requiere_nueva_password: bool
    access_token: str | None = None


class _RespuestaCognitoError(CognitoError):
    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class ClienteCognito:
    """Cliente mínimo para las APIs públicas de Cognito User Pools.

    La aplicación usa un app client confidencial. El client secret vive únicamente
    en el entorno del servidor; nunca se envía al navegador.
    """

    def __init__(self, configuracion: ConfiguracionAuth) -> None:
        if not configuracion.cognito_region:
            raise CognitoNoDisponible("Falta COGNITO_REGION.")
        if not configuracion.cognito_client_id:
            raise CognitoNoDisponible("Falta COGNITO_CLIENT_ID.")
        if not configuracion.cognito_client_secret:
            raise CognitoNoDisponible("Falta COGNITO_CLIENT_SECRET.")
        self.region = configuracion.cognito_region
        self.client_id = configuracion.cognito_client_id
        self.client_secret = configuracion.cognito_client_secret
        self.endpoint = f"https://cognito-idp.{self.region}.amazonaws.com/"

    def _secret_hash(self, username: str) -> str:
        firma = hmac.new(
            self.client_secret.encode("utf-8"),
            f"{username}{self.client_id}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(firma).decode("ascii")

    def _llamar(self, operacion: str, payload: dict[str, object]) -> dict[str, object]:
        try:
            respuesta = httpx.post(
                self.endpoint,
                headers={
                    "Content-Type": "application/x-amz-json-1.1",
                    "X-Amz-Target": (
                        "AWSCognitoIdentityProviderService." + operacion
                    ),
                },
                json=payload,
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise CognitoNoDisponible(
                "No se pudo contactar Amazon Cognito."
            ) from exc

        if respuesta.status_code < 400:
            try:
                return dict(respuesta.json())
            except ValueError as exc:
                raise CognitoNoDisponible(
                    "Amazon Cognito respondió en un formato inesperado."
                ) from exc

        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = {}
        codigo = str(cuerpo.get("__type") or cuerpo.get("code") or "")
        codigo = codigo.rsplit("#", 1)[-1]
        mensaje = str(
            cuerpo.get("message")
            or cuerpo.get("Message")
            or f"Amazon Cognito respondió HTTP {respuesta.status_code}."
        )
        raise _RespuestaCognitoError(codigo, mensaje)

    @staticmethod
    def _es_limite(exc: _RespuestaCognitoError) -> bool:
        return exc.codigo in {
            "LimitExceededException",
            "TooManyRequestsException",
            "TooManyFailedAttemptsException",
        }

    def autenticar(self, email: str, password: str) -> ResultadoCognito:
        try:
            cuerpo = self._llamar(
                "InitiateAuth",
                {
                    "AuthFlow": "USER_PASSWORD_AUTH",
                    "ClientId": self.client_id,
                    "AuthParameters": {
                        "USERNAME": email,
                        "PASSWORD": password,
                        "SECRET_HASH": self._secret_hash(email),
                    },
                },
            )
        except _RespuestaCognitoError as exc:
            if exc.codigo in {"NotAuthorizedException", "UserNotFoundException"}:
                raise CognitoCredencialesInvalidas() from exc
            if exc.codigo == "UserNotConfirmedException":
                raise CognitoUsuarioNoConfirmado() from exc
            if self._es_limite(exc):
                raise CognitoNoDisponible(
                    "Amazon Cognito limitó temporalmente los intentos."
                ) from exc
            raise CognitoNoDisponible("Amazon Cognito rechazó el login.") from exc

        if cuerpo.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            return ResultadoCognito(requiere_nueva_password=True)

        autenticacion = cuerpo.get("AuthenticationResult")
        if isinstance(autenticacion, dict) and autenticacion.get("AccessToken"):
            return ResultadoCognito(
                requiere_nueva_password=False,
                access_token=str(autenticacion["AccessToken"]),
            )

        raise CognitoNoDisponible(
            "Amazon Cognito pidió un desafío de autenticación no soportado."
        )

    def cambiar_password(self, email: str, actual: str, nueva: str) -> None:
        try:
            cuerpo = self._llamar(
                "InitiateAuth",
                {
                    "AuthFlow": "USER_PASSWORD_AUTH",
                    "ClientId": self.client_id,
                    "AuthParameters": {
                        "USERNAME": email,
                        "PASSWORD": actual,
                        "SECRET_HASH": self._secret_hash(email),
                    },
                },
            )
        except _RespuestaCognitoError as exc:
            if exc.codigo in {"NotAuthorizedException", "UserNotFoundException"}:
                raise CognitoCredencialesInvalidas() from exc
            if exc.codigo == "UserNotConfirmedException":
                raise CognitoUsuarioNoConfirmado() from exc
            if self._es_limite(exc):
                raise CognitoNoDisponible(
                    "Amazon Cognito limitó temporalmente los intentos."
                ) from exc
            raise CognitoNoDisponible(
                "Amazon Cognito no pudo validar la contraseña actual."
            ) from exc

        if cuerpo.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            sesion = cuerpo.get("Session")
            if not sesion:
                raise CognitoNoDisponible(
                    "Cognito no devolvió la sesión para completar el primer ingreso."
                )
            try:
                self._llamar(
                    "RespondToAuthChallenge",
                    {
                        "ClientId": self.client_id,
                        "ChallengeName": "NEW_PASSWORD_REQUIRED",
                        "Session": sesion,
                        "ChallengeResponses": {
                            "USERNAME": email,
                            "NEW_PASSWORD": nueva,
                            "SECRET_HASH": self._secret_hash(email),
                        },
                    },
                )
                return
            except _RespuestaCognitoError as exc:
                if exc.codigo == "InvalidPasswordException":
                    raise CognitoPasswordInvalida(exc.mensaje) from exc
                if self._es_limite(exc):
                    raise CognitoNoDisponible(
                        "Amazon Cognito limitó temporalmente la operación."
                    ) from exc
                raise CognitoNoDisponible(
                    "Amazon Cognito no pudo completar el primer ingreso."
                ) from exc

        autenticacion = cuerpo.get("AuthenticationResult")
        if not isinstance(autenticacion, dict) or not autenticacion.get("AccessToken"):
            raise CognitoNoDisponible(
                "Amazon Cognito pidió un desafío de autenticación no soportado."
            )

        try:
            self._llamar(
                "ChangePassword",
                {
                    "PreviousPassword": actual,
                    "ProposedPassword": nueva,
                    "AccessToken": autenticacion["AccessToken"],
                },
            )
        except _RespuestaCognitoError as exc:
            if exc.codigo in {"NotAuthorizedException", "UserNotFoundException"}:
                raise CognitoCredencialesInvalidas() from exc
            if exc.codigo == "InvalidPasswordException":
                raise CognitoPasswordInvalida(exc.mensaje) from exc
            if self._es_limite(exc):
                raise CognitoNoDisponible(
                    "Amazon Cognito limitó temporalmente la operación."
                ) from exc
            raise CognitoNoDisponible(
                "Amazon Cognito no pudo cambiar la contraseña."
            ) from exc

    def registrar_usuario(
        self,
        *,
        email: str,
        nombre: str,
        password_temporal: str,
    ) -> None:
        try:
            self._llamar(
                "SignUp",
                {
                    "ClientId": self.client_id,
                    "SecretHash": self._secret_hash(email),
                    "Username": email,
                    "Password": password_temporal,
                    "UserAttributes": [
                        {"Name": "email", "Value": email},
                        {"Name": "name", "Value": nombre},
                    ],
                },
            )
        except _RespuestaCognitoError as exc:
            if exc.codigo == "UsernameExistsException":
                raise CognitoUsuarioExiste() from exc
            if exc.codigo == "InvalidPasswordException":
                raise CognitoPasswordInvalida(exc.mensaje) from exc
            if self._es_limite(exc):
                raise CognitoNoDisponible(
                    "Amazon Cognito limitó temporalmente el alta."
                ) from exc
            raise CognitoNoDisponible(
                "Amazon Cognito no pudo crear la identidad del usuario."
            ) from exc

    def confirmar_registro(self, *, email: str, codigo: str) -> None:
        try:
            self._llamar(
                "ConfirmSignUp",
                {
                    "ClientId": self.client_id,
                    "SecretHash": self._secret_hash(email),
                    "Username": email,
                    "ConfirmationCode": codigo,
                },
            )
        except _RespuestaCognitoError as exc:
            if exc.codigo in {"CodeMismatchException", "ExpiredCodeException"}:
                raise CognitoCodigoInvalido() from exc
            if self._es_limite(exc):
                raise CognitoNoDisponible(
                    "Amazon Cognito limitó temporalmente la confirmación."
                ) from exc
            raise CognitoNoDisponible(
                "Amazon Cognito no pudo confirmar la cuenta."
            ) from exc

    def reenviar_confirmacion(self, *, email: str) -> None:
        try:
            self._llamar(
                "ResendConfirmationCode",
                {
                    "ClientId": self.client_id,
                    "SecretHash": self._secret_hash(email),
                    "Username": email,
                },
            )
        except _RespuestaCognitoError as exc:
            if self._es_limite(exc):
                raise CognitoNoDisponible(
                    "Amazon Cognito limitó temporalmente el reenvío."
                ) from exc
            # No se diferencia usuario inexistente para evitar enumeración.
            if exc.codigo in {
                "UserNotFoundException",
                "NotAuthorizedException",
                "InvalidParameterException",
            }:
                return
            raise CognitoNoDisponible(
                "Amazon Cognito no pudo reenviar el código."
            ) from exc

    def solicitar_restablecimiento(self, *, email: str) -> None:
        try:
            self._llamar(
                "ForgotPassword",
                {
                    "ClientId": self.client_id,
                    "SecretHash": self._secret_hash(email),
                    "Username": email,
                },
            )
        except _RespuestaCognitoError as exc:
            if self._es_limite(exc):
                raise CognitoNoDisponible(
                    "Amazon Cognito limitó temporalmente el restablecimiento."
                ) from exc
            # Respuesta deliberadamente genérica para no enumerar cuentas.
            if exc.codigo in {
                "UserNotFoundException",
                "InvalidParameterException",
                "NotAuthorizedException",
            }:
                return
            raise CognitoNoDisponible(
                "Amazon Cognito no pudo iniciar el restablecimiento."
            ) from exc

    def confirmar_restablecimiento(
        self,
        *,
        email: str,
        codigo: str,
        password_nueva: str,
    ) -> None:
        try:
            self._llamar(
                "ConfirmForgotPassword",
                {
                    "ClientId": self.client_id,
                    "SecretHash": self._secret_hash(email),
                    "Username": email,
                    "ConfirmationCode": codigo,
                    "Password": password_nueva,
                },
            )
        except _RespuestaCognitoError as exc:
            if exc.codigo in {"CodeMismatchException", "ExpiredCodeException"}:
                raise CognitoCodigoInvalido() from exc
            if exc.codigo == "InvalidPasswordException":
                raise CognitoPasswordInvalida(exc.mensaje) from exc
            if self._es_limite(exc):
                raise CognitoNoDisponible(
                    "Amazon Cognito limitó temporalmente el restablecimiento."
                ) from exc
            raise CognitoNoDisponible(
                "Amazon Cognito no pudo completar el restablecimiento."
            ) from exc
