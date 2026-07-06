"""
test_document_routes.py — Integration tests for /api/documents/* endpoints.

Tests:
  GET    /api/documents              — list documents
  GET    /api/documents/<id>         — get document
  GET    /api/documents/<id>/status  — get processing status
  DELETE /api/documents/<id>         — delete document
  POST   /api/documents/upload       — upload (mocked processing)
"""

import io
import pytest
from unittest.mock import MagicMock

from models.document import Document
from models.user import User
from database.db import db as _db
from services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers (no extra app_context — the db fixture already pushes one)
# ---------------------------------------------------------------------------

def _register_login(client, username, email, password="password123"):
    """Register + login a user and return auth headers."""
    client.post("/api/auth/signup", json={
        "username": username, "email": email, "password": password,
    })
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    token = resp.get_json().get("token", "")
    return {"Authorization": f"Bearer {token}"}


def _get_user_id(email):
    """Fetch user ID from DB (within the current app context)."""
    user = User.query.filter_by(email=email).first()
    return user.id if user else None


def _create_doc(user_id, status="completed"):
    """Create a document in the DB (within the current app context)."""
    doc = Document(
        user_id=user_id,
        filename="uuid_test.pdf",
        original_filename="terms.pdf",
        file_type="pdf",
        file_size=1024,
        file_path="/tmp/terms.pdf",
        status=status,
        llm_response="Summary of terms",
        cleaned_text="Some cleaned text",
    )
    _db.session.add(doc)
    _db.session.commit()
    return doc.id


# ---------------------------------------------------------------------------
# Authentication guard tests
# ---------------------------------------------------------------------------

class TestDocumentAuthGuard:

    def test_list_requires_auth(self, client):
        resp = client.get("/api/documents")
        assert resp.status_code == 401

    def test_get_requires_auth(self, client):
        resp = client.get("/api/documents/1")
        assert resp.status_code == 401

    def test_status_requires_auth(self, client):
        resp = client.get("/api/documents/1/status")
        assert resp.status_code == 401

    def test_delete_requires_auth(self, client):
        resp = client.delete("/api/documents/1")
        assert resp.status_code == 401

    def test_upload_requires_auth(self, client):
        resp = client.post("/api/documents/upload")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/documents
# ---------------------------------------------------------------------------

class TestListDocuments:

    def test_list_returns_empty_for_new_user(self, client):
        headers = _register_login(client, "listuser", "list@example.com")
        resp = client.get("/api/documents", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["documents"] == []
        assert data["count"] == 0

    def test_list_returns_users_documents(self, client):
        headers = _register_login(client, "listuser2", "list2@example.com")
        uid = _get_user_id("list2@example.com")
        _create_doc(uid)
        _create_doc(uid)
        resp = client.get("/api/documents", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 2

    def test_list_does_not_return_other_users_documents(self, client):
        # User A
        _register_login(client, "userA", "usera@example.com")
        uid_a = _get_user_id("usera@example.com")
        _create_doc(uid_a)

        # User B sees zero docs
        headers_b = _register_login(client, "userB", "userb@example.com")
        resp = client.get("/api/documents", headers=headers_b)
        assert resp.get_json()["count"] == 0

    def test_list_document_fields(self, client):
        headers = _register_login(client, "fielduser", "fields@example.com")
        uid = _get_user_id("fields@example.com")
        _create_doc(uid)
        resp = client.get("/api/documents", headers=headers)
        doc = resp.get_json()["documents"][0]
        for field in ("id", "filename", "file_type", "file_size", "status", "created_at"):
            assert field in doc


# ---------------------------------------------------------------------------
# GET /api/documents/<id>
# ---------------------------------------------------------------------------

class TestGetDocument:

    def test_get_existing_document(self, client):
        headers = _register_login(client, "getdocuser", "getdoc@example.com")
        uid = _get_user_id("getdoc@example.com")
        doc_id = _create_doc(uid)
        resp = client.get(f"/api/documents/{doc_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["document"]["id"] == doc_id

    def test_get_returns_text_fields(self, client):
        headers = _register_login(client, "textfielduser", "textfield@example.com")
        uid = _get_user_id("textfield@example.com")
        doc_id = _create_doc(uid)
        resp = client.get(f"/api/documents/{doc_id}", headers=headers)
        doc = resp.get_json()["document"]
        assert "llm_response" in doc
        assert "cleaned_text" in doc

    def test_get_nonexistent_document(self, client):
        headers = _register_login(client, "getmissinguser", "getmissing@example.com")
        resp = client.get("/api/documents/99999", headers=headers)
        assert resp.status_code == 404

    def test_get_another_users_document_returns_404(self, client):
        _register_login(client, "owneruser", "owner@example.com")
        uid_a = _get_user_id("owner@example.com")
        doc_id = _create_doc(uid_a)

        headers_b = _register_login(client, "thiefuser", "thief@example.com")
        resp = client.get(f"/api/documents/{doc_id}", headers=headers_b)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/documents/<id>/status
# ---------------------------------------------------------------------------

class TestGetDocumentStatus:

    def test_get_status_existing(self, client):
        headers = _register_login(client, "statususer", "status@example.com")
        uid = _get_user_id("status@example.com")
        doc_id = _create_doc(uid, status="processing")
        resp = client.get(f"/api/documents/{doc_id}/status", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "processing"
        assert data["document_id"] == doc_id

    def test_get_status_nonexistent(self, client):
        headers = _register_login(client, "statusmissing", "statusmissing@example.com")
        resp = client.get("/api/documents/99999/status", headers=headers)
        assert resp.status_code == 404

    def test_get_status_response_fields(self, client):
        headers = _register_login(client, "statusfields", "statusfields@example.com")
        uid = _get_user_id("statusfields@example.com")
        doc_id = _create_doc(uid)
        resp = client.get(f"/api/documents/{doc_id}/status", headers=headers)
        data = resp.get_json()
        assert "document_id" in data
        assert "status" in data
        assert "error_message" in data


# ---------------------------------------------------------------------------
# DELETE /api/documents/<id>
# ---------------------------------------------------------------------------

class TestDeleteDocument:

    def test_delete_existing_document(self, client, app):
        headers = _register_login(client, "deleteuser", "delete@example.com")
        uid = _get_user_id("delete@example.com")
        doc_id = _create_doc(uid)

        mock_svc = MagicMock()
        app.config["DOCUMENT_SERVICE"] = mock_svc

        resp = client.delete(f"/api/documents/{doc_id}", headers=headers)
        assert resp.status_code == 200
        assert "deleted" in resp.get_json()["message"].lower()
        mock_svc.delete_document.assert_called_once_with(doc_id, uid)

    def test_delete_nonexistent_document(self, client, app):
        headers = _register_login(client, "delnotfound", "delnotfound@example.com")
        mock_svc = MagicMock()
        mock_svc.delete_document.side_effect = ValueError("Document not found")
        app.config["DOCUMENT_SERVICE"] = mock_svc

        resp = client.delete("/api/documents/99999", headers=headers)
        assert resp.status_code == 404

    def test_delete_another_users_document_raises_404(self, client, app):
        _register_login(client, "ownerDel", "ownerdel@example.com")
        uid_a = _get_user_id("ownerdel@example.com")
        doc_id = _create_doc(uid_a)

        headers_b = _register_login(client, "attackerDel", "attackerdel@example.com")

        mock_svc = MagicMock()
        mock_svc.delete_document.side_effect = ValueError("Document not found")
        app.config["DOCUMENT_SERVICE"] = mock_svc

        resp = client.delete(f"/api/documents/{doc_id}", headers=headers_b)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/documents/upload
# ---------------------------------------------------------------------------

class TestUploadDocument:

    def _upload(self, client, headers, filename, content, content_type="application/pdf"):
        data = {"file": (io.BytesIO(content), filename, content_type)}
        return client.post(
            "/api/documents/upload",
            data=data,
            content_type="multipart/form-data",
            headers=headers,
        )

    def test_upload_pdf_success(self, client, app):
        headers = _register_login(client, "uploader", "upload@example.com")
        mock_svc = MagicMock()
        mock_svc.process_document_async = MagicMock()
        app.config["DOCUMENT_SERVICE"] = mock_svc

        resp = self._upload(client, headers, "terms.pdf", b"PDF content here" * 10)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "document" in data
        assert data["document"]["status"] == "uploaded"

    def test_upload_no_file_part(self, client):
        headers = _register_login(client, "nofileuser", "nofile@example.com")
        resp = client.post(
            "/api/documents/upload",
            data={},
            content_type="multipart/form-data",
            headers=headers,
        )
        assert resp.status_code == 400

    def test_upload_disallowed_extension(self, client):
        headers = _register_login(client, "badextuser", "badext@example.com")
        resp = self._upload(client, headers, "malware.exe", b"malicious", "application/octet-stream")
        assert resp.status_code == 400

    def test_upload_empty_file(self, client):
        headers = _register_login(client, "emptyfileuser", "emptyfile@example.com")
        resp = self._upload(client, headers, "empty.pdf", b"", "application/pdf")
        assert resp.status_code == 400
