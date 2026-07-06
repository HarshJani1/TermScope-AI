"""
Vector Store Service
Manages FAISS indices for per-document semantic search.
"""

import os
import logging
import shutil

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for FAISS vector store operations."""

    def __init__(self, store_dir, embedding_model, chunk_size=1000, chunk_overlap=200):
        self.store_dir = store_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        os.makedirs(store_dir, exist_ok=True)

        logger.info(f"Loading embedding model: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def _get_index_path(self, document_id):
        return os.path.join(self.store_dir, f"doc_{document_id}")

    def index_document(self, document_id, text):
        """Chunk text and create a FAISS index for a document."""
        try:
            logger.info(f"Indexing document {document_id} ({len(text)} chars)")
            chunks = self.text_splitter.split_text(text)
            if not chunks:
                return 0

            vector_store = FAISS.from_texts(
                texts=chunks,
                embedding=self.embeddings,
                metadatas=[{"chunk_index": i, "document_id": document_id} for i in range(len(chunks))],
            )
            index_path = self._get_index_path(document_id)
            vector_store.save_local(index_path)
            logger.info(f"FAISS index saved: {len(chunks)} chunks")
            return len(chunks)
        except Exception as e:
            logger.error(f"Failed to index document {document_id}: {e}")
            raise RuntimeError(f"Vector indexing failed: {e}")

    def search(self, document_id, query, top_k=4):
        """Search for relevant chunks in a document's FAISS index."""
        try:
            index_path = self._get_index_path(document_id)
            if not os.path.exists(index_path):
                return []

            vector_store = FAISS.load_local(
                index_path, self.embeddings, allow_dangerous_deserialization=True,
            )
            results = vector_store.similarity_search(query, k=top_k)
            return [doc.page_content for doc in results]
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []

    def delete_index(self, document_id):
        """Delete a document's FAISS index from disk."""
        index_path = self._get_index_path(document_id)
        if os.path.exists(index_path):
            shutil.rmtree(index_path)
            return True
        return False
