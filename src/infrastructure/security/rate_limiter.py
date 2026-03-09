"""Redis-backed sliding window rate limiter.

Uses atomic INCR + EXPIRE pipeline for correctness.
Falls open (allows request) if Redis is unavailable — consistent with
the existing fail-open pattern used elsewhere.
"""

from fastapi import HTTPException, Request, status

from utils.log import log_warning


class RedisRateLimiter:
    """Sliding-window rate limiter backed by Redis."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds

    def check(self, request: Request, action: str = "auth") -> None:
        """Raise 429 if the client exceeds the rate limit.

        Falls open (allows request) if Redis is unavailable.
        """
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate:{action}:{client_ip}"

        try:
            from infrastructure.cache.redis_cache import redis_tool
            client = redis_tool.client()

            pipe = client.pipeline(transaction=True)
            pipe.incr(key)
            pipe.expire(key, self._window)
            results = pipe.execute()
            current_count = results[0]

            if current_count > self._max:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )
        except HTTPException:
            raise
        except Exception as e:
            log_warning(f"Rate limiter Redis error (failing open): {e}")
