import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'foodrescue-ai-super-secret-key-2026-sustainability')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "foodrescue.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder for images/documents if needed
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
    
    # Model persistence directory
    MODEL_DIR = os.path.join(BASE_DIR, 'models', 'saved')
    
    # Food safety defaults (in hours)
    MAX_COOKED_FOOD_SHELF_HOURS = 4
    MAX_REFRIGERATED_FOOD_SHELF_HOURS = 24
