import pytest
import os
import datetime
from app import create_app
from config import Config
from models.database import db, User, Organization, OrganizationMember, FoodRecord, SurplusListing, DonationRequest, Delivery

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret'

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def seed_data(app):
    with app.app_context():
        now = datetime.datetime.utcnow()
        # Admin
        admin = User(name="Admin", email="admin@test.com", role="admin", account_status="active")
        admin.set_password("Pass@123")
        db.session.add(admin)

        # Restaurant User & Org
        rest_user = User(name="Chef Test", email="chef@test.com", role="restaurant", account_status="active")
        rest_user.set_password("Pass@123")
        db.session.add(rest_user)
        db.session.flush()

        rest_org = Organization(name="Test Kitchen", organization_type="restaurant", address="10 Test St", verification_status="verified")
        db.session.add(rest_org)
        db.session.flush()
        db.session.add(OrganizationMember(organization_id=rest_org.id, user_id=rest_user.id, role_in_org="owner"))

        # NGO User & Org
        ngo_user = User(name="NGO Test", email="ngo@test.com", role="ngo", account_status="active")
        ngo_user.set_password("Pass@123")
        db.session.add(ngo_user)
        db.session.flush()

        ngo_org = Organization(name="Test Relief", organization_type="ngo", address="20 NGO Ave", capacity_portions=100, verification_status="verified")
        db.session.add(ngo_org)
        db.session.flush()
        db.session.add(OrganizationMember(organization_id=ngo_org.id, user_id=ngo_user.id, role_in_org="owner"))

        # Volunteer User
        vol_user = User(name="Volunteer Test", email="vol@test.com", role="volunteer", account_status="active")
        vol_user.set_password("Pass@123")
        db.session.add(vol_user)
        db.session.flush()

        # Surplus listing
        listing = SurplusListing(
            donor_organization_id=rest_org.id,
            food_name="Test Rice",
            category="Cooked Meals",
            initial_quantity=50.0,
            quantity=50.0,
            unit="portions",
            prepared_at=now - datetime.timedelta(hours=1),
            use_by=now + datetime.timedelta(hours=3),
            storage_conditions="Hot Holding (60 deg C)",
            pickup_location="10 Test St",
            pickup_window_start=now - datetime.timedelta(hours=1),
            pickup_window_end=now + datetime.timedelta(hours=3),
            safety_declaration=True,
            safety_status="Eligible",
            listing_status="Available"
        )
        db.session.add(listing)

        db.session.commit()
        return {
            'admin_id': admin.id,
            'rest_user_id': rest_user.id,
            'rest_org_id': rest_org.id,
            'ngo_user_id': ngo_user.id,
            'ngo_org_id': ngo_org.id,
            'vol_user_id': vol_user.id,
            'listing_id': listing.id
        }
