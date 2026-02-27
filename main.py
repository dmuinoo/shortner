import httpx
from urllib.parse import urlparse


from urllib.parse import urlsplit
import ipaddress


from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette.datastructures import URL

from config import get_settings
from database import engine, get_db
from logger import logger
from security import rate_limit
from url_state import is_expired
from key_validators import validate_custom_key

import models, schemas, crud, keygen

settings = get_settings()

app = FastAPI(
    title="Short",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",  # poner /redocs si se queire esa url
    openapi_url="/openapi.json",
)

models.Base.metadata.create_all(bind=engine)


def is_valid_target_url(target_url) -> bool:
    s = str(target_url).strip()  # <- clavrint("DEBUG inside validator s=", repr(s))
    parts = urlsplit(s)
    print("DEBUG inside validator scheme=", parts.scheme, "host=", parts.hostname)

    if not s or " " in s:
        return False

    parts = urlsplit(s)

    if parts.scheme not in {"http", "https"}:
        return False
    if not parts.hostname:
        return False

    return True


# ...


def url_exists(target: str) -> bool:
    try:
        response = httpx.head(target, follow_redirects=True, timeout=5)
        if response.status_code == 405:
            response = httpx.get(target, follow_redirects=True, timeout=5)
        return response.status_code < 400
    except Exception:
        return False


def raise_bad_request(message: str):
    raise HTTPException(status_code=400, detail=message)


def raise_not_found(detail: str = "Not found"):
    raise HTTPException(status_code=404, detail=detail)


def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
    base_url = URL(settings.base_url)

    admin_endpoint = app.url_path_for(
        "administration info", secret_key=db_url.secret_key
    )

    db_url.url = str(base_url.replace(path=f"/{db_url.key}"))
    db_url.admin_url = str(base_url.replace(path=str(admin_endpoint)))
    return db_url


@app.get("/", tags=["Short"])
def read_root():
    return "Welcome to the URL shortener API :)"


@app.post("/url", response_model=schemas.URLInfo, tags=["Short"])
def create_url(url: schemas.URLBase, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    # Validar URL destino
    if not is_valid_target_url(url.target_url):
        raise_bad_request("Your provided URL is not valid")

    # ====================================================
    # CASO 1: custom_key puesta
    # ====================================================
    if url.custom_key:
        validate_custom_key(url.custom_key)

        if crud.get_db_url_by_key(db, url.custom_key):
            raise_bad_request("Custom key already exists")

        key = url.custom_key
        db_url = crud.create_db_url(db=db, url=url, key=key)

    # =====================================================
    # CASO 2: Generar key
    # =====================================================
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


# ...


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
def forward_to_target_url(
    url_key: str, request: Request, db: Session = Depends(get_db)
):
    rate_limit(request)

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    logger.info(f'{{"event":"redirect","ip":"{ip}","ua":"{ua}","key":"{url_key}"}}')

    db_url = crud.get_db_url_by_key(db, url_key)
    if not db_url:
        raise_not_found("Not found")

    if is_expired(db_url):
        raise HTTPException(status_code=410, detail="Link expired")

    if not url_exists(db_url.target_url):
        raise HTTPException(status_code=502, detail="Destination unavailable")

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

    db_url = crud.get_db_url_by_secret_key(db, secret_key)
    if not db_url:
        raise_not_found("Secret key not found")

    if is_expired(db_url):
        raise HTTPException(status_code=410, detail="Link expired")

    return get_admin_info(db_url)


@app.delete("/admin/{secret_key}", tags=["Admin"])
def delete_url(secret_key: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)

    db_url = crud.deactivate_db_url_by_secret_key(db, secret_key=secret_key)
    if not db_url:
        raise_not_found("Secret key not found")

    message = f"Succesfully deleted shortened URL for '{db_url.target_url}'"
    return {"detail": message}
