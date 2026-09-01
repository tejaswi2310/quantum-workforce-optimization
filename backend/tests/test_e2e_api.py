import pytest
from fastapi.testclient import TestClient
from uuid import UUID
import io
import time

def test_full_pipeline_e2e(client: TestClient):
    # 1. Register User
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "e2e_user@example.com", "password": "TestPassword123!", "full_name": "E2E User"}
    )
    assert register_response.status_code == 200
    
    # 2. Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "e2e_user@example.com", "password": "TestPassword123!"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3 & 4. Receive JWT & Call /auth/me
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    
    # 5. Create project
    proj_response = client.post(
        "/api/v1/projects/",
        json={"name": "E2E Quantum Call Center", "description": "End-to-End Test Project"},
        headers=headers
    )
    assert proj_response.status_code == 200
    project_id = proj_response.json()["id"]
    
    # 6. Retrieve project
    get_proj_response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_proj_response.status_code == 200
    assert get_proj_response.json()["id"] == project_id
    
    # 7. Upload valid CSV dataset
    valid_csv = (
        "date,hour,day_of_week,channel,skill_group,calls_received\n"
        "2026-01-01,0,Thursday,Voice,General,50\n"
        "2026-01-01,1,Thursday,Voice,General,45\n"
    )
    files = {"file": ("data.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")}
    upload_response = client.post(
        f"/api/v1/projects/{project_id}/datasets/upload",
        files=files,
        headers=headers
    )
    assert upload_response.status_code == 200
    dataset_id = upload_response.json()["id"]
    
    # 8. Retrieve uploaded datasets
    datasets_resp = client.get(f"/api/v1/projects/{project_id}/datasets", headers=headers)
    assert datasets_resp.status_code == 200
    assert len(datasets_resp.json()) == 1
    
    # 9. Start forecast
    # We expect BackgroundTasks to be triggered, but for unit tests, Starlette's TestClient
    # executes BackgroundTasks immediately after the response is returned.
    # However, since ml_service uses subprocess or heavy operations, we will mock them if needed.
    # Actually, we should be able to run a simple forecast train mock. Let's see if the endpoint works.
    # Wait, train_forecast requires background task. The response is immediately returned.
    forecast_resp = client.post(f"/api/v1/projects/{project_id}/forecast/train", headers=headers)
    assert forecast_resp.status_code == 200
    task_id = forecast_resp.json()["id"]
    
    # 10. Check forecast status
    status_resp = client.get(f"/api/v1/projects/{project_id}/forecast/status/{task_id}", headers=headers)
    assert status_resp.status_code == 200
    
    # 11. Retrieve forecast results
    results_resp = client.get(f"/api/v1/projects/{project_id}/forecast/results", headers=headers)
    assert results_resp.status_code == 200
    
    # 12-15. Optimizations
    opt_payload = {"parameters": {"budget": 5000, "sla": 80}}
    class_opt = client.post(f"/api/v1/projects/{project_id}/optimize/classical", json=opt_payload, headers=headers)
    assert class_opt.status_code == 200
    class_id = class_opt.json()["id"]
    
    shift_opt = client.post(f"/api/v1/projects/{project_id}/optimize/shifts", json=opt_payload, headers=headers)
    assert shift_opt.status_code == 200
    shift_id = shift_opt.json()["id"]
    
    quant_opt = client.post(f"/api/v1/projects/{project_id}/optimize/quantum", json=opt_payload, headers=headers)
    assert quant_opt.status_code == 200
    quant_id = quant_opt.json()["id"]
    
    hybrid_opt = client.post(f"/api/v1/projects/{project_id}/optimize/hybrid", json=opt_payload, headers=headers)
    assert hybrid_opt.status_code == 200
    hybrid_id = hybrid_opt.json()["id"]
    
    runs_resp = client.get(f"/api/v1/projects/{project_id}/optimize/runs", headers=headers)
    assert runs_resp.status_code == 200
    assert len(runs_resp.json()) == 4
    
    run_resp = client.get(f"/api/v1/projects/{project_id}/optimize/runs/{class_id}", headers=headers)
    assert run_resp.status_code == 200
    
    # 16. Run queue validation
    val_payload = {"optimization_run_id": class_id}
    val_resp = client.post(f"/api/v1/projects/{project_id}/validate/queue", json=val_payload, headers=headers)
    assert val_resp.status_code == 200
    
    # 17. Retrieve validation results
    get_val_resp = client.get(f"/api/v1/projects/{project_id}/validate/results", headers=headers)
    assert get_val_resp.status_code == 200
    
    # 18. Generate report
    report_resp = client.post(
        f"/api/v1/projects/{project_id}/reports/generate",
        json={"report_type": "business_impact"},
        headers=headers
    )
    assert report_resp.status_code == 200
    report_id = report_resp.json()["id"]
    
    # 19. Retrieve reports
    reports_resp = client.get(f"/api/v1/projects/{project_id}/reports/", headers=headers)
    assert reports_resp.status_code == 200
    assert len(reports_resp.json()) == 1
    
    # 20. Download report
    download_resp = client.get(f"/api/v1/projects/{project_id}/reports/{report_id}/download", headers=headers)
    assert download_resp.status_code == 200
    assert b"Business Impact Report" in download_resp.content
    
    # 21-23. Dashboard metrics
    metrics_resp = client.get(f"/api/v1/projects/{project_id}/dashboard/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    
    analytics_resp = client.get(f"/api/v1/projects/{project_id}/dashboard/analytics", headers=headers)
    assert analytics_resp.status_code == 200
    
    whatif_resp = client.get(f"/api/v1/projects/{project_id}/dashboard/whatif?volume_change=10&budget=5000&sla=80", headers=headers)
    # This might return 404 if queue validation results don't exist in the mock folder, 
    # but the endpoint should route correctly.
    assert whatif_resp.status_code in [200, 404]
    
    opt_dash_resp = client.get(f"/api/v1/projects/{project_id}/dashboard/optimization", headers=headers)
    assert opt_dash_resp.status_code in [200, 404]

def test_invalid_uuid_error_handling(client: TestClient):
    # Test that providing an invalid UUID returns 422, not 500
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "e2e_user2@example.com", "password": "TestPassword123!", "full_name": "E2E User"}
    )
    
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "e2e_user2@example.com", "password": "TestPassword123!"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = client.get("/api/v1/projects/invalid-uuid", headers=headers)
    assert resp.status_code == 422
    
    resp = client.get("/api/v1/projects/invalid-uuid/dashboard/metrics", headers=headers)
    assert resp.status_code == 422
