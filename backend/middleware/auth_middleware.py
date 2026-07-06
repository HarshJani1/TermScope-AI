"""
Authentication Middleware
JWT token verification decorator for protected routes.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def jwt_required_custom(f):
    """
    Custom JWT decorator that extracts user_id and passes it to the route.
    Returns a 401 JSON error for invalid/missing tokens.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            current_user_id = int(get_jwt_identity())
            return f(current_user_id, *args, **kwargs)
        except Exception as e:
            return jsonify({
                "error": "Authentication required",
                "message": str(e),
            }), 401
    return decorated
