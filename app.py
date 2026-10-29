import os
import datetime
from flask import Flask, render_template
from flask_login import LoginManager, current_user
from config import Config
from models.database import db, User, Notification
from routes import auth_bp, public_bp, restaurant_bp, ngo_bp, volunteer_bp, admin_bp, api_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Database
    db.init_app(app)
    
    # Expose Python builtins in Jinja environment
    app.jinja_env.globals.update(
        int=int,
        float=float,
        round=round,
        min=min,
        max=max,
        len=len
    )
    
    # Initialize Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Context processor for global template variables
    @app.context_processor
    def inject_globals():
        unread_count = 0
        user_notifications = []
        if current_user.is_authenticated:
            try:
                unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
                user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
            except Exception:
                unread_count = 0
                user_notifications = []
        return {
            'now': datetime.datetime.utcnow(),
            'current_year': datetime.datetime.now().year,
            'unread_notifications_count': unread_count,
            'recent_notifications': user_notifications
        }
        
    # Register Blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(restaurant_bp)
    app.register_blueprint(ngo_bp)
    app.register_blueprint(volunteer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    
    # Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('base.html', error_title="404 - Page Not Found", error_msg="The requested page could not be located."), 404
        
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('base.html', error_title="403 - Forbidden Access", error_msg="You do not have administrative permission to view this resource."), 403

    # Ensure tables exist
    with app.app_context():
        db.create_all()
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)
