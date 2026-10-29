import datetime
from models.demand_model import FoodDemandForecaster

def test_forecaster_fallback_on_insufficient_data():
    forecaster = FoodDemandForecaster(model_dir='tests/test_models')
    records = [
        {'record_date': '2026-01-01', 'sold_quantity': 40, 'prepared_quantity': 50, 'day_of_week': 0},
        {'record_date': '2026-01-02', 'sold_quantity': 45, 'prepared_quantity': 50, 'day_of_week': 1}
    ]
    target_date = datetime.date(2026, 1, 3)
    res = forecaster.forecast_demand(org_id=99, food_name='Test Rice', target_date=target_date, food_records=records)
    assert res['is_fallback'] is True
    assert 'Baseline' in res['model_used']
    assert res['predicted_demand'] > 0
    assert res['recommended_quantity'] >= res['predicted_demand']

def test_forecaster_with_sufficient_data():
    forecaster = FoodDemandForecaster(model_dir='tests/test_models')
    records = []
    base_date = datetime.date(2026, 1, 1)
    for i in range(20):
        records.append({
            'record_date': (base_date + datetime.timedelta(days=i)).strftime('%Y-%m-%d'),
            'sold_quantity': 30 + (i % 5) * 5,
            'prepared_quantity': 50,
            'day_of_week': (i % 7)
        })
    target_date = datetime.date(2026, 1, 25)
    res = forecaster.forecast_demand(org_id=99, food_name='Test Rice', target_date=target_date, food_records=records)
    assert res['predicted_demand'] > 0
    assert res['recommended_quantity'] >= res['predicted_demand']
    assert 'confidence_interval' in res
    assert res['mae'] is not None
