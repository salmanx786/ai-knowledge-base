from fastapi import FastAPI
from app.api.health import router as health_router
from app.config.settings import settings

app = FastAPI()
print(settings.app_name)

app.include_router(health_router)