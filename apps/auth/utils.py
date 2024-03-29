from passlib.context import CryptContext
import os
from datetime import datetime, timedelta
from typing import Union, Any
import jwt

ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"
JWT_SECRET_KEY = '1231256465465465465'  # should be kept secret
JWT_REFRESH_SECRET_KEY = 'sadfsfsdfsd5vcs5dx2c1zdx'  # should be kept secret

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    # return password_context.verify(password, hashed_pass)
    # TODO password hashing during user creation
    return password == hashed_pass


def create_access_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt


def decode_refresh_token(refresh_token):
    data = jwt.decode(refresh_token, JWT_REFRESH_SECRET_KEY, [ALGORITHM])
    return data


def decode_access_token(access_token):
    return jwt.decode(access_token, JWT_SECRET_KEY, [ALGORITHM])


def user_from_refresh_token(token):
    decoded = decode_refresh_token(token)
    return decoded.get('sub')


def create_refresh_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, ALGORITHM)
    return encoded_jwt
