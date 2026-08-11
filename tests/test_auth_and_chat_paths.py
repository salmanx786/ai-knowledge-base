"""Integration tests for authentication and chat failure paths.

Complements ``test_integration.py`` (happy paths + ownership isolation) by
exercising the error branches that a reviewer would probe: duplicate
registration, wrong credentials, missing/garbage tokens, and asking a question
with nothing indexed to answer from.
"""

import pytest

from tests.test_integration import create_dummy_pdf


async def _register(client, email, password="password123", org="Org"):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "organization_name": org},
    )


async def _token(client, email, password="password123"):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_duplicate_registration_returns_409(client):
    """Registering the same email twice is a 409, not a 500 or a duplicate row."""
    first = await _register(client, "dupe@example.com")
    assert first.status_code == 201

    second = await _register(client, "dupe@example.com")
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    """A wrong password is rejected with the same generic message as unknown email."""
    await _register(client, "wrongpw@example.com", password="correcthorse123")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "not-the-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_login_unknown_email_is_indistinguishable(client):
    """Unknown email yields the identical 401 message -- no user enumeration."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "whatever12345"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_protected_route_without_token_returns_401(client):
    """A protected route rejects a request with no Authorization header."""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_garbage_token_returns_401(client):
    """A malformed/forged bearer token is rejected as 401, not 500."""
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not.a.real.jwt"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Could not validate credentials."


@pytest.mark.asyncio
async def test_chat_with_no_documents_returns_404(client):
    """Asking a question with an empty index returns 404, never an ungrounded answer."""
    await _register(client, "empty@example.com", org="Empty Org")
    token = await _token(client, "empty@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/chat",
        json={"question": "anything at all", "limit": 3},
        headers=headers,
    )
    assert resp.status_code == 404
    assert "No relevant documents" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_search_returns_scored_results_ranked_desc(client):
    """Search returns the user's chunks scored and ranked highest-similarity first.

    The mocked embedder (see conftest) maps text containing "matching"/"relevant"
    to a high-similarity vector and everything else to a low one, so the
    document whose content matches the query must rank strictly ahead.
    """
    await _register(client, "ranker@example.com", org="Rank Org")
    token = await _token(client, "ranker@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    for name, text in [
        ("relevant.pdf", "relevant content about the topic"),
        ("unrelated.pdf", "some other background note"),
    ]:
        pdf = create_dummy_pdf(text)
        await client.post(
            "/api/v1/documents/upload",
            files={"file": (name, pdf, "application/pdf")},
            headers=headers,
        )

    resp = await client.post(
        "/api/v1/documents/search",
        json={"query": "relevant information", "limit": 5},
        headers=headers,
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    # Ranked by score descending.
    assert results[0]["score"] >= results[1]["score"]
    # The matching document ranks first.
    assert "relevant" in results[0]["content"]
