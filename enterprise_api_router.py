# enterprise_api_router.py
from __future__ import annotations

from typing import Any, Optional, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db  # si tu proyecto no tiene get_db, lo ajustamos en main.py con un wrapper

from enterprise_security import require_api_key
from enterprise_models import ApiKey

from enterprise_ownership import record_ownership

router = APIRouter(prefix="/v1", tags=["enterprise"])


def _call_existing_shortener(db: Session, payload: Dict[str, Any]) -> Any:
    """
    Intenta reutilizar TU lógica existente de acortar (crud/schemas).
    Ajustes típicos si algo no coincide: 1-2 líneas.
    """
    # 1) intenta construir un schema existente si lo tienes
    schema_obj: Any = payload
    try:
        import schemas  # type: ignore

        # Nombres típicos en proyectos de acortador
        candidates = [
            "ShortenRequest",
            "ShortUrlCreate",
            "ShortURLCreate",
            "UrlCreate",
            "URLCreate",
            "CreateShortUrl",
        ]
        for name in candidates:
            if hasattr(schemas, name):
                Schema = getattr(schemas, name)
                schema_obj = Schema(**payload)
                break
    except Exception:
        # Si no hay schemas o no coincide, seguimos con dict
        schema_obj = payload

    # 2) intenta llamar a tu CRUD existente
    try:
        import crud  # type: ignore

        # Firmas/nombres típicos
        fn_candidates = [
            "create_short_url",
            "create_shorturl",
            "shorten_url",
            "create_url",
        ]
        for fn_name in fn_candidates:
            if hasattr(crud, fn_name):
                fn = getattr(crud, fn_name)
                return fn(db, schema_obj)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not import/use existing crud.py shortener function: {e}",
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No compatible shortener function found in crud.py. "
               "Expected one of: create_short_url / shorten_url / create_url.",
    )


@router.post("/shorten")
def shorten_enterprise(
    request: Request,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, convert_underscores=False),
):
    """
    Endpoint autenticado por API key.
    NO sustituye tus rutas públicas.
    """
    api_key_row: ApiKey = require_api_key(request, db, x_api_key=x_api_key)

    # Llamamos a tu lógica actual para crear el short URL
    obj = _call_existing_shortener(db, body)
    record_ownership(db, short_obj=obj, company_id=api_key_row.company_id, api_key_id=api_key_row.id)
    # Si tu modelo tiene columnas company_id/api_key_id, las setea (cuando las añadamos).
    # Si no existen aún, no pasa nada.
    changed = False
    for attr, value in (("company_id", api_key_row.company_id), ("api_key_id", api_key_row.id)):
        if hasattr(obj, attr):
            try:
                setattr(obj, attr, value)
                changed = True
            except Exception:
                pass

    if changed:
        db.add(obj)
        db.commit()
        try:
            db.refresh(obj)
        except Exception:
            pass

    return obj
