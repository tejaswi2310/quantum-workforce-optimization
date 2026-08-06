# Generative AI Disclosure

**Project:** QWO-X — Hybrid AI–Quantum Workforce Intelligence Platform
**Repository:** [github.com/tejaswi2310/quantum-workforce-optimization](https://github.com/tejaswi2310/quantum-workforce-optimization)
**Referenced from:** [`README.md`](../README.md) → Generative AI Disclosure

In the interest of full transparency for WISER judges, this document logs all generative AI tool usage during the development of QWO-X.

---

## Tools Used

| Tool | Usage | Review Status |
|---|---|---|
| **ChatGPT / Claude** | README drafting, mathematical LaTeX formatting, literature review synthesis | All content manually verified and edited by the team |
| **GitHub Copilot** | Code scaffolding, docstring generation | All algorithms manually reviewed; core optimization logic hand-derived |
| **Gemini** | Brainstorming constraint formulations | Ideas validated against OR-Tools and Qiskit documentation |

## What Was NOT AI-Generated

The following were manually coded and validated against textbook formulas by the team, not generated wholesale by an AI tool:

- QUBO matrix construction (diagonal/off-diagonal term derivation from the objective function)
- QAOA ansatz parameterization and Hamiltonian construction
- Erlang-C queue simulation derivations
- OR-Tools CP-SAT constraint formulation
- Core business-logic decisions (objective weighting scheme, constraint design, penalty tuning)

## Review Process

All AI-assisted output — whether code scaffolding, documentation drafts, or brainstormed ideas — was reviewed line-by-line by a team member before being committed, and cross-checked against primary references (OR-Tools documentation, Qiskit documentation, and the literature listed in [`Literature_Review.md`](Literature_Review.md)) where applicable. No AI-generated mathematical claim or benchmark number was accepted without independent verification against the actual pipeline output.

## Accountability

Individual contributions and the corresponding AI-tool usage within each contribution area are further evidenced by Git commit history in the [repository](https://github.com/tejaswi2310/quantum-workforce-optimization). See the main [README → Team & Contributions](../README.md#team--contributions) for the breakdown of who owned which parts of the pipeline.
