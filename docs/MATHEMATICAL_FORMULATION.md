# Mathematical Formulation: Hybrid Quantum-Classical Workforce Optimization

This document mathematically defines the formulation of the call center workforce scheduling problem. To handle the computational complexity, the architecture utilizes a hybrid approach: large-scale combinatorial scheduling is resolved using a Classical Integer Linear Program (ILP), while peak-demand "reduced problem" windows are formulated as a Quadratic Unconstrained Binary Optimization (QUBO) model to leverage Quantum Approximate Optimization Algorithm (QAOA) solvers.

---

## 1. Classical Formulation (Integer Linear Programming)

### 1.1 Decision Variables
Let the schedule be discretized into hourly intervals $t \in \mathcal{T} = \{0, 1, \dots, 23\}$.
Let $\mathcal{S}$ denote the set of all possible shift templates. A shift $s \in \mathcal{S}$ is defined by a start time and includes mandatory breaks.

* $x_{s} \in \mathbb{Z}_{\ge 0}$: The number of agents assigned to shift template $s$.
* $y_{s} \in \{0, 1\}$: A binary variable that equals $1$ if at least one agent is scheduled for shift $s$, and $0$ otherwise.

*(In extended formulations considering skill groups $k \in \mathcal{K}$, variables expand to $x_{s, k}$)*

### 1.2 Objective Function
The objective is to minimize the total operational cost, which consists of the agent base wages, idle time penalties, overtime costs, and waiting costs for customers.

$$ \min \sum_{s \in \mathcal{S}} \left( C_{\text{base}} \cdot x_{s} + C_{\text{overtime}} \cdot o_{s} \right) + \sum_{t \in \mathcal{T}} \left( C_{\text{idle}} \cdot I_{t} + C_{\text{wait}} \cdot W_{t} \right) $$

For the reduced baseline model, this simplifies to minimizing the total number of scheduled agents:
$$ \min \sum_{s \in \mathcal{S}} x_s $$

### 1.3 Constraints

**1. Coverage Constraint (Demand Satisfaction):**
For every hour $t$, the number of active agents must meet or exceed the forecasted demand $d_t$.
$$ \sum_{s \in \mathcal{S}} A_{s, t} x_{s} \ge d_{t} \quad \forall t \in \mathcal{T} $$
Where $A_{s, t} = 1$ if an agent on shift $s$ is actively working at time $t$ (not on break), and $0$ otherwise.

**2. Break Constraints:**
Encoded within the shift matrix $A_{s, t}$. For an 8-hour shift, exactly 1 hour is designated as a break.
$$ \sum_{t=s}^{s+8} A_{s, t} = 8 \quad \forall s \in \mathcal{S} $$

**3. Shift Diversity (Availability) Constraint:**
To prevent fragmented schedules, the number of unique shift start times is bounded by a constant $M_{\text{shifts}}$.
$$ x_{s} \le M \cdot y_{s} \quad \forall s \in \mathcal{S} $$
$$ \sum_{s \in \mathcal{S}} y_{s} \le M_{\text{shifts}} $$
*(where $M$ is a sufficiently large big-M constant).*

**4. Erlang C SLA Constraint (Queueing Theory):**
Wait time probability $P(W > 0)$ must be controlled such that the Service Level Agreement (SLA) is satisfied.
Let $A = \frac{\lambda}{\mu}$ be the traffic intensity (Erlangs). The probability of wait is given by the Erlang C formula:
$$ P(W > 0) = \frac{\frac{A^c}{c!} \frac{c}{c - A}}{\sum_{i=0}^{c-1} \frac{A^i}{i!} + \frac{A^c}{c!} \frac{c}{c - A}} $$
The number of agents $c = \sum x_s A_{s, t}$ must be chosen such that:
$$ 1 - P(W > 0) e^{-(c - A) \frac{T_{\text{target}}}{T_{\text{AHT}}}} \ge \text{SLA}_{\text{target}} $$

---

## 2. Quantum Formulation (QUBO & QAOA)

Due to the $O(2^N)$ exponential scaling of Hilbert space, current NISQ devices cannot solve the full 24-hour multi-skill schedule. We extract a **Reduced Workforce Optimization Problem**—focusing on a critical peak window (e.g., a 4-to-8 hour block with maximum demand)—and map it to an Ising Hamiltonian.

### 2.1 QUBO Generator Model
Let $q_i \in \{0, 1\}$ for $i \in \{1, \dots, N\}$ represent the selection of a specific candidate shift or agent deployment during the peak window.

The Quadratic Unconstrained Binary Optimization (QUBO) formulation minimizes:
$$ E(q) = \sum_{i=1}^N c_i q_i + \sum_{i=1}^N \sum_{j > i}^N Q_{i,j} q_i q_j $$

We map our constrained ILP to QUBO using penalty methods:
$$ H(q) = H_{\text{cost}} + \lambda_1 H_{\text{coverage}} + \lambda_2 H_{\text{idle}} $$

### 2.2 Hamiltonian Encoding

1. **Cost Hamiltonian ($H_{\text{cost}}$)**: Minimizes the number of selected shifts.
   $$ H_{\text{cost}} = \sum_{i=1}^N \omega_i q_i $$
   Where $\omega_i$ is the wage or cost weight for shift $i$.

2. **Coverage Penalty ($H_{\text{coverage}}$)**: Enforces that the sum of active shifts meets the required demand $D$.
   $$ H_{\text{coverage}} = \left( \sum_{i=1}^N q_i - D \right)^2 $$
   Expanding this yields linear terms $(1 - 2D)q_i$ and quadratic interaction terms $2 q_i q_j$.

3. **Idle Penalty ($H_{\text{idle}}$)**: Penalizes overstaffing beyond $D$.
   Incorporated by tuning the asymmetry of the quadratic penalty or adjusting the linear weights.

The total QUBO matrix $Q$ is formed by extracting the coefficients of $q_i$ (diagonal terms) and $q_i q_j$ (off-diagonal terms).

### 2.3 Execution via QAOA
The QUBO is mapped to a Quantum Ising Hamiltonian using the substitution $q_i = \frac{1 - Z_i}{2}$, where $Z_i$ is the Pauli-Z operator. 
The Quantum Approximate Optimization Algorithm (QAOA) prepares a parameterized state $|\psi(\vec{\gamma}, \vec{\beta})\rangle$ and uses a classical optimizer (e.g., COBYLA) to find the parameters that minimize the expectation value:
$$ \min_{\vec{\gamma}, \vec{\beta}} \langle \psi(\vec{\gamma}, \vec{\beta}) | \hat{H} | \psi(\vec{\gamma}, \vec{\beta}) \rangle $$

By comparing the exact classical QUBO eigenspectrum with the QAOA sampled results, we benchmark the quantum solver's convergence on the reduced problem space.
