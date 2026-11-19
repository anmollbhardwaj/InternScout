import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.endpoints import router as api_router
from app.services.scheduler.tasks import scheduler_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("internscout")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing InternScout backend services...")
    # Initialize DB tables automatically
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schemas verified.")

    # Start APScheduler
    scheduler_service.start()

    yield

    # Clean shutdown
    logger.info("Shutting down InternScout background scheduler...")
    scheduler_service.shutdown()
    await engine.dispose()
    logger.info("Engine disposed. Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="End-to-End Automated Internshala Discovery, Resume-Tailoring & Auto-Apply Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
# Also mount websocket directly on root for convenience
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "HEALTHY", "service": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
