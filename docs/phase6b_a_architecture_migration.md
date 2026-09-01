# Phase 6B-A Architecture Migration

## 1. Old Architecture
The system relied heavily on a root-level `src/` directory containing standalone Python modules. The production FastAPI application (`backend/app`) was importing implementation details directly from `src/`. Scripts like `run_all.py` and Pytest executed with mixed module resolution environments (some leveraging `PYTHONPATH`, others relying on relative directories).

## 2. New Architecture
The core mathematical, optimization, and AI logic has been encapsulated within the backend application layer. The backend now solely relies on `app.core_engine` rather than unstable external paths. 

```text
Frontend
   |
   v
FastAPI Routers
   |
   v
Application Services
   |
   v
Core Engine
   +--> Forecasting (demand_forecaster)
   +--> Classical Optimization (classical_optimizer, shift_optimizer)
   +--> Quantum Optimization (quantum_optimizer)
   +--> Queue Simulation (queue_simulator)
   +--> Common Utilities (data_generator)
```

## 3. Modules Moved
- `src/demand_forecaster.py` -> `backend/app/core_engine/forecasting/demand_forecaster.py`
- `src/classical_optimizer.py` -> `backend/app/core_engine/optimization/classical_optimizer.py`
- `src/shift_optimizer.py` -> `backend/app/core_engine/optimization/shift_optimizer.py`
- `src/quantum_optimizer.py` -> `backend/app/core_engine/quantum/quantum_optimizer.py`
- `src/queue_simulator.py` -> `backend/app/core_engine/queue/queue_simulator.py`
- `src/data_generator.py` -> `backend/app/core_engine/common/data_generator.py`

## 4. Imports Changed
All internal imports within the moved files were updated to use the `app.core_engine...` namespace.
External imports across the repository (e.g. `tests/`, `run_all.py`, `sanity_check_*.py`, `backend/app/routers/dashboard.py`) were successfully migrated to `from app.core_engine.X.Y import Z`. Legacy standalone scripts (`run_all.py`, `sanity_check_*`, `src/dashboard.py`) had `sys.path.append('backend')` injections explicitly added to ensure module resolution compatibility outside of the Pytest environment.

## 5. Dependency Direction
Dependencies now correctly flow downwards:
`backend/app/routers` -> `backend/app/core_engine`

The FastAPI production code no longer depends on any root-level script structures.

## 6. Compatibility Decisions
- The legacy Streamlit dashboard (`src/dashboard.py`) was purposefully kept in `src/` (as `run_all.py` prints a direct invocation instruction to it), but its internal imports were upgraded to utilize the new `app.core_engine` backend package with a `sys.path` injection. 
- Standalone execution scripts (`run_all.py`) were preserved and updated. 

## 7. Tests Before Migration
23 passed, 8 warnings

## 8. Tests After Migration
23 passed, 8 warnings

## 9. Known Remaining Technical Debt
- **File Storage**: The application still hardcodes file paths to the global `data/` and `results/` folders (addressed in Phase 6B-B).
- **Mathematical Errors**: Erlang-C staffing padding remains, and Quantum optimization remains a hardcoded 4-agent problem (addressed in subsequent phases).

## 10. What is Intentionally NOT Changed
- No UUID or storage modifications were introduced.
- No mathematical logic (queue simulation, quantum solver, classical constraints) was altered.
- No frontend API logic (Token Refresh) was touched.
