# enterprise_crud.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from enterprise_models import ApiKey, AuditLog, Company
from enterprise_security import api_key_hash, generate_api_key


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# -------------------- Audit --------------------

def write_audit(
    db: Session,
    *,
    actor_subject: Optional[str],
    actor_source: Optional[str],
    action: str,
    target_type: str,
    target_id: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    row = AuditLog(
        actor_subject=actor_subject,
        actor_source=actor_source,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        before=before,
        after=after,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# -------------------- Companies --------------------

def create_company(
    db: Session,
    *,
    name: str,
    source: str = "local",
    external_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    actor_subject: Optional[str] = None,
    actor_source: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Company:
    existing = db.query(Company).filter(Company.name == name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company name already exists")

    c = Company(
        name=name,
        source=source,
        external_id=external_id,
        attributes=attributes,
        created_at=_now_utc(),
        updated_at=_now_utc(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    write_audit(
        db,
        actor_subject=actor_subject,
        actor_source=actor_source,
        action="create_company",
        target_type="company",
        target_id=str(c.id),
        before=None,
        after={"name": c.name, "source": c.source, "external_id": c.external_id, "attributes": c.attributes},
        ip=ip,
        user_agent=user_agent,
    )
    return c


def update_company(
    db: Session,
    *,
    company_id: int,
    name: Optional[str] = None,
    external_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    actor_subject: Optional[str] = None,
    actor_source: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Company:
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    before = {"name": c.name, "external_id": c.external_id, "attributes": c.attributes}

    if name is not None and name != c.name:
        # Check uniqueness
        existing = db.query(Company).filter(Company.name == name).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company name already exists")
        c.name = name

    if external_id is not None:
        c.external_id = external_id

    if attributes is not None:
        c.attributes = attributes

    c.updated_at = _now_utc()
    db.add(c)
    db.commit()
    db.refresh(c)

    after = {"name": c.name, "external_id": c.external_id, "attributes": c.attributes}

    write_audit(
        db,
        actor_subject=actor_subject,
        actor_source=actor_source,
        action="update_company",
        target_type="company",
        target_id=str(c.id),
        before=before,
        after=after,
        ip=ip,
        user_agent=user_agent,
    )
    return c


def list_companies(db: Session) -> list[Company]:
    return db.query(Company).order_by(Company.id.desc()).all()


def get_company(db: Session, company_id: int) -> Company:
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return c


# -------------------- API Keys --------------------

def create_api_key(
    db: Session,
    *,
    company_id: int,
    name: str,
    scopes: Optional[list[str]] = None,
    expires_at: Optional[datetime] = None,
    actor_subject: Optional[str] = None,
    actor_source: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[ApiKey, str]:
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    raw_key, prefix = generate_api_key()
    hashed = api_key_hash(raw_key)

    row = ApiKey(
        company_id=company_id,
        name=name,
        prefix=prefix,
        key_hash=hashed,
        scopes=scopes,
        expires_at=_as_utc(expires_at),
        revoked_at=None,
        created_by_subject=actor_subject,
        created_at=_now_utc(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    write_audit(
        db,
        actor_subject=actor_subject,
        actor_source=actor_source,
        action="create_key",
        target_type="api_key",
        target_id=str(row.id),
        before=None,
        after={
            "company_id": row.company_id,
            "name": row.name,
            "prefix": row.prefix,
            "scopes": row.scopes,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        },
        ip=ip,
        user_agent=user_agent,
    )

    # raw_key se devuelve SOLO UNA VEZ
    return row, raw_key


def list_api_keys(db: Session, company_id: int) -> list[ApiKey]:
    return (
        db.query(ApiKey)
        .filter(ApiKey.company_id == company_id)
        .order_by(ApiKey.id.desc())
        .all()
    )


def get_api_key(db: Session, key_id: int) -> ApiKey:
    row = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return row


def update_api_key(
    db: Session,
    *,
    key_id: int,
    name: Optional[str] = None,
    scopes: Optional[list[str]] = None,
    expires_at: Optional[datetime] = None,
    actor_subject: Optional[str] = None,
    actor_source: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ApiKey:
    row = get_api_key(db, key_id)

    before = {
        "name": row.name,
        "scopes": row.scopes,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
    }

    if name is not None:
        row.name = name
    if scopes is not None:
        row.scopes = scopes
    if expires_at is not None or expires_at is None:
        # Permite setear a None explícito desde el schema
        row.expires_at = _as_utc(expires_at)

    db.add(row)
    db.commit()
    db.refresh(row)

    after = {
        "name": row.name,
        "scopes": row.scopes,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
    }

    write_audit(
        db,
        actor_subject=actor_subject,
        actor_source=actor_source,
        action="update_key",
        target_type="api_key",
        target_id=str(row.id),
        before=before,
        after=after,
        ip=ip,
        user_agent=user_agent,
    )
    return row


def revoke_api_key(
    db: Session,
    *,
    key_id: int,
    actor_subject: Optional[str] = None,
    actor_source: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ApiKey:
    row = get_api_key(db, key_id)

    if row.revoked_at is None:
        before = {"revoked_at": None}
        row.revoked_at = _now_utc()
        db.add(row)
        db.commit()
        db.refresh(row)

        write_audit(
            db,
            actor_subject=actor_subject,
            actor_source=actor_source,
            action="revoke_key",
            target_type="api_key",
            target_id=str(row.id),
            before=before,
            after={"revoked_at": row.revoked_at.isoformat()},
            ip=ip,
            user_agent=user_agent,
        )

    return row


def rotate_api_key(
    db: Session,
    *,
    key_id: int,
    actor_subject: Optional[str] = None,
    actor_source: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[ApiKey, str]:
    """
    Crea una nueva key para la misma empresa con mismo name/scopes/expires,
    y revoca la anterior.
    """
    old = get_api_key(db, key_id)

    # creamos nueva
    new_row, raw = create_api_key(
        db,
        company_id=old.company_id,
        name=f"{old.name} (rotated)",
        scopes=old.scopes,
        expires_at=old.expires_at,
        actor_subject=actor_subject,
        actor_source=actor_source,
        ip=ip,
        user_agent=user_agent,
    )

    # revocamos la vieja
    revoke_api_key(
        db,
        key_id=old.id,
        actor_subject=actor_subject,
        actor_source=actor_source,
        ip=ip,
        user_agent=user_agent,
    )

    # audit extra de rotación (opcional, pero útil)
    write_audit(
        db,
        actor_subject=actor_subject,
        actor_source=actor_source,
        action="rotate_key",
        target_type="api_key",
        target_id=str(old.id),
        before={"old_key_id": old.id},
        after={"new_key_id": new_row.id},
        ip=ip,
        user_agent=user_agent,
    )

    return new_row, raw


# -------------------- Audit queries --------------------

def list_audit(
    db: Session,
    *,
    company_id: Optional[int] = None,
    limit: int = 200,
) -> list[AuditLog]:
    q = db.query(AuditLog).order_by(AuditLog.id.desc())
    # Si quieres filtrar por company: audit.target_id es string y target_type varía.
    # Para filtrado fino habría que guardar company_id explícito en audit_log; lo haremos en una mejora.
    # De momento devolvemos todo y filtras en UI si hace falta.
    return q.limit(limit).all()
