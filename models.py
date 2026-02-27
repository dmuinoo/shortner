# short/models.py

from sqlalchemy import DateTime, Boolean, Column, Integer, String
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
    created_at = Column(DateTime, default=datetime.utcnow)
