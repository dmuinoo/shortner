# enterprise_init.py
from __future__ import annotations

from fastapi import FastAPI

# Importa Base y engine de tu proyecto
from database import Base, engine  # tu database.py ya suele exponer esto

# IMPORTANTÍSIMO: importar los modelos para que SQLAlchemy los registre en Base.metadata
import enterprise_models  # noqa: F401
import enterprise_ownership  # noqa: F401
# Routers nuevos
from enterprise_admin_router import router as admin_router
from enterprise_api_router import router as enterprise_router


def init_enterprise(app: FastAPI) -> None:
    """
    Llamar una vez desde main.py después de crear `app = FastAPI(...)`.
    - Registra routers:
        /admin (panel/gestión)
        /v1 (API autenticada por X-API-Key)
    - Crea tablas nuevas si no existen
    """
    # Crea tablas (incluye las nuevas porque enterprise_models está importado)
    Base.metadata.create_all(bind=engine)

    # Registra routers
    app.include_router(admin_router)
    app.include_router(enterprise_router)
