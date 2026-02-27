from fastapi import HTTPException
from config import get_settings

settings = get_settings()

RESERVED = {
    "docs",
    "redoc",
    "openapi.json",
    "openapi",
    "admin",
    "peek",
    "url",
    "",
}


def validate_custom_key(key: str) -> None:
    k = key.strip()

    if k in RESERVED:
        raise HTTPException(status_code=400, detail="custom_key is reserved")

    if not (settings.custom_key_min_len <= len(k) <= settings.custom_key_max_len):
        raise HTTPException(status_code=400, detail="custom_key length invalid")

    allowed = set(settings.custom_key_alphabet)
    if any(ch not in allowed for ch in k):
        raise HTTPException(
            status_code=400, detail="custom_key contains invalid characters"
        )
