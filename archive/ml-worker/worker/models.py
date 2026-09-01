from sqlalchemy import Column, String, DateTime, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ForecastModel(Base):
    __tablename__ = "forecast_models"

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True))
    model_path = Column(String(500))
    metrics = Column(JSONB)
    feature_importance = Column(JSONB)
    status = Column(String(50))
    created_at = Column(DateTime)

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True))
    run_type = Column(String(50))
    parameters = Column(JSONB)
    results = Column(JSONB)
    status = Column(String(50))
    completed_at = Column(DateTime)
    created_at = Column(DateTime)

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True))
    filename = Column(String(255))
    file_path = Column(String(500))
    row_count = Column(Integer)
    schema_definition = Column(JSONB)
    uploaded_at = Column(DateTime)

class QueueValidation(Base):
    __tablename__ = "queue_validations"

    id = Column(UUID(as_uuid=True), primary_key=True)
    optimization_run_id = Column(UUID(as_uuid=True))
    hour = Column(Integer)
    calls = Column(Integer)
    agents = Column(Integer)
    sla_percent = Column(Float)
    asa_seconds = Column(Float)
    utilization_percent = Column(Float)
    abandonment_percent = Column(Float)
    pass_fail = Column(String(10))
