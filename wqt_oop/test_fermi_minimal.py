"""Test minimale conservazione energia con Fermi-Dirac"""

import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    from wqt_oop.solitone_composito import SolitoneComposito
    from wqt_oop.physics_context import PhysicsContext
except ImportError:
    import segmento_quantistico, solitone_composito, physics_context
    SegmentoQuantistico = segmento_quantistico.SegmentoQuantistico
    SolitoneComposito = solitone_composito.SolitoneComposito
    PhysicsContext = physics_context.PhysicsContext

# Setup minimo: 24 segmenti
ctx_0 = PhysicsContext.for_level(0)
ctx_1_base = PhysicsContext.for_level(1)

# Context senza dissipazione
ctx_1 = PhysicsContext(
    level=1,
    length_scale=ctx_1_base.length_scale,
    alpha_K=0.1,  # RIDOTTO per stabilità
    beta_potential=0.001,
    kappa_coupling=0.1,  # RIDOTTO
    mu_fermi=50.0,
    T_fermi=5.0,
    gamma_cooling=0.0,
    eta_radiation_base=0.0,
    gamma_damping=0.0
)

np.random.seed(42)
segments = []
for i in range(24):
    chi = 50.0 + np.random.uniform(-2, 2)  # Vicino a equilibrio
    vel = np.random.uniform(-0.5, 0.5)  # Velocità SMALL
    pos = np.random.uniform(-5, 5, 3)
    segments.append(SegmentoQuantistico(chi, vel, ctx_0, position=pos))

soliton = SolitoneComposito(segments, ctx_1, screening_enabled=True)

# Test evoluzione
dt = 0.01  # Timestep piccolo
N_steps = 100

print("TEST CONSERVAZIONE MINIMO")
print("="*60)
H_init = soliton.energia_totale
print(f"H_initial = {H_init:.6e}")

for step in range(N_steps):
    H_before = soliton.energia_totale
    soliton.evolve(dt)
    H_after = soliton.energia_totale
    drift = abs(H_after - H_before) / (abs(H_before) + 1e-30)
    
    if step % 10 == 0:
        print(f"Step {step:3d}: H={H_after:.6e}, drift={drift:.3e}")

H_final = soliton.energia_totale
drift_total = abs(H_final - H_init) / (abs(H_init) + 1e-30)

print(f"\nH_final = {H_final:.6e}")
print(f"Drift cumulativo = {drift_total:.3e}")

if drift_total < 1e-3:
    print("✓ CONSERVAZIONE OK (drift < 1e-3)")
else:
    print(f"✗ DRIFT ECCESSIVO: {drift_total:.3e}")

# Test occupazione
stats = soliton.get_occupazione_stati()
print(f"\nOccupazione stati:")
print(f"  Destrorsi: {stats['N_destro']}")
print(f"  Sinistrorsi: {stats['N_sinistro']}")
print(f"  Polarizzazione: {stats['polarizzazione']:.3f}")
print(f"  T_eff: {stats['T_eff']:.3e}")
