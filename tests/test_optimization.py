import os
import sys
import pytest
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core_engine.queue.queue_simulator import erlang_c
from app.core_engine.quantum.quantum_optimizer import solve_qubo_classical

def test_erlang_c():
    """Test Erlang C calculates correctly."""
    # Understaffed (A > c): Should return 1.0 (100% probability of delay)
    assert erlang_c(c=10, A=15) == 1.0
    
    # Empty queue (A=0): Should return 0.0
    assert erlang_c(c=5, A=0) == 0.0
    
    # Normal case
    p_w = erlang_c(c=10, A=7)
    assert 0.2 < p_w < 0.3  # Should be approx 0.2217
    
def test_qubo_classical_solver():
    """Test that the brute-force QUBO solver finds the global minimum."""
    # A simple QUBO where we penalize selecting everything,
    # but reward selecting any single item. 
    # Q = [[-1, 3], [3, -1]]
    Q = np.array([
        [-1, 3],
        [3, -1]
    ])
    N = 2
    
    config, val = solve_qubo_classical(Q, N)
    
    # Best configs: [1, 0] or [0, 1] give -1.
    # [0, 0] gives 0.
    # [1, 1] gives -1 -1 + 6 = 4.
    assert val == -1
    assert list(config) == [1, 0] or list(config) == [0, 1]
    
def test_quantum_objective_match():
    """Ensure QUBO penalty accurately maps the linear shortfall penalty logic."""
    wage = 15
    alpha = 50
    D_t = 2
    
    # Q setup for 1 hour, 3 agents
    N = 3
    Q = np.zeros((N, N))
    
    for i in range(N):
        Q[i, i] += wage - 2 * alpha * D_t + alpha
        for j in range(i + 1, N):
            Q[i, j] += 2 * alpha
            
    # Re-add constant
    constant = alpha * (D_t**2)
    
    # Calculate for config [1, 1, 0] -> 2 agents working
    # cost = 2 * 15 = 30. Shortfall = 0.
    config_2 = np.array([1, 1, 0])
    cost_2 = config_2.dot(Q).dot(config_2) + constant
    assert cost_2 == 30
    
    # Calculate for config [1, 0, 0] -> 1 agent working
    # cost = 1 * 15 = 15. Shortfall = 1. Penalty = 50 * (1)^2 = 50. Total = 65.
    config_1 = np.array([1, 0, 0])
    cost_1 = config_1.dot(Q).dot(config_1) + constant
    assert cost_1 == 65
