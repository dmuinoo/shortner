import logging

logger = logging.getLogger("shortener")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    '{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}'
)
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
