# Mathematical Formulation

**Project:** QWO-X — Hybrid AI–Quantum Workforce Intelligence Platform
**Repository:** [github.com/tejaswi2310/quantum-workforce-optimization](https://github.com/tejaswi2310/quantum-workforce-optimization)
**Referenced from:** [`README.md`](../README.md) → Mathematical Formulation / Quantum Formulation (QAOA)

This document expands the summarized formulation in the main README into a full derivation: decision variables, the multi-objective cost function, hard constraints, the QUBO mapping used for quantum exploration, and the resulting cost Hamiltonian.

---

## 1. Decision Variables

| Symbol | Domain | Description |
|---|---|---|
| $x_{i,t}$ | $\{0,1\}$ | 1 if agent $i$ is assigned to work interval $t$ |
| $b_{i,t}$ | $\{0,1\}$ | 1 if agent $i$ is on break during interval $t$ |
| $o_{i,d}$ | $\mathbb{R}_{\geq0}$ | Overtime hours for agent $i$ on day $d$ |
| $s_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Shortfall of skill-group $k$ at interval $t$ |
| $u_{i,t}$ | $\{0,1\}$ | Utilization indicator (1 if agent $i$ is actively handling calls at $t$) |
| $A_{i,t}$ | $\{0,1\}$ | Agent $i$'s availability at interval $t$ (input data) |
| $M_{i,k}$ | $\{0,1\}$ | Whether agent $i$ possesses skill $k$ (input data) |
| $D_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Forecast demand (required headcount) for skill $k$ at interval $t$ |

Indices: $i \in$ agents, $t \in$ 30-minute intervals, $k \in$ skill groups, $d \in$ days.

## 2. Objective Function

$$
\min_{x,b,o,s} Z = w_1\sum_{i,t} c_i \cdot x_{i,t} + w_2\sum_{i,d} p_o \cdot o_{i,d} + w_3\sum_{k,t} \alpha_k \cdot s_{k,t} + w_4\sum_{i,t} \beta \cdot (1-u_{i,t}) \cdot x_{i,t}
$$

- **Term 1 — Staffing Cost:** wage cost $c_i$ per interval an agent is scheduled.
- **Term 2 — Overtime Penalty:** penalty rate $p_o$ applied to overtime hours beyond the standard shift.
- **Term 3 — SLA Violation Penalty:** penalty $\alpha_k$ per unit of unmet demand (shortfall) in skill-group $k$.
- **Term 4 — Idle Time Penalty:** penalty $\beta$ for scheduled-but-non-utilized agent time.

Weights $w_1$–$w_4$ are configurable by operations managers to reflect current business priorities (e.g., cost-sensitive vs. SLA-sensitive periods).

## 3. Constraints

1. **Demand Coverage:** $\sum_{i \in \mathcal{A}_k} x_{i,t} \geq D_{k,t} - s_{k,t}, \; \forall k,t$
2. **Maximum Shift Length:** $\sum_t x_{i,t} \leq H_{\max}, \; \forall i$
3. **Mandatory Breaks:** $\sum_{t \in \mathcal{B}_i} b_{i,t} \geq B_{\min}, \; \forall i$
4. **Skill Matching:** $x_{i,t} \leq M_{i,k}, \; \forall i,k,t$
5. **Overtime Cap:** $o_{i,d} \leq O_{\max}, \; \forall i,d$
6. **Agent Availability:** $x_{i,t} \leq A_{i,t}, \; \forall i,t$
7. **SLA Target (Simulation Feedback):** $\mathbb{P}(\text{Wait} \leq T_{\max}) \geq \text{SLA}_{\text{target}}$, enforced via Erlang-C validation as a post-optimization check rather than a linear constraint (since queueing probability is non-linear in staffing levels).

The classical solver (OR-Tools CP-SAT) handles constraints 1–6 natively as a mixed-integer program; constraint 7 is validated in the downstream Erlang-C simulation step, with infeasible schedules fed back for re-optimization.

## 4. QUBO Mapping (for QAOA)

To explore the problem on a quantum backend, the constrained MIP above is converted into a **Quadratic Unconstrained Binary Optimization (QUBO)** problem:

$$
\min_x x^T Q x
$$

**Construction of $Q$:**

- **Diagonal terms** $Q_{ii}$ encode the linear costs directly from the objective (staffing cost, idle-time penalty) for each $x_{i,t}$ binary variable.
- **Off-diagonal terms** $Q_{ij}$ encode pairwise interactions: shift-overlap conflicts, skill-group conflicts, and shared demand-shortfall coupling between agents assigned to the same interval.
- **Constraint penalties:** hard constraints (2, 3, 4, 5, 6 above) are relaxed into the objective via **Lagrangian penalty terms** of the form $\lambda \cdot (\text{constraint violation})^2$, so that any solution violating a hard constraint incurs a large quadratic penalty, steering the optimizer toward feasible regions. Penalty weights $\lambda$ are tuned empirically to dominate the cost terms without destabilizing the energy landscape.

## 5. Cost Hamiltonian

Binary variables are mapped to spin variables via $x_{i,t} = \frac{1 - Z_{i,t}}{2}$, giving the cost Hamiltonian:

$$
H_C = \sum_{i,t} h_{i,t} Z_{i,t} + \sum_{(i,t),(j,t')} J_{ijtt'} Z_{i,t} Z_{j,t'}
$$

where $h_{i,t}$ (linear bias) and $J_{ijtt'}$ (coupling strength) are derived directly from the diagonal and off-diagonal entries of $Q$.

**Mixer Hamiltonian:** the standard transverse-field $X$-mixer,

$$
H_M = \sum_{i,t} X_{i,t}
$$

is used to drive state-space exploration between cost-function evaluations, per the standard QAOA ansatz (Farhi, Goldstone & Gutmann, 2014).

## 6. Post-Processing / Constraint Repair---

## 1. Decision Variables

| Symbol | Domain | Description |
|---|---|---|
| $x_{i,t}$ | $\{0,1\}$ | 1 if agent $i$ is assigned to work interval $t$ |
| $b_{i,t}$ | $\{0,1\}$ | 1 if agent $i$ is on break during interval $t$ |
| $o_{i,d}$ | $\mathbb{R}_{\geq0}$ | Overtime hours for agent $i$ on day $d$ |
| $s_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Shortfall of skill-group $k$ at interval $t$ |
| $u_{i,t}$ | $\{0,1\}$ | Utilization indicator (1 if agent $i$ is actively handling calls at $t$) |
| $A_{i,t}$ | $\{0,1\}$ | Agent $i$'s availability at interval $t$ (input data) |
| $M_{i,k}$ | $\{0,1\}$ | Whether agent $i$ possesses skill $k$ (input data) |
| $D_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Forecast demand (required headcount) for skill $k$ at interval $t$ |

Indices: $i \in$ agents, $t \in$ 30-minute intervals, $k \in$ skill groups, $d \in$ days.

## 2. Objective Function

$$
\min_{x,b,o,s} Z = w_1\sum_{i,t} c_i \cdot x_{i,t} + w_2\sum_{i,d} p_o \cdot o_{i,d} + w_3\sum_{k,t} \alpha_k \cdot s_{k,t} + w_4\sum_{i,t} \beta \cdot (1-u_{i,t}) \cdot x_{i,t}
$$

- **Term 1 — Staffing Cost:** wage cost $c_i$ per interval an agent is scheduled.
- **Term 2 — Overtime Penalty:** penalty rate $p_o$ applied to overtime hours beyond the standard shift.
- **Term 3 — SLA Violation Penalty:** penalty $\alpha_k$ per unit of unmet demand (shortfall) in skill-group $k$.
- **Term 4 — Idle Time Penalty:** penalty $\beta$ for scheduled-but-non-utilized agent time.

Weights $w_1$–$w_4$ are configurable by operations managers to reflect current business priorities (e.g., cost-sensitive vs. SLA-sensitive periods).

## 3. Constraints

1. **Demand Coverage:** $\sum_{i \in \mathcal{A}_k} x_{i,t} \geq D_{k,t} - s_{k,t}, \; \forall k,t$
2. **Maximum Shift Length:** $\sum_t x_{i,t} \leq H_{\max}, \; \forall i$
3. **Mandatory Breaks:** $\sum_{t \in \mathcal{B}_i} b_{i,t} \geq B_{\min}, \; \forall i$
4. **Skill Matching:** $x_{i,t} \leq M_{i,k}, \; \forall i,k,t$
5. **Overtime Cap:** $o_{i,d} \leq O_{\max}, \; \forall i,d$
6. **Agent Availability:** $x_{i,t} \leq A_{i,t}, \; \forall i,t$
7. **SLA Target (Simulation Feedback):** $\mathbb{P}(\text{Wait} \leq T_{\max}) \geq \text{SLA}_{\text{target}}$, enforced via Erlang-C validation as a post-optimization check rather than a linear constraint (since queueing probability is non-linear in staffing levels).

The classical solver (OR-Tools CP-SAT) handles constraints 1–6 natively as a mixed-integer program; constraint 7 is validated in the downstream Erlang-C simulation step, with infeasible schedules fed back for re-optimization.

## 4. QUBO Mapping (for QAOA)

To explore the problem on a quantum backend, the constrained MIP above is converted into a **Quadratic Unconstrained Binary Optimization (QUBO)** problem:

$$
\min_x x^T Q x
$$

**Construction of $Q$:**

- **Diagonal terms** $Q_{ii}$ encode the linear costs directly from the objective (staffing cost, idle-time penalty) for each $x_{i,t}$ binary variable.
- **Off-diagonal terms** $Q_{ij}$ encode pairwise interactions: shift-overlap conflicts, skill-group conflicts, and shared demand-shortfall coupling between agents assigned to the same interval.
- **Constraint penalties:** hard constraints (2, 3, 4, 5, 6 above) are relaxed into the objective via **Lagrangian penalty terms** of the form $\lambda \cdot (\text{constraint violation})^2$, so that any solution violating a hard constraint incurs a large quadratic penalty, steering the optimizer toward feasible regions. Penalty weights $\lambda$ are tuned empirically to dominate the cost terms without destabilizing the energy landscape.

## 5. Cost Hamiltonian

Binary variables are mapped to spin variables via $x_{i,t} = \frac{1 - Z_{i,t}}{2}$, giving the cost Hamiltonian:

$$
H_C = \sum_{i,t} h_{i,t} Z_{i,t} + \sum_{(i,t),(j,t')} J_{ijtt'} Z_{i,t} Z_{j,t'}
$$

where $h_{i,t}$ (linear bias) and $J_{ijtt'}$ (coupling strength) are derived directly from the diagonal and off-diagonal entries of $Q$.

**Mixer Hamiltonian:** the standard transverse-field $X$-mixer,

$$
H_M = \sum_{i,t} X_{i,t}
$$

is used to drive state-space exploration between cost-function evaluations, per the standard QAOA ansatz (Farhi, Goldstone & Gutmann, 2014).

## 6. Post-Processing / Constraint Repair

Because the QUBO relaxation only *penalizes* constraint violations rather than strictly forbidding them, QAOA output is passed through a classical repair step that:

1. Identifies any residual constraint violations (double-booked agents, missed breaks, skill mismatches).
2. Greedily reassigns or drops conflicting assignments to restore feasibility.
3. Re-validates the repaired schedule against Erlang-C SLA targets before it is accepted as a candidate solution.

This hybrid **classical pre-processing → quantum core → classical post-processing** pattern is what allows the QAOA-refined schedule to reach 100% cost parity with the OR-Tools baseline while remaining operationally feasible (see main [README → Results & Benchmarking](../README.md#results--benchmarking)).

Because the QUBO relaxation only *penalizes* constraint violations rather than strictly forbidding them, QAOA output is passed through a classical repair step that:

1. Identifies any residual constraint violations (double-booked agents, missed breaks, skill mismatches).
2. Greedily reassigns or drops conflicting assignments to restore feasibility.
3. Re-validates the repaired schedule against Erlang-C SLA targets before it is accepted as a candidate solution.

This hybrid **classical pre-processing → quantum core → classical post-processing** pattern is what allows the QAOA-refined schedule to reach 100% cost parity with the OR-Tools baseline while remaining operationally feasible (see main [README → Results & Benchmarking](../README.md#results--benchmarking)).---

## 1. Decision Variables

| Symbol | Domain | Description |
|---|---|---|
| $x_{i,t}$ | $\{0,1\}$ | 1 if agent $i$ is assigned to work interval $t$ |
| $b_{i,t}$ | $\{0,1\}$ | 1 if agent $i$ is on break during interval $t$ |
| $o_{i,d}$ | $\mathbb{R}_{\geq0}$ | Overtime hours for agent $i$ on day $d$ |
| $s_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Shortfall of skill-group $k$ at interval $t$ |
| $u_{i,t}$ | $\{0,1\}$ | Utilization indicator (1 if agent $i$ is actively handling calls at $t$) |
| $A_{i,t}$ | $\{0,1\}$ | Agent $i$'s availability at interval $t$ (input data) |
| $M_{i,k}$ | $\{0,1\}$ | Whether agent $i$ possesses skill $k$ (input data) |
| $D_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Forecast demand (required headcount) for skill $k$ at interval $t$ |

Indices: $i \in$ agents, $t \in$ 30-minute intervals, $k \in$ skill groups, $d \in$ days.

## 2. Objective Function

$$
\min_{x,b,o,s} Z = w_1\sum_{i,t} c_i \cdot x_{i,t} + w_2\sum_{i,d} p_o \cdot o_{i,d} + w_3\sum_{k,t} \alpha_k \cdot s_{k,t} + w_4\sum_{i,t} \beta \cdot (1-u_{i,t}) \cdot x_{i,t}
$$

- **Term 1 — Staffing Cost:** wage cost $c_i$ per interval an agent is scheduled.
- **Term 2 — Overtime Penalty:** penalty rate $p_o$ applied to overtime hours beyond the standard shift.
- **Term 3 — SLA Violation Penalty:** penalty $\alpha_k$ per unit of unmet demand (shortfall) in skill-group $k$.
- **Term 4 — Idle Time Penalty:** penalty $\beta$ for scheduled-but-non-utilized agent time.

Weights $w_1$–$w_4$ are configurable by operations managers to reflect current business priorities (e.g., cost-sensitive vs. SLA-sensitive periods).

## 3. Constraints

1. **Demand Coverage:** $\sum_{i \in \mathcal{A}_k} x_{i,t} \geq D_{k,t} - s_{k,t}, \; \forall k,t$
2. **Maximum Shift Length:** $\sum_t x_{i,t} \leq H_{\max}, \; \forall i$
3. **Mandatory Breaks:** $\sum_{t \in \mathcal{B}_i} b_{i,t} \geq B_{\min}, \; \forall i$
4. **Skill Matching:** $x_{i,t} \leq M_{i,k}, \; \forall i,k,t$
5. **Overtime Cap:** $o_{i,d} \leq O_{\max}, \; \forall i,d$
6. **Agent Availability:** $x_{i,t} \leq A_{i,t}, \; \forall i,t$
7. **SLA Target (Simulation Feedback):** $\mathbb{P}(\text{Wait} \leq T_{\max}) \geq \text{SLA}_{\text{target}}$, enforced via Erlang-C validation as a post-optimization check rather than a linear constraint (since queueing probability is non-linear in staffing levels).

The classical solver (OR-Tools CP-SAT) handles constraints 1–6 natively as a mixed-integer program; constraint 7 is validated in the downstream Erlang-C simulation step, with infeasible schedules fed back for re-optimization.

## 4. QUBO Mapping (for QAOA)

To explore the problem on a quantum backend, the constrained MIP above is converted into a **Quadratic Unconstrained Binary Optimization (QUBO)** problem:

$$
\min_x x^T Q x
$$

**Construction of $Q$:**

- **Diagonal terms** $Q_{ii}$ encode the linear costs directly from the objective (staffing cost, idle-time penalty) for each $x_{i,t}$ binary variable.
- **Off-diagonal terms** $Q_{ij}$ encode pairwise interactions: shift-overlap conflicts, skill-group conflicts, and shared demand-shortfall coupling between agents assigned to the same interval.
- **Constraint penalties:** hard constraints (2, 3, 4, 5, 6 above) are relaxed into the objective via **Lagrangian penalty terms** of the form $\lambda \cdot (\text{constraint violation})^2$, so that any solution violating a hard constraint incurs a large quadratic penalty, steering the optimizer toward feasible regions. Penalty weights $\lambda$ are tuned empirically to dominate the cost terms without destabilizing the energy landscape.

## 5. Cost Hamiltonian

Binary variables are mapped to spin variables via $x_{i,t} = \frac{1 - Z_{i,t}}{2}$, giving the cost Hamiltonian:

$$
H_C = \sum_{i,t} h_{i,t} Z_{i,t} + \sum_{(i,t),(j,t')} J_{ijtt'} Z_{i,t} Z_{j,t'}
$$

where $h_{i,t}$ (linear bias) and $J_{ijtt'}$ (coupling strength) are derived directly from the diagonal and off-diagonal entries of $Q$.

**Mixer Hamiltonian:** the standard transverse-field $X$-mixer,

$$
H_M = \sum_{i,t} X_{i,t}
$$

is used to drive state-space exploration between cost-function evaluations, per the standard QAOA ansatz (Farhi, Goldstone & Gutmann, 2014).

## 6. Post-Processing / Constraint Repair

Because the QUBO relaxation only *penalizes* constraint violations rather than strictly forbidding them, QAOA output is passed through a classical repair step that:

1. Identifies any residual constraint violations (double-booked agents, missed breaks, skill mismatches).
2. Greedily reassigns or drops conflicting assignments to restore feasibility.
3. Re-validates the repaired schedule against Erlang-C SLA targets before it is accepted as a candidate solution.

This hybrid **classical pre-processing → quantum core → classical post-processing** pattern is what allows the QAOA-refined schedule to reach 100% cost parity with the OR-Tools baseline while remaining operationally feasible (see main [README → Results & Benchmarking](../README.md#results--benchmarking)).
---

## 1. Decision Variables

| Symbol | Domain | Description |
|---|---|---|
| $x_{i,t}$ | $\{0,1\}$ | 1 if agent $i$ is assigned to work interval $t$ |
| $b_{i,t}$ | $\{0,1\}$ | 1 if agent $i$ is on break during interval $t$ |
| $o_{i,d}$ | $\mathbb{R}_{\geq0}$ | Overtime hours for agent $i$ on day $d$ |
| $s_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Shortfall of skill-group $k$ at interval $t$ |
| $u_{i,t}$ | $\{0,1\}$ | Utilization indicator (1 if agent $i$ is actively handling calls at $t$) |
| $A_{i,t}$ | $\{0,1\}$ | Agent $i$'s availability at interval $t$ (input data) |
| $M_{i,k}$ | $\{0,1\}$ | Whether agent $i$ possesses skill $k$ (input data) |
| $D_{k,t}$ | $\mathbb{Z}_{\geq0}$ | Forecast demand (required headcount) for skill $k$ at interval $t$ |

Indices: $i \in$ agents, $t \in$ 30-minute intervals, $k \in$ skill groups, $d \in$ days.

## 2. Objective Function

$$
\min_{x,b,o,s} Z = w_1\sum_{i,t} c_i \cdot x_{i,t} + w_2\sum_{i,d} p_o \cdot o_{i,d} + w_3\sum_{k,t} \alpha_k \cdot s_{k,t} + w_4\sum_{i,t} \beta \cdot (1-u_{i,t}) \cdot x_{i,t}
$$

- **Term 1 — Staffing Cost:** wage cost $c_i$ per interval an agent is scheduled.
- **Term 2 — Overtime Penalty:** penalty rate $p_o$ applied to overtime hours beyond the standard shift.
- **Term 3 — SLA Violation Penalty:** penalty $\alpha_k$ per unit of unmet demand (shortfall) in skill-group $k$.
- **Term 4 — Idle Time Penalty:** penalty $\beta$ for scheduled-but-non-utilized agent time.

Weights $w_1$–$w_4$ are configurable by operations managers to reflect current business priorities (e.g., cost-sensitive vs. SLA-sensitive periods).

## 3. Constraints

1. **Demand Coverage:** $\sum_{i \in \mathcal{A}_k} x_{i,t} \geq D_{k,t} - s_{k,t}, \; \forall k,t$
2. **Maximum Shift Length:** $\sum_t x_{i,t} \leq H_{\max}, \; \forall i$
3. **Mandatory Breaks:** $\sum_{t \in \mathcal{B}_i} b_{i,t} \geq B_{\min}, \; \forall i$
4. **Skill Matching:** $x_{i,t} \leq M_{i,k}, \; \forall i,k,t$
5. **Overtime Cap:** $o_{i,d} \leq O_{\max}, \; \forall i,d$
6. **Agent Availability:** $x_{i,t} \leq A_{i,t}, \; \forall i,t$
7. **SLA Target (Simulation Feedback):** $\mathbb{P}(\text{Wait} \leq T_{\max}) \geq \text{SLA}_{\text{target}}$, enforced via Erlang-C validation as a post-optimization check rather than a linear constraint (since queueing probability is non-linear in staffing levels).

The classical solver (OR-Tools CP-SAT) handles constraints 1–6 natively as a mixed-integer program; constraint 7 is validated in the downstream Erlang-C simulation step, with infeasible schedules fed back for re-optimization.

## 4. QUBO Mapping (for QAOA)

To explore the problem on a quantum backend, the constrained MIP above is converted into a **Quadratic Unconstrained Binary Optimization (QUBO)** problem:

$$
\min_x x^T Q x
$$

**Construction of $Q$:**

- **Diagonal terms** $Q_{ii}$ encode the linear costs directly from the objective (staffing cost, idle-time penalty) for each $x_{i,t}$ binary variable.
- **Off-diagonal terms** $Q_{ij}$ encode pairwise interactions: shift-overlap conflicts, skill-group conflicts, and shared demand-shortfall coupling between agents assigned to the same interval.
- **Constraint penalties:** hard constraints (2, 3, 4, 5, 6 above) are relaxed into the objective via **Lagrangian penalty terms** of the form $\lambda \cdot (\text{constraint violation})^2$, so that any solution violating a hard constraint incurs a large quadratic penalty, steering the optimizer toward feasible regions. Penalty weights $\lambda$ are tuned empirically to dominate the cost terms without destabilizing the energy landscape.

## 5. Cost Hamiltonian

Binary variables are mapped to spin variables via $x_{i,t} = \frac{1 - Z_{i,t}}{2}$, giving the cost Hamiltonian:

$$
H_C = \sum_{i,t} h_{i,t} Z_{i,t} + \sum_{(i,t),(j,t')} J_{ijtt'} Z_{i,t} Z_{j,t'}
$$

where $h_{i,t}$ (linear bias) and $J_{ijtt'}$ (coupling strength) are derived directly from the diagonal and off-diagonal entries of $Q$.

**Mixer Hamiltonian:** the standard transverse-field $X$-mixer,

$$
H_M = \sum_{i,t} X_{i,t}
$$

is used to drive state-space exploration between cost-function evaluations, per the standard QAOA ansatz (Farhi, Goldstone & Gutmann, 2014).

## 6. Post-Processing / Constraint Repair

Because the QUBO relaxation only *penalizes* constraint violations rather than strictly forbidding them, QAOA output is passed through a classical repair step that:

1. Identifies any residual constraint violations (double-booked agents, missed breaks, skill mismatches).
2. Greedily reassigns or drops conflicting assignments to restore feasibility.
3. Re-validates the repaired schedule against Erlang-C SLA targets before it is accepted as a candidate solution.

This hybrid **classical pre-processing → quantum core → classical post-processing** pattern is what allows the QAOA-refined schedule to reach 100% cost parity with the OR-Tools baseline while remaining operationally feasible (see main [README → Results & Benchmarking](../README.md#results--benchmarking)).
