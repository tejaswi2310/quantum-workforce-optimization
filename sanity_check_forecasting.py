import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from app.core_engine.forecasting.demand_forecaster import smape

print("=== FORECASTING SANITY CHECK ===")

eval_path = os.path.join("data", "processed", "forecast_evaluation.csv")
if not os.path.exists(eval_path):
    print(f"Error: {eval_path} not found.")
    exit(1)

df = pd.read_csv(eval_path)

# Verify counts
print(f"Total Rows: {len(df)}")
splits = df['split'].value_counts()
print("\nSplits:")
print(splits)

# Verify Test Metrics independently
test_df = df[df['split'] == 'test'].copy()
if len(test_df) == 0:
    print("Error: No test data found.")
    exit(1)
    
y_true = test_df['calls_received']
y_pred = test_df['predicted_calls']
y_base = test_df['baseline_calls']

mae_ml = mean_absolute_error(y_true, y_pred)
rmse_ml = root_mean_squared_error(y_true, y_pred)
smape_ml = smape(y_true, y_pred)

print("\n--- INDEPENDENT TEST METRICS ---")
print(f"ML MAE: {mae_ml:.4f}")
print(f"ML RMSE: {rmse_ml:.4f}")
print(f"ML sMAPE: {smape_ml:.2f}%")

mae_base = mean_absolute_error(y_true, y_base)
rmse_base = root_mean_squared_error(y_true, y_base)
smape_base = smape(y_true, y_base)

print(f"\nBaseline MAE: {mae_base:.4f}")
print(f"Baseline RMSE: {rmse_base:.4f}")
print(f"Baseline sMAPE: {smape_base:.2f}%")

# Verify Chronology
train_end = df[df['split'] == 'train']['date'].max()
test_start = df[df['split'] == 'test']['date'].min()

print(f"\nTrain Ends: {train_end}")
print(f"Test Starts: {test_start}")
if train_end < test_start:
    print("CHRONOLOGY VERIFIED: PASS")
else:
    print("CHRONOLOGY VERIFIED: FAIL")
