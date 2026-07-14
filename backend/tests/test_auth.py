import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.user import UserRole

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    # Register employee user
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testemployee@example.com",
            "password": "securepassword123",
            "full_name": "John Doe",
            "role": "EMPLOYEE"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testemployee@example.com"
    assert data["full_name"] == "John Doe"
    assert data["role"] == "EMPLOYEE"
    assert "id" in data

    # Double registration check
    response_duplicate = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testemployee@example.com",
            "password": "anotherpassword",
            "full_name": "Jane Doe",
            "role": "EMPLOYEE"
        }
    )
    assert response_duplicate.status_code == 400
    assert "already exists" in response_duplicate.json()["detail"]

@pytest.mark.asyncio
async def test_login_and_read_me(client: AsyncClient):
    # Register user
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testlogin@example.com",
            "password": "loginpassword123",
            "full_name": "Login User",
            "role": "ADMIN"
        }
    )
    assert reg_response.status_code == 201

    # Login - Retrieve token
    login_response = await client.post(
        "/api/v1/auth/token",
        data={
            "username": "testlogin@example.com",
            "password": "loginpassword123"
        }
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert token_data["token_type"] == "bearer"
    assert "access_token" in token_data
    assert "refresh_token" in token_data

    # Read profile `/me` with token
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "testlogin@example.com"
    assert me_data["full_name"] == "Login User"
    assert me_data["role"] == "ADMIN"

    # Read profile with invalid token
    bad_headers = {"Authorization": "Bearer badtoken"}
    bad_me_response = await client.get("/api/v1/auth/me", headers=bad_headers)
    assert bad_me_response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient):
    # 1. Register a test user
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testrefresh@example.com",
            "password": "refreshpassword123",
            "full_name": "Refresh User",
            "role": "EMPLOYEE"
        }
    )
    assert reg_response.status_code == 201

    # 2. Login to get tokens
    login_response = await client.post(
        "/api/v1/auth/token",
        data={
            "username": "testrefresh@example.com",
            "password": "refreshpassword123"
        }
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    assert access_token is not None
    assert refresh_token is not None

    # 3. Request fresh access token using refresh token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    new_token_data = refresh_response.json()
    assert "access_token" in new_token_data
    assert "refresh_token" in new_token_data

    # 4. Use new access token to query /me
    headers = {"Authorization": f"Bearer {new_token_data['access_token']}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "testrefresh@example.com"

    # 5. Try refresh with invalid token -> should fail with 401
    bad_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "badrefreshtoken"}
    )
    assert bad_refresh_response.status_code == 401
