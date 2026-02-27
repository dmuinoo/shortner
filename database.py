# Short/database.py


from sqlalchemy import create_engine, text  # <-- CAMBIO: import text para PRAGMA/ALTER en SQLite
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import get_settings

engine = create_engine(get_settings().db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base = declarative_base()

def ensure_sqlite_schema(engine) -> None:
    """Best-effort lightweight migrations for SQLite.

    This project still doesn't use Alembic; SQLite won't auto-add columns on
    metadata.create_all(). We add missing columns with ALTER TABLE.
    """  # <-- CAMBIO: función para “auto-migrar” columnas nuevas en SQLite
    if not str(engine.url).startswith("sqlite"):
        return

    with engine.begin() as conn:
        # urls table may not exist yet
        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if "urls" not in tables:
            return

        cols = {r[1] for r in conn.execute(text("PRAGMA table_info(urls)"))}

        if "disabled_at" not in cols:
            conn.execute(text("ALTER TABLE urls ADD COLUMN disabled_at DATETIME"))  # <-- CAMBIO: añade columna

