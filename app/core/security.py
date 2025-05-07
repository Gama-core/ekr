# app/core/security.py
from passlib.context import CryptContext

# Initialize Passlib's CryptContext
# bcrypt is a good default choice for password hashing.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# Add JWT token functions here later if needed for authentication
# from datetime import datetime, timedelta
# from typing import Optional
# from jose import JWTError, jwt
# from app.core.config import settings

# SECRET_KEY = settings.SECRET_KEY # You'd need to add SECRET_KEY to your Settings
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES # Add to Settings