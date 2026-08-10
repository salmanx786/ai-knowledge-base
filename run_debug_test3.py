import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_ai_knowledge_base.db"
os.environ["JWT_SECRET"] = "test_jwt_secret_key"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.services.auth_service import AuthenticationService
from app.schemas.auth import RegisterRequest

test_engine = create_async_engine("sqlite+aiosqlite:///test_ai_knowledge_base.db", echo=False)
TestSessionFactory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, autoflush=False, expire_on_commit=False,
)

async def run():
    if os.path.exists("test_ai_knowledge_base.db"):
        os.unlink("test_ai_knowledge_base.db")
        
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestSessionFactory() as session:
        service = AuthenticationService(session)
        payload = RegisterRequest(
            email="candidate_test@example.com",
            password="securepassword123",
            full_name="Test Candidate",
            organization_name="Test Org"
        )
        try:
            user = await service.register_user(payload)
            print("Successfully registered:", user.email)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
