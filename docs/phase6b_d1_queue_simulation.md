# Phase 6B-D1 Queue Simulation

## 1. Purpose
This module provides a mathematically honest evaluation of call center staffing schedules using the Erlang-C queueing model. It acts purely as a validation mechanism and does not attempt to repair or optimize staffing levels.

## 2. Queue Model
The simulation relies strictly on the Erlang-C model, which calculates the probability that a caller will wait in the queue ($P(W>0)$) given a specific call arrival rate, Average Handle Time (AHT), and number of scheduled agents. The model assumes infinite patience (no abandonment) and a Markovian arrival process.

## 3. Inputs
- **`scheduled_agents`** ($c$): The EXACT number of agents assigned to handle calls in the interval, as provided by the optimizer.
- **`calls`**: Total number of calls received in the interval.
- **`aht`**: Average Handle Time in seconds (default = 300).
- **`target_wait_seconds`** ($t$): SLA target wait threshold (default = 20s).

## 4. Outputs
For each hourly interval, the simulator outputs:
- **`offered_load`** ($A$): Traffic intensity in Erlangs.
- **`metric_validity`**: Queue stability state (`VALID_ERLANG_C`, `OVERLOADED`, `INVALID_INPUT`).
- **`sla_percent`**: The genuine SLA achieved given the scheduled agents.
- **`asa_seconds`**: The Average Speed of Answer in seconds.
- **`utilization_percent`**: Agent utilization limit.
- **`queue_status`**: `PASS` if `sla_percent >= 80.0`, else `FAIL`.
- **`abandonment_not_modeled`**: Explicitly set to `True`, as Erlang-C does not simulate caller abandonment.

## 5. Arrival-Rate Calculation
The arrival rate is calculated directly from total calls over the interval:
$$\lambda = \frac{\text{calls}}{\text{interval\_seconds}}$$
where `interval_seconds` is fixed to 3600 (1 hour).

## 6. Offered-Load Equation
The traffic intensity or offered load ($A$) is calculated as:
$$A = \lambda \times \text{aht}$$
This converts the calls into a pure "hours of work" capacity requirement.

## 7. Erlang-C Assumptions
- Arrival rate follows a Poisson process.
- Service times are exponentially distributed.
- Callers have infinite patience (no abandonment).
- Queue has infinite capacity.

## 8. Erlang-C Validity Condition
The Erlang-C formula is only mathematically valid and stable when:
$$A < c$$
where $c$ is the number of scheduled agents. If $c \le A$, the queue grows infinitely.

## 9. ASA Calculation
Average Speed of Answer (ASA) is calculated as:
$$\text{ASA} = \frac{P(W>0) \times \text{aht}}{c - A}$$
Valid only when $c > A$.

## 10. SLA Calculation
Service Level Agreement (SLA) is the percentage of calls answered within the target wait time ($t$).
$$\text{SLA} = 1 - P(W>0) \times e^{-(c - A) \frac{t}{\text{aht}}}$$
Valid only when $c > A$.

## 11. Utilization Calculation
Utilization is simply the ratio of workload to available capacity:
$$\text{Utilization} = \frac{A}{c} \times 100$$
Note: If the queue is overloaded ($A \ge c$), utilization equals or exceeds 100%.

## 12. Abandonment Behavior
Because the system employs standard Erlang-C (which assumes infinite patience), abandonment cannot be mathematically derived. Rather than fabricating an abandonment percentage (e.g., hardcoding `0.0`), the system explicitly reports `abandonment_not_modeled = True` and drops the fabricated `abandonment_percent` column entirely.

## 13. Overload Behavior
If the optimizer supplies a schedule where $c \le A$ (including when the optimizer sacrifices SLA to minimize cost penalties):
- `metric_validity` is set to `"OVERLOADED"`.
- `sla_percent` is explicitly returned as `None` (Null) as steady-state Erlang-C cannot calculate finite service levels for an infinite queue.
- `asa_seconds` is explicitly returned as `None` (Null) since the queue grows infinitely.
- `utilization` correctly reports the overload ($>100\%$).
- The system **DOES NOT** artificially inflate $c$ to force a passing score.

## 14. Invalid-Input Behavior
If the optimizer outputs $c \le 0$ but calls exist, `metric_validity` is flagged as `"INVALID_INPUT"`. The SLA is returned as Null and ASA as Null. If calls are 0, SLA is safely reported as 100.0%.

## 15. scheduled_agents vs required_agents
- **`required_agents`**: A theoretical minimum $c$ required to pass the SLA threshold, used purely as a baseline target.
- **`scheduled_agents`**: The actual physical agents deployed in the schedule by the CP-SAT MIP solver. 
The simulation computes metrics strictly against `scheduled_agents`, regardless of the theoretical requirement.

## 16. Metric Validity Semantics
- **`VALID_ERLANG_C`**: $c > A$. Metrics are scientifically sound.
- **`OVERLOADED`**: $0 < c \le A$. Queue explodes. Metrics are bounded to 0 SLA.
- **`INVALID_INPUT`**: $c \le 0$ with active demand.

## 17. Stable Example
- **Demand**: 100 calls, AHT 300s $\rightarrow A = 8.33$ Erlangs.
- **Scheduled Agents**: 12
- **Condition**: $12 > 8.33 \rightarrow$ `VALID_ERLANG_C`
- **Output**: SLA = 92.1%, ASA = 6.4s, Util = 69.4%

## 18. Overloaded Example
- **Demand**: 100 calls, AHT 300s $\rightarrow A = 8.33$ Erlangs.
- **Scheduled Agents**: 6
- **Condition**: $6 \le 8.33 \rightarrow$ `OVERLOADED`
- **Output**: SLA = Null, ASA = Null, Util = 138.8% (Queue instability exposed properly).

## 19. Limitations
- Infinite patience model (Erlang-C) heavily penalizes understaffed scenarios because abandonment does not clear the queue natively (unlike Erlang-A).
- Lognormal or deterministic service times are not modeled (exponential distribution assumed).

## 20. Why the Simulator Never Modifies Staffing
A simulator must function as an impartial evaluator. If the simulator intercepts failing schedules and automatically boosts staffing to achieve a stable queue, it destroys the feedback loop, masks optimization failures, and invalidates the core purpose of a workforce optimization pipeline. All staffing outputs must represent exactly what the mathematical solver decided.
