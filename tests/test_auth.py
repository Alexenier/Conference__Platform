def test_login_success(client):
    response = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    response = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_login_wrong_email(client):
    response = client.post("/auth/login", json={
        "email": "notexist@test.com",
        "password": "admin123"
    })
    assert response.status_code == 401


def test_me_authorized(client, admin_token):
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"


def test_me_unauthorized(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_invalid_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401