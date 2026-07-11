import json
import pytest
import traceback
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_session_and_rag_streaming_flow(client: AsyncClient):
    try:
        # 1. Register and login
        reg_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "chatuser@example.com",
                "password": "chatuserpwd123",
                "full_name": "Chat User",
                "role": "EMPLOYEE"
            }
        )
        assert reg_response.status_code == 201
        
        login_response = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "chatuser@example.com",
                "password": "chatuserpwd123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Chat Session
        session_response = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "IT Policy Discussion"},
            headers=headers
        )
        assert session_response.status_code == 201
        session_data = session_response.json()
        assert session_data["title"] == "IT Policy Discussion"
        session_id = session_data["id"]

        # 3. List Chat Sessions
        list_response = await client.get("/api/v1/chat/sessions", headers=headers)
        assert list_response.status_code == 200
        sessions_list = list_response.json()
        assert len(sessions_list) >= 1
        assert any(s["id"] == session_id for s in sessions_list)

        # 4. Upload a mock document as Admin so the RAG engine has context
        admin_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "chatadmin@example.com",
                "password": "chatadminpwd",
                "full_name": "Chat Admin",
                "role": "ADMIN"
            }
        )
        assert admin_reg.status_code == 201
        
        admin_login = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "chatadmin@example.com",
                "password": "chatadminpwd"
            }
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        files = {"file": ("travel_policy.txt", b"Travel reimbursement meal allowance covers $50 per day.", "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/",
            files=files,
            headers=admin_headers
        )
        assert upload_response.status_code == 202
        doc_id = upload_response.json()["id"]

        # Wait for background document parsing task to complete
        import asyncio
        completed = False
        for _ in range(10): # try up to 10 times (1 second total)
            status_check = await client.get(f"/api/v1/documents/{doc_id}", headers=admin_headers)
            assert status_check.status_code == 200
            if status_check.json()["status"] == "COMPLETED":
                completed = True
                break
            await asyncio.sleep(0.1)
        assert completed, "Document processing timed out"

        # 5. Send message inside thread and stream response
        full_response_text = ""
        metadata_parsed = None
        
        async with client.stream(
            "POST",
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "What is the meal allowance?"},
            headers=headers
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_val = line[6:]
                    if data_val.startswith("[METADATA]"):
                        metadata_parsed = json.loads(data_val[10:])
                    else:
                        full_response_text += data_val

        # Verify RAG response text is returned
        assert len(full_response_text) > 0
        assert "Based on the corporate document" in full_response_text or "allowance" in full_response_text
        
        # Verify metadata is parsed and citations exist
        assert metadata_parsed is not None
        assert "message_id" in metadata_parsed
        assert "user_message_id" in metadata_parsed
        assert "citations" in metadata_parsed
        
        citations = metadata_parsed["citations"]
        assert len(citations) >= 1
        assert citations[0]["document_id"] == doc_id
        assert citations[0]["filename"] == "travel_policy.txt"

        # 6. Retrieve Session Details (history check)
        detail_response = await client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["id"] == session_id
        assert len(detail_data["messages"]) == 2 # 1 User message + 1 Assistant response
        
        # Assistant message should have citations loaded from DB
        assistant_msg = next(m for m in detail_data["messages"] if m["sender"] == "ASSISTANT")
        assert len(assistant_msg["citations"]) == 1
        assert assistant_msg["citations"][0]["filename"] == "travel_policy.txt"

        # 7. Delete Chat Session
        delete_response = await client.delete(f"/api/v1/chat/sessions/{session_id}", headers=headers)
        assert delete_response.status_code == 204
        
        # Confirm deletion
        deleted_check = await client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
        assert deleted_check.status_code == 404

    except Exception as e:
        print("EXCEPTION CAUGHT IN TEST CHAT:")
        traceback.print_exc()
        raise e
