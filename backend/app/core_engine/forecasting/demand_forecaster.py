"""
Module for training the AI demand forecasting model.
Uses a chronological split, constructs lag features safely without future leakage,
and trains a RandomForestRegressor.

HOURLY TIME-SERIES DATA CONTRACT
---------------------------------
The lag and rolling features in this module assume the following contract
for every (channel, skill_group) group in the training data:

  * One row represents exactly one hourly observation.
  * Exactly one observation exists per hour (no duplicates, no missing hours).
  * Timestamps are valid and form a strictly regular hourly sequence.
  * Chronological sorting is applied before any lag/rolling computation.

Under this contract:
  shift(24)  == 24 hours ago (yesterday, same hour)
  shift(168) == 168 hours ago (last week, same hour)

The helper validate_forecasting_time_series() enforces this contract at
runtime and raises ValueError with a precise diagnostic if it is violated.
"""
import os

import numpy as np
import pandas as pd
from datetime import timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
import uuid
from app.services.storage_service import StorageService

def smape(y_true, y_pred):
    """Calculates Symmetric Mean Absolute Percentage Error."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    numerator = np.abs(y_true - y_pred)
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    # Handle zeros: if both are zero, smape is 0
    with np.errstate(divide='ignore', invalid='ignore'):
        res = numerator / denominator
    if res.ndim == 0:
        if np.isnan(res):
            return 0.0
        return float(res) * 100.0
    res[np.isnan(res)] = 0.0
    return np.mean(res) * 100.0


def validate_forecasting_time_series(df: "pd.DataFrame") -> None:
    """
    Validate that every (channel, skill_group) group satisfies the hourly
    time-series contract required by the row-based lag features.

    The caller must have already constructed the 'datetime' column via::

        df['datetime'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')

    and sorted the DataFrame before calling this function.

    Raises
    ------
    ValueError
        If any group contains duplicate timestamps, missing hours, or
        timestamps that are not exactly one hour apart.

    Notes
    -----
    * Does not mutate the caller's DataFrame.
    * Approximately O(n) in the number of rows.
    * Group isolation is complete: each (channel, skill_group) pair is
      validated independently.
    """
    expected_delta = pd.Timedelta(hours=1)

    for (channel, skill_group), grp in df.groupby(["channel", "skill_group"], sort=False):
        ts = grp["datetime"]  # already sorted — view only, no copy

        # 1. Duplicate timestamps
        dup_mask = ts.duplicated(keep=False)
        if dup_mask.any():
            dup_ts = ts[dup_mask].iloc[0]
            raise ValueError(
                f"Duplicate timestamp detected in group "
                f"channel='{channel}', skill_group='{skill_group}': {dup_ts}"
            )

        # 2 & 3. Missing hours / irregular interval — check consecutive diffs
        if len(ts) < 2:
            continue  # single-row group: no consecutive pair to check

        ts_values = ts.values  # numpy datetime64 array — avoids Python overhead
        for idx in range(1, len(ts_values)):
            delta = pd.Timestamp(ts_values[idx]) - pd.Timestamp(ts_values[idx - 1])
            if delta != expected_delta:
                prev_ts = pd.Timestamp(ts_values[idx - 1])
                curr_ts = pd.Timestamp(ts_values[idx])
                if delta > expected_delta:
                    # Gap — at least one hour missing
                    missing_ts = prev_ts + expected_delta
                    raise ValueError(
                        f"Missing hourly timestamp in group "
                        f"channel='{channel}', skill_group='{skill_group}': "
                        f"expected {missing_ts} after {prev_ts}, "
                        f"but next observed timestamp is {curr_ts}"
                    )
                else:
                    # Sub-hourly or irregular interval
                    raise ValueError(
                        f"Irregular timestamp interval in group "
                        f"channel='{channel}', skill_group='{skill_group}': "
                        f"observed interval {delta} between {prev_ts} and {curr_ts} "
                        f"(expected exactly 1 hour)"
                    )


def train_forecast(run_id: uuid.UUID = None):
    storage = StorageService(run_id)
    storage.ensure_run_dirs()

    # 1. Load synthetic data
    data_path = storage.data_path("raw/synthetic_call_center.csv")
    if not os.path.exists(data_path):
        # Fallback to global data/raw for backward compatibility during tests if needed
        global_path = os.path.join("data", "raw", "synthetic_call_center.csv")
        if os.path.exists(global_path):
            data_path = global_path
        else:
            raise FileNotFoundError(f"Synthetic data not found at {data_path}. Please run data_generator.py first.")
        
    df = pd.read_csv(data_path)
    
    # 2. Sort chronologically
    df['datetime'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
    df = df.sort_values(by=['datetime', 'channel', 'skill_group']).reset_index(drop=True)
    
    # 3. Validate hourly time-series contract before computing lag features.
    #    shift(24) / shift(168) are row-based and only equal 24 h / 168 h when
    #    every (channel, skill_group) group has exactly one observation per hour
    #    with no gaps, no duplicates, and no irregular intervals.
    validate_forecasting_time_series(df)

    # 4. Feature engineering (No future leakage)
    df['is_weekend'] = df['day_of_week'].isin(['Saturday', 'Sunday']).astype(int)

    # Construct lags properly grouped by series.
    # Dataset is hourly and the contract above is now validated, so:
    #   lag_24  = yesterday same hour  (shift of 24 rows within each group)
    #   lag_168 = last week same hour  (shift of 168 rows within each group)
    df['lag_24'] = df.groupby(['channel', 'skill_group'])['calls_received'].shift(24)
    df['lag_168'] = df.groupby(['channel', 'skill_group'])['calls_received'].shift(168)
    
    # Rolling mean 24 (historical only, shift by 1 to not include current hour)
    df['rolling_mean_24'] = df.groupby(['channel', 'skill_group'])['calls_received'] \
                              .transform(lambda x: x.shift(1).rolling(24, min_periods=1).mean())

    # Drop NaNs caused by lagging
    df = df.dropna(subset=['lag_168']).reset_index(drop=True)
    
    # Baseline predictions (Seasonal Naive = lag_168)
    df['baseline_pred'] = df['lag_168']
    
    # 4. Chronological Splits (70% Train, 15% Val, 15% Test)
    unique_dates = df['date'].unique()
    n_dates = len(unique_dates)
    
    train_end = int(n_dates * 0.7)
    val_end = int(n_dates * 0.85)
    
    train_dates = unique_dates[:train_end]
    val_dates = unique_dates[train_end:val_end]
    test_dates = unique_dates[val_end:]
    
    def assign_split(d):
        if d in train_dates: return 'train'
        elif d in val_dates: return 'val'
        else: return 'test'
        
    df['split'] = df['date'].apply(assign_split)
    
    # 5. One-hot encoding
    categorical_cols = ['day_of_week', 'channel', 'skill_group']
    df_encoded = pd.get_dummies(df, columns=categorical_cols)
    
    target = 'calls_received'
    exclude = ['date', 'datetime', 'interval', 'avg_handle_time', 'agents_available', 
               'sla_achieved', target, 'split', 'baseline_pred']
    features = [c for c in df_encoded.columns if c not in exclude]
    
    # 6. Prepare datasets
    train_mask = df_encoded['split'] == 'train'
    val_mask = df_encoded['split'] == 'val'
    test_mask = df_encoded['split'] == 'test'
    
    X_train, y_train = df_encoded[train_mask][features], df_encoded[train_mask][target]
    X_val, y_val = df_encoded[val_mask][features], df_encoded[val_mask][target]
    X_test, y_test = df_encoded[test_mask][features], df_encoded[test_mask][target]
    
    # 7. Train Model
    model = RandomForestRegressor(n_estimators=50, max_depth=10, min_samples_split=4, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    # 8. Evaluate Baseline and ML Model
    splits = [('TRAIN', train_mask), ('VALIDATION', val_mask), ('TEST', test_mask)]
    
    print("==================================================")
    print("FORECASTING EVALUATION RESULTS (CHRONOLOGICAL)")
    print("==================================================")
    
    for split_name, mask in splits:
        y_true = df_encoded[mask][target]
        y_base = df_encoded[mask]['baseline_pred']
        y_pred = np.clip(model.predict(df_encoded[mask][features]), 0, None)
        
        # ML metrics
        mae_ml = mean_absolute_error(y_true, y_pred)
        rmse_ml = root_mean_squared_error(y_true, y_pred)
        smape_ml = smape(y_true, y_pred)
        
        # Baseline metrics
        mae_base = mean_absolute_error(y_true, y_base)
        rmse_base = root_mean_squared_error(y_true, y_base)
        smape_base = smape(y_true, y_base)
        
        print(f"\n--- {split_name} SET ---")
        print(f"ML Model:       MAE={mae_ml:.4f}, RMSE={rmse_ml:.4f}, sMAPE={smape_ml:.2f}%")
        print(f"Baseline (SNaive): MAE={mae_base:.4f}, RMSE={rmse_base:.4f}, sMAPE={smape_base:.2f}%")
        
        # Store predictions
        df.loc[mask, 'predicted_calls'] = y_pred.round(2)
        df.loc[mask, 'model'] = 'RandomForest'
        df.loc[mask, 'baseline_calls'] = y_base.round(2)


        
    # Save the evaluation results
    output_cols = ['date', 'hour', 'interval', 'channel', 'skill_group', 
                   'calls_received', 'predicted_calls', 'baseline_calls', 'split', 'model']
    storage.atomic_write_csv(df[output_cols], storage.data_path("processed/forecast_evaluation.csv"), index=False)
    
    # 10. Generate 7-day future forecast (for optimizer)
    print("\nGenerating 7-day future forecast...")
    last_date = pd.to_datetime(df['date'].max())
    forecast_records = []
    
    channels = ["Voice", "Chat", "Email"]
    skills = ["Billing", "Technical", "Sales", "General"]
    
    # To predict future properly, we need historical lags. 
    # For a naive 7-day future, we can just grab the last 7 days of actuals.
    # To keep it simple and runnable for optimizer without recursive prediction logic, 
    # we'll build a future dataframe and map the lag_168 from the exact last week.
    
    last_7_days_mask = pd.to_datetime(df['date']) > (last_date - timedelta(days=7))
    df_last_7 = df[last_7_days_mask].copy()
    
    for i in range(1, 8):
        future_date = last_date + timedelta(days=i)
        date_str = future_date.strftime("%Y-%m-%d")
        day_name = future_date.strftime("%A")
        is_weekend = 1 if day_name in ["Saturday", "Sunday"] else 0
        
        for hour in range(24):
            for channel in channels:
                for skill in skills:
                    # Find lag_168 exactly 7 days prior
                    past_dt = future_date - timedelta(days=7)
                    past_str = past_dt.strftime("%Y-%m-%d")
                    past_row = df[(df['date'] == past_str) & (df['hour'] == hour) & 
                                  (df['channel'] == channel) & (df['skill_group'] == skill)]
                                  
                    lag_24_val = 0
                    lag_168_val = 0
                    rolling_val = 0
                    if not past_row.empty:
                        lag_168_val = past_row['calls_received'].values[0]
                        rolling_val = past_row['rolling_mean_24'].values[0] # Approx
                        lag_24_val = lag_168_val # Very rough approx for future generation
                        
                    forecast_records.append({
                        "date": date_str,
                        "day_of_week": day_name,
                        "hour": hour,
                        "interval": f"{hour:02d}:00-{(hour+1)%24:02d}:00",
                        "channel": channel,
                        "skill_group": skill,
                        "holiday": 0,
                        "is_weekend": is_weekend,
                        "lag_24": lag_24_val,
                        "lag_168": lag_168_val,
                        "rolling_mean_24": rolling_val
                    })
                    
    df_forecast = pd.DataFrame(forecast_records)
    df_fc_encoded = pd.get_dummies(df_forecast, columns=['day_of_week', 'channel', 'skill_group'])
    
    for col in features:
        if col not in df_fc_encoded.columns:
            df_fc_encoded[col] = 0
            
    X_fc = df_fc_encoded[features]
    preds = model.predict(X_fc)
    df_forecast['predicted_calls'] = np.clip(preds, 0, None).round(2)
    
    storage.atomic_write_csv(df_forecast, storage.data_path("processed/forecast_results.csv"), index=False)
    print(f"Future forecast saved to {storage.data_path('processed/forecast_results.csv')}. Rows: {len(df_forecast)}")

if __name__ == "__main__":
    train_forecast()
