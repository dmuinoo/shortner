# enterprise_schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------- Companies ----------

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source: str = Field(default="local", max_length=32)  # local|ldap|ad
    external_id: Optional[str] = Field(default=None, max_length=512)
    attributes: Optional[Dict[str, Any]] = None


class CompanyOut(BaseModel):
    id: int
    name: str
    source: str
    external_id: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    external_id: Optional[str] = Field(default=None, max_length=512)
    attributes: Optional[Dict[str, Any]] = None


# ---------- API Keys ----------

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class ApiKeyOut(BaseModel):
    id: int
    company_id: int
    name: str
    prefix: str
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_by_subject: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None

    class Config:
        from_attributes = True


class ApiKeyCreatedOnce(BaseModel):
    """
    Respuesta al crear/rotar: incluye la key en claro SOLO en esa respuesta.
    """
    api_key: ApiKeyOut
    raw_key: str


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


# ---------- Admin Auth (panel) ----------
# (por ahora simple; lo refinamos cuando integremos LDAP/AD)

class AdminLoginRequest(BaseModel):
    username: str
    password: str
    # source: local|ldap|ad (si luego quieres selector)
    source: Optional[str] = "local"


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminWhoAmI(BaseModel):
    subject: str
    source: str
    display_name: Optional[str] = None
    mail: Optional[str] = None
    groups: Optional[List[str]] = None


# ---------- Audit ----------

class AuditOut(BaseModel):
    id: int
    timestamp: datetime
    actor_subject: Optional[str] = None
    actor_source: Optional[str] = None
    action: str
    target_type: str
    target_id: str
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        from_attributes = True
