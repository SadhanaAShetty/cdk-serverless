from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.models import User, Home, SwapBid
from app.schema import (
    UserCreate,
    UserResponse,
    HomeCreate,
    HomeResponse,
    SwapBidCreate,
    SwapBidResponse
)

router = APIRouter()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user
    """

    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )

    new_user = User(
        name=user.name,
        email=user.email,
        verified=0
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/homes", responsemodel = HomeResponse)
def create_home(home : HomeCreate, db : Session = Depends(get_db)):
    """
    Create new home listing
    """
    new_home = Home(
        user_id=home.user_id,
        name = home.name,
        location = home.location,
        photos = home.photos,
        available_from = home.available_from,
        available_to = home.available_to
    )

    db.add(new_home)
    db.commit()
    db.refresh(new_home)

    return new_home

@router.get("/listings", response_model=List[HomeResponse])
def list_homes(db: Session = Depends(get_db)):
    """
    Get all home listings
    """
    return db.query(Home).all()