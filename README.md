# QWO-X: Hybrid AI–Quantum Workforce Intelligence Platform

**Adaptive Call Center Optimization via Forecasting, Hybrid Optimization & Operational Simulation**

🏆 **WISER Quantum + AI Optimization Program 2026 — Vanguard Challenge Submission**
End-to-end decision-support system combining AI demand forecasting, classical optimization (OR-Tools), quantum exploration (QAOA), and Erlang-C queue simulation for intelligent workforce planning.

📊 [Live Dashboard](https://quantum-workforce-optimization-kn96seuxrjgpjykibquvfu.streamlit.app/) • 📐 [Mathematical Formulation](docs/Mathematical_Formulation.md) • 📄 [Research Report](docs/Research_Report.md) • 🎥 [Video Walkthrough](docs/demo_video.mp4)

🔗 **Repository:** [github.com/tejaswi2310/quantum-workforce-optimization](https://github.com/tejaswi2310/quantum-workforce-optimization)

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Streamlit](https://img.shields.io/badge/dashboard-streamlit-ff4b4b) ![Status](https://img.shields.io/badge/status-active-brightgreen)

---

## 📑 Table of Contents

- [Executive Summary](#executive-summary-30-second-read)
- [Problem Statement](#problem-statement)
- [System Architecture](#system-architecture)
- [Mathematical Formulation](#mathematical-formulation)
- [Quantum Formulation (QAOA)](#quantum-formulation-qaoa)
- [Results & Benchmarking](#results--benchmarking)
- [Sensitivity Analysis](#sensitivity-analysis)
- [Dashboard & Prototype](#dashboard--prototype)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Team & Contributions](#team--contributions)
- [Generative AI Disclosure](#generative-ai-disclosure)
- [Limitations & Honest Assessment](#limitations--honest-assessment)
- [Future Work](#future-work)
- [Literature Review](#literature-review)
- [FAQ for Judges](#faq-for-judges)
- [License](#license)

---

## Executive Summary (30-Second Read)

> **Business Problem:** Call centers lose millions annually to overstaffing (idle agents, inflated labor costs) and understaffing (SLA breaches, customer churn). Traditional scheduling relies on static rules and reactive adjustments that cannot handle combinatorial scale.
>
> **Our Solution:** QWO-X is a **hybrid AI–Classical–Quantum decision intelligence platform** that forecasts demand, optimizes multi-constraint shift schedules, validates operational performance via queue simulation, and delivers actionable recommendations through an interactive executive dashboard.
>
> **Impact:** Demonstrated **39.5% reduction in operational staffing costs** (**$208,050 annual savings**) while maintaining **>90% SLA attainment**, with full explainability for operations managers.

| Metric | Before (Naive Peak Scheduling) | After (QWO-X Optimized) | Improvement |
|---|---|---|---|
| Daily Operational Cost | $1,440 | $870 | **−39.5%** |
| Annual Operational Cost | $525,600 | $317,550 | **−$208,050** |
| Avg. SLA Attainment | ~75% | >90% | **+15 pp** |
| Overtime Hours / Week | Baseline | Optimized | Reduced |
| Idle Time (Non-Peak) | Baseline | Optimized | Reduced |

---

## Problem Statement

Call center workforce scheduling is a **combinatorial optimization problem** characterized by:

- **Binary decision variables** — assign agent *i* to time interval *t* (yes/no)
- **Hard constraints** — labor laws, skill requirements, mandatory breaks, overtime caps
- **Stochastic demand** — call volumes vary by hour, day, season, marketing campaigns
- **Competing objectives** — minimize cost vs. maximize SLA vs. minimize overtime vs. reduce idle time

### Why Existing Solutions Fail

1. **Spreadsheet-based scheduling** collapses under combinatorial scale (thousands of agent-interval pairings)
2. **Static rule-based systems** cannot adapt to intraday demand shocks or seasonal patterns
3. **Black-box AI** lacks interpretability — operations managers cannot audit or trust automated decisions
4. **Pure classical solvers** face steep polynomial scaling as multi-objective constraints and problem size grow

### Why Quantum Computing Is Relevant

As scheduling instances scale — multi-site operations, multi-skill routing, agent preference optimization — the binary search space grows exponentially. Quantum Approximate Optimization Algorithm (QAOA) provides a **future-ready formulation** and a **hybrid exploration pathway** for combinatorial scheduling problems that may eventually exceed efficient classical tractability at enterprise scale (10,000+ binary variables).

---

## System Architecture

*Figure 1: End-to-end hybrid pipeline from synthetic data generation through AI forecasting, classical & quantum optimization, queue validation, and interactive dashboard.*

```
 [Synthetic Call Data] (data/raw/)
            │
            ▼
 [AI Demand Forecasting] (src/forecasting.py → RandomForest)
            │
            ▼ (Predicted Calls per 30-min Interval)
  ┌─────────┴─────────────────────────────────┐
  ▼                                           ▼
[Classical Optimization]           [Quantum Optimization]
(src/optimizer.py → OR-Tools)      (src/quantum_optimizer.py → Qiskit QAOA)
  │                                           │
  └─────────┬─────────────────────────────────┘
            ▼ (Compare & Validate)
 [Shift Optimization] (src/optimizer_shifts.py → 8h Shift Coverage)
            │
            ▼ (Final Schedule)
 [Queue SLA Validation] (src/queue_simulation.py → Erlang C Proof)
            │
            ▼
 [Interactive Streamlit Dashboard] (src/dashboard.py)
```

**Pipeline Modules:**

1. **Synthetic Data Generator** — 2 years of realistic call-center data with seasonality, holidays, and campaign spikes
2. **AI Demand Forecaster** — RandomForest regression predicting interval-level demand with feature engineering
3. **Classical Optimizer** — OR-Tools CP-SAT solving the mixed-integer program for production baseline
4. **Quantum Optimizer** — QAOA (Qiskit) exploring the QUBO-encoded formulation on simulators
5. **Shift Optimizer** — Post-processing to convert interval coverage into legal 8-hour agent shifts with breaks
6. **Queue Simulator** — Erlang-C model validating ASA, abandonment rate, and SLA attainment
7. **Decision Dashboard** — Streamlit app with executive KPIs, operations view, and what-if simulator

---

## Mathematical Formulation

### Decision Variables

| Symbol | Domain | Description |
|---|---|---|
| $x_{i,t}$ | $\{0,1\}$ | 1 if agent *i* is assigned to work interval *t*; 0 otherwise |
| $b_{i,t}$ | $\{0,1\}$ | 1 if agent *i* is on break during interval *t* |
| $o_{i,d}$ | $\mathbb{R}_{\geq0}$ | Overtime hours for agent *i* on day *d* |
| $s_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Shortfall of skill-group *k* at interval *t* |

### Objective Function (Multi-Objective Weighted)

We minimize a weighted combination of staffing cost, overtime penalty, SLA violation penalty, and idle-time penalty:

$$
\min_{x,b,o,s} Z = w_1\sum_{i,t} c_i \cdot x_{i,t} \;+\; w_2\sum_{i,d} p_o \cdot o_{i,d} \;+\; w_3\sum_{k,t} \alpha_k \cdot s_{k,t} \;+\; w_4\sum_{i,t} \beta \cdot (1-u_{i,t}) \cdot x_{i,t}
$$

where $w_1, w_2, w_3, w_4$ are business-priority weights configurable by operations managers.

### Core Constraints

1. **Demand Coverage:** $\sum_{i \in \mathcal{A}_k} x_{i,t} \geq D_{k,t} - s_{k,t}, \; \forall k,t$
2. **Maximum Shift Length:** $\sum_t x_{i,t} \leq H_{\max}, \; \forall i$
3. **Mandatory Breaks:** $\sum_{t \in \mathcal{B}_i} b_{i,t} \geq B_{\min}, \; \forall i$
4. **Skill Matching:** $x_{i,t} \leq M_{i,k}, \; \forall i,k,t$ (agent *i* must possess skill *k*)
5. **Overtime Cap:** $o_{i,d} \leq O_{\max}, \; \forall i,d$
6. **Agent Availability:** $x_{i,t} \leq A_{i,t}, \; \forall i,t$
7. **SLA Target (Simulation Feedback):** $\mathbb{P}(\text{Wait} \leq T_{\max}) \geq \text{SLA}_{\text{target}}$ (enforced via Erlang-C validation)

> 📎 Full derivation, QUBO mapping, and quantum Hamiltonian construction are available in [`docs/Mathematical_Formulation.md`](docs/Mathematical_Formulation.md).

---

## Quantum Formulation (QAOA)

We encode the constrained workforce scheduling problem as a **Quadratic Unconstrained Binary Optimization (QUBO)**:

$$
\min_x x^T Q x
$$

Where the $Q$ matrix encodes:

- **Diagonal terms:** Linear staffing and idle-time costs
- **Off-diagonal terms:** Pairwise penalties (shift overlaps, skill conflicts, demand shortfall)
- **Constraint penalties:** Lagrangian relaxation of hard constraints (breaks, overtime caps, availability)

### Cost Hamiltonian

$$
H_C = \sum_{i,t} h_{i,t} Z_{i,t} + \sum_{(i,t),(j,t')} J_{ijtt'} Z_{i,t} Z_{j,t'}
$$

**Mixer Hamiltonian:** Standard $X$-mixer for state-space exploration.

### Why QAOA Is Included (Honest Assessment)

| Aspect | Assessment |
|---|---|
| **Current Performance** | On simulated NISQ hardware with 48 binary variables, QAOA matches OR-Tools solution quality (100% cost match) but with longer runtime |
| **Formulation Value** | Validates that the workforce scheduling problem can be natively encoded as a QUBO — a non-trivial mapping for problems with overlapping constraints |
| **Hybrid Architecture** | Demonstrates a production-ready pattern: classical pre-processing → quantum core → classical post-processing (constraint repair) |
| **Future Scalability** | As quantum hardware matures (IBM Heron, Condor roadmaps), the QUBO formulation positions the system for larger instances without structural redesign |
| **Research Contribution** | Explores quantum-classical boundary for operational optimization — an under-studied application domain in quantum computing literature |

> ⚠️ **We do not claim quantum advantage at this problem scale.** The QAOA component serves as a validated research exploration and future-ready architectural module, not a production replacement for OR-Tools.

---

## Results & Benchmarking

### Classical vs. Quantum Comparison

| Metric | OR-Tools (CP-SAT) | QAOA (Qiskit Aer, p=3) | Interpretation |
|---|---|---|---|
| Daily Staffing Cost | $870.00 | $870.00 | QAOA converges to identical cost; validates QUBO encoding correctness |
| Runtime (48 binary vars) | ~1.2 s | ~18–25 s | Classical faster on small simulators; quantum explores different solution topology |
| SLA Attainment | >90% | >90% | Quantum solution maintains operational feasibility after post-processing |
| Overtime | Optimized | Optimized | Equivalent overtime allocation |
| Constraint Violations | 0 | 0 (after repair) | Classical post-processing restores hard constraints |
| Scalability Outlook | Polynomial $O(n^3)$ | Sub-exponential potential | Quantum advantage hypothesized at >10k binary variables |

**Key Insight:** At 48 binary variables, OR-Tools remains the production baseline. The QAOA component demonstrates (1) formulation validity, (2) hybrid workflow readiness, and (3) future hardware scalability — not immediate computational supremacy.

### Business Impact Summary

| Staffing Strategy | Daily Cost | Annual Cost | Annual Savings vs. Naive |
|---|---|---|---|
| Naive Peak Scheduling | $1,440 | $525,600 | — |
| AI + Classical Optimization | $870 | $317,550 | **$208,050 (39.5%)** |
| Quantum-Enhanced (QAOA Refined) | $870 | $317,550 | **$208,050 (39.5%)** |

*Note: Quantum refinement achieves identical cost to classical at this scale, serving as validation rather than immediate cost reduction. See [Quantum Formulation](#quantum-formulation-qaoa) for architectural justification.*

---

## Sensitivity Analysis

We stress-test the optimizer under realistic operational disruptions:

| Scenario | Cost Change | SLA Impact | Overtime Change | Manager Recommendation |
|---|---|---|---|---|
| Baseline | — | >90% | Optimized | Maintain current schedule |
| Demand +30% | +18–22% | 87–89% | +35–45% | Activate float pool; extend peak shifts |
| Staff Shortage −20% | +15–18% | 84–86% | +55–65% | Prioritize SLA; accept cost increase; restrict PTO |
| SLA Target 95% | +12–14% | 95% | +20–28% | Add 2–3 agents at peak; reduce idle threshold |
| Holiday / Campaign Spike | +25–31% | 86–88% | +45–55% | Pre-schedule overtime; cross-train skill groups |
| Overtime Penalty Doubled | +5–8% | >90% | −30–40% | Optimizer shifts to base-hour coverage; hire part-time float |

> ✅ Full experiment logs, convergence curves, and statistical significance tests are in [`docs/Experiment_Report.md`](docs/Experiment_Report.md).

---

## Dashboard & Prototype

**Live App:** [quantum-workforce-optimization-kn96seuxrjgpjykibquvfu.streamlit.app](https://quantum-workforce-optimization-kn96seuxrjgpjykibquvfu.streamlit.app/)

> 💤 Free-tier Streamlit apps sleep after a period of inactivity and may take ~30 seconds to spin back up on first load. If the app appears unresponsive, give it a moment, or run it locally: `streamlit run src/dashboard.py`.

### Executive View

*High-level KPIs for C-suite and operations directors — annual savings, SLA achievement, utilization, and cost breakdown.*

Key metrics displayed:
- **Annual Savings:** $208,050 (39.5% reduction)
- **SLA Achievement:** >90%
- **Average Customer Wait:** Optimized
- **Agent Utilization:** Improved
- **Overtime Reduction:** Significant

### Operations View

*Hourly staffing heatmap, agent-level schedules with skill overlays, queue length trends, and cost breakdown by category (base, overtime, shortfall penalty).*

### What-If Simulator

*Interactive controls for operations managers to adjust demand multipliers, SLA targets, overtime penalties, and available agent pools — with instant recomputed schedules and plain-language recommendations.*

### Explainability Engine

For every scheduling decision, the system generates a natural-language explanation:

> *"10:00–10:30 AM: Recommended +4 agents. Reason: Forecast demand increased 32% due to campaign launch. Expected impact: SLA improves +6% (to 93%) at a cost increase of +1.8%. Alternative: Accept 87% SLA and save $145."*

---

## Project Structure

```
quantum-workforce-optimization/
├── README.md                          # You are here
├── LICENSE                            # MIT License
├── requirements.txt                   # Python dependencies
├── run_all.py                         # Master orchestration script (fixed seeds)
├── .gitignore
├── .devcontainer/                     # Reproducible dev environment config
│
├── docs/                               # Research-grade documentation
│   ├── Mathematical_Formulation.md     # Full math: variables, constraints, QUBO, Hamiltonian
│   ├── Research_Report.md              # Intro, related work, methods, results
│   ├── Experiment_Report.md            # Sensitivity analysis, benchmarks, ablation studies
│   ├── Business_Impact_Report.md       # ROI, operational translation, executive summary
│   ├── Limitations_and_Future_Work.md  # Honest critique and roadmap
│   ├── AI_Disclosure.md                # Transparent GenAI usage log
│   ├── Literature_Review.md            # Key papers summarized and contrasted
│   └── demo_video.mp4                  # 3-min walkthrough
│
├── assets/                             # README images and diagrams
│   ├── architecture_diagram.png
│   ├── dashboard_executive.png
│   ├── dashboard_operations.png
│   ├── dashboard_whatif.png
│   └── dashboard_explain.png
│
├── data/                                # Synthetic inputs and AI forecasts
│   └── raw/
│
├── models/                              # Saved RandomForest models
│
├── results/                             # Optimization schedules and quantum comparisons
│
├── src/                                  # Production source code
│   ├── data_generator.py                # Realistic call-center data with seasonality
│   ├── forecasting.py                   # RandomForest demand forecaster
│   ├── optimizer.py                     # OR-Tools CP-SAT baseline
│   ├── quantum_optimizer.py             # Qiskit QAOA QUBO solver
│   ├── optimizer_shifts.py              # 8-hour shift coverage builder
│   ├── queue_simulation.py              # Erlang-C SLA validation
│   └── dashboard.py                     # Streamlit decision intelligence app
│
├── backend/                              # Phase 2 API scaffolding (FastAPI)
├── frontend/                             # Phase 2 UI scaffolding (React)
└── archive/                              # Deprecated / legacy files
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation & Reproduction

```bash
# 1. Clone the repository
git clone https://github.com/tejaswi2310/quantum-workforce-optimization.git
cd quantum-workforce-optimization

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run full end-to-end pipeline
python run_all.py

# 5. Launch interactive dashboard
streamlit run src/dashboard.py
```

All random seeds are fixed in `run_all.py` for full reproducibility.

---

## Team & Contributions

| Team Member | Role | Key Contributions |
|---|---|---|
| **Gelli Tejaswi Venkata Aparna** | Team Lead, Classical Optimization & Architecture | End-to-end pipeline architecture; OR-Tools CP-SAT classical optimizer; mathematical modeling (objective function, constraints, MIP formulation); business impact analysis & ROI modeling; project integration & Git management |
| **Shaik Munthaz** | Quantum Optimization & Simulation Lead | QAOA quantum formulation & Qiskit implementation; QUBO matrix encoding & Hamiltonian construction; Lagrangian constraint penalty design; Erlang-C queue simulation & SLA validation; quantum benchmarking experiments |
| **Madhusudhana Rao R** | AI Forecasting & Frontend Lead | RandomForest demand forecasting pipeline & feature engineering; synthetic data generation with seasonality/campaign modeling; Streamlit interactive dashboard (executive view, operations heatmap, what-if simulator); UI/UX design; unit & integration testing |

This is a **team submission**. Contributions are non-overlapping and individually accountable, spanning classical optimization & architecture, quantum optimization & simulation, and AI forecasting & frontend delivery. Git commit history provides full provenance for each member's contributions.

---

## Generative AI Disclosure

This project utilized generative AI tools for acceleration and documentation support:

| Tool | Usage | Review Status |
|---|---|---|
| **ChatGPT / Claude** | README drafting, mathematical LaTeX formatting, literature review synthesis | All content manually verified and edited |
| **GitHub Copilot** | Code scaffolding, docstring generation | All algorithms manually reviewed; core optimization logic hand-derived |
| **Gemini** | Brainstorming constraint formulations | Ideas validated against OR-Tools and Qiskit documentation |

**All AI-generated content was rigorously reviewed, verified, and edited by the authors.** Core algorithms — including QUBO matrix construction, QAOA ansatz parameterization, and Erlang-C queue derivations — were manually coded and validated against textbook formulas.

Full disclosure log: [`docs/AI_Disclosure.md`](docs/AI_Disclosure.md)

---

## Limitations & Honest Assessment

We believe transparency strengthens credibility. Current limitations include:

1. **Synthetic Data:** All experiments use synthetically generated call-center data. While seasonality, holidays, and campaign spikes are modeled, true operational noise patterns (system outages, agent absenteeism clusters, weather events) are not captured.
2. **Quantum Hardware Constraints:** All QAOA experiments run on classical simulators (Qiskit Aer, local). Real IBM Quantum device validation was limited by queue wait times and qubit coherence constraints for this problem size.
3. **Problem Scale:** Current QAOA experiments encode 48 binary variables. Enterprise-scale call centers (500+ agents, 96 intervals, 10+ skills) would require 10,000+ variables — beyond current NISQ capabilities.
4. **Forecast Uncertainty:** The system uses point forecasts (single predicted demand value). Full probabilistic optimization with scenario trees or stochastic programming is not yet implemented.
5. **Static Scheduling:** The optimizer produces daily schedules in batch. Real-time intraday rescheduling (e.g., handling no-shows or demand surges) is not yet supported.
6. **Single-Site Model:** The formulation assumes one call center. Multi-site coordination with shared float pools remains future work.

**Mitigation:** The modular architecture (classical baseline + quantum module + simulation layer) is designed to swap in real data APIs, larger quantum backends, and online learning modules without structural changes.

---

## Future Work

- **Real-time Adaptive Scheduling:** Reinforcement learning agent for intraday shift adjustments based on live call arrival streams
- **Multi-site Coordination:** Distributed optimization across geographic call centers with shared resource pools
- **Preference-aware Fairness:** Incorporate agent shift preferences as soft constraints to improve retention
- **Probabilistic Forecasting:** Replace point forecasts with full demand distributions; optimize for risk-adjusted expected cost
- **Larger Quantum Experiments:** Scale QAOA to 100+ variables on IBM Quantum Heron / Condor as hardware matures
- **DQI Exploration:** Investigate Decoded Quantum Interferometry as an alternative optimization paradigm for workforce scheduling
- **Production Deployment:** Containerize with Docker; integrate with existing workforce management APIs (e.g., Genesys, NICE)

---

## Literature Review

| # | Citation | Relevance to This Work |
|---|---|---|
| 1 | Karp, R. M. (1972). *Reducibility Among Combinatorial Problems.* In *Complexity of Computer Computations.* | Establishes NP-hardness foundation for workforce scheduling; justifies why exact classical solutions become intractable at scale. |
| 2 | Lucas, A. (2014). *Ising Formulations of Many NP Problems.* Frontiers in Physics, 2, 5. | Definitive reference for QUBO mappings; guided our constraint-to-QUBO penalty encoding. |
| 3 | Farhi, E., Goldstone, J., & Gutmann, S. (2014). *A Quantum Approximate Optimization Algorithm.* arXiv:1411.4028. | Original QAOA paper; theoretical foundation for our parameterized ansatz design. |
| 4 | Glover, F., Kochenberger, G., & Du, Y. (2018). *Quantum Bridge Analytics I: A Tutorial on Formulating and Using QUBO Models.* | Practical tutorial on QUBO construction; informed our Lagrangian relaxation approach for constraint penalties. |
| 5 | Pinedo, M. L. (2016). *Scheduling: Theory, Algorithms, and Systems* (5th ed.). Springer. | Workforce scheduling theory textbook; reference for shift-length, break, and overtime constraint formulations. |
| 6 | Gurkaynak, G., et al. (2022). *Quantum Computing for Financial Portfolio Optimization.* | Industry perspective on quantum optimization practicalities; parallels between portfolio and workforce allocation. |
| 7 | IBM Quantum (2025). *Quantum Development Roadmap.* | Hardware trajectory justification for including quantum as a future-ready module rather than immediate replacement. |
| 8 | WISER Program (2026). *Quantum + AI Optimization Curriculum.* | Educational framework connecting classical optimization, AI forecasting, and quantum exploration. |

> 📚 Full annotated bibliography with critique and differentiation is available in [`docs/Literature_Review.md`](docs/Literature_Review.md).

---

## FAQ for Judges

**Q: Why not just use OR-Tools? Why include quantum at all?**
> A: OR-Tools provides our production-ready baseline and handles current operational needs efficiently. The QAOA component serves three purposes: (1) it validates that workforce scheduling can be encoded as a QUBO, (2) it demonstrates a hybrid classical-quantum workflow architecture, and (3) it positions the system for future quantum hardware as problem instances scale to enterprise size (10,000+ binary variables). We explicitly do not claim quantum superiority at this scale.

**Q: What happens if call volume doubles?**
> A: The AI forecasting module would detect the trend and predict higher interval demand. The optimizer would respond by increasing staffing coverage, with trade-offs visible in the what-if simulator (higher cost vs. maintained SLA). At extreme scale, the QUBO formulation remains structurally identical, though current NISQ hardware could not yet solve it.

**Q: Why RandomForest for forecasting instead of XGBoost or deep learning?**
> A: RandomForest was selected for its strong baseline performance, interpretability (feature importance for seasonality and campaign effects), and low training overhead. The modular pipeline allows swapping in XGBoost, Prophet, or LSTM models without changing the optimization layer.

**Q: How do you ensure the quantum solution is operationally feasible?**
> A: All QAOA outputs undergo classical post-processing (constraint repair) to ensure shift legality, break compliance, and skill matching. The Erlang-C simulation then validates SLA attainment. The quantum component explores the cost landscape; classical layers guarantee feasibility.

**Q: What is your unique contribution beyond a standard scheduling project?**
> A: (1) End-to-end integration of forecasting + optimization + queue validation + explainability in one platform; (2) Honest quantum-classical benchmarking with transparent limitations; (3) Business-first dashboard designed for operations managers, not just researchers; (4) Sensitivity and risk analysis demonstrating robustness under operational disruption.

**Q: Can this be deployed in a real call center today?**
> A: The classical optimization pipeline (forecasting + OR-Tools + Erlang-C) is production-ready for single-site deployment with real data integration. The quantum module requires future hardware maturity for enterprise-scale instances.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

**Built for the WISER Quantum + AI Optimization Program 2026 — Vanguard Challenge**

*Questions or feedback? Open a [GitHub Issue](https://github.com/tejaswi2310/quantum-workforce-optimization/issues) or reach out via the WISER program portal.*
