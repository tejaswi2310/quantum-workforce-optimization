# Phase 6B-C Implementation Plan: Production Architecture Hardening

## 1. Target Architecture & Orchestration (Correction 1, 3)
The application will transition from a "split-brain" simulated execution to a robust, unified background pipeline. A new independent Orchestration Service will act as the master controller for the Core Engine, ensuring execution is identical whether invoked by FastAPI or CLI (`run_all.py`), and keeping the Core Engine decoupled from FastAPI:

```
          [FastAPI Router]            [CLI (run_all.py)]
                 ↓                             ↓
     [Run/Optimization Service]                │
                 ↓                             ↓
          [Pipeline Orchestrator (Orchestration Service)]
                 ↓                             ↓
        ┌──────────────────────────────────────────┐
        │               Core Engine                │
        │                                          │
        │ 1. Data Generator                        │
        │ 2. Forecasting                           │
        │ 3. Classical Optimization                │
        │ 4. Quantum Optimization                  │
        │ 5. Shift Optimization                    │
        │ 6. Queue Simulation                      │
        └──────────────────────────────────────────┘
                 ↓
           [StorageService]
```
While FastAPI `BackgroundTasks` will trigger the orchestrator asynchronously to prevent API blocking, the orchestration logic itself will be self-contained, permitting a future drop-in replacement with durable queue workers (e.g., Celery) without rewriting the pipeline logic.

## 2. Run Lifecycle & Database (Correction 2, 5, 10)
A single workflow run will have **one canonical `run_id`** propagated uniformly through every mathematical stage and directory lookup.
We will repurpose the existing `OptimizationRun` model to represent the entire run workflow without creating duplicate database concepts.

The lifecycle stages (`OptimizationRun.status`) will precisely track execution:
`CREATED` → `DATA_GENERATING` → `FORECASTING` → `OPTIMIZING` → `SIMULATING` → `REPORTING` → `COMPLETED`

**Failure Semantics:** 
If any stage throws an exception, it will be caught by the Orchestrator. The run will preserve its `run_id`, but the database state will transition to `FAILED`. A structured failure message (without raw stack traces) will be stored in an `error_message` column (added via migration/schema update or stuffed into a JSON `results` field) and logged securely. 

## 3. Storage Isolation (Correction 6)
`StorageService` will exclusively receive the canonical `run_id` (not `project_id`). This ensures every optimization pipeline iteration, whether concurrent or sequential, receives total isolation at `runtime/runs/<run_id>/`. The antipattern of `data/` and `results/` globals will remain strictly absent. 

## 4. Real Pipeline Execution (Correction 4)
The simulated `time.sleep()` blocks in `ml_service.py` will be permanently purged. API POST requests to `/optimize` will invoke the genuine pipeline passing the `OptimizationRun.id` to the new Orchestration Service.

## 5. KPI Integrity (Correction 7)
All hardcoded, assumed, or mathematically ungrounded KPIs will be removed from:
- API Router layers (`dashboard.py`, `forecast.py`)
- Visual dashboard layers (`src/dashboard.py`)
All returned values (e.g., cost, SLA, staffing numbers, predictions) will be calculated by parsing the true output CSVs/logs deposited by the pipeline stages into `StorageService`.

## 6. Quantum Transparency & Horizon (Correction 8, 9)
**Transparency:** The dashboard and API responses will be heavily refactored to explicitly document the quantum phase as a *Qiskit Statevector Simulation on a reduced problem space*. We will extract and display truthful metrics: Number of Qubits (8), Execution Backend (Simulator), Feasibility, and Runtime. Any claim of "Quantum Advantage" will be stripped unless empirically validated by the output CSV.
**Horizon:** Classical and Shift optimization will run across the intended full-day demand horizon. Only the Quantum solver will remain mathematically restricted to the 2-hour peak subset (due to QUBO sizing), which will be transparently documented in the output logs and the UI.

---

## Technical Action Plan

### 1. Files to Change
- `backend/app/models/models.py`: Adjust `OptimizationRun` (status lengths, add error fields to `results` JSON).
- `backend/app/routers/optimize.py`: Refactor endpoints to launch the actual orchestrator pipeline, not the sleep function.
- `backend/app/routers/dashboard.py`: Strip hardcoded KPIs. Extract metrics strictly via `StorageService`.
- `backend/app/routers/forecast.py`: Strip hardcoded prediction arrays. Link to real metrics.
- `backend/app/routers/datasets.py` & `reports.py`: Initialize `StorageService(latest_run_id)` instead of `StorageService(project_id)`.
- `backend/app/services/ml_service.py`: To be refactored or absorbed into the new `OrchestrationService`.
- `backend/app/core_engine/quantum/quantum_optimizer.py`: Enhance metadata logging in the output CSV to clarify simulator status and metrics. Ensure it safely skips/fails gracefully on import errors.
- `src/dashboard.py`: Rewrite KPI presentation layers to explicitly flag simulation bounds and parse raw storage data.
- `run_all.py`: Migrate to invoke the exact same unified `OrchestrationService` pipeline as the API.

### 2. Files to Add
- `backend/app/services/orchestration_service.py`: The new independent, reusable pipeline controller.
- `backend/tests/test_orchestration.py`: Test suite validating pipeline state transitions, failures, and concurrency isolation.
- `docs/phase6b_c_production_hardening.md`: Final documentation covering architecture, storage, failure handling, and migration strategies.

### 3. Files to Delete
- None expected. (Legacy `.py` scripts in `src/` will remain as backwards-compatibility shims).

### 4. Database Changes
- Expand the semantic use of `OptimizationRun` to act as the global job tracker.
- No heavy alembic migrations required; we will utilize the `status` enum and `results` JSON column to store execution phases and structured error logs.

### 5. API Changes
- `/api/v1/projects/{id}/optimize`: Immediately returns a `CREATED` run payload.
- `/api/v1/projects/{id}/dashboard/*`: Returns dynamic, parsed values rather than static templates.

### 6. Core-engine Changes
- Add resilient error bubbling so the orchestrator can catch and record specific stage failures.
- Modify `quantum_optimizer.py` to write explicit hardware/simulator boolean flags and qubit counts to its output CSV.

### 7. Test Changes
- Current baseline (28 passed) remains untouched.
- **Add Tests:**
  1. Pipeline state transitions (`CREATED` -> `COMPLETED`).
  2. Exception propagation triggering the `FAILED` state.
  3. Canonical `run_id` directory isolation (proving Run A cannot overwrite Run B).
  4. KPI dynamic extraction logic in the dashboard routers.
  5. Absence of fake mocks (`time.sleep` execution).

### 8. Risks
- **Background Blocking:** If the Orchestration Service accidentally blocks the FastAPI main thread, the server will hang. Mitigation: Strict enforcement of asynchronous delegation (`BackgroundTasks.add_task`).
- **Data Dependency:** The pipeline steps assume sequential execution. If a stage (e.g., forecasting) fails, subsequent stages must abort cleanly. Mitigation: Global Try/Except wrapping in the Orchestrator with early termination.

### 9. Verification Commands
- `python -m pytest -q` (Regression & Isolation Verification)
- `python run_all.py` (CLI Orchestrator equivalence check)
- `curl`/Swagger POST to `/optimize` verifying background UUID execution in `runtime/runs/<uuid>/`.
