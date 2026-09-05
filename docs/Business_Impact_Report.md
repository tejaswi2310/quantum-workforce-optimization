# Business Impact Report

**Project:** QWO-X — Hybrid AI–Quantum Workforce Intelligence Platform
**Repository:** [github.com/tejaswi2310/quantum-workforce-optimization](https://github.com/tejaswi2310/quantum-workforce-optimization)
**Live Dashboard:** [Streamlit App](https://quantum-workforce-optimization-kn96seuxrjgpjykibquvfu.streamlit.app/)

---

## Executive Summary

Call centers lose money in two directions: overstaffing (idle labor cost) and understaffing (SLA breaches, churn). QWO-X replaces naive peak-capacity scheduling with an AI-forecast-driven, mathematically optimized schedule, delivering measurable cost savings without sacrificing service quality.

## Headline Impact

| Metric | Before (Naive Peak Scheduling) | After (QWO-X Optimized) | Improvement |
|---|---|---|---|
| Daily Operational Cost | Configurable Baseline | Dynamically Optimized | **Varies by scenario** |
| Annual Operational Cost | Extrapolated Baseline | Dynamically Optimized | **Subject to volume** |
| Avg. SLA Attainment | Baseline | Target Driven | **Achieved** |
| Overtime Hours / Week | Baseline | Optimized | Reduced |
| Idle Time (Non-Peak) | Baseline | Optimized | Reduced |

## Staffing Strategy Comparison

| Staffing Strategy | Daily Cost | Annual Cost | Annual Savings vs. Naive |
|---|---|---|---|
| Naive Peak Scheduling | Dynamic | Extrapolated | — |
| AI + Classical Optimization | Optimized | Extrapolated | **Varies by scenario** |
| Quantum-Demonstrator (QAOA Refined) | Match | Match | **Match** |

## Where the Savings Come From

1. **Demand-matched staffing** — RandomForest forecasting replaces flat peak-capacity assumptions with interval-level demand predictions, so agents aren't scheduled for volume that never arrives.
2. **Constraint-aware optimization** — OR-Tools CP-SAT finds the minimum-cost feasible schedule that still satisfies skill coverage, break, and overtime-cap constraints, rather than relying on rule-of-thumb staffing ratios.
3. **SLA-validated feasibility** — Erlang-C queue simulation ensures the cost-minimized schedule doesn't sacrifice customer wait times to hit the savings number; the >90% SLA attainment is a validated output, not an assumption.
4. **Operational resilience** — sensitivity analysis (see [`Experiment_Report.md`](Experiment_Report.md)) shows the savings hold up under realistic disruptions (demand surges, staffing shortages, holiday spikes), with the dashboard surfacing concrete manager actions for each scenario.

## Deployment Readiness

The classical pipeline (forecasting → OR-Tools → Erlang-C validation → dashboard) is production-ready for single-site deployment today, pending integration with real call-volume data feeds in place of the synthetic dataset. The quantum (QAOA) module is included as a forward-looking research component and is not required for the above business impact — see [`Limitations_and_Future_Work.md`](Limitations_and_Future_Work.md) for the maturity roadmap.

## Risk & Sensitivity Summary

Full stress-test results are in [`Experiment_Report.md`](Experiment_Report.md). In brief: cost increases scale proportionally (not catastrophically) with the severity of demand shocks or staffing shortages, and the system always surfaces the SLA/cost trade-off explicitly rather than silently degrading service.
