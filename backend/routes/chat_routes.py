"""
Chat Routes
POST /api/chat/<doc_id>/ask         — Ask a follow-up question
GET  /api/chat/<doc_id>/transcript  — Get full conversation transcript
"""

from flask import Blueprint, request, jsonify, current_app
from middleware.auth_middleware import jwt_required_custom
from middleware.rate_limit import rate_limit
from models.document import Document
from models.conversation import Conversation
from database.db import db
from utils.helpers import generate_transcript_markdown

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.route("/<int:doc_id>/ask", methods=["POST"])
@jwt_required_custom
@rate_limit()
def ask_question(current_user_id, doc_id):
    """Ask a follow-up question about a processed document."""
    data = request.get_json()
    if not data or not data.get("question", "").strip():
        return jsonify({"error": "Question is required"}), 400

    question = data["question"].strip()

    try:
        # Verify document exists and belongs to user
        doc = Document.query.filter_by(id=doc_id, user_id=current_user_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        if doc.status != "completed":
            return jsonify({
                "error": "Document is not ready for Q&A",
                "status": doc.status,
            }), 400

        # Save user question to conversation
        user_msg = Conversation(
            user_id=current_user_id,
            document_id=doc_id,
            role="user",
            content=question,
        )
        db.session.add(user_msg)
        db.session.commit()

        # Get relevant chunks from FAISS
        vector_service = current_app.config["VECTOR_STORE_SERVICE"]
        relevant_chunks = vector_service.search(doc_id, question, top_k=4)

        # Get conversation history (excluding the initial analysis)
        history = Conversation.query.filter_by(
            document_id=doc_id, user_id=current_user_id
        ).order_by(Conversation.created_at.asc()).all()

        conversation_history = [
            {"role": conv.role, "content": conv.content}
            for conv in history[:-1]  # Exclude the question we just saved
        ]

        # Get LLM response
        llm_service = current_app.config["LLM_SERVICE"]
        answer = llm_service.ask_followup(
            question=question,
            document_text=doc.cleaned_text,
            relevant_chunks=relevant_chunks,
            conversation_history=conversation_history,
        )

        # Save assistant response
        assistant_msg = Conversation(
            user_id=current_user_id,
            document_id=doc_id,
            role="assistant",
            content=answer,
        )
        db.session.add(assistant_msg)
        db.session.commit()

        return jsonify({
            "question": question,
            "answer": answer,
            "document_id": doc_id,
            "conversation_id": assistant_msg.id,
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to process question: {str(e)}"}), 500


@chat_bp.route("/<int:doc_id>/transcript", methods=["GET"])
@jwt_required_custom
def get_transcript(current_user_id, doc_id):
    """Get the full conversation transcript for a document."""
    try:
        doc = Document.query.filter_by(id=doc_id, user_id=current_user_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        conversations = Conversation.query.filter_by(
            document_id=doc_id, user_id=current_user_id
        ).order_by(Conversation.created_at.asc()).all()

        # Generate markdown transcript
        markdown = generate_transcript_markdown(doc, conversations)

        return jsonify({
            "document_id": doc_id,
            "document_name": doc.original_filename,
            "transcript_markdown": markdown,
            "messages": [conv.to_dict() for conv in conversations],
            "message_count": len(conversations),
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch transcript: {str(e)}"}), 500
