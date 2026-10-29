import datetime
import json
from models.database import db, FoodRecord, Forecast
from models.demand_model import FoodDemandForecaster

forecaster = FoodDemandForecaster()

def get_forecast_for_item(org_id, food_name, target_date=None, is_holiday=False, event_flag=False, weather_temp=26.0):
    """
    Retrieves or generates a demand forecast for a specific food item in an organization.
    Saves forecast record to DB and returns full details.
    """
    if target_date is None:
        target_date = datetime.date.today() + datetime.timedelta(days=1)
    elif isinstance(target_date, str):
        target_date = datetime.datetime.strptime(target_date, '%Y-%m-%d').date()
        
    # Query historical food records for this org and item
    records = FoodRecord.query.filter_by(
        organization_id=org_id,
        food_name=food_name
    ).order_by(FoodRecord.record_date.asc()).all()
    
    # Run forecaster
    result = forecaster.forecast_demand(
        org_id=org_id,
        food_name=food_name,
        target_date=target_date,
        food_records=records,
        is_holiday=is_holiday,
        event_flag=event_flag,
        weather_temp=weather_temp
    )
    
    # Check if a forecast entry already exists for this org, item, and date
    existing_forecast = Forecast.query.filter_by(
        organization_id=org_id,
        food_name=food_name,
        target_date=target_date
    ).first()
    
    if not existing_forecast:
        existing_forecast = Forecast(
            organization_id=org_id,
            food_name=food_name,
            target_date=target_date,
            predicted_demand=result['predicted_demand'],
            recommended_quantity=result['recommended_quantity'],
            confidence_lower=result['confidence_interval'][0],
            confidence_upper=result['confidence_interval'][1],
            mae=result['mae'],
            rmse=result['rmse'],
            model_version=result['model_used'],
            factors_json=json.dumps(result['factors'])
        )
        db.session.add(existing_forecast)
    else:
        existing_forecast.predicted_demand = result['predicted_demand']
        existing_forecast.recommended_quantity = result['recommended_quantity']
        existing_forecast.confidence_lower = result['confidence_interval'][0]
        existing_forecast.confidence_upper = result['confidence_interval'][1]
        existing_forecast.mae = result['mae']
        existing_forecast.rmse = result['rmse']
        existing_forecast.model_version = result['model_used']
        existing_forecast.factors_json = json.dumps(result['factors'])
        
    db.session.commit()
    
    # Add historical timeseries data for charting
    history_data = []
    for r in records[-14:]:  # last 14 days
        history_data.append({
            'date': r.record_date.strftime('%Y-%m-%d'),
            'prepared': r.prepared_quantity,
            'sold': r.sold_quantity,
            'leftover': r.leftover_quantity
        })
    result['history'] = history_data
    return result

def train_all_org_models(org_id):
    """Retrain ML models for all distinct food items of an organization."""
    items = db.session.query(FoodRecord.food_name).filter_by(organization_id=org_id).distinct().all()
    results = {}
    for (item_name,) in items:
        records = FoodRecord.query.filter_by(organization_id=org_id, food_name=item_name).order_by(FoodRecord.record_date.asc()).all()
        res = forecaster.train(org_id, item_name, records)
        results[item_name] = res
    return results
