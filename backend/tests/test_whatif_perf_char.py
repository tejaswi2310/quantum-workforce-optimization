import pytest
import math
from app.core_engine.queue.queue_simulator import erlang_c, required_agents_for_sla

def test_erlang_c_characterization():
    assert math.isclose(erlang_c(7, 4.166666666666667), 0.15979852254327062, rel_tol=1e-7)
    assert math.isclose(erlang_c(48, 41.666666666666664), 0.2517930693143422, rel_tol=1e-7)
    assert math.isclose(erlang_c(429, 416.6666666666667), 0.4368311193737156, rel_tol=1e-7)
    assert erlang_c(10, 15.0) == 1.0
    assert erlang_c(10, -5.0) == 0.0

def test_required_agents_characterization():
    c, A, s, p = required_agents_for_sla(50, 300, 3600, 0.8, 20)
    assert c == 7
    assert math.isclose(s, 0.8677062407589419, rel_tol=1e-7)
    assert math.isclose(p, 0.1597985225432707, rel_tol=1e-7)
    c, A, s, p = required_agents_for_sla(500, 300, 3600, 0.8, 20)
    assert c == 48
    assert math.isclose(s, 0.8349274004433036, rel_tol=1e-7)
    assert math.isclose(p, 0.2517930693143422, rel_tol=1e-7)
    c, A, s, p = required_agents_for_sla(5000, 300, 3600, 0.8, 20)
    assert c == 429
    assert math.isclose(s, 0.8080328154423382, rel_tol=1e-7)
    assert math.isclose(p, 0.4368311193737156, rel_tol=1e-7)
