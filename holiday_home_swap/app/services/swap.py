from sqlalchemy.orm import Session
from app.model import SwapBid, SwapMatch, Home, User
from app.services.matching import find_matching_bids
from app.services.notification import email_service

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
        # Check if the other user has a home in the desired location
        other_home = db.query(Home).filter(
            Home.owner_id == bid.user_id, 
            Home.location == new_bid.desired_location
        ).first()

        if not other_home:
            continue
            
        # Check if the new user's home is in the location the other user wants
        user_home_in_desired_location = db.query(Home).filter(
            Home.owner_id == new_bid.user_id,
            Home.location == bid.desired_location
        ).first()
        
        if not user_home_in_desired_location:
            continue

        # Create the match
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
        
        # Send notifications to both users
        try:
            # Get user details for notifications
            new_bid_user = db.query(User).filter(User.id == new_bid.user_id).first()
            other_bid_user = db.query(User).filter(User.id == bid.user_id).first()
            
            if new_bid_user and other_bid_user:
                # Notify the new bid user
                email_service.send_match_notification(
                    new_bid_user.email, 
                    new_bid_user.name, 
                    new_bid.desired_location
                )
                
                # Notify the other user
                email_service.send_match_notification(
                    other_bid_user.email, 
                    other_bid_user.name, 
                    bid.desired_location
                )
        except Exception as e:
            print(f"Failed to send notification emails: {e}")
        
        return match    

    return None