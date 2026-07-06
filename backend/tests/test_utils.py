"""
test_utils.py — Unit tests for utility functions.

Covers:
- utils/validators.py  (allowed_file, get_file_extension, validate_upload)
- utils/helpers.py     (format_timestamp, generate_transcript_markdown)
"""

import io
import pytest
from datetime import datetime, timezone

from utils.validators import allowed_file, get_file_extension, validate_upload
from utils.helpers import format_timestamp, generate_transcript_markdown


# ---------------------------------------------------------------------------
# allowed_file
# ---------------------------------------------------------------------------

class TestAllowedFile:
    EXTS = {"pdf", "png", "jpg", "jpeg"}

    def test_allowed_pdf(self):
        assert allowed_file("document.pdf", self.EXTS) is True

    def test_allowed_png(self):
        assert allowed_file("image.PNG", self.EXTS) is True  # case insensitive

    def test_disallowed_exe(self):
        assert allowed_file("malware.exe", self.EXTS) is False

    def test_disallowed_txt(self):
        assert allowed_file("readme.txt", self.EXTS) is False

    def test_no_extension(self):
        assert allowed_file("nodotfile", self.EXTS) is False

    def test_only_dot(self):
        # ".pdf" — has a dot so extension is ""
        assert allowed_file(".pdf", self.EXTS) is True

    def test_multiple_dots(self):
        assert allowed_file("my.terms.pdf", self.EXTS) is True


# ---------------------------------------------------------------------------
# get_file_extension
# ---------------------------------------------------------------------------

class TestGetFileExtension:
    def test_simple(self):
        assert get_file_extension("file.pdf") == "pdf"

    def test_uppercase(self):
        assert get_file_extension("IMAGE.PNG") == "png"

    def test_multiple_dots(self):
        assert get_file_extension("archive.tar.gz") == "gz"

    def test_no_dot(self):
        assert get_file_extension("filenodot") == ""

    def test_empty_string(self):
        assert get_file_extension("") == ""


# ---------------------------------------------------------------------------
# validate_upload
# ---------------------------------------------------------------------------

class TestValidateUpload:
    EXTS = {"pdf", "png", "jpg"}
    MAX = 5 * 1024 * 1024  # 5 MB

    def _file(self, name, content=b"hello"):
        f = io.BytesIO(content)
        f.name = name
        f.filename = name
        return f

    def test_valid_pdf(self):
        f = self._file("doc.pdf", b"a" * 100)
        ok, err = validate_upload(f, self.EXTS, self.MAX)
        assert ok is True
        assert err is None

    def test_no_file(self):
        ok, err = validate_upload(None, self.EXTS, self.MAX)
        assert ok is False
        assert "No file selected" in err

    def test_empty_filename(self):
        f = self._file("", b"data")
        f.filename = ""
        ok, err = validate_upload(f, self.EXTS, self.MAX)
        assert ok is False
        assert "No file selected" in err

    def test_disallowed_extension(self):
        f = self._file("script.js", b"alert(1)")
        ok, err = validate_upload(f, self.EXTS, self.MAX)
        assert ok is False
        assert ".js" in err or "not allowed" in err

    def test_file_too_large(self):
        big_content = b"x" * (6 * 1024 * 1024)  # 6 MB
        f = self._file("big.pdf", big_content)
        ok, err = validate_upload(f, self.EXTS, self.MAX)
        assert ok is False
        assert "too large" in err.lower()

    def test_empty_file(self):
        f = self._file("empty.pdf", b"")
        ok, err = validate_upload(f, self.EXTS, self.MAX)
        assert ok is False
        assert "empty" in err.lower()

    def test_seek_reset_after_validation(self):
        """After validate_upload the file pointer should be at position 0."""
        content = b"pdf content"
        f = self._file("doc.pdf", content)
        validate_upload(f, self.EXTS, self.MAX)
        assert f.tell() == 0


# ---------------------------------------------------------------------------
# format_timestamp
# ---------------------------------------------------------------------------

class TestFormatTimestamp:
    def test_none_returns_none(self):
        assert format_timestamp(None) is None

    def test_formats_correctly(self):
        dt = datetime(2024, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = format_timestamp(dt)
        assert result == "2024-06-15 10:30:45 UTC"

    def test_returns_string(self):
        dt = datetime.now(timezone.utc)
        assert isinstance(format_timestamp(dt), str)


# ---------------------------------------------------------------------------
# generate_transcript_markdown
# ---------------------------------------------------------------------------

class TestGenerateTranscriptMarkdown:

    class _FakeDocument:
        def __init__(self):
            self.original_filename = "terms.pdf"
            self.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            self.updated_at = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
            self.status = "completed"
            self.llm_response = "These terms include arbitration clauses."

    class _FakeConv:
        def __init__(self, role, content):
            self.role = role
            self.content = content
            self.created_at = datetime(2024, 1, 1, 12, 10, 0, tzinfo=timezone.utc)

    def test_header_present(self):
        doc = self._FakeDocument()
        md = generate_transcript_markdown(doc, [])
        assert "TermScope" in md
        assert "terms.pdf" in md

    def test_status_in_output(self):
        doc = self._FakeDocument()
        md = generate_transcript_markdown(doc, [])
        assert "completed" in md

    def test_initial_analysis_present(self):
        doc = self._FakeDocument()
        md = generate_transcript_markdown(doc, [])
        assert "Initial Analysis" in md
        assert "arbitration clauses" in md

    def test_no_analysis_when_none(self):
        doc = self._FakeDocument()
        doc.llm_response = None
        md = generate_transcript_markdown(doc, [])
        assert "Initial Analysis" not in md

    def test_conversations_present(self):
        doc = self._FakeDocument()
        convs = [
            self._FakeConv("user", "What is arbitration?"),
            self._FakeConv("assistant", "Arbitration is a dispute resolution method."),
        ]
        md = generate_transcript_markdown(doc, convs)
        assert "Follow-up Q&A" in md
        assert "What is arbitration?" in md
        assert "dispute resolution" in md

    def test_empty_conversations(self):
        doc = self._FakeDocument()
        md = generate_transcript_markdown(doc, [])
        assert "Follow-up Q&A" not in md

    def test_returns_string(self):
        doc = self._FakeDocument()
        result = generate_transcript_markdown(doc, [])
        assert isinstance(result, str)
