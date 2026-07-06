import sys
import json
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.append("/Users/harshjani/Documents/TermScope/backend")

from app import create_app
from database.db import db
from models.user import User
from utils.redis_client import redis_client, is_redis_available

def test_login_caching_flow():
    app = create_app()
    app.config['TESTING'] = True
    
    # We will use the app's test client
    client = app.test_client()
    
    with app.app_context():
        print("Checking Redis connection...")
        if not is_redis_available():
            print("❌ Redis is not available. Please run Redis first.")
            sys.exit(1)
        print("✅ Redis is available.")
        
        # Clean up database test user and Redis keys
        test_email = "cache_test_user@example.com"
        test_password = "password123"
        test_username = "cache_test_user"
        
        # Delete existing user from DB to keep test clean
        existing_user = User.query.filter_by(email=test_email).first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
            
        # Clean up tracking set and login cache keys in Redis
        import hashlib
        cred_str = f"{test_email}:{test_password}"
        cred_hash = hashlib.sha256(cred_str.encode("utf-8")).hexdigest()
        cache_key = f"cache:login:{cred_hash}"
        redis_client.delete(cache_key)
        redis_client.delete(f"user_login_keys:{test_email}")
        
        # 1. Signup
        print("\n1. Signing up test user...")
        signup_data = {
            "username": test_username,
            "email": test_email,
            "password": test_password
        }
        res = client.post("/api/auth/signup", json=signup_data)
        assert res.status_code == 201, f"Signup failed: {res.get_json()}"
        print("✅ Signup successful.")
        
        # 2. First Login (Fresh)
        print("\n2. First login (should be fresh)...")
        login_data = {
            "email": test_email,
            "password": test_password
        }
        res = client.post("/api/auth/login", json=login_data)
        assert res.status_code == 200
        res_json = res.get_json()
        token1 = res_json["token"]
        print(f"✅ First login successful. Token: {token1[:20]}...")
        
        # Verify key exists in Redis
        assert redis_client.exists(cache_key), "❌ Cache key was not created in Redis!"
        print("✅ Cache key verified in Redis.")
        
        # Verify tracking set key exists
        tracking_key = f"user_login_keys:{test_email}"
        assert redis_client.sismember(tracking_key, cache_key), "❌ Cache key not added to tracking set!"
        print("✅ Cache key tracked in Redis set.")
        
        # 3. Second Login (Should come from cache)
        print("\n3. Second login (should be cached)...")
        res = client.post("/api/auth/login", json=login_data)
        assert res.status_code == 200
        res_json = res.get_json()
        token2 = res_json["token"]
        assert token1 == token2, f"❌ Caching failed: expected identical token, got {token2[:20]}..."
        print("✅ Second login returned identical token (caching works!).")
        
        # 4. Access a protected endpoint with token1
        print("\n4. Accessing protected endpoint /api/documents...")
        headers = {"Authorization": f"Bearer {token1}"}
        res = client.get("/api/documents", headers=headers)
        assert res.status_code == 200, f"Failed to access protected route: {res.get_json()}"
        print("✅ Protected route accessed successfully with cached token.")
        
        # 5. Logout (should blacklist token1 and invalidate cache_key)
        print("\n5. Logging out (should blacklist token and clear cache)...")
        res = client.post("/api/auth/logout", headers=headers)
        assert res.status_code == 200
        print("✅ Logout successful.")
        
        # Verify token1 is blocklisted
        from flask_jwt_extended import decode_token
        decoded = decode_token(token1)
        jti = decoded["jti"]
        assert redis_client.exists(f"token_blocklist:{jti}"), "❌ Token was not added to blocklist!"
        print("✅ Token blocklisted in Redis.")
        
        # Verify cache_key is deleted
        assert not redis_client.exists(cache_key), "❌ Cache key was not deleted on logout!"
        assert not redis_client.exists(tracking_key), "❌ Tracking set was not deleted on logout!"
        print("✅ Cache key and tracking set deleted on logout.")
        
        # 6. Third Login (Should generate a NEW token)
        print("\n6. Third login (should be fresh again)...")
        res = client.post("/api/auth/login", json=login_data)
        assert res.status_code == 200
        res_json = res.get_json()
        token3 = res_json["token"]
        assert token1 != token3, "❌ Caching issue: logout did not invalidate the login cache key!"
        print(f"✅ Third login returned a fresh, new token: {token3[:20]}...")
        
        # 7. Verify old token is rejected
        print("\n7. Verifying that the logged-out token is rejected...")
        res = client.get("/api/documents", headers=headers)
        assert res.status_code == 401, "❌ Logged-out token was not rejected!"
        print("✅ Logged-out token successfully rejected (401 Unauthorized).")
        
        # Clean up database test user and Redis keys
        user_to_delete = User.query.filter_by(email=test_email).first()
        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()
        redis_client.delete(f"cache:login:{cred_hash}")
        redis_client.delete(f"user_login_keys:{test_email}")
        redis_client.delete(f"token_blocklist:{jti}")
        
        print("\n🎉 ALL TESTS PASSED! Caching, Token Revocation, and Logout Invalidation are 100% working.")

if __name__ == "__main__":
    test_login_caching_flow()
