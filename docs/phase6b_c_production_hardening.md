# Phase 6B-C: Production Architecture Hardening

## Overview
Phase 6B-C addressed a "split-brain" architecture in the Quantum Workforce Optimization project where FastAPI was previously returning simulated/mocked success (`time.sleep()`), while the actual algorithms were only being executed via the `run_all.py` CLI script.

This phase successfully established a production-ready, framework-independent Orchestration Layer that seamlessly binds the true core mathematical engines to the FastAPI and CLI boundaries, ensuring complete storage isolation through Canonical Run IDs.

## Architecture

### The Orchestration Service (`orchestration_service.py`)
At the heart of the hardened architecture lies the Orchestration Service. It replaces the mock `ml_service.py` entirely.
- **Framework Independence:** Built in standard Python without heavy FastAPI dependencies (`Depends`, etc.), ensuring future compatibility with durable task queue workers (e.g. Celery, RQ).
- **Execution Lifecycle:** 
  The Orchestrator sequentially executes the pipeline stages: `DATA_GENERATING` -> `FORECASTING` -> `OPTIMIZING` -> `SIMULATING` -> `REPORTING` -> `COMPLETED`.

### Canonical Run ID (`OptimizationRun.id`)
The `OptimizationRun` model in the database was expanded from just optimization to act as the universal Tracker for a full pipeline run.
- **Storage Isolation:** The Run ID is passed directly to `StorageService(run_id)`. Every pipeline execution, whether concurrent or triggered via API/CLI, is guaranteed to live isolated in `runtime/runs/<run_id>/`.
- **Global Path Eradication:** The legacy usage of `project_id` for storage paths, which caused race conditions and data corruption across concurrent runs, has been eradicated.
- **Dynamic KPIs:** Hardcoded KPIs inside the dashboards and APIs have been fully replaced. The FastAPI endpoints now retrieve the latest `run_id` for a project, initialize the isolated `StorageService`, and extract genuine metrics natively from the generated CSV logs (Queue Validation, Classical Optimization).

### Quantum Execution Transparency
We have heavily prioritized scientific transparency over marketing terminology. The Quantum Optimizer's capabilities and current boundaries have been strictly labeled.
- **Simulator Labeling:** The execution backend is now properly labeled in the CSV output and dashboard UI as a `Simulator (StatevectorSampler)`.
- **Reduced Problem Scope:** The decision variable count (`N=8`) and the exact 2-hour window constraints are explicitly published, prohibiting false claims of achieving "quantum advantage" on the entire 24-hour demand horizon.

## Failure Semantics
Failures during execution are no longer swallowed or faked as success.
- If any core-engine stage throws an exception, the pipeline aborts cleanly.
- The `OptimizationRun` transitions to a `FAILED` state.
- A concise error message is logged to the DB, while a full stack trace is securely stored inside `runtime/runs/<run_id>/reports/error_trace.log`, keeping raw stack dumps away from the user-facing API.

## Future Path: Durable Queue Migration
Because `execute_optimization_pipeline(run_id: uuid.UUID)` is completely self-contained, replacing FastAPI `BackgroundTasks` with a durable distributed queue (like Celery) is straightforward:
1. Wrap `execute_optimization_pipeline` in a `@celery.task`.
2. Push the task to Redis/RabbitMQ.
3. Scale the worker nodes independently.
4. The Core Engine and Database logic requires zero refactoring.
