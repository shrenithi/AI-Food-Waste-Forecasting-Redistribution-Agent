import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.database import db, Delivery, DonationRequest, User
from routes.decorators import role_required
from services.delivery_service import DeliveryService

volunteer_bp = Blueprint('volunteer', __name__, url_prefix='/volunteer')

@volunteer_bp.route('/dashboard')
@login_required
@role_required('volunteer')
def dashboard():
    my_deliveries = Delivery.query.filter_by(volunteer_user_id=current_user.id).all()
    
    assigned_count = sum(1 for d in my_deliveries if d.delivery_status == 'Accepted')
    picked_up_count = sum(1 for d in my_deliveries if d.delivery_status == 'Picked Up')
    in_transit_count = sum(1 for d in my_deliveries if d.delivery_status == 'In Transit')
    completed_count = sum(1 for d in my_deliveries if d.delivery_status in ['Delivered', 'Recipient Confirmed'])
    
    available_jobs_count = Delivery.query.filter_by(delivery_status='Unassigned').count()
    
    active_deliveries = [d for d in my_deliveries if d.delivery_status in ['Accepted', 'Picked Up', 'In Transit']]
    
    return render_template(
        'volunteer/dashboard.html',
        assigned_count=assigned_count,
        picked_up_count=picked_up_count,
        in_transit_count=in_transit_count,
        completed_count=completed_count,
        available_jobs_count=available_jobs_count,
        active_deliveries=active_deliveries
    )

@volunteer_bp.route('/assignments')
@login_required
@role_required('volunteer')
def assignments():
    available_deliveries = Delivery.query.filter(
        Delivery.delivery_status.in_(['Unassigned'])
    ).all()
    return render_template('volunteer/assignments.html', deliveries=available_deliveries)

@volunteer_bp.route('/delivery/<int:delivery_id>/accept', methods=['POST'])
@login_required
@role_required('volunteer')
def accept_assignment(delivery_id):
    success, msg = DeliveryService.accept_delivery(delivery_id, current_user.id)
    if success:
        flash(msg, 'success')
        return redirect(url_for('volunteer.delivery_detail', delivery_id=delivery_id))
    else:
        flash(msg, 'danger')
        return redirect(url_for('volunteer.assignments'))

@volunteer_bp.route('/delivery/<int:delivery_id>', methods=['GET', 'POST'])
@login_required
@role_required('volunteer')
def delivery_detail(delivery_id):
    delivery = Delivery.query.get_or_404(delivery_id)
    
    # Handle state transition submission
    if request.method == 'POST':
        action = request.form.get('action')
        notes = request.form.get('notes')
        failure_reason = request.form.get('failure_reason')
        
        target_status = None
        if action == 'picked_up':
            target_status = 'Picked Up'
        elif action == 'in_transit':
            target_status = 'In Transit'
        elif action == 'delivered':
            target_status = 'Delivered'
        elif action == 'failed':
            target_status = 'Failed'
            
        if target_status:
            success, msg = DeliveryService.update_status(
                delivery_id=delivery.id,
                new_status=target_status,
                volunteer_user_id=current_user.id,
                notes=notes,
                failure_reason=failure_reason
            )
            if success:
                flash(msg, 'success')
            else:
                flash(msg, 'danger')
                
        return redirect(url_for('volunteer.delivery_detail', delivery_id=delivery.id))
        
    return render_template('volunteer/delivery_detail.html', delivery=delivery)

@volunteer_bp.route('/history')
@login_required
@role_required('volunteer')
def history():
    completed_routes = Delivery.query.filter(
        Delivery.volunteer_user_id == current_user.id,
        Delivery.delivery_status.in_(['Delivered', 'Recipient Confirmed', 'Failed'])
    ).order_by(Delivery.created_at.desc()).all()
    
    return render_template('volunteer/history.html', routes=completed_routes)
