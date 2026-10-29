from services.donation_service import DonationService
from services.delivery_service import DeliveryService
from models.database import Delivery, DonationRequest

def test_delivery_status_state_machine(app, seed_data):
    with app.app_context():
        listing_id = seed_data['listing_id']
        ngo_org_id = seed_data['ngo_org_id']
        vol_user_id = seed_data['vol_user_id']
        
        # Create & approve request
        _, req = DonationService.create_request(listing_id, ngo_org_id, 20.0, "Volunteer Delivery")
        DonationService.approve_request(req.id, 20.0)
        
        delivery = Delivery.query.filter_by(donation_request_id=req.id).first()
        assert delivery is not None
        assert delivery.delivery_status == 'Unassigned'
        
        # 1. Accept assignment
        ok, _ = DeliveryService.accept_delivery(delivery.id, vol_user_id)
        assert ok is True
        
        # 2. Invalid jump from Accepted to Delivered directly should be rejected
        ok, msg = DeliveryService.update_status(delivery.id, 'Delivered', vol_user_id)
        assert ok is False
        assert "Invalid status transition" in msg
        
        # 3. Picked Up
        ok, _ = DeliveryService.update_status(delivery.id, 'Picked Up', vol_user_id)
        assert ok is True
        
        # 4. In Transit
        ok, _ = DeliveryService.update_status(delivery.id, 'In Transit', vol_user_id)
        assert ok is True
        
        # 5. Delivered
        ok, _ = DeliveryService.update_status(delivery.id, 'Delivered', vol_user_id)
        assert ok is True
        
        # 6. NGO Confirms Receipt
        ok, msg = DonationService.confirm_receipt_by_ngo(req.id)
        assert ok is True
        
        updated_del = Delivery.query.get(delivery.id)
        assert updated_del.delivery_status == 'Recipient Confirmed'
