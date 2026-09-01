import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def test_project_crud_bug():
    # 1. Register and login to get token
    user_email = f"test_{uuid.uuid4()}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": user_email,
        "password": "Password123!",
        "full_name": "Project Tester"
    })
    
    login_resp = client.post("/api/v1/auth/login", json={
        "email": user_email,
        "password": "Password123!"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Try creating a project
    project_payload = {
        "name": "WISER Vanguard 2026 - Call Center Staffing",
        "description": "AI + Classical + Quantum Workforce Optimization for call center staffing."
    }
    resp = client.post("/api/v1/projects/", json=project_payload, headers=headers)
    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text)
    
if __name__ == "__main__":
    test_project_crud_bug()
