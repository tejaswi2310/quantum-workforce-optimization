# Research Report

**Project:** QWO-X — Hybrid AI–Quantum Workforce Intelligence Platform
**Submission:** WISER Quantum + AI Optimization Program 2026 — Vanguard Challenge
**Repository:** [github.com/tejaswi2310/quantum-workforce-optimization](https://github.com/tejaswi2310/quantum-workforce-optimization)
**Live Dashboard:** [Streamlit App](https://quantum-workforce-optimization-kn96seuxrjgpjykibquvfu.streamlit.app/)

---

## 1. Introduction

Call center workforce scheduling sits at the intersection of forecasting, combinatorial optimization, and queueing theory. Poor scheduling decisions compound across all three: forecast error propagates into staffing error, staffing error propagates into either wasted labor cost or SLA breaches, and both are expensive at scale. QWO-X (Quantum Workforce Optimizer — Extended) was built to address this as a single, explainable, end-to-end decision-support pipeline rather than three disconnected tools.

The project's central research question: **can a workforce scheduling problem be natively formulated as a QUBO and solved competitively via QAOA, while remaining a practical, deployable classical system today?** The short answer, detailed in Sections 4–5, is yes for formulation validity and hybrid-architecture readiness, and not yet for computational advantage at current problem scale.

## 2. Related Work

Workforce scheduling has a long history in operations research as an NP-hard combinatorial assignment problem (Karp, 1972). Classical mixed-integer programming and constraint-programming solvers such as OR-Tools CP-SAT remain the industry standard for problems in the hundreds-to-low-thousands of binary variables. In parallel, the quantum optimization literature — particularly QUBO/Ising formulations of NP-hard problems (Lucas, 2014) and the Quantum Approximate Optimization Algorithm (Farhi, Goldstone & Gutmann, 2014) — has explored combinatorial assignment problems as a proving ground for near-term quantum hardware, though workforce/shift scheduling specifically remains an under-studied application relative to portfolio optimization or logistics routing. See [`Literature_Review.md`](Literature_Review.md) for the full annotated bibliography.

## 3. Methods

The pipeline consists of seven modules, described in detail in the main [README → System Architecture](../README.md#system-architecture):

1. Synthetic data generation (2 years of interval-level call volume with seasonality, holidays, and campaign spikes)
2. RandomForest demand forecasting
3. Classical optimization via OR-Tools CP-SAT (production baseline)
4. Quantum optimization via Qiskit QAOA on a QUBO encoding (research exploration)
5. Shift-conversion post-processing (interval coverage → legal 8-hour shifts with breaks)
6. Erlang-C queue simulation for SLA validation
7. Streamlit dashboard for interactive decision support

Full mathematical detail — objective function, constraints, QUBO construction, and the cost/mixer Hamiltonians — is in [`Mathematical_Formulation.md`](Mathematical_Formulation.md).

## 4. Experimental Setup

QAOA experiments were run on the Qiskit Aer local simulator at depth $p=3$ against a 48-binary-variable instance (matching a representative single-day, single-site scheduling problem). The classical OR-Tools CP-SAT baseline was run on the identical instance for direct comparison. Sensitivity analysis was conducted across six operational disruption scenarios (demand surges, staff shortages, tightened SLA targets, holiday spikes, and overtime-penalty changes) — see [`Experiment_Report.md`](Experiment_Report.md) for full logs and convergence curves.

## 5. Results

- **Cost parity:** QAOA converged to a daily staffing cost identical to the OR-Tools baseline ($870.00), validating the correctness of the QUBO encoding.
- **Runtime:** OR-Tools solved the instance in ~1.2s; QAOA required ~18–25s on the simulator — expected at this scale, since classical solvers dominate for small, well-structured MIPs.
- **Business impact:** the optimized schedule (classical or quantum-refined) delivered a 39.5% reduction in daily/annual staffing cost versus naive peak-capacity scheduling, while lifting SLA attainment from ~75% to >90%.
- **Robustness:** sensitivity analysis confirmed the optimizer degrades gracefully under stress (e.g., +30% demand shock costs +18–22% and still holds 87–89% SLA), with the dashboard surfacing concrete manager recommendations per scenario.

Full tables are reproduced in the main [README → Results & Benchmarking](../README.md#results--benchmarking) and [Sensitivity Analysis](../README.md#sensitivity-analysis).

## 6. Discussion

The QAOA component does not outperform OR-Tools at 48 variables, and the project does not claim it does (see [FAQ for Judges](../README.md#faq-for-judges)). Its contribution is architectural and forward-looking: it proves the scheduling problem can be QUBO-encoded despite overlapping hard constraints, and it demonstrates a hybrid classical-quantum-classical pattern (pre-processing → quantum core → constraint repair) that would carry over unchanged to larger instances on future NISQ or fault-tolerant hardware.

## 7. Conclusion

QWO-X delivers a production-ready classical scheduling pipeline today (forecasting + OR-Tools + Erlang-C validation), with a quantum module included as a validated, honestly-benchmarked research extension. See [`Limitations_and_Future_Work.md`](Limitations_and_Future_Work.md) for the roadmap toward larger-scale quantum experiments and real-time adaptive scheduling.
