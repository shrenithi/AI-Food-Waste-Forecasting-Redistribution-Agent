import datetime
from services.safety_service import FoodSafetyService

def test_safety_check_blocks_missing_declaration():
    now = datetime.datetime.utcnow()
    eligible, status, reason = FoodSafetyService.evaluate_listing_eligibility(
        prepared_at=now - datetime.timedelta(hours=1),
        use_by=now + datetime.timedelta(hours=3),
        category="Cooked Meals",
        storage_conditions="Refrigerated (4°C)",
        safety_declaration=False
    )
    assert eligible is False
    assert status == "Safety Blocked"
    assert "FSSAI" in reason

def test_safety_check_blocks_expired_food():
    now = datetime.datetime.utcnow()
    eligible, status, reason = FoodSafetyService.evaluate_listing_eligibility(
        prepared_at=now - datetime.timedelta(hours=5),
        use_by=now - datetime.timedelta(minutes=10),
        category="Cooked Meals",
        storage_conditions="Refrigerated (4°C)",
        safety_declaration=True
    )
    assert eligible is False
    assert status == "Expired"

def test_safety_check_blocks_ambient_cooked_beyond_4_hours():
    now = datetime.datetime.utcnow()
    eligible, status, reason = FoodSafetyService.evaluate_listing_eligibility(
        prepared_at=now - datetime.timedelta(hours=1),
        use_by=now + datetime.timedelta(hours=5), # 6 hours total
        category="Cooked Meals",
        storage_conditions="Ambient",
        safety_declaration=True
    )
    assert eligible is False
    assert "cannot exceed 4 hours" in reason
