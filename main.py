from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import URL

import crud
import keygen
import models
import schemas

from config import get_settings
from database import engine, get_db, ensure_sqlite_schema
from key_validators import validate_custom_key
from logger import logger
from security import rate_limit
from url_state import is_expired, get_state

from target_validation import validate_target_url, get_client_ip_from_request  # <-- CAMBIO: validación fuerte + IP real

settings = get_settings()

app = FastAPI(
    title="Short",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

models.Base.metadata.create_all(bind=engine)
ensure_sqlite_schema(engine)


def raise_bad_request(message: str):
    raise HTTPException(status_code=400, detail=message)


def raise_not_found(detail: str = "Not found"):
    raise HTTPException(status_code=404, detail=detail)


def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
    base_url = URL(settings.base_url)
    admin_endpoint = app.url_path_for("administration info", secret_key=db_url.secret_key)
    db_url.url = str(base_url.replace(path=f"/{db_url.key}"))
    db_url.admin_url = str(base_url.replace(path=str(admin_endpoint)))
    return db_url


@app.get("/", tags=["Short"])
def read_root():
    return "Welcome to the URL shortener API :)"


@app.post("/url", response_model=schemas.URLInfo, tags=["Short"])
def create_url(url: schemas.URLBase, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    # ✅ Validación fuerte del destino (sin hacer HEAD/GET)  # <-- CAMBIO
    validate_target_url(str(url.target_url), for_redirect=False)  # <-- CAMBIO

    # CASO 1: custom_key
    if url.custom_key:
        validate_custom_key(url.custom_key)

        if crud.get_db_url_by_key(db, url.custom_key):
            raise_bad_request("Custom key already exists")

        db_url = crud.create_db_url(db=db, url=url, key=url.custom_key)

    # CASO 2: key generada con retry
    else:
        for _ in range(20):
            key = keygen.create_unique_url_key(db)
            try:
                db_url = crud.create_db_url(db=db, url=url, key=key)
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

    # ✅ Validación antes de redirigir (DNS resolve + cache si lo tienes)  # <-- CAMBIO
    if getattr(settings, "validate_target_on_redirect", True):  # <-- CAMBIO
        try:
            validate_target_url(str(db_url.target_url), for_redirect=True)  # <-- CAMBIO
        except HTTPException:
            raise HTTPException(status_code=410, detail="Destination blocked")  # <-- CAMBIO

    crud.update_db_clicks(db, db_url)
    return RedirectResponse(db_url.target_url)


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
