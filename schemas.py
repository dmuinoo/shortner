# short/schemas.py

from pydantic import AnyUrl, Field, BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class URLBase(BaseModel):
    target_url: AnyUrl
    custom_key: Optional[str] = Field(
        default=None,
        description="Alias opcional. Si lo dejas vacio, se genera automaticamente.",
        examples=[None],
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=3650,
        description="Caducidad opcional en días. Si no se indica, se usa el valor por defecto de settings.",
    )


class URL(URLBase):
    is_active: bool
    clicks: int

    expires_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None  # <-- CAMBIO: exponer marca de desactivación en responses
    created_at: Optional[datetime] = None

    state: str

    model_config = ConfigDict(from_attributes=True)


class URLInfo(URL):
    url: str
    admin_url: str

    state: str = Field(description="active | expired | disabled")

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Multitenant + API Keys
# -------------------------

class TenantCreate(BaseModel):  # <-- CAMBIO
    name: str = Field(min_length=2, max_length=64)


class TenantOut(BaseModel):  # <-- CAMBIO
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreate(BaseModel):  # <-- CAMBIO
    name: str = Field(default="default", min_length=1, max_length=64)


class APIKeyOut(BaseModel):  # <-- CAMBIO
    id: int
    tenant_id: int
    name: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreated(BaseModel):  # <-- CAMBIO: la API key en claro se devuelve SOLO al crear
    api_key: str
    key_info: APIKeyOut


class TenantBootstrapOut(BaseModel):  # <-- CAMBIO: crear tenant + key inicial (bootstrap)
    tenant: TenantOut
    api_key: str
    key_info: APIKeyOut


class URLInfoOwned(URLInfo):  # <-- CAMBIO: response para /api/urls (incluye owner)
    tenant_id: Optional[int] = None


class URLListOut(BaseModel):  # <-- CAMBIO
    items: List[URLInfoOwned]
