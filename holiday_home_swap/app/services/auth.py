from datetime import datetime, timedelta, timezone
from typing import Annotated
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from jose import JWTError, jwt 
from passlib.context import CryptContext
from app.db import get_db
from app.model import User, Home, SwapBid
from app.schema import (
    UserCreate,
    UserResponse,
    HomeCreate,
    HomeResponse,
    SwapBidCreate,
    SwapBidResponse,
    UserInDB
)



# openssl rand -hex 32
#dummy hash key, replace in production
SECRET_KEY = "kwbndiwdhojwmkjhbdguftygvbhjniuygvbhjnuhdgyvjniuhdjciuhgybhdnjcuhygvbhncyguv"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10








password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def get_user(db, name: str):
    if name in db:
        user_dict = db[name]
        return UserInDB(**user_dict)


def authenticate_user(db, name: str, password:str):
    user = get_user(db, name)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data : dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow()+expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes = 15)

    to_encode.update({"exp" : expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
