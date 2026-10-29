import datetime

class FoodSafetyService:
    """
    Deterministic food safety eligibility service aligned with FSSAI Surplus Food Regulations.
    Ensures safe handling standards, shelf-life validation, storage compliance,
    and prohibits expired or unverified food items from being shared.
    AI is strictly not used to certify food safety.
    """

    MAX_HOURS_AMBIENT_COOKED = 4
    MAX_HOURS_REFRIGERATED_COOKED = 48
    MAX_HOURS_BAKERY = 72
    
    STORAGE_OPTIONS = [
        'Refrigerated (4°C or below)',
        'Hot Holding (60°C or above)',
        'Ambient (Cool & Dry Place)',
        'Frozen (-18°C or below)'
    ]

    FOOD_CATEGORIES = [
        'Cooked Meals',
        'Bakery Items',
        'Fresh Produce',
        'Dairy Products',
        'Packaged Food',
        'Beverages'
    ]

    @classmethod
    def evaluate_listing_eligibility(cls, prepared_at, use_by, category, storage_conditions, safety_declaration):
        """
        Validates listing against food safety standards.
        Returns: (is_eligible: bool, safety_status: str, rejection_reason: str or None)
        """
        now = datetime.datetime.utcnow()
        
        # 1. Mandatory Food Safety Declaration
        if not safety_declaration:
            return False, 'Safety Blocked', 'Donor did not complete the mandatory FSSAI food safety hygiene declaration.'
            
        # 2. Time validation
        if use_by <= now:
            return False, 'Expired', f'Food use-by deadline ({use_by.strftime("%Y-%m-%d %H:%M")}) has passed.'
            
        if prepared_at > now:
            return False, 'Safety Blocked', 'Preparation timestamp cannot be in the future.'
            
        if use_by <= prepared_at:
            return False, 'Safety Blocked', 'Use-by deadline must be strictly after the preparation time.'
            
        # 3. Category & Storage Rule Checks
        shelf_life_hours = (use_by - prepared_at).total_seconds() / 3600.0
        
        if category == 'Cooked Meals':
            if 'Ambient' in storage_conditions and shelf_life_hours > cls.MAX_HOURS_AMBIENT_COOKED:
                return False, 'Safety Blocked', f'Cooked food stored at ambient temperature cannot exceed {cls.MAX_HOURS_AMBIENT_COOKED} hours per FSSAI safety norms.'
            if 'Refrigerated' in storage_conditions and shelf_life_hours > cls.MAX_HOURS_REFRIGERATED_COOKED:
                return False, 'Safety Blocked', f'Refrigerated cooked food exceeds maximum allowable shelf-life of {cls.MAX_HOURS_REFRIGERATED_COOKED} hours.'
                
        if category == 'Dairy Products' and 'Ambient' in storage_conditions:
            return False, 'Safety Blocked', 'Dairy items cannot be kept at ambient temperature; continuous refrigeration (<=4°C) is mandatory.'
            
        return True, 'Eligible', None

    @classmethod
    def check_listing_expiration(cls, listing):
        """
        Runs on existing listing to verify if it has expired or become invalid.
        Updates status if needed.
        """
        now = datetime.datetime.utcnow()
        if listing.use_by < now:
            listing.safety_status = 'Expired'
            if listing.listing_status in ['Available', 'Partially Reserved']:
                listing.listing_status = 'Expired'
            return True
        return False
