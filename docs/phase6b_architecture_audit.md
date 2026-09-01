# Phase 6B Architecture Audit

## A. Executive Summary
This audit evaluates the architecture, reliability, security, and demo readiness of the Quantum Workforce Optimization project as it transitions from a functional prototype (Phase 6A) into a production-grade system (Phase 6B). While the API integration and E2E tests are currently stable, significant structural and architectural flaws exist. Specifically, there are tight couplings between the backend API and the `src` scripts, single-tenant assumptions in data handling (writing CSVs to global folders rather than project-specific or database locations), and hardcoded/toy parameters in the Quantum optimization engine that undermine the project's credibility.

## B. Current Architecture
The current application uses a React frontend and a FastAPI backend with SQLite database persistence for User and Project models. However, core business logic and ML jobs are executed via standalone Python scripts residing in the `src/` directory, which parse and write CSV files to global `data/` and `results/` folders.

## C. Dependency Graph
- **Frontend** -> **Backend (FastAPI)**
- **Backend (Routers/Services)** -> **Database (SQLite)**
- **Backend (Routers/Services)** -> `src/` (Direct imports of optimization/simulation scripts)
- `src/` -> `results/`, `data/` (Direct filesystem access assuming single-tenant environment)

## D. Backend Architecture Assessment (Score: 4/10)
**Issues:**
- **P1**: Cross-layer Dependencies. The backend routers (e.g., `dashboard.py`) and services directly import logic from `src/`, causing messy boundary lines.
- **P1**: Global State / Single Tenancy. The ML service reads/writes to generic `results/` and `data/` directories, completely ignoring `project_id` isolation. Concurrent requests from different users will corrupt each other's files.
- **P2**: Path Assumptions. `ml_service.py` relies on `os.path.join(..., "../../..")` to find global directories, which breaks if the backend is containerized or moved.

## E. Frontend Architecture Assessment (Score: 5/10)
**Issues:**
- **P1**: Token Refresh logic in `api.ts` is stubbed out. A `401` response instantly logs the user out rather than utilizing the refresh token.
- **P2**: Hardcoded API endpoints and missing environment variable configurations (`.env`).
- **P3**: The dashboard does not clearly map out the workflow stages (Demand -> Classical -> Quantum -> Queue Validation).

## F. Database/Data Layer Assessment (Score: 6/10)
**Issues:**
- **P1**: File-based state management for ML inputs/outputs bypasses the database. The database records the Project/Run models, but the actual simulation data lives globally in CSVs.
- **P3**: UUIDs are correctly implemented across relations (fixed in Phase 6A).

## G. Authentication/Security Assessment (Score: 6/10)
**Issues:**
- **P1**: Frontend session management drops tokens prematurely.
- **P2**: No file extension sanitization or size limits explicitly enforced on CSV dataset uploads (Path traversal risks).

## H. Dataset Pipeline Assessment (Score: 5/10)
**Issues:**
- **P1**: Uploads are saved generically. Multiple project uploads will overwrite each other.

## I. Forecasting Assessment (Score: 6/10)
**Issues:**
- **P2**: Forecasting logic relies on static columns and handles errors poorly if input CSVs change structure.

## J. Classical Optimization Assessment (Score: 6/10)
**Issues:**
- **P1**: Writes shift schedules to a global CSV.

## K. Quantum Optimization Assessment (Score: 3/10) - CRITICAL RISK
**Issues:**
- **P0**: **Credibility Risk**. The Quantum Optimizer is a toy model. It hardcodes a 4-agent, 2-hour window (Hours 10 & 11) for a single skill ("Technical"). It caps demand at 2. It solves an 8-variable QUBO.
- **P0**: It does not scale to the actual 24-hour problem. Calling this "Quantum Workforce Optimization" in its current state is mathematically indefensible for a production application.
- **Recommendation**: Implement a Hybrid Solver approach (e.g., full-scale classical optimization + quantum optimization on a representative QUBO subproblem that iterates or aggregates) instead of a standalone hardcoded 8-variable demo.

## L. Erlang-C/Queue Simulation Assessment (Score: 5/10)
**Issues:**
- **P1**: Erlang-C uses constant AHT (300) and SLA (80/20) rather than dynamically pulling from the project/optimization configurations.
- **P1**: Automatic "stability" corrections inside the simulator (`sim_agents = int(math.ceil(A)) + 1`) invisibly overwrite the optimizer's staffing decisions, making the SLA validation artificially pass.

## M. Results/Artifact Management Assessment (Score: 3/10)
**Issues:**
- **P0**: Global CSVs instead of Project/Run scoped storage. 

## N. Testing Assessment (Score: 7/10)
**Issues:**
- **P2**: The 23 E2E tests are well constructed but only test the "happy path" single-tenant flow. Concurrency tests would fail due to file overwrites.

## O. Performance Assessment (Score: 6/10)
**Issues:**
- **P2**: Synchronous execution of some file I/O operations block the FastAPI event loop.

## P. Deployment Assessment (Score: 4/10)
**Issues:**
- **P1**: No configuration decoupling. Dockerfiles are stubbed.

## Q. Code Quality Assessment (Score: 5/10)
**Issues:**
- **P2**: Duplication of Erlang-C calculations between `src/queue_simulator.py` and `backend/app/routers/dashboard.py`.

## R. Technical Debt
- Mixing Python scripting paradigms with a REST API paradigm.
- Global file manipulation.

## S. Critical Risks
1. **Concurrency Data Corruption**: Two users optimizing at once will overwrite `results/shift_schedule.csv`.
2. **Reviewer Credibility**: The Quantum demo is too superficial to pass scientific review.

## T. Recommended Architecture
1. **Core Library Extraction**: Move `src/` modules into `backend/app/core_engine/`. 
2. **Storage Scoping**: Modify all file I/O to use paths like `storage/{project_id}/{run_id}/`.
3. **Database Integration**: Store aggregated results and metrics in the database, relying on CSVs only for raw timeseries data payloads.
4. **Hybrid Quantum Solver**: Refactor the quantum logic to iteratively solve windows or meaningfully combine with classical methods for the full 24-hour schedule.

## U. Prioritized Improvement Roadmap (PHASE 6B IMPLEMENTATION ROADMAP)

- **6B.1 Architecture Cleanup**: Move `src/` logic into backend. Eliminate `PYTHONPATH` disjoints.
- **6B.2 Data & Artifact Isolation**: Refactor storage paths to utilize UUIDs (`project_id`/`run_id`).
- **6B.3 Dataset Hardening**: Add upload size constraints and strict CSV schema validation.
- **6B.4 Erlang-C Validation**: Decouple AHT/SLA constants into parameters. Remove hidden agent-padding in validation.
- **6B.5 Optimization Improvements**: Ensure Classical Optimization supports true 24-hour schedules with accurate variables.
- **6B.6 Quantum Formulation Improvements**: Redesign the Quantum module to be a mathematically sound Hybrid solver rather than a hardcoded 4-agent script.
- **6B.7 Forecasting Reliability**: Dynamic column parsing and error bounds.
- **6B.8 Authentication/Session Improvements**: Implement actual frontend Token Refresh handling.
- **6B.9 Frontend/API Integration**: Dynamic dashboards rendering data natively mapped to `project_id`.
- **6B.10 Configuration**: Env variable enforcement.
- **6B.11 Security**: API rate limiting and path-traversal prevention.
- **6B.12 Testing**: Add multi-tenant concurrency tests and invalid CSV parsing tests.
- **6B.13 Performance**: Async I/O for file readings.
- **6B.14 Documentation & Demo Readiness**: Polish the UI workflow to perfectly match the narrative.

---

### Final Audit Output Scores
1. Architecture score: 4/10
2. Backend score: 4/10
3. Frontend score: 5/10
4. Security score: 6/10
5. Testing score: 7/10
6. Quantum methodology score: 3/10
7. Mathematical validity score: 5/10
8. Production readiness score: 3/10
9. Demo readiness score: 5/10
