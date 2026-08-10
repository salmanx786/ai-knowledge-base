import asyncio
from httpx import AsyncClient, ASGITransport
import os
import shutil

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_ai_knowledge_base.db"
os.environ["JWT_SECRET"] = "test_jwt_secret_key_which_is_long_enough_for_hs256_spec"
os.environ["UPLOAD_DIR"] = "test_uploads"
os.environ["GEMINI_API_KEY"] = "mock_key"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.db.base import Base
from app.dependencies.db import get_db

test_engine = create_async_engine("sqlite+aiosqlite:///test_ai_knowledge_base.db", echo=False)
TestSessionFactory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, autoflush=False, expire_on_commit=False,
)

async def run():
    # clean up first
    if os.path.exists("test_ai_knowledge_base.db"):
        os.unlink("test_ai_knowledge_base.db")
        
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestSessionFactory() as session:
        async def _get_db_override():
            yield session
            
        app.dependency_overrides[get_db] = _get_db_override
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            reg_payload = {
                "email": "candidate@example.com",
                "password": "securepassword123",
                "full_name": "Test Candidate",
                "organization_name": "Test Org"
            }
            print("Sending POST request to /api/v1/auth/register")
            response = await ac.post("/api/v1/auth/register", json=reg_payload)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(run())
