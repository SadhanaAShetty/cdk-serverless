from sqlalchemy.orm import Session
from app.models import SwapBid, SwapMatch, Home
from app.services.matching import find_matching_bids

def create_swap_match(db: Session, new_bid: SwapBid):
    """
    Create a swap match between two compatible bids
    """
    swap_match = db.query(Home).filter(
        Home.id == new_bid.user_id
    ).first()

    if not swap_match:
        return None
    matching_bids = find_matching_bids(db, new_bid)

    for bid in matching_bids:
        #check reverse location match
        other_home = db.query(Home).filter(
            Home.id == bid.user_id, 
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