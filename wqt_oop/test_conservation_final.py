"""Test finale conservazione energia su 1000 steps."""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico

print("="*70)
print("TEST FINALE: Conservazione Energia (1000 steps)")
print("="*70)

physics = PhysicsContext.for_level(0)
seg = SegmentoQuantistico(chi=4.5, vel=1.0, physics=physics)

H_initial = seg.energia_totale
Q_initial = seg.get_topology_charge()

print(f"\nStato iniziale:")
print(f"  H = {H_initial:.10f}")
print(f"  Q = {Q_initial:.6f}")

# Evoluzione 1000 passi
dt = 0.1
H_history = [H_initial]
Q_history = [Q_initial]

for step in range(1000):
    seg.evolve(dt)
    H_history.append(seg.energia_totale)
    Q_history.append(seg.get_topology_charge())
    
    if step % 200 == 0:
        H_drift = abs(seg.energia_totale - H_initial) / H_initial
        print(f"  Step {step:4d}: H={seg.energia_totale:.10f}, dH/H={H_drift:.3e}")

H_final = seg.energia_totale
Q_final = seg.get_topology_charge()

print(f"\nStato finale (step 1000):")
print(f"  H = {H_final:.10f}")
print(f"  Q = {Q_final:.6f}")

# Statistiche conservazione
H_drift_max = max(abs(H - H_initial)/H_initial for H in H_history)
H_drift_final = abs(H_final - H_initial) / H_initial

print(f"\n" + "="*70)
print("RISULTATI CONSERVAZIONE:")
print("="*70)
print(f"Drift massimo H:    {H_drift_max:.6e}  ({H_drift_max*100:.4f}%)")
print(f"Drift finale H:     {H_drift_final:.6e}  ({H_drift_final*100:.4f}%)")
print(f"Delta Q:            {abs(Q_final - Q_initial):.6e}")
print("="*70)

# Criteri successo
H_OK = H_drift_max < 1e-3  # 0.1%
Q_evolves = abs(Q_final - Q_initial) > 0.1  # Q deve cambiare (campo dinamico)

if H_OK:
    print("\n✅ SUCCESSO: Conservazione H < 0.1%")
else:
    print(f"\n❌ FALLITO: Drift H = {H_drift_max*100:.4f}% > 0.1%")

if Q_evolves:
    print("✅ CORRETTO: Q = chi evolve (non è un invariante locale)")
else:
    print("⚠️  WARNING: Q non evolve (potenziale non funziona)")

print("="*70)
