"""
EYEQ – FastAPI Application Entry Point

Run with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

API Docs:
    http://localhost:8000/docs
"""

import time
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.database.db import init_db
from backend.routes import auth_routes, camera_routes, alert_routes
from config.settings import APP_NAME, APP_VERSION, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, DEBUG
from utils.helpers import bootstrap_directories, get_logger

logger = get_logger(__name__)

# ─── App Setup ─────────────────────────────────────────────────

app = FastAPI(
    title=f"{APP_NAME} API",
    description="Intelligent Vision Security System – REST API",
    version=APP_VERSION,
    docs_url="/docs" if DEBUG else None,      # hide Swagger in production
    redoc_url="/redoc" if DEBUG else None,
)

# ─── CORS ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Rate Limiting (in-memory, single-instance) ────────────────

_request_counts: dict = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    # Purge old timestamps
    _request_counts[client_ip] = [t for t in _request_counts[client_ip] if t > window_start]

    if len(_request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
        )

    _request_counts[client_ip].append(now)
    return await call_next(request)


# ─── Routers ───────────────────────────────────────────────────

app.include_router(auth_routes.router)
app.include_router(camera_routes.router)
app.include_router(alert_routes.router)


# ─── Startup / Shutdown ────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    bootstrap_directories()
    init_db()
    logger.info("%s v%s started.", APP_NAME, APP_VERSION)


@app.on_event("shutdown")
def on_shutdown():
    logger.info("%s shutting down.", APP_NAME)


# ─── Health Check ──────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@app.get("/", tags=["System"])
def root():
    return {"message": f"Welcome to {APP_NAME} API. Visit /docs for API reference."}
