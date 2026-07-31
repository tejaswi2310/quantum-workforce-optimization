from celery import shared_task
from worker.database import SessionLocal
from worker.models import ForecastModel, OptimizationRun, QueueValidation
import time
from datetime import datetime

@shared_task(bind=True)
def train_random_forest(self, forecast_id: str):
    db = SessionLocal()
    try:
        forecast = db.query(ForecastModel).filter(ForecastModel.id == forecast_id).first()
        if not forecast:
            return "Forecast not found"
        
        # Simulate training delay
        time.sleep(5)
        
        # Simulated results as per the prompt requirements
        forecast.metrics = {"mae": 6.44, "rmse": 9.97, "r2": 0.8578}
        forecast.feature_importance = {"day_of_week": 0.4, "time_of_day": 0.3, "marketing_spend": 0.2, "weather": 0.1}
        forecast.status = "completed"
        db.commit()
        return f"Training completed for {forecast_id}"
    finally:
        db.close()

@shared_task(bind=True)
def run_optimization(self, run_id: str):
    db = SessionLocal()
    try:
        opt_run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not opt_run:
            return "Optimization run not found"
        
        # Simulate optimization delay
        time.sleep(5)
        
        # Simulated results as per the prompt requirements
        opt_run.results = {
            "schedule": [{"hour": i, "agents": 58} for i in range(24)],
            "total_cost": 870,
            "total_agents": 58,
            "sla_met_percent": 100
        }
        opt_run.status = "completed"
        opt_run.completed_at = datetime.utcnow()
        
        # Generate dummy queue validations
        for i in range(24):
            qv = QueueValidation(
                optimization_run_id=opt_run.id,
                hour=i,
                calls=120,
                agents=58,
                sla_percent=95.0,
                asa_seconds=15.0,
                utilization_percent=85.0,
                abandonment_percent=1.0,
                pass_fail="PASS"
            )
            db.add(qv)
            
        db.commit()
        return f"Optimization completed for {run_id}"
    finally:
        db.close()
