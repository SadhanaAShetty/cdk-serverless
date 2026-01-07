from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional

# User Schemas
class UserCreate(BaseModel):
    name: str
    email: EmailStr


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    verified: int

    class Config:
        from_attributes = True



# Home Schemas
class HomeCreate(BaseModel):
    name: str
    location: str
    photos: List[str]
    available_from: datetime
    available_to: datetime


class HomeResponse(BaseModel):
    id: int
    name: str
    location: str
    photos: List[str]
    available_from: datetime
    available_to: datetime
    owner_id: int

    class Config:
        from_attributes = True


# Swap Bid Schemas
class SwapBidCreate(BaseModel):
    desired_location: str
    start_date: datetime
    end_date: datetime


class SwapBidResponse(BaseModel):
    id: int
    desired_location: str
    start_date: datetime
    end_date: datetime
    status: str
    user_id: int

    class Config:
        from_attributes = True



# Swap Match Schemas
class SwapMatchResponse(BaseModel):
    id: int
    bid_a_id: int
    bid_b_id: int
    status: str
    match_date: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class UserInDB(BaseModel):
    hashed_password: str
