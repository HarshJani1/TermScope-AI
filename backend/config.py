"""
TermScope Backend Configuration
Manages all environment variables and application settings.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import quote_plus
load_dotenv()


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "termscope-dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # MySQL Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD", ""))    
    DB_NAME = os.getenv("DB_NAME", "termscope")
    SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_EXPIRY_HOURS", 24))
    )

    # File Upload
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "uploads"
    )
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_FILE_SIZE_MB", 16)) * 1024 * 1024  # MB
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "webp"}
    ALLOWED_PDF_EXTENSIONS = {"pdf"}
    ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_PDF_EXTENSIONS

    # FAISS Vector Store
    VECTOR_STORE_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "vector_stores"
    )

    # Groq LLM
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 4096))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.3))

    # Embeddings
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Text Processing
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))

    # Tesseract
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")

    # Cache Configuration
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", 86400))  # 24 hours

    # Rate Limiting Configuration (Token Bucket)
    RATE_LIMIT_CAPACITY = int(os.getenv("RATE_LIMIT_CAPACITY", 10))
    RATE_LIMIT_REFILL_RATE = float(os.getenv("RATE_LIMIT_REFILL_RATE", 1.0))



class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/termscope_test.db"
    # Ensure TESSERACT_CMD or other services don't fail if not present,
    # and use testing specific configs.


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
