import time
from app.models.database import SessionLocal
from app.models.models import ForecastModel, OptimizationRun, QueueValidation

def train_random_forest(forecast_id: str):
    time.sleep(2) # Simulate processing time
    db = SessionLocal()
    try:
        forecast = db.query(ForecastModel).filter(ForecastModel.id == forecast_id).first()
        if forecast:
            forecast.status = "completed"
            forecast.metrics = {"mae": 6.44, "rmse": 9.97, "r2": 0.86}
            forecast.feature_importance = {"day_of_week": 0.4, "hour": 0.3, "is_holiday": 0.2, "promo_active": 0.1}
            db.commit()
    finally:
        db.close()

def run_optimization(run_id: str):
    time.sleep(3) # Simulate processing time
    db = SessionLocal()
    try:
        opt_run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if opt_run:
            opt_run.status = "completed"
            opt_run.results = {
                "total_cost": 870,
                "agents_scheduled": 58,
                "break_compliance": 1.0,
                "schedule": [
                    {"hour": "09:00", "required": 42, "scheduled": 58, "cost": 870.0}
                ]
            }
            
            # Create a mock queue validation
            qv = QueueValidation(
                optimization_run_id=opt_run.id,
                hour=9,
                calls=420,
                agents=58,
                sla_percent=89.4,
                asa_seconds=12.4,
                utilization_percent=78.5,
                abandonment_percent=1.2,
                pass_fail="PASS"
            )
            db.add(qv)
            db.commit()
    finally:
        db.close()
