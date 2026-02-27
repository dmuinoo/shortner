import time
import hmac
import hashlib
from collections import defaultdict, deque
from fastapi import HTTPException, Request

from config import get_settings

settings = get_settings()

# Sliding window in-memory: {ip: deque[timestamps]}
_requests_log = defaultdict(lambda: deque())


def rate_limit(request: Request) -> None:
    """
    Rate limit basado en variables de entorno:
      - RATE_LIMIT_MAX_REQUESTS
      - RATE_LIMIT_WINDOW_SECONDS
    """
    ip = request.client.host if request.client else "unknown"
    now = time.time()

    window = settings.rate_limit_window_seconds
    limit = settings.rate_limit_max_requests

    q = _requests_log[ip]

    # Drop old timestamps
    while q and (now - q[0]) > window:
        q.popleft()

    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="Too Many Requests")

    q.append(now)


def sign_message(message: str) -> str:
    """
    Firma HMAC (opcional). Usa HMAC_SECRET_KEY desde .env.
    """
    mac = hmac.new(
        settings.hmac_secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    )
    return mac.hexdigest()


def verify_signature(message: str, signature: str) -> bool:
    expected = sign_message(message)
    return hmac.compare_digest(expected, signature)
