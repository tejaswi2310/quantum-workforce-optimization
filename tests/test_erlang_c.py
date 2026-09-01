import pytest
import math
from src.queue_simulator import required_agents_for_sla, TARGET_SLA, TARGET_WAIT_SECONDS, erlang_c

def test_erlang_c_low_traffic():
    c, A, sla, p_w = required_agents_for_sla(calls=5.0, aht_seconds=300, interval_seconds=3600, target_sla=0.8, target_wait_seconds=20)
    assert c > 0
    assert sla >= 0.8
    
    # Verify minimality
    prev_c = c - 1
    if prev_c > math.floor(A):
        prev_p_w = erlang_c(prev_c, A)
        prev_sla = 1.0 - prev_p_w * math.exp(-(prev_c - A) * 20 / 300)
        assert prev_sla < 0.8

def test_erlang_c_moderate_traffic():
    c, A, sla, p_w = required_agents_for_sla(calls=100.0, aht_seconds=300, interval_seconds=3600, target_sla=0.8, target_wait_seconds=20)
    assert c > A
    assert sla >= 0.8
    
    # Verify minimality
    prev_c = c - 1
    if prev_c > math.floor(A):
        prev_p_w = erlang_c(prev_c, A)
        prev_sla = 1.0 - prev_p_w * math.exp(-(prev_c - A) * 20 / 300)
        assert prev_sla < 0.8

def test_erlang_c_high_traffic():
    c, A, sla, p_w = required_agents_for_sla(calls=2000.0, aht_seconds=300, interval_seconds=3600, target_sla=0.8, target_wait_seconds=20)
    assert c > A
    assert sla >= 0.8

def test_monotonic_demand():
    c1, _, _, _ = required_agents_for_sla(calls=50.0, aht_seconds=300, interval_seconds=3600, target_sla=0.8, target_wait_seconds=20)
    c2, _, _, _ = required_agents_for_sla(calls=60.0, aht_seconds=300, interval_seconds=3600, target_sla=0.8, target_wait_seconds=20)
    assert c2 >= c1

def test_monotonic_aht():
    c1, _, _, _ = required_agents_for_sla(calls=100.0, aht_seconds=300, interval_seconds=3600, target_sla=0.8, target_wait_seconds=20)
    c2, _, _, _ = required_agents_for_sla(calls=100.0, aht_seconds=360, interval_seconds=3600, target_sla=0.8, target_wait_seconds=20)
    assert c2 >= c1

def test_monotonic_sla():
    c1, _, _, _ = required_agents_for_sla(calls=100.0, aht_seconds=300, interval_seconds=3600, target_sla=0.7, target_wait_seconds=20)
    c2, _, _, _ = required_agents_for_sla(calls=100.0, aht_seconds=300, interval_seconds=3600, target_sla=0.9, target_wait_seconds=20)
    assert c2 >= c1

def test_zero_demand():
    c, A, sla, p_w = required_agents_for_sla(calls=0.0, aht_seconds=300, interval_seconds=3600, target_sla=0.8, target_wait_seconds=20)
    assert c == 0
    assert A == 0.0
