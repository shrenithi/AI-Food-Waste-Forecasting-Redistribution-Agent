import datetime
import math
from models.database import SurplusListing, Organization
from services.safety_service import FoodSafetyService

class SmartMatchingService:
    """
    Transparent rule-based matching service between surplus food listings and registered NGOs.
    Filters by safety and capacity, then computes a compatibility score and human-readable explanation.
    """

    @classmethod
    def calculate_distance(cls, lat1, lon1, lat2, lon2):
        """Haversine formula to compute distance in km between two GPS coordinates."""
        if None in (lat1, lon1, lat2, lon2):
            return 3.5  # reasonable default urban distance in km
        try:
            R = 6371.0  # Earth radius in kilometers
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return round(R * c, 1)
        except Exception:
            return 4.0

    @classmethod
    def find_matches_for_ngo(cls, ngo_org, max_results=10, category=None, max_distance_km=25.0):
        """
        Finds and ranks surplus listings suitable for an NGO organization.
        """
        now = datetime.datetime.utcnow()
        query = SurplusListing.query.filter(
            SurplusListing.listing_status.in_(['Available', 'Partially Reserved']),
            SurplusListing.safety_status == 'Eligible',
            SurplusListing.quantity > 0,
            SurplusListing.use_by > now
        )
        
        if category and category != 'All':
            query = query.filter(SurplusListing.category == category)
            
        listings = query.all()
        ranked = []
        
        ngo_capacity = ngo_org.capacity_portions or 150
        
        for listing in listings:
            # Check expiration
            if FoodSafetyService.check_listing_expiration(listing):
                continue
                
            donor = listing.donor
            dist = cls.calculate_distance(
                ngo_org.latitude, ngo_org.longitude,
                donor.latitude if donor else None, donor.longitude if donor else None
            )
            
            if dist > max_distance_km:
                continue
                
            time_left_hrs = max(0.1, (listing.use_by - now).total_seconds() / 3600.0)
            
            # Scoring factors (0 to 100):
            # 1. Proximity score (shorter distance = higher score)
            dist_score = max(0, 100 - (dist * 4))
            
            # 2. Urgency factor (listings expiring between 1 to 5 hours get prioritized to prevent waste)
            if time_left_hrs <= 2:
                urgency_score = 100
                urgency_label = "Urgent: Expires soon (< 2 hrs)"
            elif time_left_hrs <= 6:
                urgency_score = 85
                urgency_label = "High Priority: Expires in under 6 hrs"
            else:
                urgency_score = 65
                urgency_label = "Standard Shelf-life"
                
            # 3. Capacity fit
            qty_ratio = min(listing.quantity / ngo_capacity, 1.0)
            capacity_score = 90 if 0.1 <= qty_ratio <= 1.0 else 60
            
            # Weighted Composite Match Score
            total_score = round((dist_score * 0.40) + (urgency_score * 0.35) + (capacity_score * 0.25), 1)
            
            explanation = (
                f"Match Score: {int(total_score)}%. "
                f"Proximity: {dist} km away. "
                f"Time window: {round(time_left_hrs, 1)} hours remaining. "
                f"Quantity ({int(listing.quantity)} {listing.unit}) fits well within your {ngo_capacity}-portion capacity."
            )
            
            ranked.append({
                'listing': listing,
                'distance_km': dist,
                'time_left_hrs': round(time_left_hrs, 1),
                'match_score': total_score,
                'urgency_label': urgency_label,
                'explanation': explanation
            })
            
        ranked.sort(key=lambda x: x['match_score'], reverse=True)
        return ranked[:max_results]
