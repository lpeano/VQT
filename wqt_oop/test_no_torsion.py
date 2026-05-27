"""Test conservazione energia SENZA torsione (alpha_K=0)."""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico

# Test singolo segmento SENZA torsione
print("=== TEST SENZA TORSIONE (alpha_K=0) ===\n")

# Crea contesto con alpha_K=0
base = PhysicsContext.for_level(0)
physics_no_torsion = PhysicsContext(
    level=0,
    length_scale=base.length_scale,
    alpha_K=0.0,  # DISATTIVA TORSIONE
    beta_potential=0.001,
    kappa_coupling=base.kappa_coupling,
    sigma_chi=base.sigma_chi,
    sigma_velocity=base.sigma_velocity,
    sigma_torsion=base.sigma_torsion,
    sigma_tau=base.sigma_tau,
    E_fusion_threshold=base.E_fusion_threshold,
    lambda_coherence=base.lambda_coherence,
    eps_topology=base.eps_topology,
    eta_radiation_base=base.eta_radiation_base,
    tau_coherence=base.tau_coherence,
    epsilon_local_absorption=base.epsilon_local_absorption,
    MAX_VELOCITY=base.MAX_VELOCITY,
    E_PLANCK_THRESHOLD=base.E_PLANCK_THRESHOLD,
    HUBBLE_DAMPING=base.HUBBLE_DAMPING,
    dt=base.dt
)

seg = SegmentoQuantistico(chi=4.5, vel=1.0, physics=physics_no_torsion)

print(f"Configurazione:")
print(f"  alpha_K = {physics_no_torsion.alpha_K}")
print(f"  beta    = {physics_no_torsion.beta_potential}")
print(f"\nStato iniziale:")
print(f"  chi = {seg.chi:.6f}")
print(f"  vel = {seg.vel:.6f}")
print(f"  H   = {seg.energia_totale:.6e}")

# Evoluzione 20 passi
dt = 0.1
H_history = [seg.energia_totale]

for step in range(20):
    seg.evolve(dt)
    H_history.append(seg.energia_totale)
    
    if step % 4 == 0:
        H_drift = abs(seg.energia_totale - H_history[0]) / H_history[0]
        print(f"\nStep {step}:")
        print(f"  chi = {seg.chi:.6f}")
        print(f"  vel = {seg.vel:.6f}")
        print(f"  H   = {seg.energia_totale:.6e}")
        print(f"  |dH/H_0| = {H_drift:.3e}")

# Analisi finale
H_drift_max = max(abs(H - H_history[0])/H_history[0] for H in H_history)
H_drift_final = abs(H_history[-1] - H_history[0]) / H_history[0]

print(f"\n{'='*50}")
print(f"CONSERVAZIONE ENERGIA (solo potenziale doppio pozzo):")
print(f"  |dH/H_0|_max   = {H_drift_max:.3e}")
print(f"  |dH/H_0|_final = {H_drift_final:.3e}")
print(f"  Tolleranza OK  = {H_drift_final < 1e-4}")
print(f"{'='*50}")
