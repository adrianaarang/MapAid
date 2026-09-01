"""Endpoints de autenticación y dependencias de protección de rutas."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from modules.auth.schemas import LoginRequest, TokenResponse, UserInfo
from modules.auth.services import (
    CredencialesInvalidas,
    TokenInvalido,
    login,
    verificar_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer()


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserInfo:
    """Extrae y valida el token Bearer de la cabecera Authorization."""
    try:
        return verificar_token(credenciales.credentials)
    except TokenInvalido as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        )


def solo_administradora(usuario: UserInfo = Depends(usuario_actual)) -> UserInfo:
    """Dependencia para endpoints exclusivos de la administradora."""
    if usuario.rol != "administradora":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la administradora puede realizar esta acción.",
        )
    return usuario


@router.post("/login", response_model=TokenResponse)
def post_login(payload: LoginRequest):
    """Devuelve un token JWT si las credenciales son correctas.
    No hay registro público: las cuentas las gestiona la administradora.
    """
    try:
        return login(payload.email, payload.password)
    except CredencialesInvalidas as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )


@router.get("/me", response_model=UserInfo)
def get_me(usuario: UserInfo = Depends(usuario_actual)):
    """Devuelve los datos del usuario autenticado."""
    return usuario
