# Redis-backed Limiter instance. Initialized with app in app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import RATELIMIT_STORAGE_URL

limiter = Limiter(
	key_func=get_remote_address,
	default_limits=["60 per minute"],
	storage_uri=RATELIMIT_STORAGE_URL
)
