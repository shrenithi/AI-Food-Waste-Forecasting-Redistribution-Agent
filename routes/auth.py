import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.database import db, User, Organization, OrganizationMember, AuditLog
from services.notification_service import NotificationService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)
        
    requested_role = request.args.get('role') or ('admin' if request.path == '/admin/login' else None)
    default_email = ''
    default_password = ''
    if requested_role == 'admin':
        default_email = 'admin@foodrescue.ai'
        default_password = 'Admin@123'
    elif requested_role == 'restaurant':
        default_email = 'chef@greengarden.com'
        default_password = 'Chef@123'
    elif requested_role == 'ngo':
        default_email = 'contact@cityrelief.org'
        default_password = 'Ngo@123'
    elif requested_role == 'volunteer':
        default_email = 'alex@volunteer.com'
        default_password = 'Volunteer@123'
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.account_status == 'suspended':
                flash('Your account has been suspended by administration. Please contact support.', 'danger')
                return render_template('auth/login.html', requested_role=requested_role, default_email=default_email, default_password=default_password)
                
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.name}!', 'success')
            
            # Audit log
            audit = AuditLog(actor_user_id=user.id, action="USER_LOGIN", entity_type="User", entity_id=user.id, details="User logged in successfully.")
            db.session.add(audit)
            db.session.commit()
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect_user_by_role(user)
        else:
            flash('Invalid email address or password. Please try again.', 'danger')
            
    return render_template('auth/login.html', requested_role=requested_role, default_email=default_email, default_password=default_password)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)
        
    if request.method == 'POST':
        role = request.form.get('role', 'restaurant')
        if role not in ['restaurant', 'ngo', 'volunteer']:
            flash('Invalid role selected.', 'danger')
            return render_template('auth/register.html')
            
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not name or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
            
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html')
            
        if User.query.filter_by(email=email).first():
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))
            
        # Create User
        account_status = 'active' if role == 'volunteer' else 'pending'
        user = User(
            name=name,
            email=email,
            phone=phone,
            role=role,
            account_status=account_status
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # If Restaurant or NGO, create organization
        if role in ['restaurant', 'ngo']:
            org_name = request.form.get('org_name', name + ' Organization').strip()
            org_type = request.form.get('org_type', 'restaurant' if role == 'restaurant' else 'ngo')
            address = request.form.get('address', 'Metro Area, City Center').strip()
            city = request.form.get('city', 'Metro Area').strip()
            capacity = int(request.form.get('capacity_portions', 150))
            
            org = Organization(
                name=org_name,
                organization_type=org_type,
                address=address,
                city=city,
                latitude=12.9716,  # default coordinates (Bengaluru / metro center)
                longitude=77.5946,
                contact_email=email,
                contact_phone=phone,
                capacity_portions=capacity,
                verification_status='pending',
                created_at=datetime.datetime.utcnow()
            )
            db.session.add(org)
            db.session.flush()
            
            member = OrganizationMember(organization_id=org.id, user_id=user.id, role_in_org='owner')
            db.session.add(member)
            
        db.session.commit()
        
        # Dispatch welcome notification
        NotificationService.send(
            user_id=user.id,
            title="Welcome to FoodRescue AI!",
            message="Your account has been created. Organizations undergo administrative verification before surplus listings can be claimed.",
            notification_type='system'
        )
        
        login_user(user)
        flash('Registration successful! Welcome to the FoodRescue AI network.', 'success')
        return redirect_user_by_role(user)
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('public.landing'))

def redirect_user_by_role(user):
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif user.role == 'restaurant':
        return redirect(url_for('restaurant.dashboard'))
    elif user.role == 'ngo':
        return redirect(url_for('ngo.dashboard'))
    elif user.role == 'volunteer':
        return redirect(url_for('volunteer.dashboard'))
    return redirect(url_for('public.landing'))
