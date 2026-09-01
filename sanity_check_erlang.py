import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from app.core_engine.queue.queue_simulator import required_agents_for_sla, erlang_c
import math

print("=== HAND-CALCULATED SANITY CHECK ===")
calls = 50.0
aht = 300
interval = 3600
target_sla = 0.8
wait = 20

print(f"Inputs: {calls} calls, {aht}s AHT, {interval}s interval")
arrival_rate = calls / interval
A = arrival_rate * aht
print(f"Arrival Rate: {arrival_rate:.4f} calls/s")
print(f"Offered Traffic (A): {A:.4f} Erlangs")

c, ret_A, sla, p_w = required_agents_for_sla(calls, aht, interval, target_sla, wait)

print(f"\nMinimum agents required: {c}")
print(f"Achieved SLA: {sla*100:.2f}%")
print(f"Wait Probability: {p_w*100:.2f}%")

# Independent manual check of N-1
prev_c = c - 1
if prev_c > math.floor(A):
    prev_p_w = erlang_c(prev_c, A)
    prev_sla = 1.0 - prev_p_w * math.exp(-(prev_c - A) * wait / aht)
    print(f"\nN-1 ({prev_c} agents) Check:")
    print(f"Achieved SLA: {prev_sla*100:.2f}% (Expected < 80%)")
    if prev_sla < target_sla:
        print("Minimality VERIFIED: PASS")
    else:
        print("Minimality VERIFIED: FAIL")
else:
    print(f"\nN-1 ({prev_c} agents) is less than/equal to traffic {A:.2f}. Unstable queue.")
    print("Minimality VERIFIED: PASS")
