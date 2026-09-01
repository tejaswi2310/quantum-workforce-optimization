# Phase 6B Pre-Implementation Inventory

## 1. Current Architecture
The system consists of a FastAPI backend managing an SQLite database for users and projects. However, the core machine learning and optimization engines reside in a root-level `src/` directory designed as a collection of standalone Python scripts. The backend interacts with `src/` by directly importing functions or executing them via background tasks. The React frontend interacts with the FastAPI backend over a REST API.

## 2. Dependency Map
**Imports from `src/` into the backend and tests:**
- `backend/app/routers/dashboard.py` imports `src.queue_simulator.erlang_c`, `required_agents_for_sla`
- `tests/test_optimization.py` imports `src.queue_simulator.erlang_c`, `src.quantum_optimizer.solve_qubo_classical`
- `tests/test_forecasting.py` imports `src.demand_forecaster.smape`
- `tests/test_erlang_c.py` imports `src.queue_simulator.required_agents_for_sla`
- `run_all.py`, `sanity_check_*.py` import heavily from `src/`

**Problem**: The `backend` assumes `src` is in the `PYTHONPATH`. This works when executed from the repository root but tightly couples the REST API to standalone script structures, preventing independent scaling or containerization.

## 3. Storage Map
Files are currently read/written to global directories relative to the root:
- `data/raw/synthetic_call_center.csv`
- `data/processed/forecast_results.csv`, `forecast_evaluation.csv`
- `models/forecasting_model.pkl`, `feature_columns.pkl`
- `results/classical_optimization_schedule.csv`, `agent_shifts_detailed.csv`, `shift_schedule.csv`, `active_shifts.csv`
- `results/queue_validation_results.csv`
- `results/quantum_classical_comparison.csv`

**Problem**: These paths are hardcoded globally using `os.path.join(...)` inside the `src/` modules. There is no isolation per project or per run. 

## 4. Multi-Tenancy Risks
**FILE**: `backend/app/services/ml_service.py`, `src/demand_forecaster.py`, `src/shift_optimizer.py`
**CURRENT BEHAVIOR**: ML processes overwrite global files (e.g., `results/shift_schedule.csv`).
**PROBLEM**: If User A and User B trigger an optimization concurrently on different projects, User B will overwrite User A's `shift_schedule.csv`. When User A fetches their dashboard, they will view User B's results.
**RECOMMENDED CHANGE**: Scope all file I/O to a structured directory path using UUIDs: `backend/storage/{project_id}/{run_id}/`.
**RISK**: Changing the file I/O layer will initially break the 23 passing E2E tests until the tests are updated to inject dynamic paths.

## 5. Queue/Erlang-C Findings
**FILE**: `src/queue_simulator.py`
**FUNCTION**: `run_queue_simulation`
**CURRENT BEHAVIOR**: Inside the simulation loop, it computes the traffic intensity `A`. If `sim_agents <= A`, it forcibly executes `sim_agents = int(math.ceil(A)) + 1` to prevent mathematical instability in the Erlang-C formula.
**PROBLEM**: This artificially injects extra agents into the simulated schedule, masking optimization shortfalls. A schedule that legitimately understaffs the call center will instantly be "padded" with enough agents to handle the traffic, resulting in artificially high SLAs. Additionally, AHT is hardcoded to 300 and Target Wait Time is hardcoded to 20 seconds.
**RECOMMENDED CHANGE**: Remove the padding. If `agents <= A`, the simulation should mathematically fail (SLA = 0% or wait time approaches infinity) rather than altering the staffing input. Move AHT and SLA targets to project configuration variables.
**RISK**: Fixing this will expose optimization shortfalls, meaning previously "Optimal" schedules may now fail the SLA validation phase.

## 6. Quantum Methodology Findings
**FILE**: `src/quantum_optimizer.py`
**FUNCTION**: `run_quantum_optimization`
**CURRENT BEHAVIOR**: The script hardcodes `target_skill = "Technical"`, `Hours: 10 - 12` (2 hours), and `N_agents = 4`. Demand is artificially capped at 2 (`min(d_t0, 2)`). It generates an 8-variable QUBO and solves it using Qiskit's QAOA.
**PROBLEM**: This is a trivial toy problem. It does not perform a 24-hour quantum optimization, nor does it handle realistic agent counts or demand. The dashboard displays these toy metrics as if they represent the actual 24-hour schedule. This damages the scientific credibility of the project.
**RECOMMENDED CHANGE**: Implement a Hybrid Quantum-Classical Solver. Use classical optimization for the macroscopic 24-hour formulation, and iteratively decompose difficult localized shift transitions into QUBO windows to feed into QAOA, aggregating the results back into the final schedule.
**RISK**: QAOA is computationally expensive. Scaling the problem up or increasing the sliding window size may cause timeouts during API requests.

## 7. Forecasting Pipeline
**FILE**: `src/demand_forecaster.py`
**CURRENT BEHAVIOR**: Reads from `data/raw/synthetic_call_center.csv`, trains a RandomForestRegressor, and dumps standard evaluation metrics to a static `forecast_evaluation.csv`.
**PROBLEM**: It is fully disconnected from the `dataset_id` tracked in the database. The features and horizon are hardcoded.
**RECOMMENDED CHANGE**: Modify the forecasting service to load the specific `dataset_id` associated with the `project_id`, extract the time-series boundary dynamically, and persist the model artifacts within the scoped storage directory.

## 8. Classical Optimization
**FILE**: `src/classical_optimizer.py`
**CURRENT BEHAVIOR**: Uses PuLP to solve shift assignments over 24 hours. The cost parameter ($15/hr) is hardcoded.
**PROBLEM**: The optimization correctly pulls from the static `forecast_results.csv` but writes a static output.
**RECOMMENDED CHANGE**: Parameterize the hourly cost. Read and write to the UUID-scoped storage directories.
**RISK**: Low risk, primarily I/O refactoring.

## 9. Frontend Authentication
**FILE**: `frontend/src/lib/api.ts`
**CURRENT BEHAVIOR**: The Axios response interceptor checks for a `401` response. If found, it clears the token and forces a `window.location.href = '/'` redirect.
**PROBLEM**: Because access tokens expire in 15 minutes, users actively working on the dashboard will be unexpectedly logged out. There is no refresh token exchange mechanism implemented in the interceptor.
**RECOMMENDED CHANGE**: Implement token refresh. On `401`, pause requests, post to `/api/v1/auth/token` (or a dedicated refresh endpoint) with the refresh token, and if successful, replay the paused requests. If the refresh fails, then execute the logout.
**RISK**: Race conditions during concurrent API calls triggering multiple refresh attempts simultaneously.

## 10. Existing Test Coverage
- `test_e2e_api.py`: Validates complete system flow assuming single-tenant persistence (passes 23/23).
- Missing coverage for invalid UUID formats on datasets.
- Missing concurrent optimization tests to expose file collision.
- Missing tests enforcing that Erlang-C correctly fails when understaffed.

## 11. Proposed Architecture
```text
backend/
  app/
    routers/
    services/
    core_engine/ (Replaces src/)
      forecasting/
      optimization/
      queue/
      quantum/
      common/
```
**Reasoning**: Merging `src/` into `backend/app/core_engine` guarantees that the backend executes as a cohesive module, eliminating `PYTHONPATH` hacking, standardizing imports, and allowing safe integration testing.

## 12. Proposed Storage Architecture
```text
backend/storage/{project_id}/
  datasets/{dataset_id}.csv
  runs/{run_id}/
    forecast_model.pkl
    forecast_results.csv
    classical_schedule.csv
    quantum_comparison.csv
    queue_validation.csv
```
**Reasoning**: Using a `StorageService` interface (`save_artifact`, `load_artifact`) guarantees file operations are isolated to the specific database records, entirely resolving the multi-tenancy overwrite vulnerability.

## 13. Proposed Hybrid Quantum Architecture
```text
1. 24-hour forecasted demand
2. Classical solver establishes baseline 24-hour schedule.
3. Problem Decomposition: Identify the 4-hour peak window with highest complexity (e.g. shift overlaps).
4. QUBO Generation: Formulate the sub-problem variables (Demand fulfillment, Agent limits, Overstaffing penalties).
5. QAOA Execution: Solve the windowed QUBO.
6. Schedule Reconstruction: Splice the Quantum results back into the baseline classical schedule.
7. Output realistic quantum/classical cost parity & runtime benchmarks.
```
**Reasoning**: This methodology is scientifically honest. It avoids faking a 24-hour quantum solution, utilizes a realistic QPU-compatible sub-problem size, and provides genuine benchmark comparisons between classical and quantum execution.

## 14. Migration Risks
- **Data Path Breakage**: Relocating `results/` to `backend/storage/` requires updating every pandas read/write call across all modules simultaneously to prevent the pipeline from breaking.
- **Test Invalidation**: The current E2E test suite will fail massively once the storage architecture shifts unless the test suite is refactored concurrently.
- **Quantum Execution Time**: Transitioning to a meaningful Hybrid QUBO size may increase backend latency significantly. Background task polling will be required instead of blocking HTTP requests.

## 15. Recommended Implementation Order
- **Phase 6B-A**: Architecture/import migration (Move `src/` to `backend/app/core_engine`).
- **Phase 6B-B**: Centralized multi-tenant storage (Implement `StorageService` and refactor I/O).
- **Phase 6B-C**: Queue/Erlang-C mathematical correction (Remove padding).
- **Phase 6B-D**: Hybrid quantum optimization implementation.
- **Phase 6B-E**: Frontend JWT refresh interceptors.
- **Phase 6B-F**: Final integration/regression testing.

## 16. Rollback Strategy
All changes will be isolated on `feat/phase-6b-architecture`. If migration complexities threaten the production viability of the API, the current phase can be instantly aborted by restoring the git tree to the `phase-6b-start` tag or the `backup/pre-phase-6b-architecture` branch, ensuring Phase 6A stability is never permanently lost.
