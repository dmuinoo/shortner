# short/models.py

from sqlalchemy import DateTime, Boolean, Column, Integer, String, ForeignKey  # <-- CAMBIO: ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship  # <-- CAMBIO: relationship
from datetime import datetime

from database import Base


class Tenant(Base):  # <-- CAMBIO: multitenant
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    api_keys = relationship("APIKey", back_populates="tenant")  # <-- CAMBIO
    urls = relationship("URL", back_populates="tenant")  # <-- CAMBIO


class APIKey(Base):  # <-- CAMBIO: API keys
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)  # <-- CAMBIO
    name = Column(String, nullable=False, default="default")  # <-- CAMBIO
    key_hash = Column(String, unique=True, index=True, nullable=False)  # <-- CAMBIO: hash, no plaintext
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)  # <-- CAMBIO: audit

    tenant = relationship("Tenant", back_populates="api_keys")  # <-- CAMBIO


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    secret_key = Column(String, unique=True, index=True)
    target_url = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    clicks = Column(Integer, default=0)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=True)  # <-- CAMBIO: ownership

    # Campos de seguridad
    expires_at = Column(DateTime, nullable=True)
    disabled_at = Column(DateTime, nullable=True)  # <-- CAMBIO: marca de desactivación (audit mínimo)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="urls")  # <-- CAMBIO

    @hybrid_property
    def state(self) -> str:
        now = datetime.utcnow()

        if self.disabled_at is not None:
            return "disabled"
        if self.expires_at is not None and self.expires_at <= now:
            return "expired"
        if self.is_active is False:
            return "disabled"
        return "active"
