from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    verified = Column(Integer, default=0)  # 0 = no, 1 = yes

    homes = relationship("Home", back_populates="owner")
    bids = relationship("SwapBid", back_populates="user")


class Home(Base):
    __tablename__ = "homes"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    photos = Column(JSON, nullable=False)

    available_from = Column(DateTime, nullable=False)
    available_to = Column(DateTime, nullable=False)

    owner = relationship("User", back_populates="homes")


class SwapBid(Base):
    __tablename__ = "swap_bids"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    desired_location = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    status = Column(String, default="pending")  # pending, accepted, rejected

    user = relationship("User", back_populates="bids")


class SwapMatch(Base):
    __tablename__ = "swap_matches"

    id = Column(Integer, primary_key=True, index=True)
    bid_a_id = Column(Integer, ForeignKey("swap_bids.id"), nullable=False)
    bid_b_id = Column(Integer, ForeignKey("swap_bids.id"), nullable=False)

    status = Column(String, default="proposed")  # proposed, confirmed, cancelled
    match_date = Column(DateTime, default=datetime.utcnow)

    bid_a = relationship("SwapBid", foreign_keys=[bid_a_id])
    bid_b = relationship("SwapBid", foreign_keys=[bid_b_id])
