import datetime
import io
import csv
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from models.database import db, SurplusListing, DonationRequest, Delivery, Organization
from routes.decorators import role_required
from services.matching_service import SmartMatchingService
from services.donation_service import DonationService
from services.safety_service import FoodSafetyService

ngo_bp = Blueprint('ngo', __name__, url_prefix='/ngo')

@ngo_bp.route('/dashboard')
@login_required
@role_required('ngo')
def dashboard():
    org = current_user.organization
    if not org:
        flash('No organization associated with this account.', 'danger')
        return redirect(url_for('public.landing'))
        
    now = datetime.datetime.utcnow()
    
    # Metrics
    available_listings_count = SurplusListing.query.filter(
        SurplusListing.listing_status.in_(['Available', 'Partially Reserved']),
        SurplusListing.safety_status == 'Eligible',
        SurplusListing.use_by > now,
        SurplusListing.quantity > 0
    ).count()
    
    pending_requests_count = DonationRequest.query.filter_by(
        ngo_organization_id=org.id,
        request_status='Pending'
    ).count()
    
    approved_requests_count = DonationRequest.query.filter_by(
        ngo_organization_id=org.id,
        request_status='Approved'
    ).count()
    
    completed_donations_count = DonationRequest.query.filter_by(
        ngo_organization_id=org.id,
        request_status='Completed'
    ).count()
    
    # Smart NGO matches
    smart_matches = SmartMatchingService.find_matches_for_ngo(org, max_results=3)
    
    # Recent requests
    recent_requests = DonationRequest.query.filter_by(ngo_organization_id=org.id)\
        .order_by(DonationRequest.created_at.desc()).limit(5).all()
        
    return render_template(
        'ngo/dashboard.html',
        org=org,
        available_listings_count=available_listings_count,
        pending_requests_count=pending_requests_count,
        approved_requests_count=approved_requests_count,
        completed_donations_count=completed_donations_count,
        smart_matches=smart_matches,
        recent_requests=recent_requests
    )

@ngo_bp.route('/marketplace')
@login_required
@role_required('ngo')
def marketplace():
    org = current_user.organization
    now = datetime.datetime.utcnow()
    
    # Base query for eligible listings
    query = SurplusListing.query.filter(
        SurplusListing.listing_status.in_(['Available', 'Partially Reserved']),
        SurplusListing.safety_status == 'Eligible',
        SurplusListing.quantity > 0,
        SurplusListing.use_by > now
    )
    
    category = request.args.get('category', 'All')
    search = request.args.get('search', '').strip()
    dietary = request.args.get('dietary', '')
    
    if category and category != 'All':
        query = query.filter(SurplusListing.category == category)
    if search:
        query = query.filter(SurplusListing.food_name.ilike(f'%{search}%'))
    if dietary:
        query = query.filter(SurplusListing.dietary_flags.ilike(f'%{dietary}%'))
        
    listings = query.order_by(SurplusListing.use_by.asc()).all()
    
    # Enhance listings with distance and time-to-expire
    enhanced_listings = []
    for l in listings:
        dist = SmartMatchingService.calculate_distance(
            org.latitude if org else None, org.longitude if org else None,
            l.donor.latitude if l.donor else None, l.donor.longitude if l.donor else None
        )
        hrs_left = round(max(0.1, (l.use_by - now).total_seconds() / 3600.0), 1)
        enhanced_listings.append({
            'listing': l,
            'distance_km': dist,
            'hrs_left': hrs_left
        })
        
    categories = ['All'] + FoodSafetyService.FOOD_CATEGORIES
    
    return render_template(
        'ngo/marketplace.html',
        org=org,
        listings=enhanced_listings,
        categories=categories,
        current_category=category,
        search_query=search,
        current_dietary=dietary
    )

@ngo_bp.route('/listing/<int:listing_id>', methods=['GET', 'POST'])
@login_required
@role_required('ngo')
def listing_detail(listing_id):
    org = current_user.organization
    listing = SurplusListing.query.get_or_404(listing_id)
    now = datetime.datetime.utcnow()
    
    if request.method == 'POST':
        qty = float(request.form.get('requested_quantity', 1.0))
        pickup_method = request.form.get('pickup_method', 'Volunteer Delivery')
        notes = request.form.get('notes', '')
        
        success, res = DonationService.create_request(
            listing_id=listing.id,
            ngo_org_id=org.id,
            requested_quantity=qty,
            pickup_method=pickup_method,
            notes=notes,
            actor_user_id=current_user.id
        )
        if success:
            flash(f'Your request for {qty} {listing.unit} of "{listing.food_name}" has been sent to {listing.donor.name}!', 'success')
            return redirect(url_for('ngo.my_requests'))
        else:
            flash(res, 'danger')
            
    dist = SmartMatchingService.calculate_distance(
        org.latitude if org else None, org.longitude if org else None,
        listing.donor.latitude if listing.donor else None, listing.donor.longitude if listing.donor else None
    )
    hrs_left = round(max(0.1, (listing.use_by - now).total_seconds() / 3600.0), 1)
    
    return render_template(
        'ngo/listing_detail.html',
        org=org,
        listing=listing,
        distance_km=dist,
        hrs_left=hrs_left
    )

@ngo_bp.route('/requests')
@login_required
@role_required('ngo')
def my_requests():
    org = current_user.organization
    requests_list = DonationRequest.query.filter_by(ngo_organization_id=org.id)\
        .order_by(DonationRequest.created_at.desc()).all()
    return render_template('ngo/my_requests.html', org=org, requests=requests_list)

@ngo_bp.route('/requests/<int:request_id>/cancel', methods=['POST'])
@login_required
@role_required('ngo')
def cancel_request(request_id):
    org = current_user.organization
    req = DonationRequest.query.filter_by(id=request_id, ngo_organization_id=org.id).first_or_404()
    if req.request_status == 'Pending':
        req.request_status = 'Cancelled'
        db.session.commit()
        flash('Donation request cancelled.', 'info')
    else:
        flash('Only pending requests can be cancelled.', 'warning')
    return redirect(url_for('ngo.my_requests'))

@ngo_bp.route('/tracking')
@login_required
@role_required('ngo')
def tracking():
    org = current_user.organization
    active_requests = DonationRequest.query.filter(
        DonationRequest.ngo_organization_id == org.id,
        DonationRequest.request_status.in_(['Approved', 'Completed'])
    ).order_by(DonationRequest.updated_at.desc()).all()
    return render_template('ngo/tracking.html', org=org, requests=active_requests)

@ngo_bp.route('/requests/<int:request_id>/confirm-receipt', methods=['POST'])
@login_required
@role_required('ngo')
def confirm_receipt(request_id):
    org = current_user.organization
    req = DonationRequest.query.filter_by(id=request_id, ngo_organization_id=org.id).first_or_404()
    success, msg = DonationService.confirm_receipt_by_ngo(req.id, actor_user_id=current_user.id)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('ngo.tracking'))

@ngo_bp.route('/history')
@login_required
@role_required('ngo')
def history():
    org = current_user.organization
    completed = DonationRequest.query.filter_by(
        ngo_organization_id=org.id,
        request_status='Completed'
    ).order_by(DonationRequest.updated_at.desc()).all()
    
    total_received = sum(r.approved_quantity for r in completed)
    
    return render_template('ngo/history.html', org=org, completed=completed, total_received=total_received)

@ngo_bp.route('/history/export-csv')
@login_required
@role_required('ngo')
def export_csv():
    org = current_user.organization
    completed = DonationRequest.query.filter_by(ngo_organization_id=org.id, request_status='Completed').all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Request ID', 'Food Name', 'Donor Organization', 'Quantity Received', 'Unit', 'Pickup Method', 'Date Received'])
    
    for c in completed:
        writer.writerow([
            c.id,
            c.listing.food_name if c.listing else '',
            c.listing.donor.name if c.listing and c.listing.donor else '',
            c.approved_quantity,
            c.listing.unit if c.listing else 'portions',
            c.pickup_method,
            c.updated_at.strftime('%Y-%m-%d %H:%M')
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=foodrescue_{org.name.replace(' ', '_')}_history.csv"}
    )
