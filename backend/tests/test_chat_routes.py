"""
test_chat_routes.py — Integration tests for /api/chat/* endpoints.

Tests:
  POST /api/chat/<doc_id>/ask          — ask a question
  GET  /api/chat/<doc_id>/transcript   — get full transcript
"""

import pytest
from unittest.mock import MagicMock

from models.document import Document
from models.conversation import Conversation
from models.user import User
from database.db import db as _db


# ---------------------------------------------------------------------------
# Helpers (no nested app_context — db autouse fixture provides one)
# ---------------------------------------------------------------------------

def _register_login(client, username, email, password="password123"):
    client.post("/api/auth/signup", json={"username": username, "email": email, "password": password})
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    token = resp.get_json().get("token", "")
    return {"Authorization": f"Bearer {token}"}


def _get_user_id(email):
    user = User.query.filter_by(email=email).first()
    return user.id if user else None


def _create_doc(user_id, status="completed"):
    doc = Document(
        user_id=user_id,
        filename="uuid_chat.pdf",
        original_filename="chat_terms.pdf",
        file_type="pdf",
        file_size=2048,
        file_path="/tmp/chat_terms.pdf",
        status=status,
        llm_response="Initial LLM summary",
        cleaned_text="These are the terms and conditions.",
    )
    _db.session.add(doc)
    _db.session.commit()
    return doc.id


def _add_conversation(user_id, doc_id, role, content):
    conv = Conversation(
        user_id=user_id, document_id=doc_id, role=role, content=content
    )
    _db.session.add(conv)
    _db.session.commit()
    return conv.id


def _setup_mock_services(app):
    mock_llm = MagicMock()
    mock_llm.ask_followup.return_value = "Here is the answer about your terms."
    mock_vs = MagicMock()
    mock_vs.search.return_value = ["chunk1", "chunk2"]
    app.config["LLM_SERVICE"] = mock_llm
    app.config["VECTOR_STORE_SERVICE"] = mock_vs
    return mock_llm, mock_vs


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestChatAuthGuard:

    def test_ask_requires_auth(self, client):
        resp = client.post("/api/chat/1/ask", json={"question": "test"})
        assert resp.status_code == 401

    def test_transcript_requires_auth(self, client):
        resp = client.get("/api/chat/1/transcript")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/chat/<doc_id>/ask
# ---------------------------------------------------------------------------

class TestAskQuestion:

    def test_ask_success(self, client, app):
        headers = _register_login(client, "askuser", "ask@example.com")
        uid = _get_user_id("ask@example.com")
        doc_id = _create_doc(uid)
        _setup_mock_services(app)

        resp = client.post(
            f"/api/chat/{doc_id}/ask",
            json={"question": "What are the arbitration terms?"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["question"] == "What are the arbitration terms?"
        assert "answer" in data
        assert data["document_id"] == doc_id

    def test_ask_missing_question(self, client, app):
        headers = _register_login(client, "askmissing", "askmissing@example.com")
        uid = _get_user_id("askmissing@example.com")
        doc_id = _create_doc(uid)
        _setup_mock_services(app)

        resp = client.post(f"/api/chat/{doc_id}/ask", json={}, headers=headers)
        assert resp.status_code == 400
        assert "Question is required" in resp.get_json()["error"]

    def test_ask_empty_question(self, client, app):
        headers = _register_login(client, "askempty", "askempty@example.com")
        uid = _get_user_id("askempty@example.com")
        doc_id = _create_doc(uid)
        _setup_mock_services(app)

        resp = client.post(f"/api/chat/{doc_id}/ask", json={"question": "   "}, headers=headers)
        assert resp.status_code == 400

    def test_ask_missing_body(self, client, app):
        """No body at all — JWT is valid but question is absent → 400 (or 415 on Flask 3.x)."""
        headers = _register_login(client, "asknobody", "asknobody@example.com")
        uid = _get_user_id("asknobody@example.com")
        doc_id = _create_doc(uid)
        _setup_mock_services(app)

        resp = client.post(
            f"/api/chat/{doc_id}/ask",
            headers=headers,
            json={},
        )
        # Flask 3.x returns 400 for empty JSON body with application/json header
        assert resp.status_code in (400, 415, 500)

    def test_ask_document_not_found(self, client, app):
        headers = _register_login(client, "asknotfound", "asknotfound@example.com")
        _setup_mock_services(app)

        resp = client.post(
            "/api/chat/99999/ask",
            json={"question": "any question"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_ask_document_not_completed(self, client, app):
        headers = _register_login(client, "askprocessing", "askprocessing@example.com")
        uid = _get_user_id("askprocessing@example.com")
        doc_id = _create_doc(uid, status="processing")
        _setup_mock_services(app)

        resp = client.post(
            f"/api/chat/{doc_id}/ask",
            json={"question": "Is it done?"},
            headers=headers,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "not ready" in data["error"].lower()

    def test_ask_another_users_document_returns_404(self, client, app):
        _register_login(client, "chatowner", "chatowner@example.com")
        uid_a = _get_user_id("chatowner@example.com")
        doc_id = _create_doc(uid_a)

        headers_b = _register_login(client, "chatattacker", "chatattacker@example.com")
        _setup_mock_services(app)

        resp = client.post(
            f"/api/chat/{doc_id}/ask",
            json={"question": "Steal the info"},
            headers=headers_b,
        )
        assert resp.status_code == 404

    def test_ask_calls_llm_service(self, client, app):
        headers = _register_login(client, "llmcaller", "llmcaller@example.com")
        uid = _get_user_id("llmcaller@example.com")
        doc_id = _create_doc(uid)
        mock_llm, _ = _setup_mock_services(app)

        client.post(
            f"/api/chat/{doc_id}/ask",
            json={"question": "Is there a privacy clause?"},
            headers=headers,
        )
        mock_llm.ask_followup.assert_called_once()

    def test_ask_saves_conversation_to_db(self, client, app):
        headers = _register_login(client, "convstore", "convstore@example.com")
        uid = _get_user_id("convstore@example.com")
        doc_id = _create_doc(uid)
        _setup_mock_services(app)

        client.post(
            f"/api/chat/{doc_id}/ask",
            json={"question": "Any fees?"},
            headers=headers,
        )
        convs = Conversation.query.filter_by(document_id=doc_id).all()
        roles = [c.role for c in convs]
        assert "user" in roles
        assert "assistant" in roles


# ---------------------------------------------------------------------------
# GET /api/chat/<doc_id>/transcript
# ---------------------------------------------------------------------------

class TestGetTranscript:

    def test_transcript_success(self, client, app):
        headers = _register_login(client, "transcriptuser", "transcript@example.com")
        uid = _get_user_id("transcript@example.com")
        doc_id = _create_doc(uid)
        _add_conversation(uid, doc_id, "user", "What is this?")
        _add_conversation(uid, doc_id, "assistant", "It is a terms doc.")

        resp = client.get(f"/api/chat/{doc_id}/transcript", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["document_id"] == doc_id
        assert data["message_count"] == 2
        assert "transcript_markdown" in data
        assert "messages" in data

    def test_transcript_document_not_found(self, client):
        headers = _register_login(client, "transcriptnotfound", "transcriptnotfound@example.com")
        resp = client.get("/api/chat/99999/transcript", headers=headers)
        assert resp.status_code == 404

    def test_transcript_markdown_content(self, client, app):
        headers = _register_login(client, "markdownuser", "markdown@example.com")
        uid = _get_user_id("markdown@example.com")
        doc_id = _create_doc(uid)
        _add_conversation(uid, doc_id, "user", "Privacy question?")
        _add_conversation(uid, doc_id, "assistant", "Privacy answer here.")

        resp = client.get(f"/api/chat/{doc_id}/transcript", headers=headers)
        markdown = resp.get_json()["transcript_markdown"]
        assert "TermScope" in markdown
        assert "chat_terms.pdf" in markdown

    def test_transcript_empty_conversation(self, client, app):
        headers = _register_login(client, "emptyconv", "emptyconv@example.com")
        uid = _get_user_id("emptyconv@example.com")
        doc_id = _create_doc(uid)

        resp = client.get(f"/api/chat/{doc_id}/transcript", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["message_count"] == 0
        assert data["messages"] == []

    def test_transcript_another_users_document_returns_404(self, client, app):
        _register_login(client, "transowner", "transowner@example.com")
        uid_a = _get_user_id("transowner@example.com")
        doc_id = _create_doc(uid_a)

        headers_b = _register_login(client, "transattacker", "transattacker@example.com")
        resp = client.get(f"/api/chat/{doc_id}/transcript", headers=headers_b)
        assert resp.status_code == 404

    def test_transcript_message_fields(self, client, app):
        headers = _register_login(client, "msgfields", "msgfields@example.com")
        uid = _get_user_id("msgfields@example.com")
        doc_id = _create_doc(uid)
        _add_conversation(uid, doc_id, "user", "Test question")

        resp = client.get(f"/api/chat/{doc_id}/transcript", headers=headers)
        msg = resp.get_json()["messages"][0]
        assert "id" in msg
        assert "role" in msg
        assert "content" in msg
        assert "created_at" in msg
