# short/models.py

from sqlalchemy import DateTime, Boolean, Column, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime

from database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    secret_key = Column(String, unique=True, index=True)
    target_url = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    clicks = Column(Integer, default=0)

    # Campos de seguridad
    expires_at = Column(DateTime, nullable=True)
    disabled_at = Column(DateTime, nullable=True)  # <-- CAMBIO: marca de desactivación (audit mínimo)
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
