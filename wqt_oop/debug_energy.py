"""Debug test per verificare perché E_radiated = 0."""

import sys
import numpy as np
sys.path.insert(0, r"c:\Users\lpeano\plank\VQT")

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito

# Setup fisico
dt = 0.1
ctx_0 = PhysicsContext.for_level(0)  # Per segmenti
ctx_1 = PhysicsContext.for_level(1)  # Per composito

# Crea solitone composito con 24 segmenti
np.random.seed(42)
segments = []
for i in range(24):
    chi_init = np.random.uniform(3.0, 6.0)
    v_init = np.random.uniform(-1.0, 1.0)
    seg = SegmentoQuantistico(chi_init, v_init, ctx_0)
    segments.append(seg)

soliton = SolitoneComposito(segments, ctx_1, screening_enabled=False)

print("=== TEST DEBUG ENERGY TRACKING ===")
print(f"Initial gamma_damping sui segmenti: {[s.gamma_damping for s in segments]}")

# Stato iniziale
H_init = soliton.compute_hamiltonian()
print(f"\nH_initial = {H_init:.6e}")

# Evolvi 1 step
print(f"\n--- STEP 1 ---")
soliton.evolve(dt)

# Verifica gamma_damping aggiornato
print(f"Gamma dopo evolve: {[s.gamma_damping for s in segments]}")

# Budget energetico
budget = soliton.get_energy_budget()
print(f"H_total      = {budget['H_total']:.6e}")
print(f"E_radiated   = {budget['E_radiated']:.6e}")
print(f"H_conserved  = {budget['H_conserved']:.6e}")

# Differenza
delta_H = H_init - budget['H_total']
print(f"\nDelta H (H_init - H_final) = {delta_H:.6e}")
print(f"E_radiated dovrebbe essere {delta_H:.6e}, ma è {budget['E_radiated']:.6e}")

# Evolvi altri 9 steps
print(f"\n--- STEPS 2-10 ---")
for step in range(2, 11):
    soliton.evolve(dt)
    budget = soliton.get_energy_budget()
    if step % 3 == 0:
        print(f"  Step {step}: H={budget['H_total']:.3e}, E_rad={budget['E_radiated']:.3e}, gamma={segments[0].gamma_damping:.6f}")

# Finale
print(f"\n=== FINAL (step 10) ===")
budget = soliton.get_energy_budget()
print(f"H_total      = {budget['H_total']:.6e}")
print(f"E_radiated   = {budget['E_radiated']:.6e}")
print(f"H_conserved  = {budget['H_conserved']:.6e}")

delta_H_final = H_init - budget['H_total']
print(f"\nTotal energy lost: {delta_H_final:.6e}")
print(f"E_radiated tracked: {budget['E_radiated']:.6e}")
print(f"Missing energy: {delta_H_final - budget['E_radiated']:.6e}")
