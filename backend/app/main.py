import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.database import init_db
from app.routers import auth, garmin, plans, sessions, admin

limiter = Limiter(key_func=get_remote_address, default_limits=[])

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.APP_ENV == "development":
        await init_db()
    yield


app = FastAPI(
    title="Ultimate Running Schedule API",
    version="1.0.0",
    description="AI-powered running plan generator with Garmin Connect integration",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(garmin.router, prefix="/api/v1")
app.include_router(plans.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

upload_dir = "/app/uploads"
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
