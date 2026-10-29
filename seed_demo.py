import os
import random
import datetime
import math
from app import create_app
from models.database import (
    db, User, Organization, OrganizationMember, FoodRecord,
    Forecast, SurplusListing, DonationRequest, Delivery,
    Notification, Complaint, AuditLog
)
from services.forecasting import forecaster

def seed_database():
    app = create_app()
    with app.app_context():
        print("[INFO] Seeding FoodRescue AI demonstration database...")
        db.drop_all()
        db.create_all()

        now = datetime.datetime.utcnow()
        today = datetime.date.today()

        # 1. Create Users
        admin_user = User(
            name="System Administrator",
            email="admin@foodrescue.ai",
            phone="+91 98888 11111",
            role="admin",
            account_status="active"
        )
        admin_user.set_password("Admin@123")
        db.session.add(admin_user)

        chef_user = User(
            name="Chef Vikram Sharma",
            email="chef@greengarden.com",
            phone="+91 98765 12345",
            role="restaurant",
            account_status="active"
        )
        chef_user.set_password("Chef@123")
        db.session.add(chef_user)

        canteen_user = User(
            name="Priya Nair (Manager)",
            email="manager@centralcanteen.edu",
            phone="+91 98765 23456",
            role="restaurant",
            account_status="active"
        )
        canteen_user.set_password("Chef@123")
        db.session.add(canteen_user)

        ngo_user = User(
            name="Arun Verma (Director)",
            email="contact@cityrelief.org",
            phone="+91 98765 34567",
            role="ngo",
            account_status="active"
        )
        ngo_user.set_password("Ngo@123")
        db.session.add(ngo_user)

        ngo2_user = User(
            name="Sister Clara",
            email="trust@hopeshelter.org",
            phone="+91 98765 45678",
            role="ngo",
            account_status="active"
        )
        ngo2_user.set_password("Ngo@123")
        db.session.add(ngo2_user)

        volunteer_user = User(
            name="Alex D'Souza",
            email="alex@volunteer.com",
            phone="+91 98765 56789",
            role="volunteer",
            account_status="active"
        )
        volunteer_user.set_password("Volunteer@123")
        db.session.add(volunteer_user)

        volunteer2_user = User(
            name="Maria Santos",
            email="maria@volunteer.com",
            phone="+91 98765 67890",
            role="volunteer",
            account_status="active"
        )
        volunteer2_user.set_password("Volunteer@123")
        db.session.add(volunteer2_user)

        db.session.flush()

        # 2. Create Organizations
        org_bistro = Organization(
            name="Green Garden Bistro",
            organization_type="restaurant",
            address="14 MG Road, Brigade Junction",
            city="Metro Center",
            latitude=12.9716,
            longitude=77.5946,
            contact_email="chef@greengarden.com",
            contact_phone="+91 98765 12345",
            capacity_portions=250,
            verification_status="verified",
            verification_reason="Inspected and approved by municipal food safety authority."
        )
        db.session.add(org_bistro)

        org_canteen = Organization(
            name="Campus Central Canteen",
            organization_type="canteen",
            address="Engineering Block 3, Tech University Campus",
            city="University District",
            latitude=12.9352,
            longitude=77.6245,
            contact_email="manager@centralcanteen.edu",
            contact_phone="+91 98765 23456",
            capacity_portions=400,
            verification_status="verified",
            verification_reason="Institutional catering license verified."
        )
        db.session.add(org_canteen)

        org_city_relief = Organization(
            name="City Food Relief NGO",
            organization_type="ngo",
            address="45 Residency Road, Shanthi Nagar",
            city="Metro Center",
            latitude=12.9620,
            longitude=77.5990,
            contact_email="contact@cityrelief.org",
            contact_phone="+91 98765 34567",
            capacity_portions=180,
            verification_status="verified",
            verification_reason="80G certified NGO registration validated."
        )
        db.session.add(org_city_relief)

        org_hope_shelter = Organization(
            name="Hope Shelter Trust",
            organization_type="shelter",
            address="89 Victoria Layout, Austin Town",
            city="East Metro",
            latitude=12.9645,
            longitude=77.6180,
            contact_email="trust@hopeshelter.org",
            contact_phone="+91 98765 45678",
            capacity_portions=120,
            verification_status="verified",
            verification_reason="Community shelter charter approved."
        )
        db.session.add(org_hope_shelter)

        # Pending Organization for admin verification demo
        org_pending = Organization(
            name="Sunrise Bakery & Cafe",
            organization_type="restaurant",
            address="204 Indiranagar 100ft Road",
            city="East Metro",
            latitude=12.9784,
            longitude=77.6408,
            contact_email="contact@sunrisebakery.com",
            contact_phone="+91 98765 99999",
            capacity_portions=100,
            verification_status="pending",
            verification_reason=None
        )
        db.session.add(org_pending)
        db.session.flush()

        # Memberships
        db.session.add(OrganizationMember(organization_id=org_bistro.id, user_id=chef_user.id, role_in_org="owner"))
        db.session.add(OrganizationMember(organization_id=org_canteen.id, user_id=canteen_user.id, role_in_org="owner"))
        db.session.add(OrganizationMember(organization_id=org_city_relief.id, user_id=ngo_user.id, role_in_org="owner"))
        db.session.add(OrganizationMember(organization_id=org_hope_shelter.id, user_id=ngo2_user.id, role_in_org="owner"))
        db.session.commit()

        # 3. Generate Historical Food Records (35 days of historical data)
        print("[DATA] Generating 35 days of historical food preparation & sales records...")
        dishes = [
            {"name": "Vegetable Biryani", "cat": "Cooked Meals", "base": 65, "unit": "portions"},
            {"name": "Dal Makhani & Roti", "cat": "Cooked Meals", "base": 50, "unit": "portions"},
            {"name": "Paneer Butter Masala", "cat": "Cooked Meals", "base": 45, "unit": "portions"},
            {"name": "Mediterranean Pasta", "cat": "Cooked Meals", "base": 40, "unit": "portions"},
            {"name": "Fresh Garden Salad", "cat": "Fresh Produce", "base": 30, "unit": "portions"},
            {"name": "Assorted Sandwiches", "cat": "Bakery Items", "base": 35, "unit": "portions"}
        ]

        random.seed(42)
        records_to_train = []

        for days_back in range(35, -1, -1):
            rec_date = today - datetime.timedelta(days=days_back)
            dow = rec_date.weekday()
            is_weekend = dow in [4, 5, 6]  # Fri, Sat, Sun
            is_hol = (days_back in [7, 21])
            is_event = (days_back in [3, 14, 28])
            temp = round(24.0 + random.uniform(0, 6.0), 1)

            for d in dishes:
                # Demand factors
                dow_factor = 1.25 if is_weekend else 0.92
                event_factor = 1.20 if is_event else 1.0
                hol_factor = 0.85 if is_hol else 1.0
                noise = random.uniform(0.9, 1.1)

                expected_sold = d["base"] * dow_factor * event_factor * hol_factor * noise
                sold_qty = round(max(10.0, expected_sold), 1)

                # Restaurant typically over-prepares by 8% to 20%
                prep_buffer = random.uniform(1.08, 1.22)
                prep_qty = round(math.ceil(sold_qty * prep_buffer), 1)
                leftover_qty = max(0.0, round(prep_qty - sold_qty, 1))

                rec = FoodRecord(
                    organization_id=org_bistro.id,
                    food_name=d["name"],
                    category=d["cat"],
                    record_date=rec_date,
                    prepared_quantity=prep_qty,
                    sold_quantity=sold_qty,
                    leftover_quantity=leftover_qty,
                    unit=d["unit"],
                    day_of_week=dow,
                    is_holiday=is_hol,
                    event_flag=is_event,
                    weather_temp=temp,
                    notes="Standard shift logging"
                )
                db.session.add(rec)
                records_to_train.append(rec)

        db.session.commit()

        # 4. Train AI Models & Persist via Joblib
        print("[MODEL] Training RandomForest demand models and persisting...")
        for d in dishes:
            recs = FoodRecord.query.filter_by(organization_id=org_bistro.id, food_name=d["name"]).all()
            train_res = forecaster.train(org_bistro.id, d["name"], recs)
            print(f"   Model for '{d['name']}': MAE={train_res['mae']}, RMSE={train_res['rmse']}")

        # 5. Create Active Surplus Listings
        print("[SURPLUS] Creating active surplus listings in marketplace...")
        listing1 = SurplusListing(
            donor_organization_id=org_bistro.id,
            food_name="Fresh Vegetable Biryani",
            category="Cooked Meals",
            initial_quantity=45.0,
            quantity=25.0,  # 20 portions claimed
            unit="portions",
            prepared_at=now - datetime.timedelta(hours=1),
            use_by=now + datetime.timedelta(hours=3),
            storage_conditions="Hot Holding (60 deg C or above)",
            dietary_flags="Vegetarian, Halal",
            allergens="None known",
            pickup_location="14 MG Road, Brigade Junction (Kitchen Rear Gate)",
            pickup_window_start=now - datetime.timedelta(hours=1),
            pickup_window_end=now + datetime.timedelta(hours=3),
            safety_declaration=True,
            safety_status="Eligible",
            listing_status="Partially Reserved",
            image_url="https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&auto=format&fit=crop"
        )
        db.session.add(listing1)

        listing2 = SurplusListing(
            donor_organization_id=org_bistro.id,
            food_name="Mediterranean Penne Pasta",
            category="Cooked Meals",
            initial_quantity=30.0,
            quantity=30.0,
            unit="portions",
            prepared_at=now - datetime.timedelta(hours=2),
            use_by=now + datetime.timedelta(hours=4),
            storage_conditions="Refrigerated (4 deg C or below)",
            dietary_flags="Vegetarian",
            allergens="Gluten, Dairy",
            pickup_location="14 MG Road, Brigade Junction",
            pickup_window_start=now - datetime.timedelta(hours=2),
            pickup_window_end=now + datetime.timedelta(hours=4),
            safety_declaration=True,
            safety_status="Eligible",
            listing_status="Available",
            image_url="https://images.unsplash.com/photo-1621996346565-e3d5d62817d2?w=600&auto=format&fit=crop"
        )
        db.session.add(listing2)

        listing3 = SurplusListing(
            donor_organization_id=org_canteen.id,
            food_name="Packaged Bread & Wholewheat Rolls",
            category="Bakery Items",
            initial_quantity=50.0,
            quantity=50.0,
            unit="meal boxes",
            prepared_at=now - datetime.timedelta(hours=3),
            use_by=now + datetime.timedelta(hours=24),
            storage_conditions="Ambient (Cool & Dry Place)",
            dietary_flags="Vegetarian, Vegan",
            allergens="Gluten",
            pickup_location="Campus Central Canteen, Loading Dock B",
            pickup_window_start=now - datetime.timedelta(hours=3),
            pickup_window_end=now + datetime.timedelta(hours=24),
            safety_declaration=True,
            safety_status="Eligible",
            listing_status="Available",
            image_url="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&auto=format&fit=crop"
        )
        db.session.add(listing3)
        db.session.flush()

        # 6. Donation Requests & Deliveries
        print("[DISPATCH] Creating donation requests and volunteer dispatches...")
        
        # Request 1: Approved and currently In Transit by volunteer
        req1 = DonationRequest(
            listing_id=listing1.id,
            ngo_organization_id=org_city_relief.id,
            requested_quantity=20.0,
            approved_quantity=20.0,
            pickup_method="Volunteer Delivery",
            request_status="Approved",
            notes="For evening youth center meal service."
        )
        db.session.add(req1)
        db.session.flush()

        del1 = Delivery(
            donation_request_id=req1.id,
            volunteer_user_id=volunteer_user.id,
            pickup_time=now - datetime.timedelta(minutes=45),
            picked_up_at=now - datetime.timedelta(minutes=30),
            in_transit_at=now - datetime.timedelta(minutes=15),
            delivery_status="In Transit",
            estimated_distance_km=3.8
        )
        db.session.add(del1)

        # Request 2: Completed and Recipient Confirmed
        req2 = DonationRequest(
            listing_id=listing1.id,
            ngo_organization_id=org_hope_shelter.id,
            requested_quantity=15.0,
            approved_quantity=15.0,
            pickup_method="Volunteer Delivery",
            request_status="Completed",
            notes="Dinner distribution for 15 residents."
        )
        db.session.add(req2)
        db.session.flush()

        del2 = Delivery(
            donation_request_id=req2.id,
            volunteer_user_id=volunteer_user.id,
            pickup_time=now - datetime.timedelta(hours=5),
            picked_up_at=now - datetime.timedelta(hours=4, minutes=45),
            in_transit_at=now - datetime.timedelta(hours=4, minutes=30),
            delivered_at=now - datetime.timedelta(hours=4),
            recipient_confirmed_at=now - datetime.timedelta(hours=3, minutes=50),
            delivery_status="Recipient Confirmed",
            completion_notes="Inspected by shelter manager. 15 meal boxes handed over in excellent condition.",
            estimated_distance_km=4.5
        )
        db.session.add(del2)

        # 7. Sample Complaints
        comp1 = Complaint(
            reporter_user_id=ngo_user.id,
            related_listing_id=listing1.id,
            related_request_id=req1.id,
            complaint_type="Incorrect Food Info",
            description="Spice level was higher than indicated for children.",
            complaint_status="Resolved",
            resolution_notes="Contacted restaurant chef to include spicy level tags in future listings.",
            resolved_by=admin_user.id,
            resolved_at=now
        )
        db.session.add(comp1)

        # 8. Notifications
        db.session.add(Notification(
            user_id=chef_user.id,
            title="Volunteer Courier Dispatched",
            message="Volunteer Alex D'Souza has picked up 20 portions of Vegetable Biryani.",
            notification_type="delivery",
            is_read=False
        ))
        db.session.add(Notification(
            user_id=ngo_user.id,
            title="Food In Transit",
            message="Courier is en route with your dinner shipment (~15 mins away).",
            notification_type="delivery",
            is_read=False
        ))

        # 9. Audit Logs
        db.session.add(AuditLog(
            actor_user_id=admin_user.id,
            action="VERIFY_ORGANIZATION",
            entity_type="Organization",
            entity_id=org_bistro.id,
            details="Admin approved Green Garden Bistro."
        ))
        db.session.add(AuditLog(
            actor_user_id=chef_user.id,
            action="PUBLISH_SURPLUS",
            entity_type="SurplusListing",
            entity_id=listing1.id,
            details="Published 45 portions of Fresh Vegetable Biryani with FSSAI declaration."
        ))
        db.session.add(AuditLog(
            actor_user_id=ngo_user.id,
            action="CREATE_REQUEST",
            entity_type="DonationRequest",
            entity_id=req1.id,
            details="Requested 20 portions via volunteer delivery."
        ))

        db.session.commit()
        print("[SUCCESS] FoodRescue AI database successfully seeded with realistic demonstration dataset!")

if __name__ == '__main__':
    seed_database()
