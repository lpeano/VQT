"""
================================================================================
TEST PEANO-VQT - Validazione nel repo ufficiale VQT_repo
================================================================================

Verifica i 3 fix chirurgici applicati al checkpoint:
  Bug1: chi_max invece di chi_mean come segnale di saturazione
  Bug2: soglia sqrt(2) invece di 0.8  (costante geometrica Jitterbug)
  Bug3: load_h5_and_validate usa picco chi_max, non soglia percentuale

Usa la nomenclatura del repo ufficiale:
  - get_energy_triad()        (non compute_E_triad)
  - _peano_analyzer.E_psi_total (non E_Psi_accumulated)
  - classify_geometric_phase()  (funzione standalone)
  - GeometricPhase enum

ESECUZIONE:
    cd VQT_repo
    python -m wqt_oop.test_peano_vqt
================================================================================
"""

import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.energy_metrics import (
    EnergyTriad, PeanoVQTAnalyzer,
    GeometricPhase, classify_geometric_phase,
)


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def _make_solitone(N: int = 24, chi_init: float = 4.5, vel_init: float = 0.5,
                   screening: bool = False, chi_stable: float = None) -> SolitoneComposito:
    """Crea un SolitoneComposito L1 con N=24 figli."""
    from dataclasses import replace as dc_replace
    base0 = PhysicsContext.for_level(0)
    if chi_stable is not None:
        base0 = dc_replace(base0, chi_stable=chi_stable)
    physics = PhysicsContext.for_level(1, base_context=base0)

    segs = [
        SegmentoQuantistico(
            chi=chi_init + 0.1 * np.sin(2 * np.pi * i / N),
            vel=vel_init * np.cos(2 * np.pi * i / N),
            physics=base0,
        )
        for i in range(N)
    ]
    return SolitoneComposito(segs, physics, screening_enabled=screening)


def check(condition: bool, name: str, detail: str = "") -> bool:
    label = "PASS" if condition else "FAIL"
    msg = f"  [{label}] {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    return condition


# ---------------------------------------------------------------------------
# TEST 1: Soglia Jitterbug sqrt(2) installata correttamente
# ---------------------------------------------------------------------------

def test_jitterbug_threshold():
    print("\n--- TEST 1: Soglia Jitterbug sqrt(2) ---")
    sol = _make_solitone()
    all_pass = True

    threshold = sol._peano_analyzer.chi_saturation_threshold
    expected = np.sqrt(2)
    rel_err = abs(threshold - expected) / expected

    all_pass &= check(rel_err < 1e-10,
                      "chi_saturation_threshold == sqrt(2)",
                      f"val={threshold:.8f} expected={expected:.8f}")
    return all_pass


# ---------------------------------------------------------------------------
# TEST 2: Segnale chi_max in compute_hamiltonian_coupling
# ---------------------------------------------------------------------------

def test_chi_max_signal():
    """Verifica che la saturazione usata nel drain sia chi_max/chi_stable,
    NON chi_mean/chi_stable (Bug1 fix)."""
    print("\n--- TEST 2: Segnale chi_max nel drain ---")
    all_pass = True

    # Crea solitone con chi_stable=4.5 e chi che solo 1 figlio supera sqrt(2)*4.5
    chi_stable = 4.5
    chi_sat_threshold = chi_stable * np.sqrt(2)  # = 6.36

    from dataclasses import replace as dc_replace
    base0 = dc_replace(PhysicsContext.for_level(0), chi_stable=chi_stable)
    physics = PhysicsContext.for_level(1, base_context=base0)

    # 23 figli con chi=3.0 (< soglia), 1 figlio con chi=7.0 (> soglia)
    segs = [
        SegmentoQuantistico(chi=3.0, vel=0.1, physics=base0)
        for _ in range(23)
    ] + [
        SegmentoQuantistico(chi=7.0, vel=0.1, physics=base0)  # questo supera la soglia
    ]
    sol = SolitoneComposito(segs, physics, screening_enabled=False)

    # chi_mean = (23*3 + 7)/24 = 3.167 < chi_stable * 0.8 = 3.6  => drain OFF con vecchia logica
    # chi_max  = 7.0 > chi_stable * sqrt(2) = 6.36              => drain ON  con nuova logica
    chi_mean = (23 * 3.0 + 7.0) / 24
    chi_max  = 7.0
    all_pass &= check(chi_mean / chi_stable < np.sqrt(2),
                      "chi_mean/chi_stable < sqrt(2) (drain OFF con vecchia logica)",
                      f"ratio={chi_mean/chi_stable:.4f}")
    all_pass &= check(chi_max / chi_stable > np.sqrt(2),
                      "chi_max/chi_stable > sqrt(2) (drain ON con nuova logica)",
                      f"ratio={chi_max/chi_stable:.4f}")

    # Esegui compute_hamiltonian_coupling e verifica che drain sia scattato
    sol.compute_hamiltonian()
    E_psi_after = sol._peano_analyzer.E_psi_total
    all_pass &= check(E_psi_after > 0.0,
                      "E_Psi_total > 0 dopo compute_hamiltonian (drain attivo su chi_max)",
                      f"E_Psi={E_psi_after:.4e}")
    return all_pass


# ---------------------------------------------------------------------------
# TEST 3: get_energy_triad() restituisce EnergyTriad coerente
# ---------------------------------------------------------------------------

def test_get_energy_triad():
    print("\n--- TEST 3: get_energy_triad() ---")
    sol = _make_solitone(chi_init=4.5, vel_init=0.5)
    all_pass = True

    # Prima di compute_hamiltonian: triad = None
    triad_before = sol.get_energy_triad()
    all_pass &= check(triad_before is None,
                      "get_energy_triad() = None prima di compute_hamiltonian")

    # Dopo compute_hamiltonian
    sol.compute_hamiltonian()
    triad = sol.get_energy_triad()
    all_pass &= check(triad is not None,
                      "get_energy_triad() non-None dopo compute_hamiltonian")

    if triad is not None:
        all_pass &= check(np.isfinite(triad.E_chi),
                          "EnergyTriad.E_chi finito", f"E_chi={triad.E_chi:.4e}")
        all_pass &= check(np.isfinite(triad.E_RX),
                          "EnergyTriad.E_RX finito",  f"E_RX={triad.E_RX:.4e}")
        all_pass &= check(triad.E_Psi >= 0.0,
                          "EnergyTriad.E_Psi >= 0",   f"E_Psi={triad.E_Psi:.4e}")
        all_pass &= check(np.isfinite(triad.total),
                          "EnergyTriad.total finito",  f"total={triad.total:.4e}")
    return all_pass


# ---------------------------------------------------------------------------
# TEST 4: Conservazione dE_chi + dE_RX + dE_Psi = 0 durante drain
# ---------------------------------------------------------------------------

def test_drain_conservation():
    print("\n--- TEST 4: Conservazione Peano-VQT durante drain ---")
    all_pass = True

    analyzer = PeanoVQTAnalyzer(chi_saturation_threshold=np.sqrt(2), drain_rate=0.1)

    # Triade iniziale
    triad0 = analyzer.compute_triad(E_chi_raw=100.0, E_torsion=10.0, E_exchange=-2.0)
    total_before = triad0.total

    # Applica drain con saturazione sopra soglia
    chi_sat_above = np.sqrt(2) + 0.1  # > sqrt(2)
    triad1 = analyzer.apply_drain(triad0, chi_sat_above)
    total_after = triad1.total

    all_pass &= check(analyzer.E_psi_total > 0,
                      "Drain attivo: E_psi_total > 0 dopo apply_drain sopra soglia",
                      f"E_Psi={analyzer.E_psi_total:.4e}")
    all_pass &= check(
        abs(total_after - total_before) < 1e-9,
        "Conservazione: total_after == total_before (dE_chi+dE_RX+dE_Psi=0)",
        f"delta={abs(total_after - total_before):.2e}"
    )

    # Applica drain con saturazione SOTTO soglia: nessun drain
    analyzer2 = PeanoVQTAnalyzer(chi_saturation_threshold=np.sqrt(2), drain_rate=0.1)
    triad_sub = analyzer2.compute_triad(50.0, 5.0, -1.0)
    chi_sat_below = np.sqrt(2) - 0.1
    triad_sub2 = analyzer2.apply_drain(triad_sub, chi_sat_below)
    all_pass &= check(analyzer2.E_psi_total == 0.0,
                      "Nessun drain sotto soglia sqrt(2)",
                      f"E_Psi={analyzer2.E_psi_total:.4e}")

    # validate_peano_theorem
    report = analyzer.validate_peano_theorem()
    all_pass &= check(report['is_valid'],
                      "validate_peano_theorem(): invariante rispettato",
                      f"err={report['conservation_error']:.2e}")
    return all_pass


# ---------------------------------------------------------------------------
# TEST 5: classify_geometric_phase con soglie Jitterbug
# ---------------------------------------------------------------------------

def test_geometric_phase_classification():
    print("\n--- TEST 5: Classificazione fasi Jitterbug ---")
    all_pass = True
    sqrt2 = np.sqrt(2)

    cases = [
        (0.5,       "Ottaedrica",    "chi_sat < 1.0"),
        (0.99,      "Ottaedrica",    "chi_sat < 1.0"),
        (1.0,       "Cubottaedrica", "chi_sat == 1.0 (VE)"),
        (1.2,       "Cubottaedrica", "1.0 < chi_sat < sqrt(2)"),
        (sqrt2,     "Icosaedrica",   "chi_sat == sqrt(2) (Jitterbug)"),
        (sqrt2+0.1, "Icosaedrica",   "chi_sat > sqrt(2) (materia)"),
    ]
    for chi_sat, expected_phase, label in cases:
        phase = classify_geometric_phase(chi_sat)
        all_pass &= check(phase == expected_phase,
                          f"{label} -> {expected_phase}",
                          f"got={phase}")
    return all_pass


# ---------------------------------------------------------------------------
# TEST 6: Guard per-step: drain applicato solo 1 volta per step
# ---------------------------------------------------------------------------

def test_per_step_drain_guard():
    print("\n--- TEST 6: Guard per-step nel drain ---")
    all_pass = True

    sol = _make_solitone(chi_init=4.5, vel_init=0.5, chi_stable=4.5)

    # Chiama compute_hamiltonian 2 volte nello stesso step
    sol.compute_hamiltonian()
    E_psi_first = sol._peano_analyzer.E_psi_total
    n_events_first = len(sol._peano_analyzer.phase_events)

    sol.compute_hamiltonian()  # seconda chiamata, stesso step
    E_psi_second = sol._peano_analyzer.E_psi_total
    n_events_second = len(sol._peano_analyzer.phase_events)

    all_pass &= check(n_events_second == n_events_first,
                      "Seconda chiamata nello stesso step NON aggiunge eventi drain",
                      f"n_events: {n_events_first} -> {n_events_second}")
    return all_pass


# ---------------------------------------------------------------------------
# TEST 7: Backward compatibility Hamiltoniana
# ---------------------------------------------------------------------------

def test_backward_compatibility():
    print("\n--- TEST 7: Backward Compatibility ---")
    all_pass = True
    sol = _make_solitone(chi_init=4.5, vel_init=0.5)

    H0 = sol.compute_hamiltonian()
    all_pass &= check(np.isfinite(H0),
                      "compute_hamiltonian() finito", f"H={H0:.4e}")

    sol.evolve(dt=0.05)
    H1 = sol.compute_hamiltonian()
    all_pass &= check(np.isfinite(H1),
                      "compute_hamiltonian() finito dopo evolve", f"H={H1:.4e}")

    # chi_stable nel PhysicsContext
    physics = PhysicsContext.for_level(1)
    all_pass &= check(hasattr(physics, 'chi_stable'),
                      "PhysicsContext ha chi_stable",
                      f"val={physics.chi_stable}")

    # for_level con chi_mean_init
    physics2 = PhysicsContext.for_level(2, chi_mean_init=50.0)
    all_pass &= check(physics2.chi_stable == 50.0,
                      "for_level(chi_mean_init=50) -> chi_stable=50",
                      f"chi_stable={physics2.chi_stable}")
    return all_pass


# ---------------------------------------------------------------------------
# RUNNER
# ---------------------------------------------------------------------------

def run_all_tests():
    print("=" * 60)
    print("  TEST PEANO-VQT  (VQT_repo)")
    print("  Invariante: dE_chi + dE_RX + dE_Psi = 0")
    print("  Soglia Jitterbug: chi_max/chi_stable = sqrt(2)")
    print("=" * 60)

    tests = [
        ("Soglia Jitterbug sqrt(2)",        test_jitterbug_threshold),
        ("Segnale chi_max nel drain",        test_chi_max_signal),
        ("get_energy_triad()",               test_get_energy_triad),
        ("Conservazione drain",              test_drain_conservation),
        ("Classificazione fasi Jitterbug",   test_geometric_phase_classification),
        ("Guard per-step drain",             test_per_step_drain_guard),
        ("Backward Compatibility",           test_backward_compatibility),
    ]

    results = []
    t_start = time.time()

    for name, fn in tests:
        t0 = time.time()
        try:
            passed = fn()
        except Exception as exc:
            print(f"  [EXCEPTION] {exc}")
            passed = False
        results.append((name, passed, time.time() - t0))

    elapsed = time.time() - t_start

    print("\n" + "=" * 60)
    print("  RIEPILOGO")
    print("=" * 60)
    n_pass = sum(1 for _, p, _ in results if p)
    n_fail = len(results) - n_pass

    for name, passed, dt in results:
        label = "PASS" if passed else "FAIL"
        print(f"  [{label}]  {name:<40}  {dt:.2f}s")

    print("-" * 60)
    print(f"  {n_pass}/{len(results)} test superati  ({elapsed:.2f}s totale)")

    if n_fail == 0:
        print("\n  Costante Jitterbug sqrt(2): IMPLEMENTAZIONE VERIFICATA")
    else:
        print(f"\n  {n_fail} test falliti")

    return n_fail == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
