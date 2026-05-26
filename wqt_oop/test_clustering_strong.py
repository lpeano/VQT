"""
SIMULAZIONE TEST: Clustering con Interazione di Scambio FORTE

Test per osservare auto-organizzazione materia/spazio con:
- lambda_exchange = 5.0 (100x valore standard)
- screening = DISABILITATO (forze a lungo raggio)

Se l'energia di scambio è il meccanismo corretto, dovremmo vedere:
1. Separation index > 0.5 (cluster separati)
2. Boundary flux < 50 (confine stabile)
3. Configurazione M/S stabile per centinaia di step
"""

import sys
sys.path.insert(0, r"c:\Users\lpeano\plank\VQT")

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


# Crea Physics Context con lambda_exchange FORTE
ctx_0 = PhysicsContext.for_level(0)
ctx_1_strong = PhysicsContext(
    level=1,
    length_scale=ctx_0.length_scale * np.sqrt(24),
    alpha_K=576.0,
    beta_potential=0.001,
    kappa_coupling=0.25,
    lambda_exchange=5.0,  # 100x più forte!
    sigma_chi=ctx_0.sigma_chi * np.sqrt(24),
    sigma_velocity=2.0,
    sigma_torsion=ctx_0.sigma_torsion * np.sqrt(24),
    sigma_tau=5.0,
    E_fusion_threshold=ctx_0.E_fusion_threshold * 576,
    lambda_coherence=ctx_0.lambda_coherence * np.sqrt(24),
    eps_topology=1e-6,
    eta_radiation_base=0.02,
    tau_coherence=10.0,
    epsilon_local_absorption=0.30,
    MAX_VELOCITY=10000.0,
    E_PLANCK_THRESHOLD=10000.0 * 576,
    HUBBLE_DAMPING=0.999,
    dt=0.1
)

print("=" * 80)
print(" TEST CLUSTERING: Interazione di Scambio FORTE + NO Screening")
print("=" * 80)
print(f"lambda_exchange = {ctx_1_strong.lambda_exchange} (standard: 0.05)")
print(f"alpha_K         = {ctx_1_strong.alpha_K}")
print(f"Screening       = DISABILITATO")
print()

# Crea 24 segmenti: 9 materia, 15 spazio (COLD START)
np.random.seed(42)
segments = []

for i in range(9):
    chi_init = np.random.uniform(3.5, 5.5)  # Materia
    v_init = np.random.uniform(-0.5, 0.5)  # COLD: 100x più freddo
    seg = SegmentoQuantistico(chi_init, v_init, ctx_0)
    segments.append(seg)

for i in range(15):
    chi_init = np.random.uniform(-5.5, -3.5)  # Spazio
    v_init = np.random.uniform(-0.5, 0.5)  # COLD: 100x più freddo
    seg = SegmentoQuantistico(chi_init, v_init, ctx_0)
    segments.append(seg)

np.random.shuffle(segments)

# Crea solitone con screening DISABILITATO
soliton = SolitoneComposito(segments, ctx_1_strong, screening_enabled=False)

# Bilancio iniziale
budget_init = soliton.get_energy_budget()
state = soliton.get_state_vector()
chi_vals = state[::2]
n_matter_init = np.sum(chi_vals > 0)

print("CONFIGURAZIONE INIZIALE:")
print(f"  H_total         = {budget_init['H_total']:.6e}")
print(f"  H_conserved     = {budget_init['H_conserved']:.6e}")
print(f"  Materia (chi>0) = {n_matter_init} / 24")
print()

# Calcola E_exchange iniziale
W = soliton.coupling_matrix
sign_matrix = np.sign(chi_vals[:, None] * chi_vals[None, :])
E_exchange_init = -ctx_1_strong.lambda_exchange * ctx_1_strong.alpha_K * np.sum(W * sign_matrix)

print(f"E_exchange iniziale = {E_exchange_init:.6e}")
print(f"Rapporto E_exchange/H_total = {E_exchange_init/budget_init['H_total']*100:.2f}%")
print()

# Log header
print(f"{'Step':>6}  {'H_total':>12}  {'H_cons':>12}  {'M/S':>6}  {'Flux':>5}  {'Sep':>6}")
print("-" * 70)

# Tracking
prev_phase_labels = None
history = {
    'steps': [],
    'n_matter': [],
    'boundary_flux': [],
    'separation_index': []
}

N_steps = 500
dt = 0.1

# Evoluzione
for step in range(1, N_steps + 1):
    soliton.evolve(dt)
    
    # Metriche
    budget = soliton.get_energy_budget()
    state = soliton.get_state_vector()
    chi_vals = state[::2]
    
    # Fase
    phase_labels = (chi_vals > 0).astype(int)
    n_matter = np.sum(phase_labels)
    
    # Boundary flux
    if prev_phase_labels is not None:
        boundary_flux = np.sum(phase_labels != prev_phase_labels)
    else:
        boundary_flux = 0
    prev_phase_labels = phase_labels.copy()
    
    # Clustering (distanza media same-phase)
    matter_idx = np.where(chi_vals > 0)[0]
    if len(matter_idx) >= 2:
        distances = []
        for i in range(len(matter_idx)):
            for j in range(i+1, len(matter_idx)):
                d = min(abs(matter_idx[i] - matter_idx[j]), 
                       24 - abs(matter_idx[i] - matter_idx[j]))
                distances.append(d)
        matter_cluster = np.mean(distances) if distances else 0.0
        separation = 1.0 - min(matter_cluster, 6.0) / 6.0
    else:
        separation = 0.0
    
    # Salva
    history['steps'].append(step)
    history['n_matter'].append(n_matter)
    history['boundary_flux'].append(boundary_flux)
    history['separation_index'].append(separation)
    
    # Log
    if step % 25 == 0 or step == N_steps:
        print(f"{step:6d}  {budget['H_total']:12.4e}  "
              f"{budget['H_conserved']:12.4e}  "
              f"{n_matter:2d}/{24-n_matter:2d}  "
              f"{boundary_flux:5d}  "
              f"{separation:6.3f}")

# Risultati finali
print()
print("=" * 80)
print(" RISULTATI")
print("=" * 80)

budget_final = soliton.get_energy_budget()
drift = abs((budget_final['H_conserved'] - budget_init['H_conserved']) / budget_init['H_conserved']) * 100

n_matter_mean = np.mean(history['n_matter'])
n_matter_std = np.std(history['n_matter'])
flux_total = np.sum(history['boundary_flux'])
sep_mean = np.mean(history['separation_index'])
sep_max = np.max(history['separation_index'])

print(f"H_conserved drift   = {drift:.6f}%")
print(f"Materia media       = {n_matter_mean:.1f} +/- {n_matter_std:.1f}")
print(f"Transizioni totali  = {flux_total}")
print(f"Separation index    = {sep_mean:.3f} (media), {sep_max:.3f} (max)")
print()

if sep_mean > 0.3:
    print("RISULTATO: AUTO-ORGANIZZAZIONE PRESENTE!")
    print("Le fasi si separano in cluster stabili.")
elif flux_total < 100:
    print("RISULTATO: CONFINE STABILE")
    print("Poche transizioni materia<->spazio.")
else:
    print("RISULTATO: MIXING CAOTICO")
    print("Nessuna struttura emergente.")

print("=" * 80)
