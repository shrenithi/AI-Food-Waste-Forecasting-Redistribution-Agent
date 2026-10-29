import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # 'restaurant', 'ngo', 'volunteer', 'admin'
    account_status = db.Column(db.String(30), default='pending')  # 'pending', 'active', 'suspended'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    organization_memberships = db.relationship('OrganizationMember', backref='user', cascade='all, delete-orphan')
    deliveries = db.relationship('Delivery', backref='volunteer', foreign_keys='Delivery.volunteer_user_id')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')
    complaints_filed = db.relationship('Complaint', backref='reporter', foreign_keys='Complaint.reporter_user_id')
    audit_logs = db.relationship('AuditLog', backref='actor', foreign_keys='AuditLog.actor_user_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    @property
    def organization(self):
        """Helper to get user's primary organization if any."""
        if self.organization_memberships:
            return self.organization_memberships[0].organization
        return None

    def is_verified(self):
        if self.role == 'admin':
            return True
        if self.role == 'volunteer':
            return self.account_status == 'active'
        org = self.organization
        return org is not None and org.verification_status == 'verified' and self.account_status == 'active'


class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    organization_type = db.Column(db.String(50), nullable=False)  # 'restaurant', 'canteen', 'ngo', 'shelter', 'community_kitchen'
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), default='Metro Area')
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(30), nullable=True)
    capacity_portions = db.Column(db.Integer, default=200)
    verification_status = db.Column(db.String(30), default='pending')  # 'pending', 'verified', 'rejected', 'suspended'
    verification_reason = db.Column(db.Text, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    members = db.relationship('OrganizationMember', backref='organization', cascade='all, delete-orphan')
    food_records = db.relationship('FoodRecord', backref='organization', cascade='all, delete-orphan')
    forecasts = db.relationship('Forecast', backref='organization', cascade='all, delete-orphan')
    surplus_listings = db.relationship('SurplusListing', backref='donor', cascade='all, delete-orphan')
    donation_requests = db.relationship('DonationRequest', backref='ngo', cascade='all, delete-orphan')


class OrganizationMember(db.Model):
    __tablename__ = 'organization_members'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_in_org = db.Column(db.String(50), default='owner')  # 'owner', 'manager', 'staff'


class FoodRecord(db.Model):
    __tablename__ = 'food_records'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    food_name = db.Column(db.String(120), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)  # 'Cooked Meals', 'Bakery Items', 'Fresh Produce', 'Dairy Products', 'Packaged Food', 'Beverages'
    record_date = db.Column(db.Date, nullable=False, index=True)
    prepared_quantity = db.Column(db.Float, nullable=False)
    sold_quantity = db.Column(db.Float, nullable=False)
    leftover_quantity = db.Column(db.Float, nullable=False)  # max(0, prepared - sold)
    unit = db.Column(db.String(30), default='portions')  # 'portions', 'kg', 'meal boxes', 'liters'
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    is_holiday = db.Column(db.Boolean, default=False)
    event_flag = db.Column(db.Boolean, default=False)
    weather_temp = db.Column(db.Float, nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Forecast(db.Model):
    __tablename__ = 'forecasts'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    food_name = db.Column(db.String(120), nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    predicted_demand = db.Column(db.Float, nullable=False)
    recommended_quantity = db.Column(db.Float, nullable=False)
    confidence_lower = db.Column(db.Float, nullable=True)
    confidence_upper = db.Column(db.Float, nullable=True)
    mae = db.Column(db.Float, nullable=True)
    rmse = db.Column(db.Float, nullable=True)
    model_version = db.Column(db.String(50), default='RandomForest-v1')
    factors_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def get_factors(self):
        if self.factors_json:
            try:
                return json.loads(self.factors_json)
            except Exception:
                return {}
        return {}


class SurplusListing(db.Model):
    __tablename__ = 'surplus_listings'
    
    id = db.Column(db.Integer, primary_key=True)
    donor_organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    food_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    initial_quantity = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # remaining available quantity
    unit = db.Column(db.String(30), default='portions')
    prepared_at = db.Column(db.DateTime, nullable=False)
    use_by = db.Column(db.DateTime, nullable=False, index=True)
    storage_conditions = db.Column(db.String(100), default='Refrigerated (4°C)')  # 'Ambient (Cool & Dry)', 'Refrigerated (4°C)', 'Hot Holding (60°C+)', 'Frozen (-18°C)'
    dietary_flags = db.Column(db.String(200), default='Vegetarian')  # comma separated: 'Vegetarian, Gluten-Free'
    allergens = db.Column(db.String(200), default='None known')
    pickup_location = db.Column(db.String(255), nullable=False)
    pickup_window_start = db.Column(db.DateTime, nullable=False)
    pickup_window_end = db.Column(db.DateTime, nullable=False)
    safety_declaration = db.Column(db.Boolean, default=True)  # FSSAI guideline compliance declaration
    safety_status = db.Column(db.String(30), default='Eligible')  # 'Eligible', 'Under Review', 'Safety Blocked', 'Expired'
    listing_status = db.Column(db.String(30), default='Available', index=True)  # 'Available', 'Partially Reserved', 'Fully Reserved', 'Completed', 'Cancelled', 'Expired'
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    requests = db.relationship('DonationRequest', backref='listing', cascade='all, delete-orphan')

    def is_currently_eligible(self):
        now = datetime.datetime.utcnow()
        if self.use_by < now:
            return False
        if self.safety_status != 'Eligible':
            return False
        if self.listing_status not in ['Available', 'Partially Reserved']:
            return False
        if self.quantity <= 0:
            return False
        return True


class DonationRequest(db.Model):
    __tablename__ = 'donation_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('surplus_listings.id'), nullable=False, index=True)
    ngo_organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    requested_quantity = db.Column(db.Float, nullable=False)
    approved_quantity = db.Column(db.Float, default=0.0)
    pickup_method = db.Column(db.String(30), default='Volunteer Delivery')  # 'Self-Pickup', 'Volunteer Delivery'
    requested_pickup_time = db.Column(db.DateTime, nullable=True)
    request_status = db.Column(db.String(30), default='Pending', index=True)  # 'Pending', 'Approved', 'Rejected', 'Cancelled', 'Completed'
    rejection_reason = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    delivery = db.relationship('Delivery', backref='donation_request', uselist=False, cascade='all, delete-orphan')


class Delivery(db.Model):
    __tablename__ = 'deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    donation_request_id = db.Column(db.Integer, db.ForeignKey('donation_requests.id'), nullable=False, unique=True)
    volunteer_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    pickup_time = db.Column(db.DateTime, nullable=True)
    picked_up_at = db.Column(db.DateTime, nullable=True)
    in_transit_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    recipient_confirmed_at = db.Column(db.DateTime, nullable=True)
    delivery_status = db.Column(db.String(40), default='Unassigned', index=True)  
    # Transitions: Unassigned -> Assigned -> Accepted -> Picked Up -> In Transit -> Delivered -> Recipient Confirmed (or Failed)
    completion_notes = db.Column(db.Text, nullable=True)
    failure_reason = db.Column(db.String(255), nullable=True)
    estimated_distance_km = db.Column(db.Float, default=4.5)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(30), default='system')  # 'verification', 'request', 'approval', 'delivery', 'safety', 'system'
    is_read = db.Column(db.Boolean, default=False)
    link_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Complaint(db.Model):
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    related_listing_id = db.Column(db.Integer, db.ForeignKey('surplus_listings.id'), nullable=True)
    related_request_id = db.Column(db.Integer, db.ForeignKey('donation_requests.id'), nullable=True)
    complaint_type = db.Column(db.String(60), nullable=False)  # 'Incorrect Food Info', 'Missed Pickup', 'Failed Delivery', 'Suspected Unsafe Food', 'Abusive Behavior'
    description = db.Column(db.Text, nullable=False)
    complaint_status = db.Column(db.String(30), default='Open')  # 'Open', 'Under Review', 'Resolved', 'Dismissed'
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
