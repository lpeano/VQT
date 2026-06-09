"""
GATE Einstein-Cartan: la dinamica EC additiva NON deve toccare il legacy.

Test:
  1. einstein_cartan: forze = gradiente conservativo (vs numerico) + twist limitati.
  2. GATE A/B: evolve_with_ec(flag OFF) == evolve() bit-identico (stesso seed).
  3. Stabilita': evolve_with_ec(flag ON) non produce NaN/esplosioni.

ESECUZIONE:
  cd VQT_repo
  python -m wqt_oop.test_einstein_cartan_equivalence
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "experiments", "exp3"))
import numpy as np


def _leaves_chi(root):
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    out = []
    def w(n):
        if isinstance(n, SegmentoQuantistico):
            out.append(n.chi)
        else:
            for c in n.children:
                w(c)
    w(root)
    return np.array(out)


def test_modulo_gradiente():
    from wqt_oop import einstein_cartan as ec
    ok = ec._self_test()
    assert ok, "einstein_cartan: gradiente NON conservativo o forza chiusura nulla"
    print("  [1] modulo EC: gradiente conservativo + chiusura -> PASS")


def test_gate_ab_flag_off():
    from test_soglia_formazione import make
    np.random.seed(7)
    a = make(1, chi_mean=72, level=2)
    for _ in range(40):
        a.compute_hamiltonian(); a.evolve(0.01)
    np.random.seed(7)
    b = make(1, chi_mean=72, level=2)        # ec_dynamics_enabled = False (default)
    for _ in range(40):
        b.compute_hamiltonian(); b.evolve_with_ec(0.01)
    d = float(np.max(np.abs(_leaves_chi(a) - _leaves_chi(b))))
    assert d == 0.0, f"flag OFF NON identico al legacy: max|dchi|={d:.3e}"
    print(f"  [2] GATE A/B: flag OFF == legacy bit-identico (diff={d:.1e}) -> PASS")


def test_stabilita_flag_on():
    from test_soglia_formazione import make
    np.random.seed(42)
    c = make(1, chi_mean=72, level=2)
    c.set_ec_dynamics(True)
    for _ in range(60):
        c.compute_hamiltonian(); c.evolve_with_ec(0.01)
    chi = _leaves_chi(c)
    assert not np.any(np.isnan(chi)), "EC ON: NaN nel campo"
    assert np.abs(chi).max() < 1e4, f"EC ON: esplosione |chi|max={np.abs(chi).max():.2e}"
    print(f"  [3] EC ON stabile: no NaN, |chi|max={np.abs(chi).max():.1f} -> PASS")


def main():
    print("=" * 60)
    print("  GATE EINSTEIN-CARTAN (additivita' + stabilita')")
    print("=" * 60)
    test_modulo_gradiente()
    test_gate_ab_flag_off()
    test_stabilita_flag_on()
    print("  TUTTI I TEST PASS")


if __name__ == "__main__":
    main()
