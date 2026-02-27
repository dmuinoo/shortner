from datetime import datetime, timezone


def is_expired(db_url) -> bool:
    if not db_url.expires_at:
        return False
    exp = db_url.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp < datetime.now(timezone.utc)

def get_state(db_url) -> str:
    """Return a simple state string for UI/admin responses."""
    if not getattr(db_url, "is_active", True):
        return "disabled"  # <-- CAMBIO: estado deshabilitado explícito
    if is_expired(db_url):
        return "expired"  # <-- CAMBIO: estado caducado explícito
    return "active"  # <-- CAMBIO: estado activo explícito
