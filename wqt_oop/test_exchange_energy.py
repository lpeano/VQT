"""Test diagnostico: verifica contributo energetico interazione di scambio."""

import sys
sys.path.insert(0, r"c:\Users\lpeano\plank\VQT")

import numpy as np
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito

# Setup fisico
ctx_0 = PhysicsContext.for_level(0)
ctx_1 = PhysicsContext.for_level(1)

print("=" * 70)
print(" DIAGNOSTICA INTERAZIONE DI SCAMBIO TOPOLOGICO")
print("=" * 70)
print(f"lambda_exchange = {ctx_1.lambda_exchange}")
print(f"kappa_coupling  = {ctx_1.kappa_coupling}")
print(f"alpha_K         = {ctx_1.alpha_K}")
print()

# Crea configurazione test: 12 materia, 12 spazio
np.random.seed(42)
segments = []
for i in range(12):
    chi_init = np.random.uniform(3.5, 5.5)  # Materia
    v_init = np.random.uniform(-2.0, 2.0)
    seg = SegmentoQuantistico(chi_init, v_init, ctx_0)
    segments.append(seg)

for i in range(12):
    chi_init = np.random.uniform(-5.5, -3.5)  # Spazio
    v_init = np.random.uniform(-2.0, 2.0)
    seg = SegmentoQuantistico(chi_init, v_init, ctx_0)
    segments.append(seg)

np.random.shuffle(segments)

# Crea solitone CON screening
soliton = SolitoneComposito(segments, ctx_1, screening_enabled=True)

# Calcola componenti energia
H_int = soliton.compute_hamiltonian_internal()
H_coup = soliton.compute_hamiltonian_coupling()
H_tot = soliton.compute_hamiltonian()

print("BILANCIO ENERGETICO INIZIALE:")
print(f"  H_internal  = {H_int:.6e}")
print(f"  H_coupling  = {H_coup:.6e}")
print(f"  H_total     = {H_tot:.6e}")
print()

# Calcola manualmente i contributi individuali
state = soliton.get_state_vector()
chi_vals = state[::2]

# Matrice coupling
W = soliton.coupling_matrix
chi_diff = chi_vals[:, None] - chi_vals[None, :]

# Torsione
E_torsion = 0.5 * ctx_1.alpha_K * np.sum(W * chi_diff**2)

# Scambio (senza screening, ma CON scaling alpha_K come nel codice vero)
sign_matrix = np.sign(chi_vals[:, None] * chi_vals[None, :])
E_exchange = -ctx_1.lambda_exchange * ctx_1.alpha_K * np.sum(W * sign_matrix)

# Coupling (senza torsione e scambio)
E_coupling_base = 0.5 * ctx_1.kappa_coupling * np.sum(W * chi_diff**2)

print("CONTRIBUTI INDIVIDUALI (senza screening):")
print(f"  E_coupling_base  = {E_coupling_base:.6e}")
print(f"  E_torsion        = {E_torsion:.6e}")
print(f"  E_exchange       = {E_exchange:.6e}")
print()

# Rapporti
if abs(E_coupling_base) > 1e-10:
    ratio_torsion = E_torsion / abs(E_coupling_base) * 100
    ratio_exchange = E_exchange / abs(E_coupling_base) * 100
    print(f"RAPPORTI PERCENTUALI (rispetto a E_coupling_base):")
    print(f"  E_torsion   = {ratio_torsion:.2f}%")
    print(f"  E_exchange  = {ratio_exchange:.2f}%")
    print()

# Conta same-phase vs cross-phase
n_same = np.sum(sign_matrix > 0) // 2  # Diviso 2 perché matrice simmetrica
n_cross = np.sum(sign_matrix < 0) // 2
print(f"INTERAZIONI:")
print(f"  Same-phase  : {n_same} (attrazione)")
print(f"  Cross-phase : {n_cross} (repulsione)")
print()

# Test: cosa succede con lambda più grande?
print("=" * 70)
print(" SIMULAZIONE CON LAMBDA_EXCHANGE x10")
print("=" * 70)

# Crea nuovo context con lambda aumentato
ctx_1_strong = PhysicsContext(
    level=1,
    length_scale=ctx_1.length_scale,
    alpha_K=ctx_1.alpha_K,
    beta_potential=ctx_1.beta_potential,
    kappa_coupling=ctx_1.kappa_coupling,
    lambda_exchange=0.5,  # 10x
    sigma_chi=ctx_1.sigma_chi,
    sigma_velocity=ctx_1.sigma_velocity,
    sigma_torsion=ctx_1.sigma_torsion,
    sigma_tau=ctx_1.sigma_tau,
    E_fusion_threshold=ctx_1.E_fusion_threshold,
    lambda_coherence=ctx_1.lambda_coherence,
    eps_topology=ctx_1.eps_topology,
    eta_radiation_base=ctx_1.eta_radiation_base,
    tau_coherence=ctx_1.tau_coherence,
    epsilon_local_absorption=ctx_1.epsilon_local_absorption,
    MAX_VELOCITY=ctx_1.MAX_VELOCITY,
    E_PLANCK_THRESHOLD=ctx_1.E_PLANCK_THRESHOLD,
    HUBBLE_DAMPING=ctx_1.HUBBLE_DAMPING,
    dt=ctx_1.dt
)

# Ricrea segmenti con nuovo context
segments_strong = []
np.random.seed(42)
for i in range(12):
    chi_init = np.random.uniform(3.5, 5.5)
    v_init = np.random.uniform(-2.0, 2.0)
    seg = SegmentoQuantistico(chi_init, v_init, ctx_0)
    segments_strong.append(seg)

for i in range(12):
    chi_init = np.random.uniform(-5.5, -3.5)
    v_init = np.random.uniform(-2.0, 2.0)
    seg = SegmentoQuantistico(chi_init, v_init, ctx_0)
    segments_strong.append(seg)

np.random.shuffle(segments_strong)

soliton_strong = SolitoneComposito(segments_strong, ctx_1_strong, screening_enabled=True)

H_coup_strong = soliton_strong.compute_hamiltonian_coupling()
E_exchange_strong = -ctx_1_strong.lambda_exchange * ctx_1_strong.alpha_K * np.sum(W * sign_matrix)

print(f"lambda_exchange = {ctx_1_strong.lambda_exchange} (era {ctx_1.lambda_exchange})")
print(f"E_exchange      = {E_exchange_strong:.6e} (era {E_exchange:.6e})")
print(f"H_coupling      = {H_coup_strong:.6e} (era {H_coup:.6e})")
print()

if abs(E_coupling_base) > 1e-10:
    ratio_exchange_strong = E_exchange_strong / abs(E_coupling_base) * 100
    print(f"E_exchange / E_coupling_base = {ratio_exchange_strong:.2f}%")

print("=" * 70)
