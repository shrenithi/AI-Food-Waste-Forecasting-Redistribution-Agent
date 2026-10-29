import datetime
import io
import csv
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func
from models.database import db, User, Organization, SurplusListing, DonationRequest, Delivery, Complaint, AuditLog, FoodRecord
from routes.decorators import role_required
from services.notification_service import NotificationService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin_root():
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login', role='admin'))

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    total_restaurants = Organization.query.filter(Organization.organization_type.in_(['restaurant', 'canteen'])).count()
    total_ngos = Organization.query.filter(Organization.organization_type.in_(['ngo', 'shelter', 'community_kitchen'])).count()
    total_volunteers = User.query.filter_by(role='volunteer').count()
    pending_verifications = Organization.query.filter_by(verification_status='pending').count()
    
    now = datetime.datetime.utcnow()
    active_listings = SurplusListing.query.filter(
        SurplusListing.listing_status.in_(['Available', 'Partially Reserved']),
        SurplusListing.use_by > now
    ).count()
    
    pending_requests = DonationRequest.query.filter_by(request_status='Pending').count()
    completed_donations = DonationRequest.query.filter_by(request_status='Completed').count()
    
    total_redistributed = db.session.query(func.sum(DonationRequest.approved_quantity)).filter(
        DonationRequest.request_status == 'Completed'
    ).scalar() or 0.0
    
    total_leftovers = db.session.query(func.sum(FoodRecord.leftover_quantity)).scalar() or 0.0
    total_prepared = db.session.query(func.sum(FoodRecord.prepared_quantity)).scalar() or 0.0
    
    waste_reduction_rate = round((total_redistributed / total_leftovers * 100), 1) if total_leftovers > 0 else 0.0
    
    recent_complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(5).all()
    recent_audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
    
    return render_template(
        'admin/dashboard.html',
        total_restaurants=total_restaurants,
        total_ngos=total_ngos,
        total_volunteers=total_volunteers,
        pending_verifications=pending_verifications,
        active_listings=active_listings,
        pending_requests=pending_requests,
        completed_donations=completed_donations,
        total_redistributed=round(total_redistributed, 1),
        total_leftovers=round(total_leftovers, 1),
        total_prepared=round(total_prepared, 1),
        waste_reduction_rate=waste_reduction_rate,
        recent_complaints=recent_complaints,
        recent_audits=recent_audits
    )

@admin_bp.route('/verifications')
@login_required
@role_required('admin')
def verifications():
    pending_orgs = Organization.query.filter_by(verification_status='pending').order_by(Organization.created_at.desc()).all()
    all_orgs = Organization.query.order_by(Organization.created_at.desc()).all()
    return render_template('admin/verifications.html', pending_orgs=pending_orgs, all_orgs=all_orgs)

@admin_bp.route('/verifications/<int:org_id>/<action>', methods=['POST'])
@login_required
@role_required('admin')
def review_verification(org_id, action):
    org = Organization.query.get_or_404(org_id)
    reason = request.form.get('reason', '')
    
    if action == 'approve':
        org.verification_status = 'verified'
        org.verification_reason = reason or "Verified by administrator review."
        org.verified_at = datetime.datetime.utcnow()
        # Activate owner
        for m in org.members:
            m.user.account_status = 'active'
        flash(f'Organization "{org.name}" has been approved!', 'success')
    elif action == 'reject':
        org.verification_status = 'rejected'
        org.verification_reason = reason or "Failed administrative documentation checks."
        flash(f'Organization "{org.name}" application was rejected.', 'warning')
    elif action == 'suspend':
        org.verification_status = 'suspended'
        org.verification_reason = reason or "Suspended due to compliance policy review."
        for m in org.members:
            m.user.account_status = 'suspended'
        flash(f'Organization "{org.name}" was suspended.', 'danger')
        
    audit = AuditLog(
        actor_user_id=current_user.id,
        action=f"VERIFICATION_{action.upper()}",
        entity_type="Organization",
        entity_id=org.id,
        details=f"Admin {action}ed organization '{org.name}'. Reason: {reason}"
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notify users
    NotificationService.notify_organization_users(
        org_id=org.id,
        title=f"Organization Status: {org.verification_status.capitalize()}",
        message=f"Your organization account is now {org.verification_status}. Notes: {org.verification_reason}",
        notification_type='verification'
    )
    return redirect(url_for('admin.verifications'))

@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    role_filter = request.args.get('role', '')
    search = request.args.get('search', '').strip()
    
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    if search:
        query = query.filter((User.name.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%')))
        
    user_list = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=user_list, current_role=role_filter, search=search)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot suspend your own admin account.', 'warning')
        return redirect(url_for('admin.users'))
        
    new_status = 'suspended' if user.account_status == 'active' else 'active'
    user.account_status = new_status
    
    audit = AuditLog(
        actor_user_id=current_user.id,
        action="USER_STATUS_CHANGE",
        entity_type="User",
        entity_id=user.id,
        details=f"User '{user.name}' ({user.email}) status set to {new_status}."
    )
    db.session.add(audit)
    db.session.commit()
    flash(f"User {user.name} is now {new_status}.", 'info')
    return redirect(url_for('admin.users'))

@admin_bp.route('/listings')
@login_required
@role_required('admin')
def listings():
    search = request.args.get('search', '').strip()
    query = SurplusListing.query
    if search:
        query = query.filter(SurplusListing.food_name.ilike(f'%{search}%'))
    listings_list = query.order_by(SurplusListing.created_at.desc()).all()
    return render_template('admin/listings.html', listings=listings_list, search=search)

@admin_bp.route('/listings/<int:listing_id>/moderate', methods=['POST'])
@login_required
@role_required('admin')
def moderate_listing(listing_id):
    listing = SurplusListing.query.get_or_404(listing_id)
    action = request.form.get('action')
    reason = request.form.get('reason', 'Administrative moderation.')
    
    if action == 'block':
        listing.safety_status = 'Safety Blocked'
        listing.listing_status = 'Cancelled'
        flash(f'Listing #{listing.id} has been blocked on safety grounds.', 'danger')
    elif action == 'remove':
        listing.listing_status = 'Cancelled'
        flash(f'Listing #{listing.id} removed.', 'warning')
        
    audit = AuditLog(
        actor_user_id=current_user.id,
        action=f"LISTING_{action.upper()}",
        entity_type="SurplusListing",
        entity_id=listing.id,
        details=f"Listing #{listing.id} ({listing.food_name}) was {action}ed. Reason: {reason}"
    )
    db.session.add(audit)
    db.session.commit()
    return redirect(url_for('admin.listings'))

@admin_bp.route('/complaints', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def complaints():
    if request.method == 'POST':
        complaint_id = int(request.form.get('complaint_id'))
        status = request.form.get('status')
        resolution = request.form.get('resolution_notes')
        
        comp = Complaint.query.get_or_404(complaint_id)
        comp.complaint_status = status
        comp.resolution_notes = resolution
        comp.resolved_by = current_user.id
        if status == 'Resolved':
            comp.resolved_at = datetime.datetime.utcnow()
            
        audit = AuditLog(
            actor_user_id=current_user.id,
            action="RESOLVE_COMPLAINT",
            entity_type="Complaint",
            entity_id=comp.id,
            details=f"Complaint #{comp.id} set to '{status}'. Notes: {resolution}"
        )
        db.session.add(audit)
        db.session.commit()
        flash(f'Complaint #{comp.id} status updated to {status}.', 'success')
        return redirect(url_for('admin.complaints'))
        
    complaints_list = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin/complaints.html', complaints=complaints_list)

@admin_bp.route('/analytics')
@login_required
@role_required('admin')
def analytics():
    # Overall summary
    tot_prep = db.session.query(func.sum(FoodRecord.prepared_quantity)).scalar() or 0.0
    tot_sold = db.session.query(func.sum(FoodRecord.sold_quantity)).scalar() or 0.0
    tot_surplus = db.session.query(func.sum(FoodRecord.leftover_quantity)).scalar() or 0.0
    tot_donated = db.session.query(func.sum(DonationRequest.approved_quantity)).filter(
        DonationRequest.request_status == 'Completed'
    ).scalar() or 0.0
    
    delivery_completed = Delivery.query.filter_by(delivery_status='Recipient Confirmed').count()
    delivery_total = Delivery.query.count()
    delivery_rate = round((delivery_completed / delivery_total * 100), 1) if delivery_total > 0 else 100.0
    
    return render_template(
        'admin/analytics.html',
        tot_prep=round(tot_prep, 1),
        tot_sold=round(tot_sold, 1),
        tot_surplus=round(tot_surplus, 1),
        tot_donated=round(tot_donated, 1),
        delivery_rate=delivery_rate,
        delivery_completed=delivery_completed,
        delivery_total=delivery_total
    )

@admin_bp.route('/audit-logs')
@login_required
@role_required('admin')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(150).all()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/analytics/export-csv')
@login_required
@role_required('admin')
def export_csv():
    records = FoodRecord.query.order_by(FoodRecord.record_date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Record ID', 'Organization', 'Date', 'Food Item', 'Prepared', 'Sold', 'Leftovers', 'Unit'])
    for r in records:
        writer.writerow([r.id, r.organization.name if r.organization else '', r.record_date, r.food_name, r.prepared_quantity, r.sold_quantity, r.leftover_quantity, r.unit])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=foodrescue_system_analytics.csv"}
    )
