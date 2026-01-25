from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.db import get_db
from app.model import User, Home, SwapBid, SwapMatch
from app.services.swap import create_swap_match
from app.schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserPreferences,
    HomeCreate,
    HomeResponse,
    SwapBidCreate,
    SwapBidResponse,
    Token,
    SwapMatchResponse, 
    MatchDetailResponse
)
from app.services.auth import get_password_hash, login_user, get_current_user
from app.services.storage import image_storage
from app.config import settings

router = APIRouter()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user with hashed password
    """
    #Check if user already exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )

    #Hash the password before storing
    hashed_password = get_password_hash(user.password)
    
    #Create new user
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


@router.post("/auth/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login user and return JWT token
    """
    return login_user(db, form_data.username, form_data.password)


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information 
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
    # Validate dates
    if home.available_from >= home.available_to:
        raise HTTPException(
            status_code=400,
            detail="Available to date must be after available from date"
        )

    if home.available_from < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Available from date must be in the future"
        )
    
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


@router.post("/homes/{home_id}/photos")
async def upload_home_photos(
    home_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload photos for a home listing 
    """
    # Get the home and verify ownership
    home = db.query(Home).filter(Home.id == home_id).first()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")
    
    if home.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to upload photos for this home"
        )
    
    # Validate image count
    current_photo_count = len(home.photos) if home.photos else 0
    image_storage.validate_image_count(current_photo_count, len(files), home.room_count)
    
    # Upload each image and get S3 keys
    uploaded_keys = []
    for file in files:
        try:
            s3_key = image_storage.process_and_upload_image(file, current_user.id, home_id)
            uploaded_keys.append(s3_key)
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to upload {file.filename}: {str(e)}"
            )
    
    # Store S3 keys in database
    if home.photos:
        home.photos.extend(uploaded_keys)
    else:
        home.photos = uploaded_keys
    
    db.commit()
    db.refresh(home)
    
    return {
        "message": f"Successfully uploaded {len(uploaded_keys)} photos",
        "photo_count": len(home.photos),
        "uploaded_keys": uploaded_keys
    }


@router.get("/homes/{home_id}", response_model=HomeResponse)
def get_home(home_id: int, db: Session = Depends(get_db)):
    """
    Get specific home with presigned photo URLs
    """
    home = db.query(Home).filter(Home.id == home_id).first()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")
    
    # Generate presigned URLs for photos
    if home.photos:
        home.photos = image_storage.generate_presigned_urls(
            home.photos, 
            expiration=settings.PRESIGNED_URL_EXPIRATION
        )
    
    return home

@router.get("/listings", response_model=List[HomeResponse])
def list_homes(db: Session = Depends(get_db)):
    """Get all home listings with presigned photo URLs"""
    homes = db.query(Home).all()
    
    # Generate presigned URLs for all homes
    for home in homes:
        if home.photos:
            home.photos = image_storage.generate_presigned_urls(home.photos)
    
    return homes

@router.post("/swap_bids", response_model=SwapBidResponse)
def create_swap_bid(
    bid: SwapBidCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Create a new swap bid 
    """
    # Validate dates
    if bid.start_date >= bid.end_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )
    
    if bid.start_date < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Start date must be in the future"
        )
    
    # Check if user has at least one home to swap
    user_homes = db.query(Home).filter(Home.owner_id == current_user.id).all()
    if not user_homes:
        raise HTTPException(
            status_code=400,
            detail="You must have at least one home listed to create a swap bid"
        )
    
    new_bid = SwapBid(
        user_id=current_user.id,  
        desired_location=bid.desired_location,
        start_date=bid.start_date,
        end_date=bid.end_date,
        status="pending"
    )
    
    db.add(new_bid)
    db.commit()
    db.refresh(new_bid)
    
    # Try to find matches for this new bid
    create_swap_match(db, new_bid)
    
    return new_bid

@router.get("/swap_bids", response_model=List[SwapBidResponse])
def list_my_swap_bids(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's swap bids
    """
    return db.query(SwapBid).filter(SwapBid.user_id == current_user.id).all()

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


@router.post("/debug/test-email")
def test_email_notification(
    user_email: str,
    user_name: str = "Test User",
    match_location: str = "Paris",
    current_user: User = Depends(get_current_user)
):
    """
    Debug endpoint to test email notifications
    """
    print(f" Testing email notification to {user_email}")
    
    from app.services.notification import email_service
    
    try:
        success = email_service.send_match_notification(user_email, user_name, match_location)
        
        return {
            "success": success,
            "message": "Email sent successfully" if success else "Email failed to send",
            "sender_configured": bool(settings.SES_SENDER_EMAIL),
            "recipient": user_email,
            "aws_profile": settings.AWS_PROFILE
        }
    except Exception as e:
        print(f"Exception in test email: {e}")
        return {
            "success": False,
            "error": str(e),
            "sender_configured": bool(settings.SES_SENDER_EMAIL),
            "aws_profile": settings.AWS_PROFILE
        }

@router.get("/matches", response_model =List[SwapMatchResponse])
def get_my_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all matches for current user
    """
    user_bid_ids = [bid.id for bid in current_user.bids]

    matches = db.query(SwapMatch).filter(
        (SwapMatch.bid_a_id.in_(user_bid_ids)) |
        (SwapMatch.bid_b_id.in_(user_bid_ids))
    ).all()

    return matches

@router.get("/matches/{match_id}", response_model=MatchDetailResponse)
def get_match_details(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed match information including both users and homes
    """
    match = db.query(SwapMatch).filter(SwapMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Get the bids
    bid_a = db.query(SwapBid).filter(SwapBid.id == match.bid_a_id).first()
    bid_b = db.query(SwapBid).filter(SwapBid.id == match.bid_b_id).first()

    # Determine which is the current user's bid
    if bid_a.user_id == current_user.id:
        my_bid = bid_a
        other_bid = bid_b
    elif bid_b.user_id == current_user.id:
        my_bid = bid_b
        other_bid = bid_a
    else:
        raise HTTPException(status_code=403, detail="Not authorized to view this match")
    
    # Get other user
    other_user = db.query(User).filter(User.id == other_bid.user_id).first()

    # Get homes fix the logic to get correct homes
    my_home = db.query(Home).filter(
        Home.owner_id == current_user.id,
        Home.location.ilike(other_bid.desired_location)
    ).first()

    other_home = db.query(Home).filter(
        Home.owner_id == other_user.id,
        Home.location.ilike(my_bid.desired_location)
    ).first()

    # Generate presigned URLs for photos
    if my_home and my_home.photos:
        my_home.photos = image_storage.generate_presigned_urls(my_home.photos)
    
    if other_home and other_home.photos:
        other_home.photos = image_storage.generate_presigned_urls(other_home.photos)

    return MatchDetailResponse(
        id=match.id,
        status=match.status,
        match_date=match.match_date,
        my_bid=my_bid,
        other_bid=other_bid,
        my_home=my_home,
        other_home=other_home,
        other_user=other_user
    )

@router.put("/matches/{match_id}/accept")
def accept_match(
    match_id : int,
    db :Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    """
    Accept a match proposal
    """
    match = db.query(SwapMatch).filter(SwapMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    #verify user is part of this match
    bid_a = db.query(SwapBid).filter(SwapBid.id == match.bid_a_id).first()
    bid_b = db.query(SwapBid).filter(SwapBid.id == match.bid_b_id).first()

    if current_user.id not in [bid_a.user_id, bid_b.user_id]:
        raise HTTPException(status_code=403, detail="Not authorized to change this match")
  
    if match.status != "proposed":
        raise HTTPException(status_code=400, detail="Match is not in a proposed state")
    

    #update match state
    match.status = "accepted"
    bid_a.status = "accepted"
    bid_b.status = "accepted"

    db.commit()
    return {"message": "Match accepted successfully", "match_id":match_id}

@router.put("/matches/{match_id}/reject")
def reject_match(
    match_id : int,
    db : Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    match = db.query(SwapMatch).filter(SwapMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Verify user is part of this match
    bid_a = db.query(SwapBid).filter(SwapBid.id == match.bid_a_id).first()
    bid_b = db.query(SwapBid).filter(SwapBid.id == match.bid_b_id).first()
    
    if current_user.id not in [bid_a.user_id, bid_b.user_id]:
        raise HTTPException(status_code=403, detail="Not authorized to modify this match")
    
    if match.status != "proposed":
        raise HTTPException(status_code=400, detail="Match is not in proposed state")
    
    # Update match status and reset bids to pending
    match.status = "rejected"
    bid_a.status = "pending"
    bid_b.status = "pending"
    
    db.commit()
    
    return {"message": "Match rejected successfully", "match_id": match_id}