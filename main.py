from fastapi import FastAPI, Depends, HTTPException, Request, Header, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import URL

import crud
import keygen
import models
import schemas
import math

from config import settings
from database import engine, get_db, ensure_sqlite_schema
from key_validators import validate_custom_key
from logger import logger
from security import rate_limit, get_current_tenant, require_root_admin  # <-- CAMBIO: auth multitenant
from url_state import is_expired, get_state
from datetime import datetime, timezone, timedelta
from target_validation import validate_target_url, get_client_ip_from_request  # <-- CAMBIO: validación fuerte + IP real

from enterprise_init import init_enterprise


app = FastAPI(
    title="Short",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 🔐 Inicializa modo enterprise
init_enterprise(app)

models.Base.metadata.create_all(bind=engine)
ensure_sqlite_schema(engine)


def raise_bad_request(message: str):
    raise HTTPException(status_code=400, detail=message)


def raise_not_found(detail: str = "Not found"):
    raise HTTPException(status_code=404, detail=detail)


def _remaining_days(expires_at):
    if not expires_at:
         return None

    # Si viene maive de la BDD, asumimos que es UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = expires_at.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    delta = expires_at - now
    
    # Si ya expiro -> devolver 0
    if delta.total_seconds() <= 0:
        return None
    
    # Si queda menos de 1 dia pero sigue valida -> devolver 1
    return max(1, math.ceil(delta.total_seconds() / 86400 ))

def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
    base_url = URL(settings.base_url)
    admin_endpoint = app.url_path_for("administration info", secret_key=db_url.secret_key)
    
    url = str(base_url.replace(path=f"/{db_url.key}"))

    return schemas.URLInfo(
        key=db_url.key,
        secret_key=db_url.secret_key,
        target_url=db_url.target_url,
        is_active=db_url.is_active,
        clicks=db_url.clicks,
        url=url,
        expires_in_days=_remaining_days(db_url.expires_at),
        # Añade aqui los campos reales que tenga tu URLInfo
        admin_url=str(base_url.replace(path=str(admin_endpoint))),
        state=get_state(db_url),
    )


@app.get("/", tags=["Short"])
def read_root():
    return "Welcome to the URL shortener API :)"


# -------------------------
# Public create (legacy)
# -------------------------

@app.post("/url", response_model=schemas.URLInfo, tags=["Short"])
def create_url(url: schemas.URLBase, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    validate_target_url(str(url.target_url), for_redirect=False)  # <-- CAMBIO

    if url.custom_key:
        validate_custom_key(url.custom_key)

        if crud.get_db_url_by_key_any(db, url.custom_key):  # <-- CAMBIO: mira cualquier, no solo activas
            raise_bad_request("Custom key already exists")

        db_url = crud.create_db_url(db=db, url=url, key=url.custom_key, tenant_id=None)  # <-- CAMBIO
    else:
        for _ in range(20):
            key = keygen.create_unique_url_key(db)
            try:
                db_url = crud.create_db_url(db=db, url=url, key=key, tenant_id=None)  # <-- CAMBIO
                break
            except IntegrityError:
                db.rollback()
                continue
        else:
            raise_bad_request("Could not generate unique key")

    return get_admin_info(db_url)


@app.get("/peek/{key}", tags=["Info"])
def peek_url(key: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    db_url = crud.get_db_url_by_key(db, key)
    if not db_url:
        raise_not_found("URL key not found")

    if is_expired(db_url):
        raise HTTPException(status_code=410, detail="Link expired")

    return {"target_url": db_url.target_url}


@app.get("/{url_key}", tags=["Short"])
def forward_to_target_url(url_key: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    ip = get_client_ip_from_request(request)  # <-- CAMBIO
    ua = request.headers.get("user-agent", "")
    logger.info(f'{{"event":"redirect","ip":"{ip}","ua":"{ua}","key":"{url_key}"}}')

    db_url = crud.get_db_url_by_key(db, url_key)
    if not db_url:
        raise_not_found("Not found")

    if not db_url.is_active:
        raise HTTPException(status_code=410, detail="Link disabled")

    if is_expired(db_url):
        raise HTTPException(status_code=410, detail="Link expired")

    if getattr(settings, "validate_target_on_redirect", True):  # <-- CAMBIO
        try:
            validate_target_url(str(db_url.target_url), for_redirect=True)  # <-- CAMBIO
        except HTTPException:
            raise HTTPException(status_code=410, detail="Destination blocked")  # <-- CAMBIO

    crud.update_db_clicks(db, db_url)
    return RedirectResponse(db_url.target_url)


# -------------------------
# Admin by capability (legacy)
# -------------------------

@app.get(
    "/admin/{secret_key}",
    name="administration info",
    response_model=schemas.URLInfo,
    tags=["Admin"],
)
def admin_info(secret_key: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    db_url = crud.get_db_url_by_secret_key(db, secret_key, include_inactive=True)
    if not db_url:
        raise_not_found("Secret key not found")

    return get_admin_info(db_url)


@app.get("/admin/{secret_key}/validate", tags=["Admin"])  # <-- CAMBIO
def admin_validate(secret_key: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    db_url = crud.get_db_url_by_secret_key(db, secret_key, include_inactive=True)
    if not db_url:
        raise_not_found("Secret key not found")

    try:
        validate_target_url(str(db_url.target_url), for_redirect=True)
        return {"ok": True, "target_url": db_url.target_url, "message": "Destination passes current policy"}
    except HTTPException as e:
        return {"ok": False, "target_url": db_url.target_url, "error": e.detail}


@app.delete("/admin/{secret_key}", tags=["Admin"])
def delete_url(secret_key: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    db_url = crud.deactivate_db_url_by_secret_key(db, secret_key=secret_key)
    if not db_url:
        raise_not_found("Secret key not found")

    return {"detail": f"Succesfully deleted shortened URL for '{db_url.target_url}'"}


@app.post("/admin/{secret_key}/enable", tags=["Admin"], response_model=schemas.URLInfo)
def enable_url(secret_key: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    db_url = crud.activate_db_url_by_secret_key(db, secret_key)
    if not db_url:
        raise_not_found("Secret key not found")
    return get_admin_info(db_url)


@app.post("/admin/{secret_key}/disable", tags=["Admin"], response_model=schemas.URLInfo)
def disable_url(secret_key: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    db_url = crud.deactivate_db_url_by_secret_key(db, secret_key)
    if not db_url:
        raise_not_found("Secret key not found")
    return get_admin_info(db_url)


class ExpiryUpdate(BaseModel):
    expires_in_days: int | None = None

@app.patch("/admin/{secret_key}/expiry", tags=["Admin"], response_model=schemas.URLInfo)
def update_expiry(secret_key: str, payload: ExpiryUpdate, request: Request, db: Session = Depends(get_db)):
  
    rate_limit(request)

    if payload.expires_in_days is not None and payload.expires_in_days < 1:
        raise_bad_request("expires_in_days must be >= 1 or null")

    db_url = crud.update_expiry_by_secret_key(db, secret_key, payload.expires_in_days)
    if not db_url:
        raise_not_found("Secret key not found")
    return get_admin_info(db_url)


# -------------------------
# Authenticated multitenant API (/api)
# -------------------------


def require_root_admin_dep(
    x_root_key: str = Header(..., alias="X-Root-Key"),
):
    if x_root_key != settings.root_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Root-Key",
        )


@app.post("/api/bootstrap", response_model=schemas.TenantBootstrapOut, tags=["Auth"])  # <-- CAMBIO
def bootstrap_tenant(
    payload: schemas.TenantCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_root_admin_dep),
    ):    
    """
    Crea un tenant y una API key inicial.
    Protegido con X-Root-Key (ROOT_ADMIN_KEY).
    """
    rate_limit(request)

    existing = crud.get_tenant_by_name(db, payload.name)
    if existing:
        raise_bad_request("Tenant already exists")

    tenant = crud.create_tenant(db, payload.name)
    raw_key, ak = crud.create_api_key(db, tenant_id=tenant.id, name="bootstrap")

    return schemas.TenantBootstrapOut(
        tenant=tenant,
        api_key=raw_key,
        key_info=ak,
    )


@app.post("/api/apikeys", response_model=schemas.APIKeyCreated, tags=["Auth"])  # <-- CAMBIO
def create_api_key(payload: schemas.APIKeyCreate, request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    raw, ak = crud.create_api_key(db, tenant_id=tenant.id, name=payload.name)
    return schemas.APIKeyCreated(api_key=raw, key_info=ak)


@app.get("/api/apikeys", response_model=list[schemas.APIKeyOut], tags=["Auth"])  # <-- CAMBIO
def list_api_keys(request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    return crud.list_api_keys_for_tenant(db, tenant.id)


@app.patch("/api/apikeys/{api_key_id}/disable", response_model=schemas.APIKeyOut, tags=["Auth"])  # <-- CAMBIO
def disable_api_key(api_key_id: int, request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    ak = crud.disable_api_key(db, tenant.id, api_key_id)
    if not ak:
        raise_not_found("API key not found")
    return ak


@app.post("/api/urls", response_model=schemas.URLInfoOwned, tags=["URLs Auth"])  # <-- CAMBIO
def create_url_for_tenant(url: schemas.URLBase, request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    validate_target_url(str(url.target_url), for_redirect=False)

    if url.custom_key:
        validate_custom_key(url.custom_key)
        if crud.get_db_url_by_key_any(db, url.custom_key):
            raise_bad_request("Custom key already exists")
        db_url = crud.create_db_url(db=db, url=url, key=url.custom_key, tenant_id=tenant.id)
    else:
        for _ in range(20):
            key = keygen.create_unique_url_key(db)
            try:
                db_url = crud.create_db_url(db=db, url=url, key=key, tenant_id=tenant.id)
                break
            except IntegrityError:
                db.rollback()
                continue
        else:
            raise_bad_request("Could not generate unique key")

    info = get_admin_info(db_url)
    return schemas.URLInfoOwned.model_validate(info, from_attributes=True)  # <-- CAMBIO


@app.get("/api/urls", response_model=schemas.URLListOut, tags=["URLs Auth"])  # <-- CAMBIO

def list_urls(request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db), limit: int = 100, offset: int = 0):
    rate_limit(request)
    items = crud.list_urls_for_tenant(db, tenant.id, limit=limit, offset=offset)
    out_items = []
    for u in items:
        info = get_admin_info(u)
        out_items.append(schemas.URLInfoOwned.model_validate(info, from_attributes=True))  # <-- CAMBIO
    return schemas.URLListOut(items=out_items)


@app.get("/api/urls/{url_key}", response_model=schemas.URLInfoOwned, tags=["URLs Auth"])  # <-- CAMBIO
def get_url(url_key: str, request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    u = crud.get_db_url_by_key_for_tenant(db, url_key, tenant.id)
    if not u:
        raise_not_found("URL not found")
    info = get_admin_info(u)
    return schemas.URLInfoOwned.model_validate(info, from_attributes=True)  # <-- CAMBIO


@app.patch("/api/urls/{url_key}/disable", response_model=schemas.URLInfoOwned, tags=["URLs Auth"])  # <-- CAMBIO
def disable_url_for_tenant(url_key: str, request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    u = crud.deactivate_db_url_for_tenant(db, url_key, tenant.id)
    if not u:
        raise_not_found("URL not found")
    info = get_admin_info(u)
    return schemas.URLInfoOwned.model_validate(info, from_attributes=True)  # <-- CAMBIO


@app.patch("/api/urls/{url_key}/enable", response_model=schemas.URLInfoOwned, tags=["URLs Auth"])  # <-- CAMBIO
def enable_url_for_tenant(url_key: str, request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    u = crud.activate_db_url_for_tenant(db, url_key, tenant.id)
    if not u:
        raise_not_found("URL not found")
    info = get_admin_info(u)
    return schemas.URLInfoOwned.model_validate(info, from_attributes=True)  # <-- CAMBIO

# TEST ----
import os
print("LOADED MAIN:", os.path.abspath(__file__))

@app.patch("/api/urls/{url_key}/expiry", response_model=schemas.URLInfoOwned, tags=["URLs Auth"])  # <-- CAMBIO
def update_expiry_for_tenant(url_key: str, payload: ExpiryUpdate, request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    if payload.expires_in_days is not None and payload.expires_in_days < 1:
        raise_bad_request("expires_in_days must be >= 1 or null")
    u = crud.update_expiry_for_tenant(db, url_key, tenant.id, payload.expires_in_days)
    if not u:
        raise_not_found("URL not found")
    info = get_admin_info(u)
    return schemas.URLInfoOwned.model_validate(info, from_attributes=True)  # <-- CAMBIO


@app.delete("/api/urls/{url_key}", tags=["URLs Auth"])  # <-- CAMBIO: soft delete
def delete_url_for_tenant(url_key: str, request: Request, tenant: models.Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    rate_limit(request)
    u = crud.deactivate_db_url_for_tenant(db, url_key, tenant.id)
    if not u:
        raise_not_found("URL not found")
    return {"detail": "URL disabled"}
