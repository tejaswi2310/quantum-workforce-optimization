# Literature Review

**Project:** QWO-X — Hybrid AI–Quantum Workforce Intelligence Platform
**Repository:** [github.com/tejaswi2310/quantum-workforce-optimization](https://github.com/tejaswi2310/quantum-workforce-optimization)
**Referenced from:** [`README.md`](../README.md) → Literature Review

Full annotated bibliography supporting the mathematical and architectural choices in QWO-X.

---

### 1. Karp, R. M. (1972). *Reducibility Among Combinatorial Problems.* In *Complexity of Computer Computations.*

Establishes the NP-hardness foundation underlying workforce scheduling as a combinatorial assignment problem. This is the theoretical justification for why exact classical solutions become computationally intractable as problem size (agents × intervals × skills) grows, and why heuristic, hybrid, or quantum-exploratory approaches are worth investigating at enterprise scale.

### 2. Lucas, A. (2014). *Ising Formulations of Many NP Problems.* Frontiers in Physics, 2, 5.

The definitive reference for mapping NP-hard combinatorial problems onto QUBO/Ising form. This paper directly guided QWO-X's constraint-to-QUBO penalty encoding — specifically, the Lagrangian relaxation approach used to fold hard constraints (breaks, overtime caps, skill matching) into the QUBO objective as quadratic penalty terms.

### 3. Farhi, E., Goldstone, J., & Gutmann, S. (2014). *A Quantum Approximate Optimization Algorithm.* arXiv:1411.4028.

The original QAOA paper. Provides the theoretical foundation for the parameterized ansatz (alternating cost and mixer Hamiltonians) used in QWO-X's quantum optimizer, and the standard transverse-field $X$-mixer adopted for state-space exploration.

### 4. Glover, F., Kochenberger, G., & Du, Y. (2018). *Quantum Bridge Analytics I: A Tutorial on Formulating and Using QUBO Models.*

A practical, implementation-focused tutorial on QUBO construction. Informed the Lagrangian relaxation approach used for constraint-penalty tuning in QWO-X, bridging the gap between Lucas (2014)'s theoretical formulation and a working QUBO matrix.

### 5. Pinedo, M. L. (2016). *Scheduling: Theory, Algorithms, and Systems* (5th ed.). Springer.

The standard workforce/operations scheduling theory textbook. Used as the reference for shift-length, mandatory-break, and overtime-cap constraint formulations in QWO-X's mixed-integer program.

### 6. Gurkaynak, G., et al. (2022). *Quantum Computing for Financial Portfolio Optimization.*

An industry perspective on the practical realities of applying quantum optimization to a different but structurally similar combinatorial allocation problem (portfolio optimization vs. workforce allocation). Provided a useful comparison point for setting realistic expectations about near-term QAOA performance and honest benchmarking practices.

### 7. IBM Quantum (2025). *Quantum Development Roadmap.*

Justifies the "future-ready module" framing of QWO-X's quantum component: as NISQ hardware trajectories (Heron, Condor) mature toward higher qubit counts and lower error rates, the QUBO formulation used here is designed to scale to larger instances without structural redesign.

### 8. WISER Program (2026). *Quantum + AI Optimization Curriculum.*

The educational framework for the WISER Quantum + AI Optimization Program 2026 — Vanguard Challenge, connecting classical optimization, AI forecasting, and quantum exploration as complementary (not competing) components of a hybrid decision-support system — the design philosophy underlying QWO-X's architecture.
