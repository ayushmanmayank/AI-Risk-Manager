"""FastAPI entrypoint for the AI Risk Manager fraud detection API (Day 3 MVP).

Run with:  uvicorn api.main:app --reload   (from the project root)
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routes import alerts, analytics, chargebacks, health, models, predict, simulate, transactions
from api.services.anomaly_service import anomaly_service
from api.services.db import init_db
from api.services.model_info_service import model_info_service
from api.services.model_service import model_service
from api.services.simulation_service import simulation_service

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("fraud_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Model and DB are initialized once per process, not per-request.
    init_db()
    model_service.load()
    anomaly_service.load()
    simulation_service.load()
    model_info_service.load()
    logger.info(
        "startup complete model_loaded=%s baseline_fraud_rate=%.4f%%",
        model_service.is_loaded,
        anomaly_service.baseline_fraud_rate * 100,
    )
    yield


app = FastAPI(
    title="AI Risk Manager - Fraud Detection API",
    version="0.3.0",
    lifespan=lifespan,
)

# Local-dev CORS only: Vite's default ports on localhost/127.0.0.1. This is
# not the auth/rate-limiting deferral from Day 3 — the frontend cannot make
# any cross-origin request at all without it. Tighten before any real deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
