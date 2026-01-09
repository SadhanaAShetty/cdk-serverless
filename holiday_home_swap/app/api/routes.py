from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.model import User, Home, SwapBid
from app.schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserPreferences,
    NotificationSettings,
    HomeCreate,
    HomeResponse,
    HouseRules,
    SwapBidCreate,
    SwapBidResponse,
    Token
)
from app.services.auth import get_password_hash, login_user, get_current_user

router = APIRouter()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user with hashed password
    """
    # Check if user already exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )

    # Hash the password before storing
    hashed_password = get_password_hash(user.password)
    
    # Create new user
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        verified=0
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/auth/login", response_model=Token)
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Login user and return JWT token
    """
    return login_user(db, user_login.email, user_login.password)


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information (protected route)
    """
    return current_user


@router.get("/users/preferences", response_model=dict)
def get_user_preferences(current_user: User = Depends(get_current_user)):
    """
    Get current user preferences
    """
    return {
        "preferences": current_user.preferences or {},
        "notification_settings": current_user.notification_settings or {},
        "profile_complete": current_user.profile_complete
    }


@router.put("/users/preferences", response_model=UserResponse)
def update_user_preferences(
    preferences: UserPreferences, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Update user preferences for home swapping
    """
    # Convert preferences to dict for JSON storage
    current_user.preferences = preferences.dict()
    
    # Check if profile is now complete
    if current_user.preferences and current_user.homes:
        current_user.profile_complete = 1
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/homes", response_model=HomeResponse)
def create_home(home: HomeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create new home listing with enhanced details (protected route)
    """
    # Convert house_rules to dict if provided
    house_rules_dict = home.house_rules.dict() if home.house_rules else None
    
    new_home = Home(
        owner_id=current_user.id,
        name=home.name,
        location=home.location,
        room_count=home.room_count,
        home_type=home.home_type,
        amenities=home.amenities,
        house_rules=house_rules_dict,
        photos=home.photos,  
        available_from=home.available_from,
        available_to=home.available_to
    )

    db.add(new_home)
    db.commit()
    db.refresh(new_home)
    
    # Update user profile completion status
    if current_user.preferences:
        current_user.profile_complete = 1
        db.commit()

    return new_home

@router.get("/listings", response_model=List[HomeResponse])
def list_homes(db: Session = Depends(get_db)):
    """
    Get all home listings
    """
    return db.query(Home).all()

@router.get("/swap_bids", response_model=List[SwapBidResponse])
def list_swap_bids(bid : SwapBidCreate, db: Session = Depends(get_db)):
    """"
    Get all swap bids
    """
    new_bids = SwapBid(
        user_id = bid.user_id,
        desired_location = bid.desired_location,
        start_date = bid.start_date,
        end_date = bid.end_date,
        status = "pending"
    )
    db.add(new_bids)
    db.commit()
    db.refresh(new_bids)
    return new_bids

@router.get("/swap_bids/{bid_id}", response_model=SwapBidResponse)
def get_swap_bid(bid_id: int, db: Session = Depends(get_db)):
    """
    Get a specific swap bid by ID
    """
    bid = db.query(SwapBid).filter(SwapBid.id == bid_id).first()
    if not bid:
        raise HTTPException(
            status_code=404,
            detail="Swap bid not found"
        )
    return bid