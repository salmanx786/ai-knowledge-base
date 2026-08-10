import os
import fitz
import pytest
from pathlib import Path
from app.config.settings import settings

def create_dummy_pdf(text: str) -> bytes:
    """Helper to generate a valid PDF containing the specified text in memory."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

@pytest.mark.asyncio
async def test_authentication_flow(client):
    """Test user registration, login, and profile retrieval."""
    # 1. Register a new user
    reg_payload = {
        "email": "candidate@example.com",
        "password": "securepassword123",
        "full_name": "Test Candidate",
        "organization_name": "Test Org"
    }
    response = await client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "candidate@example.com"
    assert "id" in data
    assert data["is_active"] is True

    # 2. Login to get token
    login_payload = {
        "email": "candidate@example.com",
        "password": "securepassword123"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "Bearer"

    # 3. Access current user info
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "candidate@example.com"
    assert user_data["full_name"] == "Test Candidate"

@pytest.mark.asyncio
async def test_document_upload_and_deletion(client):
    """Test document upload, verify DB entry + physical storage, and verify file cleanup on delete."""
    # Register & Login
    reg_payload = {
        "email": "user1@example.com",
        "password": "password123",
        "organization_name": "Org 1"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)
    login_response = await client.post("/api/v1/auth/login", json={"email": "user1@example.com", "password": "password123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate dummy PDF
    pdf_bytes = create_dummy_pdf("This is a valid PDF containing important knowledge base information.")
    files = {"file": ("test_doc.pdf", pdf_bytes, "application/pdf")}

    # Upload document
    response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert response.status_code == 201
    doc_data = response.json()
    doc_id = doc_data["id"]
    assert doc_data["filename"] == "test_doc.pdf"
    assert doc_data["extracted_text"].strip() == "This is a valid PDF containing important knowledge base information."

    # Check that file exists on disk
    owner_dir = Path(settings.upload_dir) / str(doc_data["owner_id"])
    files_in_dir = list(owner_dir.glob("*.pdf"))
    assert len(files_in_dir) == 1
    file_path = files_in_dir[0]
    assert file_path.exists()

    # Delete document
    delete_response = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert delete_response.status_code == 204

    # Verify document is gone from disk
    assert not file_path.exists()

@pytest.mark.asyncio
async def test_document_list_pagination_and_summary(client):
    """Test pagination limit/offset and that GET /documents returns summaries without extracted_text."""
    # Register & Login
    reg_payload = {
        "email": "pager@example.com",
        "password": "password123",
        "organization_name": "Org Pagination"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)
    login_response = await client.post("/api/v1/auth/login", json={"email": "pager@example.com", "password": "password123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload 3 documents
    for i in range(3):
        pdf_bytes = create_dummy_pdf(f"Text content for document number {i}.")
        files = {"file": (f"doc_{i}.pdf", pdf_bytes, "application/pdf")}
        await client.post("/api/v1/documents/upload", files=files, headers=headers)

    # 1. Fetch index with limit=2, offset=0
    response = await client.get("/api/v1/documents?limit=2&offset=0", headers=headers)
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 2
    # Verify that extracted_text is not present in the index summary response
    for doc in docs:
        assert "extracted_text" not in doc

    # 2. Fetch index with limit=2, offset=2 (should get the remaining 1 document)
    response = await client.get("/api/v1/documents?limit=2&offset=2", headers=headers)
    assert response.status_code == 200
    docs_offset = response.json()
    assert len(docs_offset) == 1
    assert "extracted_text" not in docs_offset[0]

@pytest.mark.asyncio
async def test_ownership_isolation(client):
    """Test that User B cannot read, delete, or search User A's documents."""
    # User A setup
    await client.post("/api/v1/auth/register", json={
        "email": "usera@example.com", "password": "password123", "organization_name": "Org A"
    })
    login_a = await client.post("/api/v1/auth/login", json={"email": "usera@example.com", "password": "password123"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User B setup
    await client.post("/api/v1/auth/register", json={
        "email": "userb@example.com", "password": "password123", "organization_name": "Org B"
    })
    login_b = await client.post("/api/v1/auth/login", json={"email": "userb@example.com", "password": "password123"})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A uploads a document
    pdf_bytes = create_dummy_pdf("Secret document owned by User A.")
    files = {"file": ("usera_doc.pdf", pdf_bytes, "application/pdf")}
    upload_response = await client.post("/api/v1/documents/upload", files=files, headers=headers_a)
    doc_a_id = upload_response.json()["id"]

    # 1. User B tries to GET User A's document detail
    response = await client.get(f"/api/v1/documents/{doc_a_id}", headers=headers_b)
    assert response.status_code == 404

    # 2. User B tries to DELETE User A's document
    response = await client.delete(f"/api/v1/documents/{doc_a_id}", headers=headers_b)
    assert response.status_code == 404

    # 3. User B tries to search and shouldn't find User A's document content
    search_payload = {"query": "Secret document owned by User A", "limit": 5}
    response = await client.post("/api/v1/documents/search", json=search_payload, headers=headers_b)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 0

@pytest.mark.asyncio
async def test_invalid_pdf_handling_and_cleanup(client):
    """Test uploading an invalid PDF returns 400 and leaves no orphaned file on disk."""
    # Register & Login
    reg_payload = {
        "email": "pdf_fail@example.com",
        "password": "password123",
        "organization_name": "Org Fail"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)
    login_response = await client.post("/api/v1/auth/login", json={"email": "pdf_fail@example.com", "password": "password123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload invalid PDF (junk bytes)
    files = {"file": ("malformed.pdf", b"this is not a valid pdf format", "application/pdf")}
    response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    
    # Assert return code is 400 Bad Request
    assert response.status_code == 400
    assert "Failed to extract text" in response.json()["detail"]

    # Ensure no orphaned files exist in user's directory
    # Find user ID (me)
    user_me = await client.get("/api/v1/users/me", headers=headers)
    user_id = user_me.json()["id"]
    owner_dir = Path(settings.upload_dir) / str(user_id)
    
    # If the directory was created, check that it contains no pdf files
    if owner_dir.exists():
        files_in_dir = list(owner_dir.glob("*.pdf"))
        assert len(files_in_dir) == 0

@pytest.mark.asyncio
async def test_upload_size_limit(client):
    """Test uploading a file larger than the configured maximum size returns 413 and unlinks any file."""
    # Register & Login
    reg_payload = {
        "email": "size_fail@example.com",
        "password": "password123",
        "organization_name": "Org Size Limit"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)
    login_response = await client.post("/api/v1/auth/login", json={"email": "size_fail@example.com", "password": "password123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Temporarily set upload limit to 0MB so any upload is rejected
    settings.max_upload_size_mb = 0
    try:
        pdf_bytes = create_dummy_pdf("This file should be oversized.")
        files = {"file": ("oversized.pdf", pdf_bytes, "application/pdf")}
        response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
        
        # Verify 413 Payload Too Large is returned
        assert response.status_code == 413
        assert "exceeds the maximum limit" in response.json()["detail"]
    finally:
        # Restore default settings
        settings.max_upload_size_mb = 10

    # Ensure no files were written to disk
    user_me = await client.get("/api/v1/users/me", headers=headers)
    user_id = user_me.json()["id"]
    owner_dir = Path(settings.upload_dir) / str(user_id)
    if owner_dir.exists():
        files_in_dir = list(owner_dir.glob("*.pdf"))
        assert len(files_in_dir) == 0

@pytest.mark.asyncio
async def test_chat_endpoint_with_mocked_gemini(client):
    """Test /chat endpoint to verify LLM execution grounding and citations return."""
    # Register & Login
    reg_payload = {
        "email": "chat_user@example.com",
        "password": "password123",
        "organization_name": "Org Chat"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)
    login_response = await client.post("/api/v1/auth/login", json={"email": "chat_user@example.com", "password": "password123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload document with specific content matching the retrieval query
    # conftest mock_embeddings returns 0.9 similarity for matching text
    pdf_bytes = create_dummy_pdf("matching content about python and machine learning RAG.")
    files = {"file": ("rag_info.pdf", pdf_bytes, "application/pdf")}
    await client.post("/api/v1/documents/upload", files=files, headers=headers)

    # Call the chat endpoint
    chat_payload = {"question": "matching info about python", "limit": 3}
    response = await client.post("/api/v1/chat", json=chat_payload, headers=headers)
    
    assert response.status_code == 200
    chat_data = response.json()
    
    # Verify the mocked response and that citation sources are populated
    assert "Mocked response" in chat_data["answer"]
    assert "matching info about python" in chat_data["answer"]
    assert len(chat_data["sources"]) > 0
    assert "document_id" in chat_data["sources"][0]
    assert "chunk_index" in chat_data["sources"][0]


@pytest.mark.asyncio
async def test_invalid_pagination_parameters(client):
    """Test that invalid pagination parameters return HTTP 422 Unprocessable Entity."""
    # Register & Login
    reg_payload = {
        "email": "invalid_page@example.com",
        "password": "password123",
        "organization_name": "Org Page Fail"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)
    login_response = await client.post("/api/v1/auth/login", json={"email": "invalid_page@example.com", "password": "password123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. limit=0 (should fail ge=1)
    response = await client.get("/api/v1/documents?limit=0", headers=headers)
    assert response.status_code == 422

    # 2. limit=101 (should fail le=100)
    response = await client.get("/api/v1/documents?limit=101", headers=headers)
    assert response.status_code == 422

    # 3. offset=-1 (should fail ge=0)
    response = await client.get("/api/v1/documents?offset=-1", headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_endpoint_llm_config_error(client, monkeypatch):
    """Test that chat endpoint handles LLMConfigurationError cleanly with a 500 without details."""
    from app.repositories.errors import LLMConfigurationError

    # Register & Login
    reg_payload = {
        "email": "chat_config_fail@example.com",
        "password": "password123",
        "organization_name": "Org Chat Config Fail"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)
    login_response = await client.post("/api/v1/auth/login", json={"email": "chat_config_fail@example.com", "password": "password123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload document with specific content matching the retrieval query
    pdf_bytes = create_dummy_pdf("matching content about configuration error testing.")
    files = {"file": ("config_test.pdf", pdf_bytes, "application/pdf")}
    await client.post("/api/v1/documents/upload", files=files, headers=headers)

    # Monkeypatch to raise LLMConfigurationError when generating answer
    def mock_generate_fail(*args, **kwargs):
        raise LLMConfigurationError("Sensitive API key or deployment issue info")
    monkeypatch.setattr("app.services.llm.generate_answer", mock_generate_fail)

    # Call the chat endpoint
    chat_payload = {"question": "matching info", "limit": 3}
    response = await client.post("/api/v1/chat", json=chat_payload, headers=headers)

    # Verify generic 500 configuration message and no internal details
    assert response.status_code == 500
    assert "LLM is not configured." in response.json()["detail"]
    assert "Sensitive" not in response.json()["detail"]

