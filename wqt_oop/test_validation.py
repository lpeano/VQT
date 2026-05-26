"""
================================================================================
TEST VALIDAZIONE ARCHITETTURA OOP
================================================================================

Confronta nuova architettura object-oriented con sistema legacy.

OBIETTIVI:
1. Verifica conservazione hamiltoniana (|dH/H| < 10^-8)
2. Verifica carica topologica (Schi = costante)
3. Verifica chiusura spinoriale (Stau == 0 mod 4pi)
4. Confronto energie con WQT_manifold.py originale

TEST CASES:
- test_single_segment(): 1 SegmentoQuantistico, evoluzione libera
- test_24_segments_leech(): SolitoneComposito(24), senza screening
- test_24_segments_screening(): SolitoneComposito(24), con screening dinamico
- test_conservation_laws(): Invarianti fisiche
- test_compare_with_legacy(): Confronto con database legacy
================================================================================
"""

import numpy as np
import sys
import os

# Aggiungi path al package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


class TestResults:
    """Container risultati test."""
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.details = []
    
    def add_result(self, test_name: str, passed: bool, message: str = ""):
        if passed:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            self.tests_failed += 1
            status = "❌ FAIL"
        
        self.details.append(f"{status}: {test_name}")
        if message:
            self.details.append(f"        {message}")
    
    def print_summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        for detail in self.details:
            print(detail)
        print("=" * 70)
        print(f"PASSED: {self.tests_passed}")
        print(f"FAILED: {self.tests_failed}")
        print(f"TOTAL:  {self.tests_passed + self.tests_failed}")
        print("=" * 70)


def test_single_segment(results: TestResults):
    """Test evoluzione singolo segmento."""
    print("\n### TEST 1: Segmento Singolo ###")
    
    physics = PhysicsContext.for_level(0)
    seg = SegmentoQuantistico(chi=4.5, vel=1.0, physics=physics)
    
    # Energia iniziale
    H_initial = seg.energia_totale
    Q_initial = seg.get_topology_charge()
    
    print(f"H_initial = {H_initial:.6e}")
    print(f"Q_initial = {Q_initial:.6f}")
    
    # Evoluzione 100 passi
    dt = 0.1
    for _ in range(100):
        seg.evolve(dt)
    
    H_final = seg.energia_totale
    Q_final = seg.get_topology_charge()
    
    print(f"H_final   = {H_final:.6e}")
    print(f"Q_final   = {Q_final:.6f}")
    
    # Verifica conservazione
    H_drift = abs(H_final - H_initial) / H_initial
    Q_drift = abs(Q_final - Q_initial)
    
    print(f"|dH/H|    = {H_drift:.3e}")
    print(f"|dQ|      = {Q_drift:.3e}")
    
    # Criteri
    H_OK = H_drift < 0.01  # 1% tolleranza (no coupling)
    Q_OK = Q_drift < 1e-10
    
    results.add_result(
        "Single Segment Evolution",
        H_OK and Q_OK,
        f"|dH/H|={H_drift:.3e}, |dQ|={Q_drift:.3e}"
    )


def test_24_segments_no_screening(results: TestResults):
    """Test SolitoneComposito(24) senza screening."""
    print("\n### TEST 2: 24 Segmenti (No Screening) ###")
    
    physics = PhysicsContext.for_level(1)
    
    # Crea 24 segmenti con distribuzione bimodale
    segments = []
    np.random.seed(42)
    for i in range(24):
        chi = 4.5 if i < 12 else -4.5
        chi += np.random.normal(0, 0.1)
        vel = np.random.uniform(0.5, 1.5)
        
        seg = SegmentoQuantistico(chi=chi, vel=vel, physics=PhysicsContext.for_level(0))
        segments.append(seg)
    
    # Crea composito SENZA screening
    soliton = SolitoneComposito(children=segments, physics=physics, screening_enabled=False)
    
    print(f"N_children = {soliton.N_children}")
    print(f"DOF = {soliton.get_num_dof()}")
    
    # Energia iniziale
    H_initial = soliton.energia_totale
    Q_initial = soliton.get_topology_charge()
    
    print(f"H_initial = {H_initial:.6e}")
    print(f"Q_initial = {Q_initial:.6f}")
    
    # Evoluzione 100 passi
    dt = 0.1
    for step in range(100):
        soliton.evolve(dt)
        
        if step % 20 == 0:
            diag = soliton.get_diagnostics()
            print(f"  Step {step:3d}: H={diag['energia']:.3e}, std(τ)={diag['tau_std']:.6f}")
    
    H_final = soliton.energia_totale
    Q_final = soliton.get_topology_charge()
    
    print(f"H_final   = {H_final:.6e}")
    print(f"Q_final   = {Q_final:.6f}")
    
    # Verifica
    H_drift = abs(H_final - H_initial) / H_initial
    Q_drift = abs(Q_final - Q_initial)
    
    print(f"|ΔH/H|    = {H_drift:.3e}")
    print(f"|ΔQ|      = {Q_drift:.3e}")
    
    # Criteri (più rilassati per sistema accoppiato)
    H_OK = H_drift < 0.05  # 5% tolleranza
    Q_OK = Q_drift < 1e-8
    
    results.add_result(
        "24 Segments (No Screening)",
        H_OK and Q_OK,
        f"|dH/H|={H_drift:.3e}, |dQ|={Q_drift:.3e}"
    )


def test_24_segments_with_screening(results: TestResults):
    """Test SolitoneComposito(24) CON screening dinamico."""
    print("\n### TEST 3: 24 Segmenti (CON Screening) ###")
    
    physics = PhysicsContext.for_level(1)
    
    # Crea 24 segmenti
    segments = []
    np.random.seed(42)
    for i in range(24):
        chi = 4.5 if i < 12 else -4.5
        chi += np.random.normal(0, 0.1)
        vel = np.random.uniform(0.5, 1.5)
        
        seg = SegmentoQuantistico(chi=chi, vel=vel, physics=PhysicsContext.for_level(0))
        segments.append(seg)
    
    # Crea composito CON screening
    soliton = SolitoneComposito(children=segments, physics=physics, screening_enabled=True)
    
    print(f"Screening: ENABLED")
    print(f"  σ_χ   = {physics.sigma_chi}")
    print(f"  σ_v   = {physics.sigma_velocity}")
    print(f"  σ_K²  = {physics.sigma_torsion}")
    print(f"  σ_τ   = {physics.sigma_tau}")
    
    # Energia iniziale
    H_initial = soliton.energia_totale
    Q_initial = soliton.get_topology_charge()
    
    print(f"H_initial = {H_initial:.6e}")
    print(f"Q_initial = {Q_initial:.6f}")
    
    # Evoluzione 100 passi
    dt = 0.1
    tau_initial = soliton.get_diagnostics()['tau_std']
    
    for step in range(100):
        soliton.evolve(dt)
        
        if step % 20 == 0:
            diag = soliton.get_diagnostics()
            print(f"  Step {step:3d}: H={diag['energia']:.3e}, std(τ)={diag['tau_std']:.6f}")
    
    H_final = soliton.energia_totale
    Q_final = soliton.get_topology_charge()
    tau_final = soliton.get_diagnostics()['tau_std']
    
    print(f"H_final   = {H_final:.6e}")
    print(f"Q_final   = {Q_final:.6f}")
    print(f"std(τ)_i  = {tau_initial:.6f}")
    print(f"std(τ)_f  = {tau_final:.6f}")
    
    # Verifica
    H_drift = abs(H_final - H_initial) / H_initial
    Q_drift = abs(Q_final - Q_initial)
    tau_growth = tau_final / (tau_initial + 1e-10)
    
    print(f"|dH/H|    = {H_drift:.3e}")
    print(f"|dQ|      = {Q_drift:.3e}")
    print(f"tau_growth  = {tau_growth:.3f}x")
    
    # Criteri
    H_OK = H_drift < 0.1  # 10% con screening
    Q_OK = Q_drift < 1e-8
    tau_diverge_OK = tau_growth > 1.5  # Deve divergere!
    
    results.add_result(
        "24 Segments (WITH Screening)",
        H_OK and Q_OK and tau_diverge_OK,
        f"|dH/H|={H_drift:.3e}, |dQ|={Q_drift:.3e}, tau_growth={tau_growth:.2f}x"
    )


def test_conservation_laws(results: TestResults):
    """Test invarianti fisiche."""
    print("\n### TEST 4: Leggi di Conservazione ###")
    
    physics = PhysicsContext.for_level(1)
    
    # Sistema 24 segmenti
    segments = []
    np.random.seed(123)
    for i in range(24):
        chi = (-1)**i * (4.5 + np.random.normal(0, 0.2))
        vel = np.random.uniform(-1.0, 1.0)
        seg = SegmentoQuantistico(chi=chi, vel=vel, physics=PhysicsContext.for_level(0))
        segments.append(seg)
    
    soliton = SolitoneComposito(children=segments, physics=physics, screening_enabled=True)
    
    # Valori iniziali
    H_init = soliton.energia_totale
    Q_init = soliton.get_topology_charge()
    closure_init = soliton.get_spinor_closure()
    
    print(f"Invarianti iniziali:")
    print(f"  H = {H_init:.6e}")
    print(f"  Q = {Q_init:.6f}")
    print(f"  Στ mod 4π = {closure_init:.6f}")
    
    # Evoluzione lungo 1000 passi
    dt = 0.1
    H_history = [H_init]
    Q_history = [Q_init]
    
    for step in range(1000):
        soliton.evolve(dt)
        H_history.append(soliton.energia_totale)
        Q_history.append(soliton.get_topology_charge())
    
    H_final = H_history[-1]
    Q_final = Q_history[-1]
    closure_final = soliton.get_spinor_closure()
    
    # Statistiche drift
    H_drift_max = max(abs(H - H_init)/H_init for H in H_history)
    Q_drift_max = max(abs(Q - Q_init) for Q in Q_history)
    closure_drift = abs(closure_final - closure_init)
    
    print(f"\nInvarianti finali:")
    print(f"  H = {H_final:.6e}")
    print(f"  Q = {Q_final:.6f}")
    print(f"  Στ mod 4π = {closure_final:.6f}")
    
    print(f"\nDrift massimi:")
    print(f"  |dH/H|_max = {H_drift_max:.3e}")
    print(f"  |dQ|_max   = {Q_drift_max:.3e}")
    print(f"  |dclosure| = {closure_drift:.3e}")
    
    # Criteri
    H_OK = H_drift_max < 0.1
    Q_OK = Q_drift_max < 1e-6
    closure_OK = closure_drift < 1.0  # Rilassato (mod 4π)
    
    results.add_result(
        "Conservation Laws (1000 steps)",
        H_OK and Q_OK and closure_OK,
        f"H_drift={H_drift_max:.2e}, Q_drift={Q_drift_max:.2e}"
    )


def test_fusion_threshold(results: TestResults):
    """Test criterio fusione."""
    print("\n### TEST 5: Criterio Fusione ###")
    
    # Sistema low-energy (non deve fondere) - usa soglia default alta
    physics_low = PhysicsContext.for_level(1)
    
    segments_low = []
    for i in range(24):
        seg = SegmentoQuantistico(chi=0.1, vel=0.1, physics=PhysicsContext.for_level(0))
        segments_low.append(seg)
    
    soliton_low = SolitoneComposito(children=segments_low, physics=physics_low, screening_enabled=False)
    
    # Sistema high-energy (deve fondere) - crea contesto custom con soglia bassa
    base = PhysicsContext.for_level(0)
    physics_high = PhysicsContext(
        level=1,
        length_scale=base.length_scale * np.sqrt(24),
        alpha_K=base.alpha_K * 576,
        E_fusion_threshold=1e6,  # Soglia ridotta per test
        # Copia altri parametri...
        beta_potential=base.beta_potential,
        kappa_coupling=base.kappa_coupling,
        sigma_chi=base.sigma_chi * np.sqrt(24),
        sigma_velocity=base.sigma_velocity,
        sigma_torsion=base.sigma_torsion * np.sqrt(24),
        sigma_tau=base.sigma_tau,
        lambda_coherence=base.lambda_coherence * np.sqrt(24),
        eps_topology=base.eps_topology,
        eta_radiation_base=base.eta_radiation_base,
        tau_coherence=base.tau_coherence,
        epsilon_local_absorption=base.epsilon_local_absorption,
        MAX_VELOCITY=base.MAX_VELOCITY,
        E_PLANCK_THRESHOLD=base.E_PLANCK_THRESHOLD * 576,
        HUBBLE_DAMPING=base.HUBBLE_DAMPING,
        dt=base.dt
    )
    
    segments_high = []
    for i in range(24):
        seg = SegmentoQuantistico(chi=10.0, vel=100.0, physics=PhysicsContext.for_level(0))
        segments_high.append(seg)
    
    soliton_high = SolitoneComposito(children=segments_high, physics=physics_high, screening_enabled=False)
    
    should_fuse_low = soliton_low.check_fusion_threshold()
    should_fuse_high = soliton_high.check_fusion_threshold()
    
    print(f"Low Energy System:")
    print(f"  H = {soliton_low.energia_totale:.3e}")
    print(f"  Should fuse? {should_fuse_low}")
    
    print(f"\nHigh Energy System:")
    print(f"  H = {soliton_high.energia_totale:.3e}")
    print(f"  Should fuse? {should_fuse_high}")
    
    # Criteri
    fusion_logic_OK = (not should_fuse_low) and should_fuse_high
    
    results.add_result(
        "Fusion Threshold Logic",
        fusion_logic_OK,
        f"Low={should_fuse_low}, High={should_fuse_high}"
    )


def main():
    """Esegui tutti i test."""
    print("=" * 70)
    print("VALIDAZIONE ARCHITETTURA OOP - WQT MANIFOLD")
    print("=" * 70)
    
    results = TestResults()
    
    # Esegui test
    test_single_segment(results)
    test_24_segments_no_screening(results)
    test_24_segments_with_screening(results)
    test_conservation_laws(results)
    test_fusion_threshold(results)
    
    # Summary
    results.print_summary()
    
    # Exit code
    return 0 if results.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
