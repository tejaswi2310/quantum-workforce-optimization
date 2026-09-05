import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

@pytest.fixture
def auth_client_and_project():
    client = TestClient(app)
    
    # Register and Login
    client.post(
        "/api/v1/auth/register",
        json={"email": "api_val_user@example.com", "password": "TestPassword123!", "full_name": "API Val User"}
    )
    
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "api_val_user@example.com", "password": "TestPassword123!"}
    )
    token = login_response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    
    # Create Project
    proj_response = client.post(
        "/api/v1/projects/",
        json={"name": "API Validation Project", "description": "Testing API Validation"}
    )
    project_id = proj_response.json()["id"]
    
    return client, project_id

@patch("fastapi.BackgroundTasks.add_task")
def test_optimize_classical_api_validation(mock_add_task, auth_client_and_project):
    client, project_id = auth_client_and_project
    
    # CASE A: VALID (Empty parameters)
    # The endpoint should return 200 OK. The background task is mocked to avoid execution.
    valid_payload = {"parameters": {}}
    valid_response = client.post(f"/api/v1/projects/{project_id}/optimize/classical", json=valid_payload)
    
    assert valid_response.status_code == 200, f"Expected 200, got {valid_response.status_code} - {valid_response.text}"
    assert valid_response.json()["status"] == "pending"
    assert mock_add_task.called, "The background task should have been triggered."
    
    # CASE B: INVALID (Unsupported parameters)
    # The endpoint should return 400 Bad Request immediately.
    invalid_payload = {"parameters": {"budget": 5000}}
    invalid_response = client.post(f"/api/v1/projects/{project_id}/optimize/classical", json=invalid_payload)
    
    assert invalid_response.status_code == 400, f"Expected 400, got {invalid_response.status_code} - {invalid_response.text}"
    assert "Unsupported parameters provided" in invalid_response.json()["detail"]
