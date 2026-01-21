from sqlalchemy.orm import Session
from app.model import SwapBid, Home


def dates_overlap(start1, end1, start2, end2):
    """Check if two date ranges overlap"""
    return start1 <= end2 and start2 <= end1


def find_matching_bids(db: Session, new_bid: SwapBid) -> list[SwapBid]:
    """
    Find swap bids that match the new bid 
    """
    print(f" Looking for matches for bid wanting: {new_bid.desired_location}")
    
    # Find homes in the desired location
    homes_in_desired_location = db.query(Home).filter(
        Home.location.ilike(new_bid.desired_location)
    ).all()
    print(f" Found {len(homes_in_desired_location)} homes in {new_bid.desired_location}")
    
    owner_ids_with_desired_homes = {home.owner_id for home in homes_in_desired_location}

    # Find the new user's homes to see what locations they can offer
    new_user_homes = db.query(Home).filter(
        Home.owner_id == new_bid.user_id
    ).all()
    new_user_locations = {home.location.lower() for home in new_user_homes}
    print(f" New user can offer locations: {new_user_locations}")

    # Find potential matching bids
    potential_bids = []
    all_pending_bids = db.query(SwapBid).filter(
        SwapBid.status == "pending",
        SwapBid.user_id != new_bid.user_id
    ).all()
    
    print(f"Checking {len(all_pending_bids)} pending bids for matches")
    
    for bid in all_pending_bids:
        if (bid.user_id in owner_ids_with_desired_homes and 
            bid.desired_location.lower() in new_user_locations):
            potential_bids.append(bid)
            print(f" Found potential match: User {bid.user_id} wants {bid.desired_location}")

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
            print(f" Date overlap confirmed! Match found with bid {bid.id}")
    
    print(f"Total matches found: {len(matching_bids)}")
    return matching_bids