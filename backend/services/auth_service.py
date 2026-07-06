"""
Authentication Service
Handles password hashing/verification and JWT token operations.
"""

import bcrypt
from flask_jwt_extended import create_access_token

from database.db import db
from models.user import User


class AuthService:
    """Service for user authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a plaintext password against a bcrypt hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )

    @staticmethod
    def create_user(username: str, email: str, password: str) -> User:
        """
        Create a new user account.
        Raises ValueError if username or email already exists.
        """
        # Check for existing username
        if User.query.filter_by(username=username).first():
            raise ValueError("Username already exists")

        # Check for existing email
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already registered")

        password_hash = AuthService.hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def authenticate(email: str, password: str) -> tuple[User, str]:
        """
        Authenticate user credentials and return user + JWT token.
        Raises ValueError on invalid credentials.
        """
        user = User.query.filter_by(email=email).first()
        if not user or not AuthService.verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        token = create_access_token(
            identity=str(user.id),
            additional_claims={"username": user.username, "email": user.email},
        )
        return user, token
