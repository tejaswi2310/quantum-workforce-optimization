import pytest
import uuid
import io

@pytest.fixture(scope="module")
def project_id(client, user1_token):
    headers = {"Authorization": f"Bearer {user1_token}"}
    payload = {"name": "Dataset Test Project"}
    resp = client.post("/api/v1/projects/", json=payload, headers=headers)
    return resp.json()["id"]

def test_valid_csv_upload(client, user1_token, project_id):
    headers = {"Authorization": f"Bearer {user1_token}"}
    csv_content = "date,hour,day_of_week,channel,skill_group,calls_received,avg_handle_time\n2026-01-01,0,Monday,Voice,Billing,10,250"
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    resp = client.post(f"/api/v1/projects/{project_id}/datasets/upload", headers=headers, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "test.csv"
    assert data["row_count"] == 1
    assert "schema_definition" in data
    assert data["schema_definition"]["channel"] == "object"
    assert data["schema_definition"]["calls_received"] == "int64"

def test_empty_csv(client, user1_token, project_id):
    headers = {"Authorization": f"Bearer {user1_token}"}
    csv_content = ""
    files = {"file": ("empty.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    resp = client.post(f"/api/v1/projects/{project_id}/datasets/upload", headers=headers, files=files)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()

def test_malformed_csv(client, user1_token, project_id):
    headers = {"Authorization": f"Bearer {user1_token}"}
    # Create an invalid CSV format
    csv_content = "date,hour,day_of_week\n2026-01-01"
    files = {"file": ("malformed.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    resp = client.post(f"/api/v1/projects/{project_id}/datasets/upload", headers=headers, files=files)
    assert resp.status_code == 400
    assert "missing" in resp.json()["detail"].lower()

def test_unsupported_extension(client, user1_token, project_id):
    headers = {"Authorization": f"Bearer {user1_token}"}
    files = {"file": ("test.txt", io.BytesIO(b"dummy content"), "text/plain")}
    
    resp = client.post(f"/api/v1/projects/{project_id}/datasets/upload", headers=headers, files=files)
    assert resp.status_code == 415

def test_missing_required_columns(client, user1_token, project_id):
    headers = {"Authorization": f"Bearer {user1_token}"}
    # Missing 'calls_received' and 'channel'
    csv_content = "date,hour,day_of_week,skill_group\n2026-01-01,0,Monday,Billing"
    files = {"file": ("missing_cols.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    resp = client.post(f"/api/v1/projects/{project_id}/datasets/upload", headers=headers, files=files)
    assert resp.status_code == 400
    assert "missing required columns" in resp.json()["detail"].lower()

def test_non_existent_project(client, user1_token):
    headers = {"Authorization": f"Bearer {user1_token}"}
    fake_project_id = str(uuid.uuid4())
    csv_content = "date,hour,day_of_week,channel,skill_group,calls_received\n2026-01-01,0,Monday,Voice,Billing,10"
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    resp = client.post(f"/api/v1/projects/{fake_project_id}/datasets/upload", headers=headers, files=files)
    assert resp.status_code == 404

def test_unauthorized_project_upload(client, user2_token, project_id):
    # User 2 tries to upload to User 1's project
    headers = {"Authorization": f"Bearer {user2_token}"}
    csv_content = "date,hour,day_of_week,channel,skill_group,calls_received\n2026-01-01,0,Monday,Voice,Billing,10"
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    resp = client.post(f"/api/v1/projects/{project_id}/datasets/upload", headers=headers, files=files)
    assert resp.status_code == 404 # Not found is safer than 403 for enumeration

def test_duplicate_filename_behavior(client, user1_token, project_id):
    headers = {"Authorization": f"Bearer {user1_token}"}
    csv_content = "date,hour,day_of_week,channel,skill_group,calls_received\n2026-01-01,0,Monday,Voice,Billing,10"
    
    # Upload first time
    files1 = {"file": ("dup.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp1 = client.post(f"/api/v1/projects/{project_id}/datasets/upload", headers=headers, files=files1)
    assert resp1.status_code == 200
    
    # Upload second time with same filename
    files2 = {"file": ("dup.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp2 = client.post(f"/api/v1/projects/{project_id}/datasets/upload", headers=headers, files=files2)
    assert resp2.status_code == 200
    assert resp1.json()["id"] != resp2.json()["id"]
    
def test_get_datasets(client, user1_token, project_id):
    headers = {"Authorization": f"Bearer {user1_token}"}
    resp = client.get(f"/api/v1/projects/{project_id}/datasets/", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
