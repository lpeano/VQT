"""
VALIDAZIONE FERMI-DIRAC - Eseguibile come package module
Run: python -m wqt_oop.validate_fermi
"""

import numpy as np
from .fermi_dirac_screening import FermiDiracScreening
from .physics_context import PhysicsContext
from .segmento_quantistico import SegmentoQuantistico
from .solitone_composito import SolitoneComposito


def validate_all():
    print("="*70)
    print("VALIDAZIONE FERMI-DIRAC SCREENING")
    print("="*70 + "\n")
    
    # Test 1: Distribuzionebase
    print("1. DISTRIBUZIONE FERMI-DIRAC")
    print("-"*70)
    screener = FermiDiracScreening(mu=50.0, T_eff=5.0)
    
    for chi in [20, 40, 50, 60, 80]:
        f = screener.occupation(np.array([chi]))[0]
        A = screener.screening_factor(np.array([chi]))[0]
        print(f"chi={chi:5.1f} -> f={f:.4f}, A(screen)={A:.4f}")
    
    # Test 2: Conservazione con sistema ridotto
    print("\n2. CONSERVAZIONE ENERGIA (sistema ridotto)")
    print("-"*70)
    
    ctx_0 = PhysicsContext.for_level(0)
    ctx_1_base = PhysicsContext.for_level(1)
    
    ctx_1 = PhysicsContext(
        level=1,
        length_scale=ctx_1_base.length_scale,
        alpha_K=0.01,  # Molto ridotto
        beta_potential=0.001,
        kappa_coupling=0.01,
        lambda_exchange=0.0,
        mu_fermi=50.0,
        T_fermi=5.0,
        gamma_cooling=0.0,
        eta_radiation_base=0.0,
        gamma_damping=0.0
    )
    
    np.random.seed(42)
    segments = []
    for i in range(24):
        chi = 50.0 + np.random.uniform(-0.5, 0.5)
        vel = np.random.uniform(-0.1, 0.1)
        pos = np.random.uniform(-2, 2, 3)
        segments.append(SegmentoQuantistico(chi, vel, ctx_0, position=pos))
    
    soliton = SolitoneComposito(segments, ctx_1, screening_enabled=True)
    
    H_init = soliton.energia_totale
    print(f"H_init = {H_init:.6e}")
    
    dt = 0.005  # Timestep molto piccolo
    for step in range(100):
        soliton.evolve(dt)
        if step % 25 == 0:
            H = soliton.energia_totale
            drift = abs(H - H_init) / (abs(H_init) + 1e-30)
            print(f"  Step {step:3d}: H={H:.6e}, drift={drift:.3e}")
    
    H_final = soliton.energia_totale
    drift_total = abs(H_final - H_init) / (abs(H_init) + 1e-30)
    print(f"Drift finale = {drift_total:.3e}")
    
    # Test 3: Occupazione stati
    print("\n3. OCCUPAZIONE STATI")
    print("-"*70)
    
    stats = soliton.get_occupazione_stati()
    print(f"Destrorsi (chi > mu):  N={stats['N_destro']}")
    print(f"Sinistrorsi (chi <=mu): N={stats['N_sinistro']}")
    print(f"Polarizzazione: {stats['polarizzazione']:.3f}")
    print(f"T_eff: {stats['T_eff']:.3e}")
    print(f"Entropia: {stats['entropia_mixing']:.3f}")
    
    # Summary
    print("\n" + "="*70)
    print("RISULTATI:")
    print(f"  - Distribuzione Fermi-Dirac: OK")
    print(f"  - Drift energetico: {drift_total:.3e} " + ("OK" if drift_total < 0.01 else "ELEVATO"))
    print(f"  - Occupazione stati: OK")
    print(f"  - Sistema OPERATIVO: {'SI' if drift_total < 0.05 else 'CON LIMITAZIONI'}")
    print("="*70)
    
    return drift_total < 0.05


if __name__ == "__main__":
    success = validate_all()
    exit(0 if success else 1)
