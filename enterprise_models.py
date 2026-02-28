# enterprise_models.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship

from database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)

    # local | ldap | ad
    source = Column(String(32), nullable=False, default="local")

    # Identificador externo estable (DN/GUID/lo que uses en AD/LDAP)
    external_id = Column(String(512), nullable=True, index=True)

    # Atributos extra (company, department, etc.)
    attributes = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    api_keys = relationship("ApiKey", back_populates="company", cascade="all,delete")


class ApiKey(Base):
    __tablename__ = "enterprise_api_keys"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Para lookup rápido (ej: primeros 8 chars)
    prefix = Column(String(32), nullable=False, index=True)

    # Hash/HMAC de la key completa (nunca guardes la key en claro)
    key_hash = Column(String(256), nullable=False)

    # JSON list: ["shorten:create", ...]
    scopes = Column(JSON, nullable=True)

    expires_at = Column(DateTime, nullable=True, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)

    created_by_subject = Column(String(256), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    last_used_at = Column(DateTime, nullable=True)
    last_used_ip = Column(String(64), nullable=True)

    company = relationship("Company", back_populates="api_keys")

    __table_args__ = (
        # Asegura que no haya dos prefixes iguales dentro de la misma empresa (evita ambigüedad)
        Index("ix_api_keys_company_prefix", "company_id", "prefix"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    actor_subject = Column(String(256), nullable=True, index=True)
    actor_source = Column(String(32), nullable=True)  # local|ldap|ad

    action = Column(String(64), nullable=False, index=True)  # e.g. create_key, revoke_key, update_expiry
    target_type = Column(String(64), nullable=False, index=True)  # e.g. api_key, company
    target_id = Column(String(64), nullable=False, index=True)

    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)

    ip = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
