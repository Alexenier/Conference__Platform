import warnings
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

ALGORITHM = "HS256"

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pwd_context.verify(plain[:72], hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None