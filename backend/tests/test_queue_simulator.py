import pytest
import pandas as pd
import os
import uuid
import math
from app.core_engine.queue.queue_simulator import run_queue_simulation, required_agents_for_sla, erlang_c
from app.services.storage_service import StorageService

def test_adequate_staffing_valid_erlang_c(tmp_path):
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.base_dir = tmp_path / "runs" / str(run_id)
    storage.ensure_run_dirs()

    # Create dummy schedule
    df = pd.DataFrame({
        "hour": [10],
        "calls": [100.0], # 100 calls/hr, AHT=300s -> A = 100*300/3600 = 8.33
        "scheduled_agents": [12], # > 8.33, should be valid
        "required_agents": [11]
    })
    
    df.to_csv(storage.result_path("classical_optimization_schedule.csv"), index=False)
    
    run_queue_simulation(run_id)
    
    res_df = pd.read_csv(storage.result_path("queue_validation_results.csv"))
    assert len(res_df) == 1
    row = res_df.iloc[0]
    
    assert row['scheduled_agents'] == 12
    assert row['metric_validity'] == "VALID_ERLANG_C"
    assert row['sla_percent'] > 0
    assert row['asa_seconds'] > 0
    assert row['abandonment_not_modeled'] == True

def test_understaffed_interval_remains_understaffed(tmp_path):
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.base_dir = tmp_path / "runs" / str(run_id)
    storage.ensure_run_dirs()

    df = pd.DataFrame({
        "hour": [11],
        "calls": [100.0], # A = 8.33
        "scheduled_agents": [6], # c <= A, should be overloaded
        "required_agents": [11]
    })
    
    df.to_csv(storage.result_path("classical_optimization_schedule.csv"), index=False)
    
    run_queue_simulation(run_id)
    
    res_df = pd.read_csv(storage.result_path("queue_validation_results.csv"))
    row = res_df.iloc[0]
    
    assert row['scheduled_agents'] == 6, "Simulator must not modify scheduled_agents"
    assert row['metric_validity'] == "OVERLOADED"
    assert pd.isna(row['sla_percent'])
    assert pd.isna(row['asa_seconds'])

def test_zero_staffing(tmp_path):
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.base_dir = tmp_path / "runs" / str(run_id)
    storage.ensure_run_dirs()

    df = pd.DataFrame({
        "hour": [12],
        "calls": [100.0], 
        "scheduled_agents": [0]
    })
    
    df.to_csv(storage.result_path("classical_optimization_schedule.csv"), index=False)
    run_queue_simulation(run_id)
    
    res_df = pd.read_csv(storage.result_path("queue_validation_results.csv"))
    row = res_df.iloc[0]
    
    assert row['scheduled_agents'] == 0
    assert row['metric_validity'] in ["INVALID_INPUT", "OVERLOADED"]
    assert pd.isna(row['asa_seconds'])
    assert pd.isna(row['sla_percent'])

def test_zero_calls(tmp_path):
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.base_dir = tmp_path / "runs" / str(run_id)
    storage.ensure_run_dirs()

    df = pd.DataFrame({
        "hour": [13],
        "calls": [0.0], 
        "scheduled_agents": [2]
    })
    
    df.to_csv(storage.result_path("classical_optimization_schedule.csv"), index=False)
    run_queue_simulation(run_id)
    
    res_df = pd.read_csv(storage.result_path("queue_validation_results.csv"))
    row = res_df.iloc[0]
    
    assert row['scheduled_agents'] == 2
    assert row['metric_validity'] == "VALID_ERLANG_C"
    assert row['sla_percent'] == 100.0
    assert row['asa_seconds'] == 0.0
    assert row['utilization_percent'] == 0.0

def test_higher_staffing_does_not_perform_worse(tmp_path):
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.base_dir = tmp_path / "runs" / str(run_id)
    storage.ensure_run_dirs()

    df = pd.DataFrame({
        "hour": [14, 15],
        "calls": [100.0, 100.0], 
        "scheduled_agents": [10, 12]
    })
    
    df.to_csv(storage.result_path("classical_optimization_schedule.csv"), index=False)
    run_queue_simulation(run_id)
    
    res_df = pd.read_csv(storage.result_path("queue_validation_results.csv"))
    
    sla_10 = res_df.iloc[0]['sla_percent']
    asa_10 = res_df.iloc[0]['asa_seconds']
    
    sla_12 = res_df.iloc[1]['sla_percent']
    asa_12 = res_df.iloc[1]['asa_seconds']
    
    assert sla_12 >= sla_10
    assert asa_12 <= asa_10
