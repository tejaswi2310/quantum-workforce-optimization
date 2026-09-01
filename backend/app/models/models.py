import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, ForeignKey, JSON, Uuid
from sqlalchemy.orm import relationship

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(String)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    forecast_models = relationship("ForecastModel", back_populates="project", cascade="all, delete-orphan")
    optimization_runs = relationship("OptimizationRun", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filename = Column(String(255))
    file_path = Column(String(500))
    row_count = Column(Integer)
    schema_definition = Column(JSON)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="datasets")


class ForecastModel(Base):
    __tablename__ = "forecast_models"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    model_path = Column(String(500))
    metrics = Column(JSON)
    feature_importance = Column(JSON)
    status = Column(String(50), default="training")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="forecast_models")


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    run_type = Column(String(50)) # 'classical', 'quantum', 'shift', 'hybrid'
    parameters = Column(JSON)
    results = Column(JSON)
    status = Column(String(50), default="pending")
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="optimization_runs")
    queue_validations = relationship("QueueValidation", back_populates="optimization_run", cascade="all, delete-orphan")


class QueueValidation(Base):
    __tablename__ = "queue_validations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    optimization_run_id = Column(Uuid(as_uuid=True), ForeignKey("optimization_runs.id"), index=True)
    hour = Column(Integer)
    calls = Column(Integer)
    agents = Column(Integer)
    sla_percent = Column(Float)
    asa_seconds = Column(Float)
    utilization_percent = Column(Float)
    abandonment_percent = Column(Float)
    pass_fail = Column(String(10))

    optimization_run = relationship("OptimizationRun", back_populates="queue_validations")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    report_type = Column(String(50))
    file_path = Column(String(500))
    generated_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="reports")
