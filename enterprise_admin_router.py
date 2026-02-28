# enterprise_admin_router.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db  # asumo que existe en tu database.py (muy típico). Si no, lo ajustamos en 30s.

from enterprise_admin_auth import require_admin, admin_login_local, AdminPrincipal
from enterprise_schemas import (
    AdminLoginRequest,
    AdminTokenResponse,
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    ApiKeyCreate,
    ApiKeyOut,
    ApiKeyCreatedOnce,
    ApiKeyUpdate,
    AuditOut,
)
import enterprise_crud as ecrud

router = APIRouter(prefix="/admin", tags=["admin"])


# -------- Auth --------

@router.post("/login", response_model=AdminTokenResponse)
def admin_login(payload: AdminLoginRequest):
    # Por ahora solo local. Luego metemos LDAP/AD sin romper este endpoint.
    token = admin_login_local(payload.username, payload.password)
    return AdminTokenResponse(access_token=token)


# -------- Companies --------

@router.post("/companies", response_model=CompanyOut)
def create_company(
    request: Request,
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    return ecrud.create_company(
        db,
        name=payload.name,
        source=payload.source,
        external_id=payload.external_id,
        attributes=payload.attributes,
        actor_subject=admin.subject,
        actor_source=admin.source,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    return ecrud.list_companies(db)


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    request: Request,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    return ecrud.update_company(
        db,
        company_id=company_id,
        name=payload.name,
        external_id=payload.external_id,
        attributes=payload.attributes,
        actor_subject=admin.subject,
        actor_source=admin.source,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# -------- API Keys --------

@router.post("/companies/{company_id}/keys", response_model=ApiKeyCreatedOnce)
def create_key(
    company_id: int,
    request: Request,
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    row, raw = ecrud.create_api_key(
        db,
        company_id=company_id,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        actor_subject=admin.subject,
        actor_source=admin.source,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ApiKeyCreatedOnce(api_key=row, raw_key=raw)


@router.get("/companies/{company_id}/keys", response_model=list[ApiKeyOut])
def list_keys(
    company_id: int,
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    return ecrud.list_api_keys(db, company_id)


@router.patch("/keys/{key_id}", response_model=ApiKeyOut)
def update_key(
    key_id: int,
    request: Request,
    payload: ApiKeyUpdate,
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    return ecrud.update_api_key(
        db,
        key_id=key_id,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        actor_subject=admin.subject,
        actor_source=admin.source,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/keys/{key_id}/revoke", response_model=ApiKeyOut)
def revoke_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    return ecrud.revoke_api_key(
        db,
        key_id=key_id,
        actor_subject=admin.subject,
        actor_source=admin.source,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/keys/{key_id}/rotate", response_model=ApiKeyCreatedOnce)
def rotate_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    row, raw = ecrud.rotate_api_key(
        db,
        key_id=key_id,
        actor_subject=admin.subject,
        actor_source=admin.source,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ApiKeyCreatedOnce(api_key=row, raw_key=raw)


# -------- Audit --------

@router.get("/audit", response_model=list[AuditOut])
def list_audit(
    company_id: Optional[int] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: AdminPrincipal = Depends(require_admin),
):
    return ecrud.list_audit(db, company_id=company_id, limit=limit)
