"""
Core rate limiting configuration using SlowAPI.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance keyed per IP
limiter = Limiter(key_func=get_remote_address)
