import datetime
import io
import csv
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from models.database import db, FoodRecord, SurplusListing, DonationRequest, Delivery, Forecast, Organization
from routes.decorators import role_required, verified_org_required
from services.forecasting import get_forecast_for_item, train_all_org_models
from services.safety_service import FoodSafetyService
from services.donation_service import DonationService

restaurant_bp = Blueprint('restaurant', __name__, url_prefix='/restaurant')

@restaurant_bp.route('/dashboard')
@login_required
@role_required('restaurant')
def dashboard():
    org = current_user.organization
    if not org:
        flash('No organization associated with this account.', 'danger')
        return redirect(url_for('public.landing'))
        
    today = datetime.date.today()
    
    # 1. Today's Metrics
    today_records = FoodRecord.query.filter_by(organization_id=org.id, record_date=today).all()
    prepared_today = sum(r.prepared_quantity for r in today_records)
    sold_today = sum(r.sold_quantity for r in today_records)
    surplus_today = max(0, prepared_today - sold_today)
    
    # 2. Counts
    active_listings_count = SurplusListing.query.filter(
        SurplusListing.donor_organization_id == org.id,
        SurplusListing.listing_status.in_(['Available', 'Partially Reserved']),
        SurplusListing.use_by > datetime.datetime.utcnow()
    ).count()
    
    pending_requests_count = DonationRequest.query.join(SurplusListing).filter(
        SurplusListing.donor_organization_id == org.id,
        DonationRequest.request_status == 'Pending'
    ).count()
    
    completed_donations_count = DonationRequest.query.join(SurplusListing).filter(
        SurplusListing.donor_organization_id == org.id,
        DonationRequest.request_status == 'Completed'
    ).count()
    
    # Total redistributed quantity
    total_redistributed = db.session.query(func.sum(DonationRequest.approved_quantity)).join(SurplusListing).filter(
        SurplusListing.donor_organization_id == org.id,
        DonationRequest.request_status == 'Completed'
    ).scalar() or 0.0
    
    # 3. Weekly preparation vs sales chart data (last 7 days)
    seven_days_ago = today - datetime.timedelta(days=6)
    recent_records = FoodRecord.query.filter(
        FoodRecord.organization_id == org.id,
        FoodRecord.record_date >= seven_days_ago
    ).order_by(FoodRecord.record_date.asc()).all()
    
    # Aggregate by date
    date_map = {}
    for i in range(7):
        d = seven_days_ago + datetime.timedelta(days=i)
        date_map[d.strftime('%a %d')] = {'prep': 0.0, 'sold': 0.0, 'leftover': 0.0}
        
    for r in recent_records:
        key = r.record_date.strftime('%a %d')
        if key in date_map:
            date_map[key]['prep'] += r.prepared_quantity
            date_map[key]['sold'] += r.sold_quantity
            date_map[key]['leftover'] += r.leftover_quantity
            
    chart_labels = list(date_map.keys())
    chart_prep = [round(v['prep'], 1) for v in date_map.values()]
    chart_sold = [round(v['sold'], 1) for v in date_map.values()]
    chart_leftover = [round(v['leftover'], 1) for v in date_map.values()]
    
    # 4. Recent donation activity table
    recent_donations = DonationRequest.query.join(SurplusListing).filter(
        SurplusListing.donor_organization_id == org.id
    ).order_by(DonationRequest.created_at.desc()).limit(5).all()
    
    # 5. Upcoming pickup deadlines
    now = datetime.datetime.utcnow()
    upcoming_pickups = SurplusListing.query.filter(
        SurplusListing.donor_organization_id == org.id,
        SurplusListing.listing_status.in_(['Available', 'Partially Reserved']),
        SurplusListing.use_by > now
    ).order_by(SurplusListing.use_by.asc()).limit(4).all()
    
    # Distinct items for AI assistant suggestion
    distinct_items = FoodRecord.query.filter_by(organization_id=org.id).with_entities(FoodRecord.food_name).distinct().all()
    distinct_food_names = [name for (name,) in distinct_items]
    
    return render_template(
        'restaurant/dashboard.html',
        org=org,
        prepared_today=prepared_today,
        sold_today=sold_today,
        surplus_today=surplus_today,
        active_listings_count=active_listings_count,
        pending_requests_count=pending_requests_count,
        completed_donations_count=completed_donations_count,
        total_redistributed=round(total_redistributed, 1),
        chart_labels=chart_labels,
        chart_prep=chart_prep,
        chart_sold=chart_sold,
        chart_leftover=chart_leftover,
        recent_donations=recent_donations,
        upcoming_pickups=upcoming_pickups,
        distinct_food_names=distinct_food_names
    )

@restaurant_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required('restaurant')
def inventory():
    org = current_user.organization
    if request.method == 'POST':
        food_name = request.form.get('food_name', '').strip()
        category = request.form.get('category', 'Cooked Meals')
        prepared_qty = float(request.form.get('prepared_quantity', 0.0))
        sold_qty = float(request.form.get('sold_quantity', 0.0))
        unit = request.form.get('unit', 'portions')
        record_date_str = request.form.get('record_date')
        
        if record_date_str:
            rec_date = datetime.datetime.strptime(record_date_str, '%Y-%m-%d').date()
        else:
            rec_date = datetime.date.today()
            
        leftover_qty = max(0.0, prepared_qty - sold_qty)
        
        record = FoodRecord(
            organization_id=org.id,
            food_name=food_name,
            category=category,
            record_date=rec_date,
            prepared_quantity=prepared_qty,
            sold_quantity=sold_qty,
            leftover_quantity=leftover_qty,
            unit=unit,
            day_of_week=rec_date.weekday(),
            is_holiday=bool(request.form.get('is_holiday')),
            event_flag=bool(request.form.get('event_flag')),
            weather_temp=float(request.form.get('weather_temp', 26.0)),
            notes=request.form.get('notes', '')
        )
        db.session.add(record)
        db.session.commit()
        flash(f'Food record for "{food_name}" successfully recorded! Leftovers calculated: {leftover_qty} {unit}.', 'success')
        return redirect(url_for('restaurant.inventory'))
        
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '')
    
    query = FoodRecord.query.filter_by(organization_id=org.id)
    if search_query:
        query = query.filter(FoodRecord.food_name.ilike(f'%{search_query}%'))
    if category_filter and category_filter != 'All':
        query = query.filter(FoodRecord.category == category_filter)
        
    records = query.order_by(FoodRecord.record_date.desc(), FoodRecord.id.desc()).limit(100).all()
    categories = FoodSafetyService.FOOD_CATEGORIES
    
    return render_template(
        'restaurant/inventory.html',
        org=org,
        records=records,
        categories=categories,
        search_query=search_query,
        category_filter=category_filter
    )

@restaurant_bp.route('/sales-records')
@login_required
@role_required('restaurant')
def sales_records():
    org = current_user.organization
    page = request.args.get('page', 1, type=int)
    records = FoodRecord.query.filter_by(organization_id=org.id).order_by(
        FoodRecord.record_date.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('restaurant/sales_records.html', org=org, records=records)

@restaurant_bp.route('/forecast', methods=['GET', 'POST'])
@login_required
@role_required('restaurant')
def forecast():
    org = current_user.organization
    distinct_items = FoodRecord.query.filter_by(organization_id=org.id).with_entities(FoodRecord.food_name).distinct().all()
    food_names = [n for (n,) in distinct_items]
    
    selected_item = request.args.get('food_name') or request.form.get('food_name')
    if not selected_item and food_names:
        selected_item = food_names[0]
        
    target_date_str = request.args.get('target_date') or request.form.get('target_date')
    if target_date_str:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    else:
        target_date = datetime.date.today() + datetime.timedelta(days=1)
        
    is_holiday = bool(request.args.get('is_holiday') or request.form.get('is_holiday'))
    event_flag = bool(request.args.get('event_flag') or request.form.get('event_flag'))
    weather_temp = float(request.args.get('weather_temp') or request.form.get('weather_temp') or 26.5)
    
    forecast_result = None
    if selected_item:
        forecast_result = get_forecast_for_item(
            org_id=org.id,
            food_name=selected_item,
            target_date=target_date,
            is_holiday=is_holiday,
            event_flag=event_flag,
            weather_temp=weather_temp
        )
        
    return render_template(
        'restaurant/forecast.html',
        org=org,
        food_names=food_names,
        selected_item=selected_item,
        target_date=target_date,
        is_holiday=is_holiday,
        event_flag=event_flag,
        weather_temp=weather_temp,
        forecast=forecast_result
    )

@restaurant_bp.route('/surplus', methods=['GET', 'POST'])
@login_required
@role_required('restaurant')
def surplus():
    org = current_user.organization
    if request.method == 'POST':
        food_name = request.form.get('food_name', '').strip()
        category = request.form.get('category', 'Cooked Meals')
        quantity = float(request.form.get('quantity', 0.0))
        unit = request.form.get('unit', 'portions')
        storage_conditions = request.form.get('storage_conditions', 'Refrigerated (4°C or below)')
        dietary_flags = request.form.get('dietary_flags', 'Vegetarian')
        allergens = request.form.get('allergens', 'None known')
        pickup_location = request.form.get('pickup_location') or org.address
        
        # Timestamps
        prep_str = request.form.get('prepared_at')
        use_by_str = request.form.get('use_by')
        window_end_str = request.form.get('pickup_window_end')
        
        now = datetime.datetime.utcnow()
        prepared_at = datetime.datetime.strptime(prep_str, '%Y-%m-%dT%H:%M') if prep_str else now - datetime.timedelta(hours=1)
        use_by = datetime.datetime.strptime(use_by_str, '%Y-%m-%dT%H:%M') if use_by_str else now + datetime.timedelta(hours=4)
        pickup_end = datetime.datetime.strptime(window_end_str, '%Y-%m-%dT%H:%M') if window_end_str else use_by
        
        safety_declaration = bool(request.form.get('safety_declaration'))
        
        # Food safety evaluation
        is_eligible, safety_status, rejection_reason = FoodSafetyService.evaluate_listing_eligibility(
            prepared_at=prepared_at,
            use_by=use_by,
            category=category,
            storage_conditions=storage_conditions,
            safety_declaration=safety_declaration
        )
        
        if not is_eligible:
            flash(f'Listing Safety Verification Failed: {rejection_reason}', 'danger')
            return redirect(url_for('restaurant.surplus'))
            
        listing = SurplusListing(
            donor_organization_id=org.id,
            food_name=food_name,
            category=category,
            initial_quantity=quantity,
            quantity=quantity,
            unit=unit,
            prepared_at=prepared_at,
            use_by=use_by,
            storage_conditions=storage_conditions,
            dietary_flags=dietary_flags,
            allergens=allergens,
            pickup_location=pickup_location,
            pickup_window_start=prepared_at,
            pickup_window_end=pickup_end,
            safety_declaration=safety_declaration,
            safety_status='Eligible',
            listing_status='Available',
            image_url=request.form.get('image_url') or 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop'
        )
        db.session.add(listing)
        db.session.commit()
        flash(f'Surplus food listing for "{food_name}" ({quantity} {unit}) published to NGO marketplace!', 'success')
        return redirect(url_for('restaurant.surplus'))
        
    listings = SurplusListing.query.filter_by(donor_organization_id=org.id).order_by(SurplusListing.created_at.desc()).all()
    categories = FoodSafetyService.FOOD_CATEGORIES
    storage_options = FoodSafetyService.STORAGE_OPTIONS
    
    return render_template(
        'restaurant/surplus.html',
        org=org,
        listings=listings,
        categories=categories,
        storage_options=storage_options
    )

@restaurant_bp.route('/surplus/<int:listing_id>/close', methods=['POST'])
@login_required
@role_required('restaurant')
def close_surplus(listing_id):
    org = current_user.organization
    listing = SurplusListing.query.filter_by(id=listing_id, donor_organization_id=org.id).first_or_404()
    listing.listing_status = 'Cancelled'
    db.session.commit()
    flash(f'Listing #{listing.id} ({listing.food_name}) has been cancelled and closed.', 'info')
    return redirect(url_for('restaurant.surplus'))

@restaurant_bp.route('/requests')
@login_required
@role_required('restaurant')
def requests():
    org = current_user.organization
    requests_list = DonationRequest.query.join(SurplusListing).filter(
        SurplusListing.donor_organization_id == org.id
    ).order_by(DonationRequest.created_at.desc()).all()
    
    return render_template('restaurant/requests.html', org=org, requests=requests_list)

@restaurant_bp.route('/requests/<int:request_id>/approve', methods=['POST'])
@login_required
@role_required('restaurant')
def approve_request(request_id):
    approved_qty = float(request.form.get('approved_quantity', 0.0))
    success, msg = DonationService.approve_request(request_id, approved_qty, actor_user_id=current_user.id)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('restaurant.requests'))

@restaurant_bp.route('/requests/<int:request_id>/reject', methods=['POST'])
@login_required
@role_required('restaurant')
def reject_request(request_id):
    reason = request.form.get('reason', 'Insufficient inventory remaining')
    success, msg = DonationService.reject_request(request_id, reason, actor_user_id=current_user.id)
    if success:
        flash(msg, 'info')
    else:
        flash(msg, 'danger')
    return redirect(url_for('restaurant.requests'))

@restaurant_bp.route('/tracking')
@login_required
@role_required('restaurant')
def delivery_tracking():
    org = current_user.organization
    approved_requests = DonationRequest.query.join(SurplusListing).filter(
        SurplusListing.donor_organization_id == org.id,
        DonationRequest.request_status.in_(['Approved', 'Completed'])
    ).order_by(DonationRequest.updated_at.desc()).all()
    
    return render_template('restaurant/delivery_tracking.html', org=org, requests=approved_requests)

@restaurant_bp.route('/reports')
@login_required
@role_required('restaurant')
def reports():
    org = current_user.organization
    records = FoodRecord.query.filter_by(organization_id=org.id).all()
    
    tot_prepared = sum(r.prepared_quantity for r in records)
    tot_sold = sum(r.sold_quantity for r in records)
    tot_leftover = sum(r.leftover_quantity for r in records)
    
    # Donations
    donations = DonationRequest.query.join(SurplusListing).filter(
        SurplusListing.donor_organization_id == org.id,
        DonationRequest.request_status == 'Completed'
    ).all()
    tot_donated = sum(d.approved_quantity for d in donations)
    
    waste_diverted_pct = round((tot_donated / tot_leftover * 100), 1) if tot_leftover > 0 else 0.0
    
    return render_template(
        'restaurant/reports.html',
        org=org,
        tot_prepared=tot_prepared,
        tot_sold=tot_sold,
        tot_leftover=tot_leftover,
        tot_donated=tot_donated,
        waste_diverted_pct=waste_diverted_pct,
        donations=donations
    )

@restaurant_bp.route('/reports/export-csv')
@login_required
@role_required('restaurant')
def export_csv():
    org = current_user.organization
    records = FoodRecord.query.filter_by(organization_id=org.id).order_by(FoodRecord.record_date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Record ID', 'Date', 'Day of Week', 'Food Item', 'Category', 'Prepared Qty', 'Sold Qty', 'Leftover Qty', 'Unit', 'Holiday Flag', 'Weather Temp (C)'])
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for r in records:
        writer.writerow([
            r.id,
            r.record_date.strftime('%Y-%m-%d'),
            days[r.day_of_week] if 0 <= r.day_of_week <= 6 else r.day_of_week,
            r.food_name,
            r.category,
            r.prepared_quantity,
            r.sold_quantity,
            r.leftover_quantity,
            r.unit,
            'Yes' if r.is_holiday else 'No',
            r.weather_temp or ''
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=foodrescue_{org.name.replace(' ', '_')}_records.csv"}
    )
