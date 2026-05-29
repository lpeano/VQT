"""
test_peano_integration.py
=========================
Verifica integrazione Peano-VQT:
  1. Drain conserva dE_chi + dE_RX + dE_Psi = 0
  2. Nessun drain sotto la soglia di saturazione
  3. SolitoneComposito espone correttamente la triade
  4. Guard per-step previene double-drain in evolve()
"""

import sys
import os
import numpy as np

# Path setup per esecuzione diretta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wqt_oop.energy_metrics import PeanoVQTAnalyzer, EnergyTriad
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _make_l1_soliton(chi_mean: float = 50.0, chi_spread: float = 5.0) -> SolitoneComposito:
    """Crea un SolitoneComposito L1 con 24 figli di test."""
    rng = np.random.default_rng(42)
    physics_L0 = PhysicsContext(level=0, length_scale=1.616255e-35, chi_stable=50.0)
    physics_L1 = PhysicsContext.for_level(1)

    children = [
        SegmentoQuantistico(
            chi=chi_mean + rng.uniform(-chi_spread, chi_spread),
            vel=rng.uniform(-0.5, 0.5),
            physics=physics_L0,
        )
        for _ in range(24)
    ]
    return SolitoneComposito(children, physics_L1, screening_enabled=False)


# -----------------------------------------------------------------------
# Test 1: drain conserva la somma della triade
# -----------------------------------------------------------------------

def test_drain_conservation():
    print("[1] Verifica drain conservation...")
    analyzer = PeanoVQTAnalyzer(chi_saturation_threshold=0.5, drain_rate=0.2)

    triad_before = analyzer.compute_triad(
        E_chi_raw=100.0,
        E_torsion=10.0,
        E_exchange=-5.0,
    )
    total_before = triad_before.total

    # saturazione > soglia → deve avvenire drain
    triad_after = analyzer.apply_drain(triad_before, chi_saturation=0.9)
    total_after = triad_after.total

    assert abs(total_after - total_before) < 1e-10, (
        f"Invariante violato: Δtotal = {total_after - total_before:.2e}"
    )
    assert triad_after.E_chi < triad_before.E_chi, "E_chi deve diminuire"
    assert triad_after.E_Psi > triad_before.E_Psi, "E_Psi deve aumentare"
    assert triad_after.E_RX == triad_before.E_RX, "E_RX deve restare invariato"

    drain = triad_before.E_chi - triad_after.E_chi
    print(f"  total_before = {total_before:.6f}")
    print(f"  total_after  = {total_after:.6f}")
    print(f"  drain        = {drain:.6f}")
    assert PeanoVQTAnalyzer.verify_drain_conservation(triad_before, triad_after), \
        "verify_drain_conservation deve ritornare True"
    print("  [PASS]")


# -----------------------------------------------------------------------
# Test 2: nessun drain sotto soglia
# -----------------------------------------------------------------------

def test_no_drain_below_threshold():
    print("[2] Verifica no-drain sotto soglia...")
    analyzer = PeanoVQTAnalyzer(chi_saturation_threshold=0.8, drain_rate=0.1)
    triad_before = analyzer.compute_triad(50.0, 5.0, -2.0)

    triad_after = analyzer.apply_drain(triad_before, chi_saturation=0.3)

    assert triad_after.E_chi == triad_before.E_chi, "E_chi non deve cambiare"
    assert triad_after.E_Psi == 0.0, "E_Psi deve restare 0"
    assert len(analyzer.phase_events) == 0, "Nessun evento deve essere registrato"
    print("  [PASS]")


# -----------------------------------------------------------------------
# Test 3: SolitoneComposito espone la triade correttamente
# -----------------------------------------------------------------------

def test_solitone_composito_triad():
    print("[3] Verifica SolitoneComposito triad...")
    soliton = _make_l1_soliton()

    # Prima di qualsiasi chiamata
    assert soliton.get_energy_triad() is None, \
        "Triade deve essere None prima di compute_hamiltonian_coupling"

    H_coup = soliton.compute_hamiltonian_coupling()
    assert isinstance(H_coup, float), "compute_hamiltonian_coupling deve restituire float"

    triad = soliton.get_energy_triad()
    assert triad is not None, "_last_triad deve essere settata"
    assert isinstance(triad, EnergyTriad), "Tipo atteso: EnergyTriad"

    # Per costruzione: triad.total = E_chi_raw + E_RX = H_coup
    # (il drain sposta energia da E_chi a E_Psi, la somma totale è invariata)
    assert abs(triad.total - H_coup) < 1e-6 * max(abs(H_coup), 1.0), (
        f"Triade non coerente: triad.total={triad.total:.4e}, H_coup={H_coup:.4e}"
    )

    # Budget energetico include la triade
    budget = soliton.get_energy_budget()
    for key in ('E_chi', 'E_RX', 'E_Psi'):
        assert key in budget, f"Budget manca '{key}'"

    print(f"  H_coupling = {H_coup:.4e}")
    print(f"  E_chi = {triad.E_chi:.4e}, E_RX = {triad.E_RX:.4e}, E_Psi = {triad.E_Psi:.4e}")
    print("  [PASS]")


# -----------------------------------------------------------------------
# Test 4: guard per-step previene double-drain
# -----------------------------------------------------------------------

def test_guard_prevents_double_drain():
    print("[4] Verifica guard per-step (no double-drain)...")
    soliton = _make_l1_soliton(chi_mean=50.0)

    # Prima chiamata nello stesso step (simula H_before)
    soliton.compute_hamiltonian_coupling()
    E_psi_after_first = soliton._peano_analyzer.E_psi_total

    # Seconda chiamata nello stesso step (simula H_after in evolve)
    soliton.compute_hamiltonian_coupling()
    E_psi_after_second = soliton._peano_analyzer.E_psi_total

    assert E_psi_after_first == E_psi_after_second, (
        f"Double-drain rilevato: E_Psi prima={E_psi_after_first:.4e}, "
        f"dopo={E_psi_after_second:.4e}"
    )
    print(f"  E_Psi stabile a {E_psi_after_first:.4e} su due chiamate")
    print("  [PASS]")


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  TEST INTEGRAZIONE PEANO-VQT")
    print("=" * 60 + "\n")

    test_drain_conservation()
    test_no_drain_below_threshold()
    test_solitone_composito_triad()
    test_guard_prevents_double_drain()

    print("\n" + "=" * 60)
    print("  TUTTI I TEST PASSATI")
    print("=" * 60 + "\n")
