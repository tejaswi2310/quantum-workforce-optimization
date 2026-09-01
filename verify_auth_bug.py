import requests

base_url = "http://127.0.0.1:8000/api/v1/auth"
print("Testing Register endpoint...")
r1 = requests.post(f"{base_url}/register", json={
    "email": "testuser2026@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
})
print("Register response:", r1.status_code, r1.text)

print("Testing Duplicate Registration...")
r2 = requests.post(f"{base_url}/register", json={
    "email": "testuser2026@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
})
print("Duplicate response:", r2.status_code, r2.text)

print("Testing Too Long Password...")
r3 = requests.post(f"{base_url}/register", json={
    "email": "anotheruser@example.com",
    "password": "a" * 80,
    "full_name": "Test User"
})
print("Long password response:", r3.status_code, r3.text)

print("Testing Login endpoint...")
r4 = requests.post(f"{base_url}/login", json={
    "email": "testuser2026@example.com",
    "password": "TestPassword123!"
})
print("Login response:", r4.status_code, r4.text)

if r4.status_code == 200:
    token = r4.json().get("access_token")
    print("Testing /me endpoint...")
    r5 = requests.get(f"{base_url}/me", headers={"Authorization": f"Bearer {token}"})
    print("/me response:", r5.status_code, r5.text)
