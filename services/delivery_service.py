import datetime
from models.database import db, Delivery, AuditLog, User
from services.notification_service import NotificationService

class DeliveryService:
    """
    Enforces strict status transition validation for food rescue deliveries.
    Valid sequence:
    Unassigned -> Accepted -> Picked Up -> In Transit -> Delivered -> Recipient Confirmed
    (or -> Failed)
    """

    VALID_TRANSITIONS = {
        'Unassigned': ['Accepted'],
        'Assigned': ['Accepted', 'Failed'],
        'Accepted': ['Picked Up', 'Failed'],
        'Picked Up': ['In Transit', 'Failed'],
        'In Transit': ['Delivered', 'Failed'],
        'Delivered': ['Recipient Confirmed'],
        'Recipient Confirmed': [],
        'Failed': []
    }

    @classmethod
    def can_transition(cls, current_status, new_status):
        return new_status in cls.VALID_TRANSITIONS.get(current_status, [])

    @classmethod
    def accept_delivery(cls, delivery_id, volunteer_user_id):
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return False, "Delivery assignment not found."
            
        volunteer = User.query.get(volunteer_user_id)
        if not volunteer or volunteer.role != 'volunteer' or volunteer.account_status != 'active':
            return False, "Only active verified volunteers can accept delivery assignments."
            
        if delivery.delivery_status not in ['Unassigned', 'Assigned']:
            return False, f"Assignment cannot be accepted from '{delivery.delivery_status}' status."
            
        delivery.volunteer_user_id = volunteer_user_id
        delivery.delivery_status = 'Accepted'
        
        audit = AuditLog(
            actor_user_id=volunteer_user_id,
            action="ACCEPT_DELIVERY_ASSIGNMENT",
            entity_type="Delivery",
            entity_id=delivery.id,
            details=f"Volunteer '{volunteer.name}' accepted delivery for donation request #{delivery.donation_request_id}."
        )
        db.session.add(audit)
        db.session.commit()
        
        # Notify donor and NGO
        req = delivery.donation_request
        NotificationService.notify_organization_users(
            org_id=req.listing.donor_organization_id,
            title="Volunteer Assigned for Pickup",
            message=f"Volunteer {volunteer.name} ({volunteer.phone or 'Contact on dashboard'}) accepted the pickup.",
            notification_type='delivery',
            link_url='/restaurant/tracking'
        )
        NotificationService.notify_organization_users(
            org_id=req.ngo_organization_id,
            title="Volunteer Assigned to Deliver Food",
            message=f"Volunteer {volunteer.name} will transport {req.approved_quantity} {req.listing.unit} to your location.",
            notification_type='delivery',
            link_url='/ngo/tracking'
        )
        return True, "Assignment successfully accepted."

    @classmethod
    def update_status(cls, delivery_id, new_status, volunteer_user_id=None, notes=None, failure_reason=None):
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return False, "Delivery not found."
            
        if volunteer_user_id and delivery.volunteer_user_id != volunteer_user_id:
            return False, "Unauthorized: You are not the assigned volunteer for this delivery."
            
        if not cls.can_transition(delivery.delivery_status, new_status):
            return False, f"Invalid status transition from '{delivery.delivery_status}' to '{new_status}'."

        now = datetime.datetime.utcnow()
        delivery.delivery_status = new_status
        
        if new_status == 'Picked Up':
            delivery.picked_up_at = now
        elif new_status == 'In Transit':
            delivery.in_transit_at = now
        elif new_status == 'Delivered':
            delivery.delivered_at = now
            if notes:
                delivery.completion_notes = notes
        elif new_status == 'Failed':
            delivery.failure_reason = failure_reason or notes or "Delivery cancelled or encounter error."
            
        audit = AuditLog(
            actor_user_id=volunteer_user_id,
            action=f"UPDATE_DELIVERY_{new_status.upper().replace(' ', '_')}",
            entity_type="Delivery",
            entity_id=delivery.id,
            details=f"Delivery status changed to '{new_status}'. Notes: {notes or ''} {failure_reason or ''}"
        )
        db.session.add(audit)
        db.session.commit()
        
        req = delivery.donation_request
        if new_status == 'Picked Up':
            NotificationService.notify_organization_users(
                org_id=req.ngo_organization_id,
                title="Food Picked Up - Heading Your Way",
                message=f"Volunteer collected food from {req.listing.donor.name} and will start transit shortly.",
                notification_type='delivery',
                link_url='/ngo/tracking'
            )
        elif new_status == 'Delivered':
            NotificationService.notify_organization_users(
                org_id=req.ngo_organization_id,
                title="Food Delivered - Please Confirm Receipt",
                message=f"Volunteer delivered {req.approved_quantity} {req.listing.unit} to your premises. Please confirm receipt.",
                notification_type='delivery',
                link_url='/ngo/tracking'
            )
            
        return True, f"Delivery status updated to {new_status}."
