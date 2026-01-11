from sqlalchemy.orm import Session
from app.model import SwapBid, SwapMatch, Home
from app.services.matching import find_matching_bids

def create_swap_match(db: Session, new_bid: SwapBid):
    """
    Create a swap match between two compatible bids
    """
    # Check if the user has a home (they need a home to swap)
    user_home = db.query(Home).filter(
        Home.owner_id == new_bid.user_id
    ).first()

    if not user_home:
        return None
    matching_bids = find_matching_bids(db, new_bid)

    for bid in matching_bids:
        # Check if the other user have a home in the desired location?
        other_home = db.query(Home).filter(
            Home.owner_id == bid.user_id, 
            Home.location == new_bid.desired_location
        ).first()

        if not other_home:
            continue

        match = SwapMatch(
            bid_a_id=new_bid.id,
            bid_b_id=bid.id,
            status="proposed"
        )   
        db.add(match)
        new_bid.status = "matched"
        bid.status = "matched"
        db.commit()
        db.refresh(match)
        return match    

    return None