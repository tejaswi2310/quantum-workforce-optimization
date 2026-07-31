# Mathematical Formulation

## Objective Function
Minimize the total cost of scheduling agents:
`Min Σ C * x_i`
Where `C` is the daily cost per agent, and `x_i` is a binary variable indicating if shift `i` is active.

## Constraints
1. **Coverage Constraint**: 
   `Σ x_i >= d_t` for all `t`
   The number of agents scheduled at time `t` must be greater than or equal to the forecasted demand `d_t`.
2. **Break Constraint**: 
   Every agent must have exactly 1 hour of break during their 8-hour shift.
3. **Shift Length**: 
   All shifts are exactly 8 hours long.

## Quantum Formulation (QUBO)
The integer linear programming (ILP) problem is converted to a Quadratic Unconstrained Binary Optimization (QUBO) model:
`H = A * (Objective) + B * (Penalty_Coverage) + C * (Penalty_Breaks)`
Where A, B, C are penalty weights. QAOA minimizes the expectation value of this Hamiltonian.

## Queue Theory (Erlang C)
- `Traffic Intensity (A) = λ / μ`
- `Probability of Wait (P_w) = ErlangC(c, A)`
- `Service Level (SLA) = 1 - P_w * exp(-(c - A) * t / avg_handle_time)`
