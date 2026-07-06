"""
test_auth_routes.py — Integration tests for /api/auth/* endpoints.

Tests:
  POST /api/auth/signup
  POST /api/auth/login
  POST /api/auth/logout
"""

import pytest


# ---------------------------------------------------------------------------
# /api/auth/signup
# ---------------------------------------------------------------------------

class TestSignup:

    def test_signup_success(self, client):
        resp = client.post("/api/auth/signup", json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "securepass",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["message"] == "Account created successfully"
        assert data["user"]["username"] == "alice"
        assert data["user"]["email"] == "alice@example.com"
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]

    def test_signup_missing_body(self, client):
        resp = client.post("/api/auth/signup")
        # Flask 3.x returns 415 when Content-Type header is missing
        assert resp.status_code in (400, 415)

    def test_signup_username_too_short(self, client):
        resp = client.post("/api/auth/signup", json={
            "username": "ab",
            "email": "ab@example.com",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert "details" in resp.get_json()

    def test_signup_invalid_email(self, client):
        resp = client.post("/api/auth/signup", json={
            "username": "validuser",
            "email": "notanemail",
            "password": "password123",
        })
        assert resp.status_code == 400

    def test_signup_password_too_short(self, client):
        resp = client.post("/api/auth/signup", json={
            "username": "validuser",
            "email": "valid@example.com",
            "password": "abc",
        })
        assert resp.status_code == 400

    def test_signup_multiple_validation_errors(self, client):
        resp = client.post("/api/auth/signup", json={
            "username": "x",
            "email": "bademail",
            "password": "123",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert len(data["details"]) >= 3

    def test_signup_duplicate_username(self, client):
        client.post("/api/auth/signup", json={
            "username": "dupuser", "email": "dup1@example.com", "password": "pass1234",
        })
        resp = client.post("/api/auth/signup", json={
            "username": "dupuser", "email": "dup2@example.com", "password": "pass1234",
        })
        assert resp.status_code == 409

    def test_signup_duplicate_email(self, client):
        client.post("/api/auth/signup", json={
            "username": "user1", "email": "shared@example.com", "password": "pass1234",
        })
        resp = client.post("/api/auth/signup", json={
            "username": "user2", "email": "shared@example.com", "password": "pass1234",
        })
        assert resp.status_code == 409

    def test_signup_email_normalized_to_lowercase(self, client):
        resp = client.post("/api/auth/signup", json={
            "username": "casetest",
            "email": "CASE@EXAMPLE.COM",
            "password": "password123",
        })
        assert resp.status_code == 201
        assert resp.get_json()["user"]["email"] == "case@example.com"


# ---------------------------------------------------------------------------
# /api/auth/login
# ---------------------------------------------------------------------------

class TestLogin:

    def _register(self, client, username="logintest", email="login@example.com", password="password123"):
        client.post("/api/auth/signup", json={
            "username": username, "email": email, "password": password,
        })

    def test_login_success(self, client):
        self._register(client)
        resp = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert data["token"]
        assert data["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, client):
        self._register(client)
        resp = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_login_missing_email(self, client):
        resp = client.post("/api/auth/login", json={"password": "password123"})
        assert resp.status_code == 400

    def test_login_missing_password(self, client):
        self._register(client)
        resp = client.post("/api/auth/login", json={"email": "login@example.com"})
        assert resp.status_code == 400

    def test_login_missing_body(self, client):
        resp = client.post("/api/auth/login")
        # Flask 3.x returns 415 when Content-Type header is missing
        assert resp.status_code in (400, 415)

    def test_login_returns_user_dict(self, client):
        self._register(client)
        resp = client.post("/api/auth/login", json={
            "email": "login@example.com", "password": "password123",
        })
        user = resp.get_json()["user"]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "password_hash" not in user


# ---------------------------------------------------------------------------
# /api/auth/logout
# ---------------------------------------------------------------------------

class TestLogout:

    def test_logout_without_token(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401

    def test_logout_with_invalid_token(self, client):
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 401
