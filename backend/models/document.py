"""
Document Model
Stores uploaded files, extracted/cleaned text, LLM responses, and processing status.
"""

from datetime import datetime, timezone
from database.db import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(
            "uploaded",
            "processing",
            "extracting",
            "cleaning",
            "indexing",
            "analyzing",
            "completed",
            "failed",
            name="document_status",
        ),
        default="uploaded",
        index=True,
    )
    extracted_text = db.Column(db.Text)
    cleaned_text = db.Column(db.Text)
    llm_response = db.Column(db.Text)
    error_message = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    conversations = db.relationship(
        "Conversation", backref="document", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self, include_text=False):
        """
        Serialize document to dictionary.
        Set include_text=True to include extracted/cleaned text and LLM response.
        """
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_text:
            data["extracted_text"] = self.extracted_text
            data["cleaned_text"] = self.cleaned_text
            data["llm_response"] = self.llm_response
        return data

    def __repr__(self):
        return f"<Document {self.original_filename} [{self.status}]>"
