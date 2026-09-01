"""Lógica de autenticación.

Usa bcrypt para verificar contraseñas y JWT para los tokens de sesión.
El token lleva el id del usuario y su rol, y expira en 8 horas.
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from modules.auth import models
from modules.auth.schemas import TokenResponse, UserInfo

# En producción cambiar esta clave por una larga y aleatoria en .env
_SECRET_KEY = os.getenv("JWT_SECRET", "mapaid-demo-secret-2024")
_ALGORITHM = "HS256"
_EXPIRE_HORAS = 8


class CredencialesInvalidas(ValueError):
    """Email o contraseña incorrectos."""


class TokenInvalido(ValueError):
    """El token no es válido o ha expirado."""


def login(email: str, password: str) -> TokenResponse:
    usuario = models.obtener_usuario_por_email(email)

    if usuario is None:
        raise CredencialesInvalidas("Email o contraseña incorrectos.")

    contrasena_correcta = bcrypt.checkpw(
        password.encode(), usuario["password_hash"].encode()
    )
    if not contrasena_correcta:
        raise CredencialesInvalidas("Email o contraseña incorrectos.")

    expira = datetime.now(timezone.utc) + timedelta(hours=_EXPIRE_HORAS)
    payload = {
        "sub": str(usuario["id"]),
        "rol": usuario["rol"],
        "exp": expira,
    }
    token = jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)

    return TokenResponse(
        token=token,
        rol=usuario["rol"],
        email=usuario["email"],
    )


def verificar_token(token: str) -> UserInfo:
    """Decodifica el token y devuelve los datos del usuario.

    Lanza TokenInvalido si el token es incorrecto o ha expirado.
    """
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        usuario_id = int(payload["sub"])
        rol = payload["rol"]
    except (JWTError, KeyError, ValueError) as error:
        raise TokenInvalido("Token inválido o expirado.") from error

    usuario = models.obtener_usuario_por_id(usuario_id)
    if usuario is None:
        raise TokenInvalido("El usuario del token ya no existe.")

    return UserInfo(id=usuario["id"], email=usuario["email"], rol=usuario["rol"])
