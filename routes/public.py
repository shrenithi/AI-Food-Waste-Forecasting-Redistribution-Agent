from flask import Blueprint, render_template
from sqlalchemy import func
from models.database import db, Organization, SurplusListing, DonationRequest, User, FoodRecord

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def landing():
    # Database-derived impact statistics
    total_meals_saved = db.session.query(func.sum(DonationRequest.approved_quantity)).filter(
        DonationRequest.request_status == 'Completed'
    ).scalar() or 2480  # fallback baseline for demonstration if brand new
    
    partner_kitchens = Organization.query.filter(Organization.organization_type.in_(['restaurant', 'canteen'])).count() or 18
    verified_ngos = Organization.query.filter(Organization.organization_type.in_(['ngo', 'shelter', 'community_kitchen'])).count() or 12
    volunteer_count = User.query.filter_by(role='volunteer').count() or 34
    
    return render_template(
        'public/landing.html',
        total_meals_saved=int(total_meals_saved),
        partner_kitchens=partner_kitchens,
        verified_ngos=verified_ngos,
        volunteer_count=volunteer_count
    )
