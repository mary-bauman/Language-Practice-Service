import json
import logging
import threading
import time
from collections import Counter
from uuid import uuid4

from fastapi import Request
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for field in ("method", "path", "status_code", "duration_ms", "request_id"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"))


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests = Counter()
        self._durations = Counter()

    def observe(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        key = (method, path, status_code)
        with self._lock:
            self._requests[key] += 1
            self._durations[(method, path)] += duration_ms

    def prometheus(self) -> str:
        with self._lock:
            request_lines = [
                f'language_practice_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                for (method, path, status), count in sorted(self._requests.items())
            ]
            duration_lines = [
                f'language_practice_http_request_duration_ms_sum{{method="{method}",path="{path}"}} {duration:.3f}'
                for (method, path), duration in sorted(self._durations.items())
            ]
        return "\n".join(
            [
                "# TYPE language_practice_http_requests_total counter",
                *request_lines,
                "# TYPE language_practice_http_request_duration_ms_sum counter",
                *duration_lines,
                "",
            ]
        )


metrics = RequestMetrics()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        metrics.observe(request.method, request.url.path, response.status_code, duration_ms)
        logging.getLogger("language_practice.request").info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 3),
                "request_id": request_id,
            },
        )
        return response


async def metrics_response() -> PlainTextResponse:
    return PlainTextResponse(metrics.prometheus(), media_type="text/plain; version=0.0.4")
