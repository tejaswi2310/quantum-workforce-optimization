# Limitations & Future Work

**Project:** QWO-X — Hybrid AI–Quantum Workforce Intelligence Platform
**Repository:** [github.com/tejaswi2310/quantum-workforce-optimization](https://github.com/tejaswi2310/quantum-workforce-optimization)
**Referenced from:** [`README.md`](../README.md) → Limitations & Honest Assessment / Future Work

We believe transparency strengthens credibility. This document expands on the limitations and roadmap summarized in the main README.

---

## Limitations

1. **Synthetic Data:** All experiments use synthetically generated call-center data. While seasonality, holidays, and campaign spikes are modeled, true operational noise patterns (system outages, agent absenteeism clusters, weather events) are not captured.
2. **Quantum Hardware Constraints:** All QAOA experiments run on classical simulators (Qiskit Aer, local). Real IBM Quantum device validation was limited by queue wait times and qubit coherence constraints for this problem size.
3. **Problem Scale:** Current QAOA experiments encode 48 binary variables. Enterprise-scale call centers (500+ agents, 96 intervals, 10+ skills) would require 10,000+ variables — beyond current NISQ capabilities.
4. **Forecast Uncertainty:** The system uses point forecasts (a single predicted demand value per interval). Full probabilistic optimization with scenario trees or stochastic programming is not yet implemented.
5. **Static Scheduling:** The optimizer produces daily schedules in batch. Real-time intraday rescheduling (e.g., handling no-shows or demand surges) is not yet supported.
6. **Single-Site Model:** The formulation assumes one call center. Multi-site coordination with shared float pools remains future work.

**Mitigation strategy:** the modular architecture (classical baseline + quantum module + simulation layer) is designed so that real data APIs, larger quantum backends, and online learning modules can be swapped in without structural redesign of the pipeline.

## Future Work

- **Real-time Adaptive Scheduling:** a reinforcement learning agent for intraday shift adjustments based on live call arrival streams, rather than static daily batch schedules.
- **Multi-site Coordination:** distributed optimization across geographic call centers with shared resource/float pools.
- **Preference-aware Fairness:** incorporate agent shift preferences as soft constraints in the objective function to improve retention.
- **Probabilistic Forecasting:** replace point forecasts with full demand distributions (e.g., quantile regression or Bayesian forecasting) and optimize for risk-adjusted expected cost rather than a single expected value.
- **Larger Quantum Experiments:** scale QAOA to 100+ variables on IBM Quantum Heron / Condor hardware as it matures, moving beyond local simulator validation.
- **DQI Exploration:** investigate Decoded Quantum Interferometry as an alternative optimization paradigm for workforce scheduling, alongside QAOA.
- **Production Deployment:** containerize the pipeline with Docker and integrate with existing workforce management APIs (e.g., Genesys, NICE) for real-world deployment.
