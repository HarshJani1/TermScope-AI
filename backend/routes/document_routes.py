"""
Document Routes
POST   /api/documents/upload      — Upload a document
GET    /api/documents              — List user's documents
GET    /api/documents/<id>         — Get document details
GET    /api/documents/<id>/status  — Get processing status
DELETE /api/documents/<id>         — Delete a document
"""

import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from middleware.auth_middleware import jwt_required_custom
from middleware.rate_limit import rate_limit
from models.document import Document
from database.db import db
from utils.validators import validate_upload, get_file_extension

document_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


@document_bp.route("/upload", methods=["POST"])
@jwt_required_custom
@rate_limit(capacity=3, refill_rate=0.0167)  # burst of 3, 1 refill per minute
def upload_document(current_user_id):
    """Upload an image or PDF file for processing."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # Validate the file
    is_valid, error_msg = validate_upload(
        file,
        current_app.config["ALLOWED_EXTENSIONS"],
        current_app.config["MAX_CONTENT_LENGTH"],
    )
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    try:
        # Generate unique filename
        original_filename = file.filename
        ext = get_file_extension(original_filename)
        unique_filename = f"{uuid.uuid4().hex}.{ext}"

        # Ensure upload directory exists
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(upload_dir, unique_filename)
        file.seek(0)
        file.save(file_path)
        file_size = os.path.getsize(file_path)

        # Create document record
        doc = Document(
            user_id=current_user_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_type=ext,
            file_size=file_size,
            file_path=file_path,
            status="uploaded",
        )
        db.session.add(doc)
        db.session.commit()

        # Start async processing
        from services.document_service import DocumentService
        doc_service = current_app.config["DOCUMENT_SERVICE"]
        doc_service.process_document_async(doc.id)

        return jsonify({
            "message": "File uploaded successfully. Processing started.",
            "document": doc.to_dict(),
        }), 201

    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@document_bp.route("", methods=["GET"])
@jwt_required_custom
def list_documents(current_user_id):
    """List all documents for the authenticated user."""
    try:
        docs = Document.query.filter_by(user_id=current_user_id)\
            .order_by(Document.created_at.desc()).all()
        return jsonify({
            "documents": [doc.to_dict() for doc in docs],
            "count": len(docs),
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch documents: {str(e)}"}), 500


@document_bp.route("/<int:doc_id>", methods=["GET"])
@jwt_required_custom
def get_document(current_user_id, doc_id):
    """Get full document details including extracted text and LLM response."""
    try:
        doc = Document.query.filter_by(id=doc_id, user_id=current_user_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        return jsonify({"document": doc.to_dict(include_text=True)}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch document: {str(e)}"}), 500


@document_bp.route("/<int:doc_id>/status", methods=["GET"])
@jwt_required_custom
def get_status(current_user_id, doc_id):
    """Get the processing status of a document."""
    try:
        doc = Document.query.filter_by(id=doc_id, user_id=current_user_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        return jsonify({
            "document_id": doc.id,
            "status": doc.status,
            "error_message": doc.error_message,
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch status: {str(e)}"}), 500


@document_bp.route("/<int:doc_id>", methods=["DELETE"])
@jwt_required_custom
def delete_document(current_user_id, doc_id):
    """Delete a document and all associated data."""
    try:
        doc_service = current_app.config["DOCUMENT_SERVICE"]
        doc_service.delete_document(doc_id, current_user_id)
        return jsonify({"message": "Document deleted successfully"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500
