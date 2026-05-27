"""Test bilancio termodinamico con dissipazione radiativa."""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito

print("="*70)
print("TEST BILANCIO TERMODINAMICO - Sistema Dissipativo")
print("="*70)

# Crea sistema 24 segmenti con screening
physics = PhysicsContext.for_level(1)
segments = []
np.random.seed(42)

for i in range(24):
    chi = 4.5 if i < 12 else -4.5
    chi += np.random.normal(0, 0.5)
    vel = np.random.uniform(0.5, 1.5)
    
    seg = SegmentoQuantistico(chi=chi, vel=vel, physics=PhysicsContext.for_level(0))
    segments.append(seg)

soliton = SolitoneComposito(children=segments, physics=physics, screening_enabled=True)

print(f"\nSistema: {soliton.N_children} segmenti, screening ABILITATO")
print(f"Parametri radiazione:")
print(f"  eta_base     = {physics.eta_radiation_base:.4f}")
print(f"  tau_coherence = {physics.tau_coherence:.2f}")

# Bilancio iniziale
budget_init = soliton.get_energy_budget()
H_init = budget_init['H_total']
H_conserved_init = budget_init['H_conserved']

print(f"\nBilancio iniziale:")
print(f"  H_internal   = {budget_init['H_internal']:.6e}")
print(f"  H_coupling   = {budget_init['H_coupling']:.6e}")
print(f"  H_total      = {budget_init['H_total']:.6e}")
print(f"  E_radiated   = {budget_init['E_radiated']:.6e}")
print(f"  H_conserved  = {budget_init['H_conserved']:.6e}")

# Evoluzione 200 passi
dt = 0.1
H_total_history = [H_init]
H_conserved_history = [H_conserved_init]
E_rad_history = [0.0]

print(f"\nEvoluzione (200 steps, dt={dt}):")

for step in range(200):
    soliton.evolve(dt)
    
    budget = soliton.get_energy_budget()
    H_total_history.append(budget['H_total'])
    H_conserved_history.append(budget['H_conserved'])
    E_rad_history.append(budget['E_radiated'])
    
    if step % 40 == 0:
        aux = soliton.get_auxiliary_state()
        tau_var = np.var(aux['tau_locale'])
        eta_eff = physics.compute_radiation_efficiency(tau_var)
        
        print(f"  Step {step:3d}: H_tot={budget['H_total']:.3e}, "
              f"E_rad={budget['E_radiated']:.3e}, "
              f"H_cons={budget['H_conserved']:.3e}, "
              f"eta_eff={eta_eff:.4f}")

# Bilancio finale
budget_final = soliton.get_energy_budget()

print(f"\nBilancio finale (step 200):")
print(f"  H_internal   = {budget_final['H_internal']:.6e}")
print(f"  H_coupling   = {budget_final['H_coupling']:.6e}")
print(f"  H_total      = {budget_final['H_total']:.6e}")
print(f"  E_radiated   = {budget_final['E_radiated']:.6e}")
print(f"  H_conserved  = {budget_final['H_conserved']:.6e}")

# Analisi conservazione
H_total_drift = abs(budget_final['H_total'] - H_init) / H_init
E_rad_fraction = budget_final['E_radiated'] / H_init
H_conserved_drift = abs(budget_final['H_conserved'] - H_conserved_init) / H_conserved_init

print(f"\n" + "="*70)
print("RISULTATI:")
print("="*70)
print(f"Drift H_total:       {H_total_drift*100:.2f}%  (atteso > 0, energia esce)")
print(f"Frazione radiata:    {E_rad_fraction*100:.2f}%  (E_rad/H_init)")
print(f"Drift H_conserved:   {H_conserved_drift*100:.4f}%  (deve essere ~ 0)")
print("="*70)

# Criteri successo
H_decreases = budget_final['H_total'] < H_init  # Energia diminuisce
E_rad_positive = budget_final['E_radiated'] > 0  # Radiazione accumulata
H_conserved_OK = H_conserved_drift < 0.01  # Bilancio conservato entro 1%

if H_decreases:
    print("\nOK: H_total diminuisce (radiazione funziona)")
else:
    print("\nERRORE: H_total non diminuisce!")

if E_rad_positive:
    print("OK: E_radiated > 0 (sink energetico attivo)")
else:
    print("ERRORE: E_radiated = 0 (nessuna radiazione)")

if H_conserved_OK:
    print(f"OK: H_conserved stabile (drift {H_conserved_drift*100:.4f}%)")
else:
    print(f"ERRORE: H_conserved drift {H_conserved_drift*100:.2f}% > 1%")

print("="*70)
