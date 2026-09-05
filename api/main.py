"""FastAPI entrypoint for the AI Risk Manager fraud detection API (Day 3 MVP).

Run with:  uvicorn api.main:app --reload   (from the project root)
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import (
    alerts,
    analytics,
    chargebacks,
    health,
    models,
    monitoring,
    predict,
    return_model_info,
    return_predict,
    simulate,
    transactions,
)
from api.services.anomaly_service import anomaly_service
from api.services.db import init_db
from api.services.drift_service import drift_service
from api.services.model_info_service import model_info_service
from api.services.model_service import model_service
from api.services.return_model_info_service import return_model_info_service
from api.services.return_model_service import return_model_service
from api.services.simulation_service import simulation_service

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("fraud_api")


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Derived feature tables the services below read at startup. Neither is
# committed (both are gitignored: regenerable, and large), so on a fresh
# clone they're simply absent until the setup steps have been run.
REQUIRED_DATA_FILES = (
    (
        PROJECT_ROOT / "data" / "processed" / "features.csv",
        "python scripts/setup_datasets.py   (needs your own free Kaggle account for creditcard.csv)",
    ),
    (
        PROJECT_ROOT / "data" / "processed" / "return_features.csv",
        "python scripts/setup_datasets.py   (fully automatic -- UCI, no account needed)",
    ),
)


def _preflight_data_check() -> None:
    """Fail with the actual fix, not a bare FileNotFoundError.

    Without this, a fresh clone's first `uvicorn api.main:app` dies deep
    inside whichever service happened to read its CSV first -- the
    traceback names a path under data/processed/ and nothing else, which
    tells you a file is missing but not that it's *derived*, nor which
    command derives it. That sent people looking for a file to download
    into data/processed/, which is not how it gets there.

    Purely a message-quality guard: it checks for existence and nothing
    more, so a run where the files are present reaches the services in
    exactly the state it always did.
    """
    missing = [(path, how) for path, how in REQUIRED_DATA_FILES if not path.exists()]
    if not missing:
        return

    lines = [
        "Cannot start: required derived data file(s) are missing.",
        "",
        "These are built from the raw datasets, not shipped in the repo",
        "(both are gitignored -- regenerable, and too large/licensed to commit):",
        "",
    ]
    for path, how in missing:
        lines.append(f"  missing: {path.relative_to(PROJECT_ROOT)}")
        lines.append(f"     fix: {how}")
        lines.append("")
    lines.append("setup_datasets.py runs these build steps itself; they're the manual equivalent:")
    lines.append("  python src/features/build_features.py")
    lines.append("  python src/features/build_return_features.py")
    lines.append("")
    lines.append("Full walkthrough: README.md -> 'Dataset setup'")
    raise RuntimeError("\n".join(lines))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Model and DB are initialized once per process, not per-request.
    _preflight_data_check()
    init_db()
    model_service.load()
    anomaly_service.load()
    simulation_service.load()
    model_info_service.load()
    return_model_service.load()
    return_model_info_service.load()
    drift_service.load()
    logger.info(
        "startup complete model_loaded=%s baseline_fraud_rate=%.4f%%",
        model_service.is_loaded,
        anomaly_service.baseline_fraud_rate * 100,
    )
    yield


# debug is explicitly False (not just relying on Starlette's own default,
# also False) -- debug=True would echo full tracebacks (file paths, code
# structure, local variable values) straight into 500 responses. Full
# details still reach you: every unhandled exception is logged
# server-side with its real traceback via the handler below, just never
# sent to the client.
app = FastAPI(
    title="AI Risk Manager - Fraud Detection API",
    version="0.3.0",
    lifespan=lifespan,
    debug=False,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last-resort catch-all: an unhandled exception would otherwise still
    produce a safe, generic Starlette 500 response even without this (this
    is not what closes a real hole) -- it's here so that safe response is
    logged with the real traceback server-side, matching every other
    request's structured logging line, and so the generic-message
    behavior is an explicit, visible decision in this file rather than an
    implicit default a reviewer has to go verify in Starlette's source.
    """
    logger.exception("unhandled_exception path=%s method=%s", request.url.path, request.method)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# No wildcard, never has been -- allow_origins is always an explicit list.
# The list below is only the LOCAL-DEV DEFAULT, used when CORS_ORIGINS
# isn't set at all; a real deployment MUST set CORS_ORIGINS to the actual
# production frontend origin (see README's Production considerations) --
# this mechanism already supports that with zero code changes, just the
# env var. Left as localhost-only defaults (not a placeholder production
# domain) so a fresh clone works immediately with no required setup, at
# the cost of needing that one explicit env var before any real deploy --
# a tradeoff stated here, not hidden.
#
# Configurable via CORS_ORIGINS (comma-separated) because the frontend's
# origin genuinely differs between `npm run dev` (Vite on :5173) and the
# Dockerized frontend (nginx, published on :3000 by default -- see
# docker-compose.yml and .env.example). The default list below covers
# both out of the box so neither setup needs an env var to work.
#
# IMPORTANT (the actual common breakage point): these must be origins the
# BROWSER sends as `Origin` — i.e. localhost + a PUBLISHED port — never a
# Docker-internal service hostname like `http://backend:8000`. The browser
# runs on the host machine, not inside the compose network, so a
# container-only hostname would never match any real request's Origin
# header and CORS would silently fail.
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:3000,http://127.0.0.1:3000"
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS allow_origins=%s", CORS_ORIGINS)


# Security headers, applied to every response. Two policies:
# - Everywhere: X-Content-Type-Options (stop MIME-sniffing) and
#   X-Frame-Options: DENY (this API serves no page anyone should ever
#   frame -- not a UI, not an auth flow with a legitimate embed case).
# - Content-Security-Policy differs by path. The JSON API surface gets
#   `default-src 'none'` -- there's no reason a JSON response should ever
#   load a script/style/image/frame, so deny everything outright. /docs
#   and /redoc are real HTML pages that load Swagger/ReDoc's JS+CSS from
#   jsdelivr's CDN by default (FastAPI's own default, not something this
#   app added -- see get_swagger_ui_html's swagger_js_url/swagger_css_url
#   defaults) plus a favicon from fastapi.tiangolo.com, so those two
#   paths get a scoped policy that allows exactly those origins and
#   nothing else, rather than either breaking the docs UI or leaving it
#   with no policy at all.
_DOCS_PATHS = {"/docs", "/redoc"}
_DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)
_API_CSP = "default-src 'none'; frame-ancestors 'none'"


# Every real request body this API ever needs is tiny (TransactionIn is
# ~30 floats, well under 1KB as JSON; ReturnOrderIn is smaller still) --
# there is no legitimate caller that would ever send more than a few KB.
# Starlette/FastAPI apply no request-body size cap of their own by
# default (that's left to a reverse proxy or the app), so an oversized
# payload would otherwise be read fully into memory before Pydantic ever
# gets a chance to reject it on shape. Checked via Content-Length before
# the body is read at all -- a request lying about its Content-Length
# (or omitting it and streaming an oversized chonky body via chunked
# transfer-encoding) is a residual gap this header check doesn't close;
# a production deployment's reverse proxy (nginx's client_max_body_size,
# or the PaaS's own edge limit) is the real backstop for that case -- see
# README's Production Considerations.
MAX_REQUEST_BODY_BYTES = int(os.environ.get("MAX_REQUEST_BODY_BYTES", str(256 * 1024)))


@app.middleware("http")
async def body_size_limit_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body exceeds the {MAX_REQUEST_BODY_BYTES}-byte limit"},
                )
        except ValueError:
            pass  # Malformed header -- let normal request handling reject it downstream.
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        _DOCS_CSP if request.url.path in _DOCS_PATHS else _API_CSP
    )
    return response


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request_id=%s method=%s path=%s status=%s latency_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(predict.router, prefix="/api/v1", tags=["predict"])
app.include_router(transactions.router, prefix="/api/v1", tags=["transactions"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(simulate.router, prefix="/api/v1", tags=["simulate"])
app.include_router(models.router, prefix="/api/v1", tags=["models"])
app.include_router(chargebacks.router, prefix="/api/v1", tags=["chargebacks"])
app.include_router(return_predict.router, prefix="/api/v1", tags=["return-risk"])
app.include_router(return_model_info.router, prefix="/api/v1", tags=["return-risk"])
app.include_router(monitoring.router, prefix="/api/v1", tags=["monitoring"])
