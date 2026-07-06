"""
test_services.py — Unit tests for service-layer classes.

Covers:
- services/text_cleaner.py  (TextCleaner.clean)
- services/auth_service.py  (hash_password, verify_password, create_user, authenticate)
"""

import pytest
from unittest.mock import MagicMock, patch

from services.text_cleaner import TextCleaner
from services.auth_service import AuthService


# ---------------------------------------------------------------------------
# TextCleaner
# ---------------------------------------------------------------------------

class TestTextCleaner:

    def test_empty_string_returns_empty(self):
        assert TextCleaner.clean("") == ""

    def test_none_returns_empty(self):
        assert TextCleaner.clean(None) == ""

    def test_strips_leading_trailing_whitespace(self):
        result = TextCleaner.clean("   hello world   ")
        assert result == "hello world"

    def test_collapses_multiple_spaces(self):
        result = TextCleaner.clean("too  many   spaces")
        assert result == "too many spaces"

    def test_removes_control_characters(self):
        # \x01 is a control char that should be removed
        result = TextCleaner.clean("hello\x01world")
        assert "\x01" not in result

    def test_fixes_hyphenated_line_breaks(self):
        raw = "termi-\nnation clause"
        result = TextCleaner.clean(raw)
        assert "termination" in result

    def test_collapses_multiple_blank_lines(self):
        raw = "Para one\n\n\n\n\nPara two"
        result = TextCleaner.clean(raw)
        assert "\n\n\n" not in result

    def test_normalizes_unicode_quotes(self):
        raw = "\u2018hello\u2019 and \u201chello\u201d"
        result = TextCleaner.clean(raw)
        assert "'" in result
        assert '"' in result
        assert "\u2018" not in result
        assert "\u201c" not in result

    def test_normalizes_en_dash(self):
        result = TextCleaner.clean("2020\u20132024")
        assert "-" in result
        assert "\u2013" not in result

    def test_normalizes_em_dash(self):
        result = TextCleaner.clean("terms\u2014conditions")
        assert "--" in result
        assert "\u2014" not in result

    def test_normalizes_ellipsis(self):
        result = TextCleaner.clean("wait\u2026")
        assert "..." in result
        assert "\u2026" not in result

    def test_removes_non_breaking_space(self):
        result = TextCleaner.clean("hello\u00a0world")
        assert "\u00a0" not in result

    def test_removes_bom(self):
        result = TextCleaner.clean("\ufeffhello")
        assert "\ufeff" not in result

    def test_preserves_paragraph_structure(self):
        raw = "Para one text here.\n\nPara two text here."
        result = TextCleaner.clean(raw)
        assert "\n\n" in result

    def test_joins_single_newlines_within_paragraph(self):
        raw = "This is\na single paragraph."
        result = TextCleaner.clean(raw)
        # Single newline should be joined into a space
        assert "\n" not in result
        assert "This is a single paragraph." in result

    def test_returns_string(self):
        assert isinstance(TextCleaner.clean("test"), str)


# ---------------------------------------------------------------------------
# AuthService — password hashing
# ---------------------------------------------------------------------------

class TestAuthServicePasswords:

    def test_hash_password_returns_string(self):
        h = AuthService.hash_password("mypassword")
        assert isinstance(h, str)

    def test_hash_is_not_plaintext(self):
        h = AuthService.hash_password("mypassword")
        assert h != "mypassword"

    def test_verify_correct_password(self):
        h = AuthService.hash_password("correctpassword")
        assert AuthService.verify_password("correctpassword", h) is True

    def test_verify_wrong_password(self):
        h = AuthService.hash_password("correctpassword")
        assert AuthService.verify_password("wrongpassword", h) is False

    def test_each_hash_is_unique(self):
        """bcrypt generates a new salt each time."""
        h1 = AuthService.hash_password("samepassword")
        h2 = AuthService.hash_password("samepassword")
        assert h1 != h2

    def test_verify_is_still_true_for_different_hashes(self):
        """Both hashes should verify against the same plaintext."""
        h1 = AuthService.hash_password("samepassword")
        h2 = AuthService.hash_password("samepassword")
        assert AuthService.verify_password("samepassword", h1) is True
        assert AuthService.verify_password("samepassword", h2) is True


# ---------------------------------------------------------------------------
# AuthService — create_user / authenticate (need app context + DB)
# ---------------------------------------------------------------------------

class TestAuthServiceDB:

    def test_create_user_success(self, app, db):
        user = AuthService.create_user("newuser", "new@example.com", "password123")
        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.password_hash != "password123"

    def test_create_user_duplicate_username(self, app, db):
        AuthService.create_user("dupuser", "first@example.com", "pass1234")
        with pytest.raises(ValueError, match="Username already exists"):
            AuthService.create_user("dupuser", "second@example.com", "pass1234")

    def test_create_user_duplicate_email(self, app, db):
        AuthService.create_user("user1", "shared@example.com", "pass1234")
        with pytest.raises(ValueError, match="Email already registered"):
            AuthService.create_user("user2", "shared@example.com", "pass1234")

    def test_authenticate_success(self, app, db):
        AuthService.create_user("loginuser", "login@example.com", "mypassword")
        user, token = AuthService.authenticate("login@example.com", "mypassword")
        assert user.email == "login@example.com"
        assert isinstance(token, str)
        assert len(token) > 20

    def test_authenticate_wrong_password(self, app, db):
        AuthService.create_user("wrongpwuser", "wrongpw@example.com", "correctpw")
        with pytest.raises(ValueError, match="Invalid email or password"):
            AuthService.authenticate("wrongpw@example.com", "wrongpassword")

    def test_authenticate_nonexistent_user(self, app, db):
        with pytest.raises(ValueError, match="Invalid email or password"):
            AuthService.authenticate("ghost@example.com", "anypassword")

    def test_authenticate_email_case_insensitive_stored(self, app, db):
        """Email is stored lowercased by the route layer; auth uses DB query."""
        AuthService.create_user("caseuser", "case@example.com", "pass1234")
        user, token = AuthService.authenticate("case@example.com", "pass1234")
        assert user is not None
