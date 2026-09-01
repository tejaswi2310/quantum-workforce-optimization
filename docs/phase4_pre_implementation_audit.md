# Phase 4 Pre-Implementation Audit

## Pre-Requisites Search

### 1. `frontend/src/pages/Dashboard.tsx`
- **Problem**: Contains heavy use of fabricated metrics and `Math.random()`.
  - Lines 27-46: `Math.random()` used for hourly calls and 7-day forecast.
  - Lines 75-80: Hardcoded "51,240" total calls, "240s" AHT, "10:00 AM" peak hour.
  - Lines 143-145: Hardcoded MAE, RMSE, and R² for forecasting.
  - Lines 186-192: Hardcoded schedule numbers (Required 42, Scheduled 58, Cost $870.00).
  - Lines 202-243: Hardcoded Quantum and Classical metrics ($870, 100% match).
  - Lines 247-273: Hardcoded Business Impact savings ($1,440 vs $870).
  - Lines 301-310: Hardcoded Queue Validation metrics (420 calls, 58 agents, 89.4% SLA).
- **Classification**: **FAIL**
- **Recommended Fix**: Completely rip out all mock data arrays. Refactor the component to use `useEffect` and `fetch` to retrieve `/api/v1/projects/{project_id}/dashboard/metrics` and `analytics` from the FastAPI backend. Implement standard Loading/Error/Success states.

### 2. `backend/app/routers/dashboard.py`
- **Problem**: Returns statically typed dictionaries for analytics, inventing shape distributions.
  - `get_dashboard_analytics`: Returns hardcoded `calls_per_hour`, `calls_by_channel`.
  - `get_whatif_scenario`: Implements a mathematically dishonest "what-if" projection that linearly scales cost and agents by `1 + volume_change/100`, which ignores Erlang-C non-linearities.
- **Classification**: **FAIL**
- **Recommended Fix**: Re-write `get_dashboard_analytics` to read real CSV output (`synthetic_call_center.csv` or `forecast_results.csv`). For `get_whatif_scenario`, either implement real Erlang-C scaling or clearly label it as a linear sensitivity approximation on the frontend.

### 3. `backend/app/routers/reports.py`
- **Problem**: Fabricates naive cost as `opt_cost * 1.6`.
- **Classification**: **FAIL**
- **Recommended Fix**: Compute true naive cost (e.g., peak demand * hours) or calculate actual Erlang-C required agent-hours vs scheduled agent-hours, rather than inventing a flat `1.6x` multiplier.

### 4. `backend/app/services/ml_service.py`
- **Problem**: 
  - `train_random_forest`: Hardcodes evaluation metrics `mae: 6.44`, `rmse: 9.97`.
  - `run_optimization`: Averages out queue validation data into a single fake row for Hour 9.
- **Classification**: **FAIL**
- **Recommended Fix**: Have `train_random_forest` parse the real `forecast_evaluation.csv`. Remove the fake QueueValidation DB entry in `run_optimization` since the true validation data lives in `queue_validation_results.csv`.

### 5. Agent Limit Consistency
- **Problem**: The classical optimizer generates a purely random array of agents dynamically during the optimization step. The README and previous text claim an "80 agent" limit, but `classical_optimizer.py` generates 120 agents to bypass infeasibility. There is no true linkage between available workforce pool and optimization.
- **Classification**: **FAIL**
- **Recommended Fix**: Extract workforce generation out of `classical_optimizer.py` and into `generate_data.py` (or load from CSV). Limit the solver strictly to the *actual* available pool.

### 6. Queue Simulator Abandonment
- **Problem**: The fake abandonment formula `max(0.1, (100 - SLA) * 0.1)` was removed in Phase 3, but the dashboard still expects an abandonment rate.
- **Classification**: **WARNING**
- **Recommended Fix**: Remove abandonment from the dashboard UI entirely or explicitly label it "Not Modeled (Erlang-C Infinite Patience)".

### 7. Quantum Transparency
- **Problem**: The dashboard presents Qiskit QAOA as solving the full workforce problem. In reality, it only solves an 8-variable reduced QUBO instance for a single 2-hour window.
- **Classification**: **FAIL**
- **Recommended Fix**: Update the frontend to clearly display "Reduced QUBO (8 Variables)" and explain that it represents a small sub-problem.

## Next Steps
This audit dictates the structure of the Phase 4 Implementation Plan, targeting end-to-end mathematical honesty.
