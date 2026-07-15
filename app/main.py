from fastapi import FastAPI

from app.api.health import router as health_router
from app.config.settings import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(health_router)
