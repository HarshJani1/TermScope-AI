"""
test_models.py — Unit tests for SQLAlchemy models.

Covers:
  - User.to_dict()
  - Document.to_dict() / Document.to_dict(include_text=True)
  - Conversation.to_dict()
  - Model __repr__ methods
"""

import pytest
from database.db import db as _db
from models.user import User
from models.document import Document
from models.conversation import Conversation
from services.auth_service import AuthService


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------

class TestUserModel:

    def _make_user(self):
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=AuthService.hash_password("password"),
        )
        _db.session.add(user)
        _db.session.commit()
        return user.id

    def test_to_dict_excludes_password(self, app, db):
        uid = self._make_user()
        user = _db.session.get(User, uid)
        d = user.to_dict()
        assert "password" not in d
        assert "password_hash" not in d

    def test_to_dict_contains_expected_fields(self, app, db):
        uid = self._make_user()
        user = _db.session.get(User, uid)
        d = user.to_dict()
        for key in ("id", "username", "email", "created_at", "updated_at"):
            assert key in d

    def test_to_dict_email_value(self, app, db):
        uid = self._make_user()
        user = _db.session.get(User, uid)
        assert user.to_dict()["email"] == "test@example.com"

    def test_repr(self, app, db):
        uid = self._make_user()
        user = _db.session.get(User, uid)
        assert "testuser" in repr(user)


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

class TestDocumentModel:

    def _make_user_and_doc(self):
        user = User(
            username="docmodel",
            email="docmodel@example.com",
            password_hash=AuthService.hash_password("password"),
        )
        _db.session.add(user)
        _db.session.flush()

        doc = Document(
            user_id=user.id,
            filename="uuid.pdf",
            original_filename="original.pdf",
            file_type="pdf",
            file_size=2048,
            file_path="/tmp/original.pdf",
            status="completed",
            extracted_text="Raw extracted text",
            cleaned_text="Cleaned text",
            llm_response="LLM analysis",
        )
        _db.session.add(doc)
        _db.session.commit()
        return doc.id

    def test_to_dict_default_excludes_text(self, app, db):
        doc_id = self._make_user_and_doc()
        doc = _db.session.get(Document, doc_id)
        d = doc.to_dict()
        assert "extracted_text" not in d
        assert "cleaned_text" not in d
        assert "llm_response" not in d

    def test_to_dict_include_text_true(self, app, db):
        doc_id = self._make_user_and_doc()
        doc = _db.session.get(Document, doc_id)
        d = doc.to_dict(include_text=True)
        assert d["extracted_text"] == "Raw extracted text"
        assert d["cleaned_text"] == "Cleaned text"
        assert d["llm_response"] == "LLM analysis"

    def test_to_dict_contains_expected_fields(self, app, db):
        doc_id = self._make_user_and_doc()
        doc = _db.session.get(Document, doc_id)
        d = doc.to_dict()
        for key in ("id", "user_id", "filename", "file_type", "file_size", "status", "created_at"):
            assert key in d

    def test_to_dict_shows_original_filename(self, app, db):
        doc_id = self._make_user_and_doc()
        doc = _db.session.get(Document, doc_id)
        # filename in to_dict should reflect the original_filename field
        assert doc.to_dict()["filename"] == "original.pdf"

    def test_repr(self, app, db):
        doc_id = self._make_user_and_doc()
        doc = _db.session.get(Document, doc_id)
        r = repr(doc)
        assert "original.pdf" in r
        assert "completed" in r


# ---------------------------------------------------------------------------
# Conversation model
# ---------------------------------------------------------------------------

class TestConversationModel:

    def _make_full_chain(self):
        user = User(
            username="convmodel",
            email="convmodel@example.com",
            password_hash=AuthService.hash_password("password"),
        )
        _db.session.add(user)
        _db.session.flush()

        doc = Document(
            user_id=user.id,
            filename="conv_uuid.pdf",
            original_filename="conv_terms.pdf",
            file_type="pdf",
            file_size=512,
            file_path="/tmp/conv.pdf",
            status="completed",
        )
        _db.session.add(doc)
        _db.session.flush()

        conv = Conversation(
            user_id=user.id,
            document_id=doc.id,
            role="user",
            content="What are the key terms?",
        )
        _db.session.add(conv)
        _db.session.commit()
        return conv.id

    def test_to_dict_contains_expected_fields(self, app, db):
        conv_id = self._make_full_chain()
        conv = _db.session.get(Conversation, conv_id)
        d = conv.to_dict()
        for key in ("id", "document_id", "role", "content", "created_at"):
            assert key in d

    def test_to_dict_content_value(self, app, db):
        conv_id = self._make_full_chain()
        conv = _db.session.get(Conversation, conv_id)
        assert conv.to_dict()["content"] == "What are the key terms?"

    def test_to_dict_role_value(self, app, db):
        conv_id = self._make_full_chain()
        conv = _db.session.get(Conversation, conv_id)
        assert conv.to_dict()["role"] == "user"

    def test_repr(self, app, db):
        conv_id = self._make_full_chain()
        conv = _db.session.get(Conversation, conv_id)
        r = repr(conv)
        assert "user" in r


# ---------------------------------------------------------------------------
# Health check endpoint (smoke test)
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert "TermScope" in data["service"]

    def test_404_endpoint(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_405_method_not_allowed(self, client):
        resp = client.post("/api/health")
        assert resp.status_code == 405
