# enterprise_ownership.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Integer, String, Index
from sqlalchemy.orm import Session

from database import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class LinkOwnership(Base):
    """
    Mapea un short link creado -> (company_id, api_key_id)
    Sin FK para no depender de tu modelo actual (que no conocemos aquí).
    """
    __tablename__ = "link_ownership"

    id = Column(Integer, primary_key=True, index=True)

    # Identificador del link (normalmente el "code" del acortador)
    short_code = Column(String(128), nullable=False, index=True, unique=True)

    company_id = Column(Integer, nullable=False, index=True)
    api_key_id = Column(Integer, nullable=False, index=True)

    created_at = Column(DateTime, nullable=False, default=_now_utc)

    __table_args__ = (
        Index("ix_link_ownership_company_api", "company_id", "api_key_id"),
    )


def _extract_short_code(obj: Any) -> Optional[str]:
    """
    Intenta sacar el "código corto" desde el objeto que devuelve tu CRUD.
    Ajustado para nombres típicos.
    """
    for attr in ("code", "short_code", "short", "slug", "key", "id"):
        if hasattr(obj, attr):
            v = getattr(obj, attr)
            if v is None:
                continue
            # Si id es int, lo convertimos a str (fallback)
            return str(v)
    return None


def record_ownership(
    db: Session,
    *,
    short_obj: Any,
    company_id: int,
    api_key_id: int,
) -> None:
    """
    Guarda/actualiza la relación short_code -> company/api_key.
    """
    code = _extract_short_code(short_obj)
    if not code:
        # No rompemos el acortador si no encontramos el código.
        return

    row = db.query(LinkOwnership).filter(LinkOwnership.short_code == code).first()
    if row:
        row.company_id = company_id
        row.api_key_id = api_key_id
        db.add(row)
        db.commit()
        return

    row = LinkOwnership(
        short_code=code,
        company_id=company_id,
        api_key_id=api_key_id,
        created_at=_now_utc(),
    )
    db.add(row)
    db.commit()
