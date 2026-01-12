from sqlalchemy.orm import Session
from app.model import SwapBid, Home


def dates_overlap(start1, end1, start2, end2):
    """Check if two date ranges overlap"""
    return start1 <= end2 and start2 <= end1


def find_matching_bids(db: Session, new_bid: SwapBid) -> list[SwapBid]:
    """
    Find swap bids that match the new bid
    """
    # Find homes in the desired location
    homes_in_desired_location = db.query(Home).filter(
        Home.location == new_bid.desired_location
    ).all()
    owner_ids_with_desired_homes = {home.owner_id for home in homes_in_desired_location}

    # Find the new user's homes to see what locations they can offer
    new_user_homes = db.query(Home).filter(
        Home.owner_id == new_bid.user_id
    ).all()
    new_user_locations = {home.location for home in new_user_homes}

    # Find potential matching bids
    potential_bids = db.query(SwapBid).filter(
        SwapBid.status == "pending",
        SwapBid.user_id.in_(owner_ids_with_desired_homes),
        SwapBid.user_id != new_bid.user_id,
        SwapBid.desired_location.in_(new_user_locations) 
    ).all()

    # Filter by date overlap
    matching_bids = []
    for bid in potential_bids:
        if dates_overlap(
            bid.start_date, 
            bid.end_date, 
            new_bid.start_date, 
            new_bid.end_date
        ):
            matching_bids.append(bid)
    
    return matching_bids