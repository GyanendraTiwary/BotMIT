# config.py
import hashlib

GOOGLE_API_KEY = "AIzaSyDdw6HUrtinwKhXBLMO0_AW_jyuoXtY7pU"

# Admin credentials (using sha256 hash)
ADMIN_USERNAME = "admin"
# Password hash for "admin123"
ADMIN_PASSWORD_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"

def check_password(password):
    """Check if the provided password matches the stored hash"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == ADMIN_PASSWORD_HASH