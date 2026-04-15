import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routers import auth, garmin, plans

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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
