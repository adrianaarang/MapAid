"""Esquemas del módulo de autenticación."""
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    email: str = Field(alias="email")
    password: str = Field(alias="contrasena")


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    access_token: str = Field(alias="token")
    rol: str
    email: str


class UserInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: int
    email: str
    rol: str
