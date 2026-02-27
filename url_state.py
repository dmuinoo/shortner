from datetime import datetime, timezone


def is_expired(db_url) -> bool:
    if not db_url.expires_at:
        return False
    exp = db_url.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp < datetime.now(timezone.utc)
