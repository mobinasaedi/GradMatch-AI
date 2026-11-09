def test_register_and_session_cookie(client):
    response = client.post("/api/auth/register", json={"email": "new-user@example.com", "password": "a-long-test-password-123"})
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "new-user@example.com"
    assert "gradmatch_session" in response.cookies
    assert "gradmatch_csrf" in response.cookies


def test_duplicate_registration_rejected(client):
    payload = {"email": "duplicate@example.com", "password": "a-long-test-password-123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_login_rejects_wrong_password(client):
    client.post("/api/auth/register", json={"email": "login@example.com", "password": "a-long-test-password-123"})
    response = client.post("/api/auth/login", json={"email": "login@example.com", "password": "wrong-password"})
    assert response.status_code == 401


def test_forgot_password_does_not_reveal_account_existence(client):
    a = client.post("/api/auth/forgot-password", json={"email": "known@example.com"})
    b = client.post("/api/auth/forgot-password", json={"email": "unknown@example.com"})
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()
