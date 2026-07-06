"""
Authentication Routes
POST /api/auth/signup  — Register a new user
POST /api/auth/login   — Login and receive JWT
"""

from flask import Blueprint, request, jsonify
from services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Register a new user account."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # Validation
    errors = []
    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters")
    if not email or "@" not in email:
        errors.append("Valid email is required")
    if not password or len(password) < 6:
        errors.append("Password must be at least 6 characters")
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        user = AuthService.create_user(username, email, password)
        return jsonify({
            "message": "Account created successfully",
            "user": user.to_dict(),
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    from utils.redis_client import redis_client, is_redis_available
    import hashlib
    import json
    from config import get_config
    
    config = get_config()
    ttl = int(config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
    cache_key = None

    if is_redis_available():
        try:
            # Hash email + password for cache key
            cred_str = f"{email}:{password}"
            cred_hash = hashlib.sha256(cred_str.encode("utf-8")).hexdigest()
            cache_key = f"cache:login:{cred_hash}"
            
            cached_res = redis_client.get(cache_key)
            if cached_res:
                res_data = json.loads(cached_res)
                token = res_data.get("token")
                if token:
                    from flask_jwt_extended import decode_token
                    from datetime import datetime, timezone
                    try:
                        decoded = decode_token(token)
                        jti = decoded.get("jti")
                        # Verify the token is not blocklisted
                        is_blocklisted = False
                        if jti:
                            is_blocklisted = bool(redis_client.exists(f"token_blocklist:{jti}"))
                        
                        # Verify the token is not expired (leave 10s buffer)
                        exp = decoded.get("exp")
                        now = datetime.now(timezone.utc).timestamp()
                        
                        if not is_blocklisted and exp and (exp - now > 10):
                            return jsonify(res_data), 200
                    except Exception:
                        pass
        except Exception as e:
            pass # Ignore redis read error and fallback to DB

    try:
        user, token = AuthService.authenticate(email, password)
        response_data = {
            "message": "Login successful",
            "token": token,
            "user": user.to_dict(),
        }
        
        # Cache the successful response
        if cache_key and is_redis_available():
            try:
                redis_client.setex(cache_key, ttl, json.dumps(response_data))
                # Track the cache key under the user's email for logout invalidation
                tracking_key = f"user_login_keys:{email}"
                redis_client.sadd(tracking_key, cache_key)
                redis_client.expire(tracking_key, ttl)
            except Exception:
                pass # Ignore redis write error

        return jsonify(response_data), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Revoke user's JWT token by adding it to Redis blocklist."""
    from flask_jwt_extended import jwt_required, get_jwt
    from datetime import datetime, timezone
    from utils.redis_client import redis_client, is_redis_available

    # Define a helper inline or use the route under a try block
    # Note: we can use jwt_required() without arguments
    @jwt_required()
    def process_logout():
        try:
            if not is_redis_available():
                return jsonify({"error": "Cache service unavailable, logout failed"}), 503

            jwt_data = get_jwt()
            jti = jwt_data["jti"]
            exp_timestamp = jwt_data["exp"]
            
            now = datetime.now(timezone.utc).timestamp()
            ttl = max(int(exp_timestamp - now), 1)
            
            # Revoke token
            redis_client.setex(f"token_blocklist:{jti}", ttl, "true")

            # Clear cached login responses for this user's email
            email = jwt_data.get("email")
            if email:
                tracking_key = f"user_login_keys:{email}"
                keys_to_clear = redis_client.smembers(tracking_key)
                if keys_to_clear:
                    for key in keys_to_clear:
                        redis_client.delete(key)
                redis_client.delete(tracking_key)

            return jsonify({"message": "Successfully logged out"}), 200
        except Exception as e:
            return jsonify({"error": f"Logout failed: {str(e)}"}), 500

    return process_logout()

