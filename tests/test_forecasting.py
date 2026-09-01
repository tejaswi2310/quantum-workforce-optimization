import os
import pandas as pd
import pytest
from app.core_engine.forecasting.demand_forecaster import smape

def test_smape_zero_handling():
    # Should handle zeros gracefully
    assert smape(0, 0) == 0.0
    assert smape(0, 10) == 200.0  # |0-10| / (10/2) = 10 / 5 = 2 = 200%
    assert smape(10, 0) == 200.0

def test_chronological_splits():
    # Load evaluation results
    eval_path = os.path.join("data", "processed", "forecast_evaluation.csv")
    if not os.path.exists(eval_path):
        pytest.skip(f"{eval_path} not found")
        
    df = pd.read_csv(eval_path)
    df['datetime'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
    
    train_dates = df[df['split'] == 'train']['datetime']
    val_dates = df[df['split'] == 'val']['datetime']
    test_dates = df[df['split'] == 'test']['datetime']
    
    # Verify strict chronology
    assert train_dates.max() < val_dates.min(), "Train data bleeds into validation data!"
    assert val_dates.max() < test_dates.min(), "Validation data bleeds into test data!"

def test_lags_dont_leak():
    # Ensure lag_168 is exactly 7 days prior for a specific row
    eval_path = os.path.join("data", "processed", "forecast_evaluation.csv")
    if not os.path.exists(eval_path):
        pytest.skip(f"{eval_path} not found")
        
    df = pd.read_csv(eval_path)
    
    # Just checking the baseline since we assigned lag_168 to baseline_calls
    # If date is X, baseline_calls must equal calls_received of X - 7 days.
    
    # Take a random test row
    test_row = df[df['split'] == 'test'].iloc[0]
    target_dt = pd.to_datetime(test_row['date']) - pd.Timedelta(days=7)
    
    past_rows = df[(df['date'] == target_dt.strftime("%Y-%m-%d")) & 
                   (df['hour'] == test_row['hour']) &
                   (df['channel'] == test_row['channel']) &
                   (df['skill_group'] == test_row['skill_group'])]
                   
    if not past_rows.empty:
        assert test_row['baseline_calls'] == past_rows['calls_received'].values[0]
