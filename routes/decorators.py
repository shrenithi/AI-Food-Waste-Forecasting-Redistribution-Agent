from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user

def role_required(*roles):
    """Decorator ensuring current_user is authenticated and has one of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles and current_user.role != 'admin':
                flash('You do not have permission to access that page.', 'danger')
                if current_user.role == 'restaurant':
                    return redirect(url_for('restaurant.dashboard'))
                elif current_user.role == 'ngo':
                    return redirect(url_for('ngo.dashboard'))
                elif current_user.role == 'volunteer':
                    return redirect(url_for('volunteer.dashboard'))
                elif current_user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def verified_org_required(f):
    """Decorator ensuring restaurant/ngo user belongs to a verified organization."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role in ['restaurant', 'ngo']:
            org = current_user.organization
            if not org or org.verification_status != 'verified':
                flash('Your organization account is currently pending administrative verification. Full operational access will be granted upon review.', 'warning')
        return f(*args, **kwargs)
    return decorated_function
