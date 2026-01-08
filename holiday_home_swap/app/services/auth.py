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
    UserInDB,
    TokenData
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

async def get_current_user(db, token: Annotated[str, Depends(oauth2_scheme)]):
    credential_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate credentials",
        headers = {"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decade(token, SECRET_KEY, algorithms=[ALGORITHM])
        email : str = payload.get("sub")
        if email is None:
            raise credential_exception
        
        token_data = TokenData(email=email)
    except JWTError:
        raise credential_exception
    
    user = get_user(db, email=token_data.email)
    
    if user is None:
        raise credential_exception
    return user

async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/token", response_model = Token)
async def login_for_access_token(db, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Incorrect username or password",
            headers = {"WWW-Authenticate": "Bearer"}        
        )
    access_token_expires = timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data = {"sub": user.email}, expires_delta= access_token_expires)
    return {"access_token" : access_token, "token_type":"bearer"}

