import uuid



def test_create_project(client, user1_token):
    headers = {"Authorization": f"Bearer {user1_token}"}
    payload = {"name": "Test Project 1", "description": "A project for testing CRUD"}
    resp = client.post("/api/v1/projects/", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    # Verify it's a valid UUID string
    assert uuid.UUID(data["id"])
    assert data["name"] == "Test Project 1"
    assert data["description"] == "A project for testing CRUD"

def test_list_projects(client, user1_token):
    headers = {"Authorization": f"Bearer {user1_token}"}
    resp = client.get("/api/v1/projects/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(p["name"] == "Test Project 1" for p in data)

def test_get_project_by_id(client, user1_token):
    headers = {"Authorization": f"Bearer {user1_token}"}
    # Create first
    payload = {"name": "Test Project 2"}
    resp = client.post("/api/v1/projects/", json=payload, headers=headers)
    project_id = resp.json()["id"]

    # Get it
    resp = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == project_id
    assert resp.json()["name"] == "Test Project 2"

def test_another_user_cannot_get_project(client, user1_token, user2_token):
    # User 1 creates project
    headers1 = {"Authorization": f"Bearer {user1_token}"}
    payload = {"name": "Secret Project"}
    resp = client.post("/api/v1/projects/", json=payload, headers=headers1)
    project_id = resp.json()["id"]

    # User 2 tries to get it
    headers2 = {"Authorization": f"Bearer {user2_token}"}
    resp2 = client.get(f"/api/v1/projects/{project_id}", headers=headers2)
    assert resp2.status_code == 404

def test_invalid_project_id(client, user1_token):
    headers = {"Authorization": f"Bearer {user1_token}"}
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/projects/{fake_id}", headers=headers)
    assert resp.status_code == 404

def test_delete_project(client, user1_token):
    headers = {"Authorization": f"Bearer {user1_token}"}
    payload = {"name": "To Be Deleted"}
    resp = client.post("/api/v1/projects/", json=payload, headers=headers)
    project_id = resp.json()["id"]

    # Delete it
    del_resp = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert del_resp.status_code == 200

    # Ensure it's gone
    get_resp = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 404

def test_unauthorized_access(client):
    resp = client.get("/api/v1/projects/")
    assert resp.status_code == 401
