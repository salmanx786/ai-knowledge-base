import asyncio
import os
import shutil
from pathlib import Path
import pytest
from typing import AsyncGenerator

# Configure environment variables before importing any app modules to force test configurations
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_ai_knowledge_base.db"
os.environ["JWT_SECRET"] = "test_jwt_secret_key_which_is_long_enough_for_hs256_spec"
os.environ["UPLOAD_DIR"] = "test_uploads"
os.environ["GEMINI_API_KEY"] = "mock_key"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import ASGITransport, AsyncClient


from app.main import app
from app.db.base import Base
from app.dependencies.db import get_db

# 1. Isolated Test Database Setup
TEST_DB_FILE = "test_ai_knowledge_base.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

# Clean up any leftover database file and upload folder before run
def clean_test_resources():
    if os.path.exists(TEST_DB_FILE):
        try:
            os.unlink(TEST_DB_FILE)
        except Exception:
            pass
    if os.path.exists("test_uploads"):
        try:
            shutil.rmtree("test_uploads")
        except Exception:
            pass

clean_test_resources()


@pytest.fixture(scope="session", autouse=True)
async def init_db():
    """Create database tables before tests and clean up after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    clean_test_resources()

@pytest.fixture(autouse=True)
async def clean_db_after_test():
    """Clean up database tables after each test to ensure isolation."""
    yield
    # Clean up database tables after test
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    
    # Clean up uploads folder after test
    if os.path.exists("test_uploads"):
        try:
            shutil.rmtree("test_uploads")
        except Exception:
            pass

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session per test with automatic rollback."""
    async with TestSessionFactory() as session:
        yield session

# Override the FastAPI database session dependency
@pytest.fixture(autouse=True)
def override_db_dependency():
    async def _get_db_override():
        async with TestSessionFactory() as session:
            yield session
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db, None)

# 2. Mocking heavy external dependencies (Embeddings & Gemini)
@pytest.fixture(autouse=True)
def mock_embeddings(monkeypatch):
    """Mock SentenceTransformers to avoid loading PyTorch and downloading weights."""
    def mock_embed(self, text: str) -> list[float]:
        # Return a dummy 384-dimensional vector (fixed size)
        # We can make it slightly distinct based on text to make similarity mock testing realistic
        val = 0.1
        if "matching" in text or "relevant" in text:
            val = 0.9
        elif "dissimilar" in text:
            val = -0.5
        return [val] * 384
        
    monkeypatch.setattr("app.services.embeddings.EmbeddingService.embed", mock_embed)

@pytest.fixture(autouse=True)
def mock_gemini(monkeypatch):
    """Mock LLM response calls to avoid real Google Gen AI API traffic."""
    def mock_generate(*, system: str, context: str, question: str) -> str:
        return f"Mocked response for '{question}' based on context: {context[:50]}..."
        
    monkeypatch.setattr("app.services.llm.generate_answer", mock_generate)

# 3. HTTP Client for Endpoint Testing
@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client to make request calls to the FastAPI app."""
    # Use ASGITransport instead of deprecated app parameter or HTTPTransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
