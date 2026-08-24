"""
app/services/auth_service.py

Password hashing (bcrypt, called directly) and JWT issuing/verification.
"""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# Using bcrypt directly rather than passlib.CryptContext: passlib's bcrypt
# backend probes `bcrypt.__about__.__version__`, which was removed in
# bcrypt>=4.1, causing a hard crash on hash(). Calling bcrypt directly
# sidesteps that entirely.
# bcrypt has a hard 72-byte input limit — truncate defensively so an
# unusually long password doesn't raise instead of just being truncated.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    truncated = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    truncated = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(truncated, hashed_password.encode("utf-8"))


def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])