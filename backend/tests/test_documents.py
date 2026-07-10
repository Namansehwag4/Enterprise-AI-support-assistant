import os
import pytest
from httpx import AsyncClient
from app.domain.models.user import UserRole

@pytest.mark.asyncio
async def test_document_upload_and_delete_flow(client: AsyncClient):
    # 1. Register and login as Admin (restricted endpoint check)
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@example.com",
            "password": "adminsecurepwd",
            "full_name": "Admin User",
            "role": "ADMIN"
        }
    )
    assert reg_response.status_code == 201
    
    login_response = await client.post(
        "/api/v1/auth/token",
        data={
            "username": "admin@example.com",
            "password": "adminsecurepwd"
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Register a standard Employee user to verify auth restrictions
    emp_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "employee@example.com",
            "password": "empsecurepwd",
            "full_name": "Employee User",
            "role": "EMPLOYEE"
        }
    )
    assert emp_reg.status_code == 201
    
    emp_login = await client.post(
        "/api/v1/auth/token",
        data={
            "username": "employee@example.com",
            "password": "empsecurepwd"
        }
    )
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 3. Test that Employee CANNOT upload documents
    files = {"file": ("policy.txt", b"This is a corporate HR policy on leaves.", "text/plain")}
    emp_upload_response = await client.post(
        "/api/v1/documents/",
        files=files,
        headers=emp_headers
    )
    assert emp_upload_response.status_code == 403 # Forbidden for Employees
    
    # 4. Upload document as Admin
    files = {"file": ("policy.txt", b"This is a corporate HR policy on leaves.", "text/plain")}
    upload_response = await client.post(
        "/api/v1/documents/",
        files=files,
        headers=headers
    )
    assert upload_response.status_code == 202 # Accepted
    doc_data = upload_response.json()
    assert doc_data["filename"] == "policy.txt"
    assert doc_data["status"] == "PROCESSING"
    doc_id = doc_data["id"]
    
    # Since parsing runs in a background task on the FastAPI dev server, we can wait a moment,
    # but in pytest conftest ASGITransport runs everything synchronously in the event loop,
    # meaning the background task executes immediately before returning or we can check its DB status.
    # Let's check status via GET /documents/{id}
    details_response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert details_response.status_code == 200
    details_data = details_response.json()
    # It should have run the background task and changed to COMPLETED
    assert details_data["status"] == "COMPLETED"
    
    # 5. List documents
    list_response = await client.get("/api/v1/documents/", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert len(list_data) >= 1
    assert any(d["id"] == doc_id for d in list_data)

    # 6. Delete document as Admin
    delete_response = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert delete_response.status_code == 204
    
    # Try fetching details again -> should return 404
    missing_response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert missing_response.status_code == 404
