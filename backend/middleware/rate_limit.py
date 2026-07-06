"""
Rate Limiting Middleware
Implements a Token-Bucket rate limiting decorator backed by Redis.
"""

import time
import logging
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from utils.redis_client import redis_client, is_redis_available

logger = logging.getLogger(__name__)

# Lua script for atomic Token-Bucket execution in Redis.
# KEYS[1]: The rate limit key
# ARGV[1]: Bucket capacity
# ARGV[2]: Refill rate (tokens per second)
# ARGV[3]: Current timestamp
# ARGV[4]: Cost of the request (default is 1)
TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4] or 1)

-- Get current bucket state
local data = redis.call('HMGET', key, 'tokens', 'last_updated')
local tokens = tonumber(data[1])
local last_updated = tonumber(data[2])

if not tokens then
    -- First request, initialize bucket
    tokens = capacity - cost
    last_updated = now
    redis.call('HMSET', key, 'tokens', tokens, 'last_updated', now)
    redis.call('EXPIRE', key, 86400) -- expire key after 24h of inactivity
    return 1
else
    -- Calculate refilled tokens based on elapsed time
    local elapsed = now - last_updated
    local refilled = tokens + (elapsed * refill_rate)
    if refilled > capacity then
        refilled = capacity
    end

    if refilled >= cost then
        tokens = refilled - cost
        last_updated = now
        redis.call('HMSET', key, 'tokens', tokens, 'last_updated', now)
        redis.call('EXPIRE', key, 86400)
        return 1
    else
        -- Not enough tokens, save the refilled amount to not lose time progression
        redis.call('HMSET', key, 'tokens', refilled, 'last_updated', now)
        return 0
    end
end
"""


def rate_limit(capacity=None, refill_rate=None, cost=1):
    """
    Decorator for Token-Bucket rate limiting using Redis.
    Identifies clients via JWT user ID or client IP address.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # If Redis is unavailable, fail open (allow request)
            if not is_redis_available():
                logger.warning("Redis is unavailable. Rate limiting is disabled (failing open).")
                return f(*args, **kwargs)

            # Determine config values
            limit_capacity = capacity if capacity is not None else current_app.config.get("RATE_LIMIT_CAPACITY", 10)
            limit_refill = refill_rate if refill_rate is not None else current_app.config.get("RATE_LIMIT_REFILL_RATE", 1.0)

            identifier = None
            try:
                # Try checking JWT identity if present
                verify_jwt_in_request(optional=True)
                user_id = get_jwt_identity()
                if user_id:
                    identifier = f"user:{user_id}"
            except Exception:
                pass

            if not identifier:
                # Fallback to client IP
                ip = request.headers.get("X-Forwarded-For", request.remote_addr)
                if ip and "," in ip:
                    ip = ip.split(",")[0].strip()
                identifier = f"ip:{ip}"

            # Create a unique key per endpoint + identifier
            endpoint = request.endpoint or "global"
            redis_key = f"rate_limit:{identifier}:{endpoint}"

            now = time.time()
            try:
                # Execute Lua script atomically
                allowed = redis_client.eval(TOKEN_BUCKET_LUA, 1, redis_key, limit_capacity, limit_refill, now, cost)
                if not allowed:
                    logger.warning(f"Rate limit exceeded for {identifier} on endpoint '{endpoint}'")
                    return jsonify({
                        "error": "Too Many Requests",
                        "message": "Rate limit exceeded. Please try again later."
                    }), 429
            except Exception as e:
                logger.error(f"Error executing rate limit Lua script: {str(e)}")
                # Fail open if Redis execution fails
                return f(*args, **kwargs)

            return f(*args, **kwargs)
        return wrapped
    return decorator
