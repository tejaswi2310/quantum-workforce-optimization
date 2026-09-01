import pytest

def test_json_login(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "swaggertest@example.com",
        "password": "Password123!",
        "full_name": "Swagger Test"
    })
    
    response = client.post("/api/v1/auth/login", json={
        "email": "swaggertest@example.com",
        "password": "Password123!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_swagger_oauth2_login(client):
    response = client.post("/api/v1/auth/token", data={
        "username": "swaggertest@example.com",
        "password": "Password123!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_me_endpoint(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "swaggertest@example.com",
        "password": "Password123!"
    })
    token = response.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_duplicate_registration(client):
    email = "duplicate@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "First User"
    })
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Second User"
    })
    assert response.status_code == 400

def test_long_password(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "longpass@example.com",
        "password": "a" * 73,
        "full_name": "Long Password"
    })
    assert response.status_code == 422

