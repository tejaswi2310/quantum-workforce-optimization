# ⚡ Quantum Workforce Optimizer

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/tejas/q-workforce/main/src/dashboard.py)

An AI-powered call center staffing calculator that predicts incoming call volumes, optimizes agent schedules using classical linear programming and quantum QAOA, and mathematically validates customer wait times using Erlang C queuing theory.

---

## 🔮 Business Impact (ROI)

| Staffing Strategy | Daily Operational Cost | Annual Operational Cost | Net Annual Savings |
|---|---|---|---|
| **Naive Scheduling** (Peak Capacity) | $1,440.00 | $525,600 | - |
| **Optimized Scheduling** (AI + LP) | $870.00 | $317,550 | **$208,050 (39.5%)** |
| **Quantum-Enhanced** (QAOA Refined) | $870.00 | $317,550 | **$208,050 (39.5%)** |

---

## 🏗️ Architecture Flow Diagram

```text
  [Synthetic Call Data] (data/raw/)
            │
            ▼
  [AI Demand Forecasting] (src/forecasting.py -> RandomForest)
            │
            ▼ (Predicted Calls)
  ┌─────────┴─────────────────────────────────┐
  ▼                                           ▼
[Classical Optimization]           [Quantum Optimization]
(src/optimizer.py -> OR-Tools)    (src/quantum_optimizer.py -> Qiskit QAOA)
  │                                           │
  └─────────┬─────────────────────────────────┘
            ▼ (Compare Optimums: 100% Match)
  [Shift Optimization] (src/optimizer_shifts.py -> 8h Shift Coverage)
            │
            ▼ (Final Schedule)
  [Queue SLA Validation] (src/queue_simulation.py -> Erlang C Proof)
            │
            ▼
  [Interactive Streamlit Dashboard] (src/dashboard.py)
```

---

## 🚀 Quick Start

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Pipeline (End-to-End):**
   ```bash
   python run_all.py
   ```
   This generates the raw synthetic data, trains the ML model, outputs optimization schedules, runs QAOA simulations, and computes queue validations.

3. **Launch the Dashboard:**
   ```bash
   streamlit run src/dashboard.py
   ```

---

## 📁 Repository Structure

- `data/` - Synthetic call center inputs and AI forecasts.
- `models/` - Saved RandomForest models.
- `results/` - Optimization schedules and quantum comparisons.
- `src/` - Data pipeline, optimization solvers, and Streamlit app.
- `docs/` - Mathematical formulations and deployment documentation.
- `AI_DISCLOSURE.md` - Declaration of AI assistant usage.

---

## 👥 The Team
Developed for the **WISER 2026 Vanguard Challenge**.
- Lead Data Scientist: Tejas
- Quantum Software Engineer: Tejas

---

## 📜 AI Usage Disclosure
This project utilized generative AI tools (Gemini, Claude, GitHub Copilot) for code acceleration, documentation, and mathematical optimization structures. Please refer to [AI_DISCLOSURE.md](AI_DISCLOSURE.md) for details.
