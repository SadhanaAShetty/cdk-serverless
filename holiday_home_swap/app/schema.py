from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional

# User Schemas
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str  


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPreferences(BaseModel):
    """User preferences for home swapping"""
    preferred_locations: List[str] = [] 
    home_types: List[str] = []  
    min_rooms: Optional[int] = None  
    max_rooms: Optional[int] = None 
    required_amenities: List[str] = []  
    deal_breakers: List[str] = [] 
    


class NotificationSettings(BaseModel):
    """User notification preferences"""
    email_matches: bool = True  
    email_messages: bool = True 
    email_reminders: bool = False 


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    verified: int
    profile_complete: int
    preferences: Optional[dict] = None
    notification_settings: Optional[dict] = None

    class Config:
        from_attributes = True



# Home Schemas
class HouseRules(BaseModel):
    """House rules for a home"""
    pets_allowed: bool = False
    smoking_allowed: bool = False
    max_guests: int = 2
    quiet_hours: Optional[str] = None  
    additional_rules: List[str] = []  


class HomeCreate(BaseModel):
    name: str
    location: str
    room_count: int  
    home_type: str 
    amenities: List[str] = [] 
    house_rules: Optional[HouseRules] = None
    photos: List[str] = [] 
    available_from: datetime
    available_to: datetime


class HomeResponse(BaseModel):
    id: int
    name: str
    location: str
    room_count: int
    home_type: str
    amenities: List[str]
    house_rules: Optional[dict] = None
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
