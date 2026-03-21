from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Shared limiter instance. Initialized with app in app.py
limiter = Limiter(key_func=get_remote_address, default_limits=["60 per minute"])
