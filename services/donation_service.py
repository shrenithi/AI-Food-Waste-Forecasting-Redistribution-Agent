import datetime
from models.database import db, SurplusListing, DonationRequest, Delivery, AuditLog, Organization
from services.notification_service import NotificationService
from services.safety_service import FoodSafetyService

class DonationService:
    @staticmethod
    def create_request(listing_id, ngo_org_id, requested_quantity, pickup_method, requested_pickup_time=None, notes=None, actor_user_id=None):
        """
        Creates a donation request from an NGO for a surplus listing.
        Performs food safety eligibility and remaining quantity validation.
        """
        listing = SurplusListing.query.with_for_update().get(listing_id)
        if not listing:
            return False, "Food listing not found."
            
        if FoodSafetyService.check_listing_expiration(listing):
            db.session.commit()
            return False, "This food listing has reached its use-by expiration date and cannot be requested."
            
        if listing.safety_status != 'Eligible':
            return False, f"Listing cannot be requested due to safety status: {listing.safety_status}"
            
        if listing.listing_status not in ['Available', 'Partially Reserved']:
            return False, f"Listing is no longer available (Status: {listing.listing_status})."
            
        if requested_quantity <= 0:
            return False, "Requested quantity must be greater than zero."
            
        if requested_quantity > listing.quantity:
            return False, f"Requested quantity ({requested_quantity}) exceeds available quantity ({listing.quantity} {listing.unit})."

        ngo = Organization.query.get(ngo_org_id)
        if not ngo or ngo.verification_status != 'verified':
            return False, "Only verified NGOs can submit donation requests."
            
        req = DonationRequest(
            listing_id=listing.id,
            ngo_organization_id=ngo_org_id,
            requested_quantity=requested_quantity,
            approved_quantity=0.0,
            pickup_method=pickup_method,
            requested_pickup_time=requested_pickup_time or listing.pickup_window_start,
            request_status='Pending',
            notes=notes
        )
        db.session.add(req)
        
        # Audit log
        audit = AuditLog(
            actor_user_id=actor_user_id,
            action="CREATE_DONATION_REQUEST",
            entity_type="DonationRequest",
            entity_id=req.id,
            details=f"NGO '{ngo.name}' requested {requested_quantity} {listing.unit} of '{listing.food_name}' via {pickup_method}."
        )
        db.session.add(audit)
        
        # Commit transaction
        db.session.commit()
        
        # Notify donor organization
        NotificationService.notify_organization_users(
            org_id=listing.donor_organization_id,
            title="New Donation Request Received",
            message=f"{ngo.name} requested {requested_quantity} {listing.unit} of '{listing.food_name}'.",
            notification_type='request',
            link_url='/restaurant/requests'
        )
        
        return True, req

    @staticmethod
    def approve_request(request_id, approved_quantity, actor_user_id=None):
        """
        Approve an NGO request atomically with database locking.
        Deducts available quantity from listing and spawns a Delivery entry if volunteer transport is chosen.
        """
        req = DonationRequest.query.with_for_update().get(request_id)
        if not req:
            return False, "Donation request not found."
            
        if req.request_status != 'Pending':
            return False, f"Request cannot be approved because it is in '{req.request_status}' status."
            
        listing = SurplusListing.query.with_for_update().get(req.listing_id)
        if not listing:
            return False, "Associated listing not found."
            
        if FoodSafetyService.check_listing_expiration(listing):
            db.session.commit()
            return False, "Listing has expired and cannot be approved."
            
        if approved_quantity <= 0 or approved_quantity > req.requested_quantity:
            return False, f"Approved quantity must be between 1 and {req.requested_quantity}."
            
        if approved_quantity > listing.quantity:
            return False, f"Approved quantity ({approved_quantity}) exceeds remaining available food ({listing.quantity} {listing.unit})."

        # Apply approval
        req.approved_quantity = approved_quantity
        req.request_status = 'Approved'
        req.updated_at = datetime.datetime.utcnow()
        
        # Deduct quantity from listing
        listing.quantity -= approved_quantity
        if listing.quantity <= 0:
            listing.quantity = 0
            listing.listing_status = 'Fully Reserved'
        else:
            listing.listing_status = 'Partially Reserved'
            
        # Create delivery assignment if volunteer delivery requested
        if req.pickup_method == 'Volunteer Delivery':
            delivery = Delivery(
                donation_request_id=req.id,
                delivery_status='Unassigned',
                pickup_time=req.requested_pickup_time or listing.pickup_window_start,
                estimated_distance_km=4.2
            )
            db.session.add(delivery)
        else:
            # Self-Pickup
            delivery = Delivery(
                donation_request_id=req.id,
                delivery_status='Accepted',  # NGO self-pickup
                pickup_time=req.requested_pickup_time or listing.pickup_window_start,
                completion_notes="Self-pickup arranged directly by recipient organization staff."
            )
            db.session.add(delivery)
            
        audit = AuditLog(
            actor_user_id=actor_user_id,
            action="APPROVE_DONATION_REQUEST",
            entity_type="DonationRequest",
            entity_id=req.id,
            details=f"Approved {approved_quantity} {listing.unit} for NGO '{req.ngo.name}'."
        )
        db.session.add(audit)
        
        db.session.commit()
        
        # Notify NGO
        NotificationService.notify_organization_users(
            org_id=req.ngo_organization_id,
            title="Donation Request Approved!",
            message=f"Your request for {approved_quantity} {listing.unit} of '{listing.food_name}' was approved by {listing.donor.name}.",
            notification_type='approval',
            link_url='/ngo/tracking'
        )
        
        return True, "Request successfully approved."

    @staticmethod
    def reject_request(request_id, reason="Capacity unavailable", actor_user_id=None):
        """Reject an NGO donation request."""
        req = DonationRequest.query.get(request_id)
        if not req:
            return False, "Request not found."
            
        if req.request_status != 'Pending':
            return False, f"Request cannot be rejected from '{req.request_status}' status."
            
        req.request_status = 'Rejected'
        req.rejection_reason = reason
        req.updated_at = datetime.datetime.utcnow()
        
        audit = AuditLog(
            actor_user_id=actor_user_id,
            action="REJECT_DONATION_REQUEST",
            entity_type="DonationRequest",
            entity_id=req.id,
            details=f"Rejected request for {req.requested_quantity} portions. Reason: {reason}"
        )
        db.session.add(audit)
        db.session.commit()
        
        NotificationService.notify_organization_users(
            org_id=req.ngo_organization_id,
            title="Donation Request Declined",
            message=f"Your request was declined by donor. Reason: {reason}",
            notification_type='request',
            link_url='/ngo/requests'
        )
        return True, "Request rejected."

    @staticmethod
    def confirm_receipt_by_ngo(request_id, actor_user_id=None):
        """
        Recipient NGO confirms final receipt of food.
        Completes the request and delivery lifecycle.
        """
        req = DonationRequest.query.get(request_id)
        if not req:
            return False, "Request not found."
            
        if req.request_status not in ['Approved', 'In Transit']:
            return False, f"Cannot confirm receipt when status is '{req.request_status}'."
            
        req.request_status = 'Completed'
        req.updated_at = datetime.datetime.utcnow()
        
        if req.delivery:
            req.delivery.delivery_status = 'Recipient Confirmed'
            req.delivery.recipient_confirmed_at = datetime.datetime.utcnow()
            
        # Check if all listings units completed
        listing = req.listing
        if listing.quantity == 0:
            all_requests_done = all(r.request_status in ['Completed', 'Rejected', 'Cancelled'] for r in listing.requests)
            if all_requests_done:
                listing.listing_status = 'Completed'
                
        audit = AuditLog(
            actor_user_id=actor_user_id,
            action="CONFIRM_DONATION_RECEIPT",
            entity_type="DonationRequest",
            entity_id=req.id,
            details=f"NGO '{req.ngo.name}' confirmed safe receipt of {req.approved_quantity} {listing.unit}."
        )
        db.session.add(audit)
        db.session.commit()
        
        # Notify donor and volunteer
        NotificationService.notify_organization_users(
            org_id=listing.donor_organization_id,
            title="Donation Completed & Confirmed!",
            message=f"NGO {req.ngo.name} successfully received {req.approved_quantity} {listing.unit} of '{listing.food_name}'. Thank you for reducing waste!",
            notification_type='delivery',
            link_url='/restaurant/tracking'
        )
        
        if req.delivery and req.delivery.volunteer_user_id:
            NotificationService.send(
                user_id=req.delivery.volunteer_user_id,
                title="Delivery Completed!",
                message=f"NGO {req.ngo.name} confirmed safe delivery receipt. Thank you for your service!",
                notification_type='delivery',
                link_url='/volunteer/history'
            )
            
        return True, "Donation receipt successfully confirmed."
