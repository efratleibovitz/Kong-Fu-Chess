"""server/core/observability.py

Shared observability helpers for all services.

Structured logging: every service calls `get_logger(service_name)` and
logs with extra fields - output is one JSON object per line so it can be
ingested by any log aggregator (CloudWatch, Datadog, etc.) without extra
parsing config.

Health checks: `build_health_response(service, checks)` produces the
standard shape used by every /health endpoint:
  {"status": "ok"|"degraded", "service": "...", "checks": {...}}
A check is "ok" if its value is True, "degraded" otherwise.
"""

import json
import logging
import os
import time


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "msg": record.getMessage(),
        }
        # Any extra fields passed via `extra=` end up on the record.
        for key, val in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in doc and not key.startswith("_"):
                doc[key] = val
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return json.dumps(doc)


def get_logger(service: str) -> logging.Logger:
    logger = logging.getLogger(f"kfc.{service}")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    # Bind service name onto every record automatically.
    logger = logging.LoggerAdapter(logger, {"service": service})
    return logger


def build_health_response(service: str, checks: dict[str, bool]) -> dict:
    status = "ok" if all(checks.values()) else "degraded"
    return {
        "status": status,
        "service": service,
        "checks": {k: ("ok" if v else "fail") for k, v in checks.items()},
    }


async def check_postgres() -> bool:
    """Returns True if Postgres is reachable."""
    try:
        from server.core.database import _connect
        conn = _connect()
        conn.close()
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    """Returns True if Redis responds to a ping."""
    try:
        from server.core.redis_client import get_redis
        r = await get_redis()
        if r is None:
            return False
        await r.ping()
        return True
    except Exception:
        return False
