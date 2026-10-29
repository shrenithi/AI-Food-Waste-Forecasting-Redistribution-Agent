from services.donation_service import DonationService
from models.database import SurplusListing, DonationRequest

def test_cannot_request_more_than_available(app, seed_data):
    with app.app_context():
        listing_id = seed_data['listing_id']
        ngo_org_id = seed_data['ngo_org_id']
        success, msg = DonationService.create_request(
            listing_id=listing_id,
            ngo_org_id=ngo_org_id,
            requested_quantity=100.0, # only 50 available
            pickup_method="Volunteer Delivery"
        )
        assert success is False
        assert "exceeds available quantity" in msg

def test_successful_request_and_approval(app, seed_data):
    with app.app_context():
        listing_id = seed_data['listing_id']
        ngo_org_id = seed_data['ngo_org_id']
        
        # 1. Create Request
        success, req = DonationService.create_request(
            listing_id=listing_id,
            ngo_org_id=ngo_org_id,
            requested_quantity=30.0,
            pickup_method="Volunteer Delivery"
        )
        assert success is True
        assert req.request_status == 'Pending'
        
        # 2. Approve Request
        app_success, msg = DonationService.approve_request(
            request_id=req.id,
            approved_quantity=30.0
        )
        assert app_success is True
        
        # 3. Verify Remaining Quantity Deducted
        updated_listing = SurplusListing.query.get(listing_id)
        assert updated_listing.quantity == 20.0
        assert updated_listing.listing_status == 'Partially Reserved'
