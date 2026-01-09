from sqlalchemy.orm import Session
from app.models import SwapBid, SwapMatch, Home


def dates_overlap(start1, end1, start2, end2):
    return start1 <= end2 and start2 <= end1


def find_matching_bids(db: Session, new_bid: SwapBid) -> list[SwapBid]:
    """
    Find swap bids that match the new bid
    """
    homes= db.query(Home).filter(Home.location == new_bid.desired_location).all()
    owner_ids = {home.user_id for home in homes}

    potential_bids = db.query(SwapBid).filter(
        SwapBid.status == "pending",
        SwapBid.user_id.in_(owner_ids),
        SwapBid.user_id != new_bid.user_id
    ).all()

    return [bid for bid in potential_bids 
            if dates_overlap(
                bid.start_date, 
                bid.end_date, 
                new_bid.start_date, 
                new_bid.end_date
                )
            ]