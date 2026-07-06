"""
Document Service
Orchestrates the full document processing pipeline:
Upload → Extract → Clean → Index (FAISS) → Analyze (LLM)
"""

import os
import logging
import threading

from database.db import db
from models.document import Document
from models.conversation import Conversation
from services.ocr_service import OCRService
from services.pdf_service import PDFService
from services.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class DocumentService:
    """Orchestrates document processing with background thread execution."""

    def __init__(self, app, llm_service, vector_store_service):
        self.app = app
        self.llm_service = llm_service
        self.vector_store_service = vector_store_service

    def _update_status(self, document_id, status, **kwargs):
        """Update document status and optional fields in the database."""
        doc = db.session.get(Document, document_id)
        if doc:
            doc.status = status
            for key, value in kwargs.items():
                setattr(doc, key, value)
            db.session.commit()

    def process_document_async(self, document_id):
        """Launch document processing in a background thread."""
        thread = threading.Thread(
            target=self._process_pipeline,
            args=(document_id,),
            daemon=True,
        )
        thread.start()

    def _process_pipeline(self, document_id):
        """
        Full processing pipeline (runs in background thread).
        Steps: Extract → Clean → Index in FAISS → Analyze with LLM
        """
        with self.app.app_context():
            try:
                doc = db.session.get(Document, document_id)
                if not doc:
                    logger.error(f"Document {document_id} not found")
                    return

                logger.info(f"Starting pipeline for document {document_id}: {doc.original_filename}")

                # --- Step 1: Extract text ---
                self._update_status(document_id, "extracting")
                file_ext = doc.file_type.lower()

                if file_ext in ("png", "jpg", "jpeg", "tiff", "bmp", "gif", "webp"):
                    raw_text = OCRService.extract_text(
                        doc.file_path,
                        tesseract_cmd=self.app.config.get("TESSERACT_CMD"),
                    )
                elif file_ext == "pdf":
                    raw_text = PDFService.extract_text(doc.file_path)
                else:
                    raise RuntimeError(f"Unsupported file type: {file_ext}")

                self._update_status(document_id, "extracting", extracted_text=raw_text)

                # --- Step 2: Clean text ---
                self._update_status(document_id, "cleaning")
                cleaned_text = TextCleaner.clean(raw_text)
                self._update_status(document_id, "cleaning", cleaned_text=cleaned_text)

                # --- Step 3: Index in FAISS ---
                self._update_status(document_id, "indexing")
                num_chunks = self.vector_store_service.index_document(document_id, cleaned_text)
                logger.info(f"Indexed {num_chunks} chunks for document {document_id}")

                # --- Step 4: Analyze with LLM ---
                self._update_status(document_id, "analyzing")
                llm_response = self.llm_service.analyze_document(cleaned_text)
                self._update_status(
                    document_id, "completed", llm_response=llm_response
                )

                # Store initial LLM response as the first conversation entry
                initial_conversation = Conversation(
                    user_id=doc.user_id,
                    document_id=document_id,
                    role="assistant",
                    content=llm_response,
                )
                db.session.add(initial_conversation)
                db.session.commit()

                logger.info(f"Pipeline completed for document {document_id}")

            except Exception as e:
                logger.error(f"Pipeline failed for document {document_id}: {e}")
                with self.app.app_context():
                    self._update_status(
                        document_id, "failed", error_message=str(e)
                    )

    def delete_document(self, document_id, user_id):
        """Delete a document and its FAISS index."""
        doc = Document.query.filter_by(id=document_id, user_id=user_id).first()
        if not doc:
            raise ValueError("Document not found")

        # Delete uploaded file
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        # Delete FAISS index
        self.vector_store_service.delete_index(document_id)

        # Delete from database (cascades to conversations)
        db.session.delete(doc)
        db.session.commit()
        return True
