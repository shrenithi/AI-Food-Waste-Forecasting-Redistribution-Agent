from routes.auth import auth_bp
from routes.public import public_bp
from routes.restaurant import restaurant_bp
from routes.ngo import ngo_bp
from routes.volunteer import volunteer_bp
from routes.admin import admin_bp
from routes.api import api_bp

__all__ = [
    'auth_bp',
    'public_bp',
    'restaurant_bp',
    'ngo_bp',
    'volunteer_bp',
    'admin_bp',
    'api_bp'
]
