# ⚡ Quantum Workforce Optimizer

An AI-powered, quantum-ready call center staffing calculator that predicts incoming call volumes, optimizes agent schedules using classical linear programming, explores quantum QAOA solutions, and mathematically validates customer wait times using Erlang C queuing theory.

## 📖 Project Overview
The Quantum Workforce Optimizer is an advanced scheduling solution designed for enterprise-scale workforce management. By integrating AI-driven demand forecasting, Operations Research (OR) optimization, and Quantum computing principles, this project minimizes operational costs while strictly adhering to Service Level Agreements (SLAs).

## 🎯 Problem Statement
Call centers often rely on naive, peak-capacity scheduling, leading to massive overstaffing during off-peak hours and unnecessary financial waste. Conversely, understaffing leads to SLA breaches, high wait times, and customer dissatisfaction. Finding the optimal shift schedule across multiple channels and skill groups is a highly complex combinatorial optimization problem.

## 💼 Business Motivation
Reducing operational costs while maintaining customer satisfaction is a critical priority for large-scale operations. By transitioning from peak-capacity scheduling to a mathematically optimized schedule, enterprises can achieve significant cost savings—potentially reducing daily staffing costs by up to 39.5%—without compromising service quality.

## 🏆 Challenge Alignment
Developed for the **WISER 2026 Vanguard Challenge**. This project directly addresses the challenge's core objectives by delivering a production-ready, mathematically rigorous, and forward-looking (Quantum) solution to workforce optimization.

## 🏗️ Project Architecture

```text
  [Synthetic Call Data] (data/raw/)
            │
            ▼
  [AI Demand Forecasting] (RandomForest)
            │
            ▼ (Predicted Calls)
  ┌─────────┴─────────────────────────────────┐
  ▼                                           ▼
[Classical Optimization]           [Quantum Optimization]
(OR-Tools SCIP)                    (Qiskit QAOA / Simulator)
  │                                           │
  └─────────┬─────────────────────────────────┘
            ▼ (Compare Optimums: 100% Match)
  [Shift Optimization] (8-hour Shift Coverage)
            │
            ▼ (Final Schedule)
  [Queue SLA Validation] (Erlang C Proof)
            │
            ▼
  [Interactive Dashboard] (Streamlit / Future React)
```

## 💻 Technology Stack
- **Data & Forecasting:** Python, Pandas, Numpy, Scikit-Learn
- **Classical Optimization:** Google OR-Tools (SCIP Solver)
- **Quantum Optimization:** Qiskit (QAOA), Qiskit Optimization
- **Queueing Theory:** Erlang C Mathematical Models
- **Visualization (Phase 1):** Streamlit, Matplotlib
- **Web Stack (Phase 2 Scaffolding):** FastAPI, React, PostgreSQL, Docker

## 🚀 Installation Guide

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd quantum-workforce-optimization
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

## 🔄 Workflow

1. **Run the End-to-End Pipeline:**
   ```bash
   python run_all.py
   ```
   This automated script orchestrates the following:
   - Generates synthetic historical data.
   - Trains the demand forecasting model.
   - Runs the classical linear programming solver to determine agent requirements.
   - Maps the required agents to optimal 8-hour shifts.
   - Executes the Quantum QAOA simulation for performance comparison.
   - Validates the resulting schedule against queueing theory (Erlang C) to guarantee SLAs.

2. **Launch the Interactive Dashboard:**
   ```bash
   streamlit run src/dashboard.py
   ```

## 📐 Mathematical Overview
- **Forecasting:** Random Forest Regressor predicting hourly volume.
- **Classical Optimization:** Integer Linear Programming (ILP) minimizing `Σ C * x_i` subject to coverage and break constraints.
- **Quantum Optimization:** Quadratic Unconstrained Binary Optimization (QUBO) using QAOA (Quantum Approximate Optimization Algorithm).
- **Queue Validation:** Erlang C formula computing the probability of wait (P_w) to ensure Service Level (SLA) >= Target.

## ✨ Features
- 📊 **Historical Analytics:** View call volume patterns and KPI summaries.
- 🔮 **AI Forecasting:** 7-day predicted call volume with confidence intervals.
- ⚙️ **Optimal Scheduling:** Translates hourly requirements into real-world 8-hour shifts with breaks.
- 🔬 **Quantum Benchmarking:** Compares Classical Exact solvers (MIP) against Quantum QAOA.
- 💰 **Business ROI:** Calculates real-time cost savings compared to naive scheduling.
- ✅ **SLA Guarantee:** Proves the generated schedule meets the configured SLA using Erlang C.

## 📸 Screenshots
*(Placeholder for Dashboard Screenshots - Add relevant images here in future phases)*
- `Dashboard Overview`
- `Optimization Results`
- `Quantum Comparison`

## 📊 Results Summary
- **SLA Achieved:** 100% across all 24 hours.
- **Cost Reduction:** ~39.5% reduction in daily staffing costs compared to peak-capacity naive scheduling.
- **Quantum Parity:** The QAOA simulation achieved a 100% match with the classical exact solver for the modeled 8x8 shift matrix.

## 📁 Repository Structure
- `data/` - Synthetic call center inputs and AI forecasts.
- `models/` - Saved ML models (e.g., RandomForest).
- `results/` - Optimization schedules and quantum comparisons.
- `src/` - Data pipeline, optimization solvers, and Streamlit app.
- `docs/` - Mathematical formulations and deployment documentation.
- `backend/` - Scaffolding for Phase 2 API (FastAPI).
- `frontend/` - Scaffolding for Phase 2 UI (React).
- `run_all.py` - Master orchestration script.
- `AI_DISCLOSURE.md` - Declaration of AI assistant usage.

## 🔮 Future Work
- **Phase 2:** Migrate the Streamlit dashboard to the React/FastAPI full-stack architecture for enhanced scalability.
- **Phase 3:** Integrate live data feeds and expand the Quantum QAOA model to handle larger qubit state spaces on real quantum hardware.

## 📚 References
- Erlang, A. K. (1917). *Solution of some Problems in the Theory of Probabilities of Significance in Automatic Telephone Exchanges*.
- Farhi, E., Goldstone, J., & Gutmann, S. (2014). *A Quantum Approximate Optimization Algorithm*.
- Google OR-Tools Documentation.

## 🤖 AI Usage Disclosure
This project utilized generative AI tools to accelerate development. Please refer to [AI_DISCLOSURE.md](AI_DISCLOSURE.md) for full transparency and verification details.

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
