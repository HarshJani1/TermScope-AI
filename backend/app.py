"""
TermScope Backend — Main Application
AI-powered Terms & Conditions analysis platform.
"""

import os
import logging
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import get_config
from database.db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory — creates and configures the Flask app."""
    # Serve static files from the frontend build directory if it exists
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
    app = Flask(__name__, static_folder=frontend_dist, static_url_path="")

    # Load configuration
    config = get_config()
    app.config.from_object(config)
    logger.info(f"Starting TermScope in {os.getenv('FLASK_ENV', 'development')} mode")

    # CORS — allow frontend on common dev ports
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })

    # JWT
    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        try:
            from utils.redis_client import redis_client, is_redis_available
            if is_redis_available():
                token_in_redis = redis_client.get(f"token_blocklist:{jti}")
                return token_in_redis is not None
            return False
        except Exception as e:
            logger.error(f"Redis blocklist check failed: {e}")
            return False

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired", "message": "Please log in again"}), 401


    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "Invalid token", "message": str(error)}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"error": "Authorization required", "message": "Token is missing"}), 401

    # Initialize database
    init_db(app)

    # Ensure directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["VECTOR_STORE_DIR"], exist_ok=True)

    # Initialize services
    from services.llm_service import LLMService
    from services.vector_store_service import VectorStoreService
    from services.document_service import DocumentService

    llm_service = LLMService(
        api_key=app.config["GROQ_API_KEY"],
        model=app.config["LLM_MODEL"],
        max_tokens=app.config["LLM_MAX_TOKENS"],
        temperature=app.config["LLM_TEMPERATURE"],
    )

    vector_store_service = VectorStoreService(
        store_dir=app.config["VECTOR_STORE_DIR"],
        embedding_model=app.config["EMBEDDING_MODEL"],
        chunk_size=app.config["CHUNK_SIZE"],
        chunk_overlap=app.config["CHUNK_OVERLAP"],
    )

    document_service = DocumentService(
        app=app,
        llm_service=llm_service,
        vector_store_service=vector_store_service,
    )

    # Store services in app config for access from routes
    app.config["LLM_SERVICE"] = llm_service
    app.config["VECTOR_STORE_SERVICE"] = vector_store_service
    app.config["DOCUMENT_SERVICE"] = document_service

    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.document_routes import document_bp
    from routes.chat_routes import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(chat_bp)

    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "healthy",
            "service": "TermScope API",
            "version": "1.0.0",
        }), 200

    # Global error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(413)
    def file_too_large(e):
        return jsonify({"error": "File too large"}), 413

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500

    # Catch-all route to serve the React frontend index.html for any SPA routes,
    # but avoid intercepting /api/ routes which should 404/error properly if not matched.
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path.startswith("api/"):
            return jsonify({"error": "Endpoint not found"}), 404
        
        # Check if the requested file exists in static folder (e.g. assets, favicon)
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        
        # Otherwise serve index.html for client side routing
        return send_from_directory(app.static_folder, 'index.html')

    logger.info("TermScope API initialized successfully")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5010, debug=True)
