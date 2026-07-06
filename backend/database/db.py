"""
TermScope Database Setup
SQLAlchemy instance and initialization utilities.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize the database with the Flask app and create all tables."""
    db.init_app(app)
    with app.app_context():
        from models.user import User  # noqa: F401
        from models.document import Document  # noqa: F401
        from models.conversation import Conversation  # noqa: F401
        db.create_all()
