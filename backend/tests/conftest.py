"""
conftest.py — Shared pytest fixtures for TermScope backend tests.

Strategy:
  - The `app` fixture (session-scoped) creates the Flask app and keeps ONE
    persistent app context open for the entire test session. This means all
    DB writes from both test helpers AND the Flask test client share the same
    SQLAlchemy session factory.
  - The `db` fixture (function-scoped, autouse) truncates all tables after
    each test for isolation.
  - The `client` fixture wraps the test client so requests stay in the same
    application context.
"""

import io
import os
import pytest

# Force FLASK_ENV to testing so create_app() uses TestingConfig from the start
os.environ["FLASK_ENV"] = "testing"

from app import create_app
from database.db import db as _db
from models.user import User
from models.document import Document
from models.conversation import Conversation
from services.auth_service import AuthService


# ---------------------------------------------------------------------------
# App + DB
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """
    Create a Flask application configured for testing.

    A single app context is pushed for the entire session so that test helpers
    and the Flask test client share the same SQLAlchemy session/connection.
    """
    test_config = {
        "TESTING": True,
        # File-based SQLite is needed because in-memory SQLite creates a
        # separate database per connection, which breaks cross-context queries.
        "SQLALCHEMY_DATABASE_URI": "sqlite:////tmp/termscope_test.db",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JWT_SECRET_KEY": "test-jwt-secret",
        "SECRET_KEY": "test-secret",
        "UPLOAD_FOLDER": "/tmp/termscope_test_uploads",
        "VECTOR_STORE_DIR": "/tmp/termscope_test_vectors",
        "GROQ_API_KEY": "test-groq-key",
        "LLM_MODEL": "test-model",
        "LLM_MAX_TOKENS": 100,
        "LLM_TEMPERATURE": 0.3,
        "EMBEDDING_MODEL": "all-MiniLM-L6-v2",
        "CHUNK_SIZE": 500,
        "CHUNK_OVERLAP": 50,
        "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,
        "ALLOWED_EXTENSIONS": {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "webp", "pdf"},
        "ALLOWED_IMAGE_EXTENSIONS": {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "webp"},
        "ALLOWED_PDF_EXTENSIONS": {"pdf"},
    }

    flask_app = create_app()
    flask_app.config.update(test_config)

    # Push ONE app context that lives for the entire test session.
    ctx = flask_app.app_context()
    ctx.push()

    _db.drop_all()    # Clean slate
    _db.create_all()

    yield flask_app

    _db.drop_all()
    ctx.pop()


@pytest.fixture(scope="function", autouse=True)
def db(app):
    """
    Push a fresh app context for each test so that both the Flask test
    client requests and test-helper DB operations share the same
    SQLAlchemy session on the file-based SQLite database.
    The context is popped and all tables are cleaned after every test.
    """
    with app.app_context():
        _db.session.remove()
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        _db.session.remove()


@pytest.fixture(scope="function")
def client(app):
    """Flask test client that reuses the same app context."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

@pytest.fixture
def make_user(db):
    """Factory to create and persist a User."""
    def _make(username="testuser", email="test@example.com", password="password123"):
        user = User(
            username=username,
            email=email,
            password_hash=AuthService.hash_password(password),
        )
        db.session.add(user)
        db.session.commit()
        return user.id, user.username, user.email
    return _make


@pytest.fixture
def make_document(db):
    """Factory to create and persist a Document."""
    def _make(
        user_id,
        original_filename="terms.pdf",
        file_type="pdf",
        status="completed",
        llm_response="Test analysis",
        cleaned_text="Test terms content",
    ):
        doc = Document(
            user_id=user_id,
            filename=f"uuid_{original_filename}",
            original_filename=original_filename,
            file_type=file_type,
            file_size=1024,
            file_path=f"/tmp/{original_filename}",
            status=status,
            llm_response=llm_response,
            cleaned_text=cleaned_text,
        )
        db.session.add(doc)
        db.session.commit()
        return doc.id
    return _make


@pytest.fixture
def auth_headers(app, client, make_user):
    """
    Register a user and return valid JWT Authorization headers.
    Returns (headers_dict, user_id).
    """
    user_id, username, email = make_user(
        username="authuser", email="auth@example.com", password="securepassword"
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "auth@example.com", "password": "securepassword"},
    )
    token = resp.get_json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id


@pytest.fixture
def pdf_file():
    data = b"%PDF-1.4 fake pdf content for testing" * 20
    return io.BytesIO(data)


@pytest.fixture
def image_file():
    data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return io.BytesIO(data)
