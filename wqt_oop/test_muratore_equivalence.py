"""
GATE Muratore di Planck: l'espansione additiva NON tocca il legacy + si auto-regola.

Test:
  1. muratore_planck: il feedback converge al punto fisso (a*, H->0) KNOB-FREE.
  2. GATE A/B: evolve_with_muratore(flag OFF) == evolve() bit-identico (stesso seed).
  3. Auto-regolazione nel tree: muratore ON su un blocco con difetto -> a cresce,
     stabile (no NaN), a>=1, la densita' fisica scende verso rho* (espansione reale).

ESECUZIONE:
  cd VQT_repo
  python -m wqt_oop.test_muratore_equivalence
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


def test_modulo_muratore():
    from wqt_oop import muratore_planck as mp
    assert mp._self_test(), "muratore: il feedback NON converge al punto fisso (a*, H->0)"
    print("  [1] modulo muratore: auto-regolazione knob-free (a->a*, H->0) -> PASS")


def test_gate_ab_off():
    from test_soglia_formazione import make
    np.random.seed(7)
    a = make(1, chi_mean=72, level=2)
    for _ in range(40):
        a.compute_hamiltonian(); a.evolve(0.01)
    np.random.seed(7)
    b = make(1, chi_mean=72, level=2)            # muratore + ec OFF (default)
    for _ in range(40):
        b.compute_hamiltonian(); b.evolve_with_muratore(0.01)
    d = float(np.max(np.abs(_leaves_chi(a) - _leaves_chi(b))))
    assert d == 0.0, f"flag OFF NON identico al legacy: max|dchi|={d:.3e}"
    print(f"  [2] GATE A/B: muratore OFF == legacy bit-identico (diff={d:.1e}) -> PASS")


def test_autoregolazione_on():
    from test_soglia_formazione import make
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    from wqt_oop.solitone_composito import SolitoneComposito
    np.random.seed(42)
    c = make(1, chi_mean=50, level=2)
    # Inietta un DIFETTO in un blocco L1 (kink: pozzi alternati +-chi0) -> torsione
    # concentrata K2 > rho* -> il muratore DEVE espandere quel blocco. (In un campo
    # liscio K2 < rho* e il muratore correttamente non espande: testato off-path.)
    def first_l1(node):
        if node.children and isinstance(node.children[0], SegmentoQuantistico):
            return node
        for ch in node.children:
            if isinstance(ch, SolitoneComposito):
                r = first_l1(ch)
                if r is not None:
                    return r
        return None
    blk = first_l1(c)
    # ampiezza con OVERSHOOT (1.8*chi0): con W normalizzata per riga K2 e' una media
    # pesata dei salti^2, e supera rho*=(2chi0)^2 solo oltre i pozzi -> difetto forte.
    amp = 1.8 * c.physics.chi_stable
    for i, leaf in enumerate(blk.children):
        leaf.chi = amp if (i % 2 == 0) else -amp     # kink alternato con overshoot
    c.set_muratore(True)                          # abilita muratore (+ EC come sorgente)
    a0 = c.get_expansion_state()["a_max"]
    for _ in range(80):
        c.compute_hamiltonian(); c.evolve_with_muratore(0.05)
    st = c.get_expansion_state()
    chi = _leaves_chi(c)
    assert not np.any(np.isnan(chi)), "muratore ON: NaN nel campo"
    assert np.abs(chi).max() < 1e4, f"muratore ON: esplosione |chi|max={np.abs(chi).max():.2e}"
    assert st["a_mean"] >= 1.0, f"a medio < 1 (lo spazio non deve contrarsi): {st['a_mean']}"
    assert st["a_max"] > a0, "nessun blocco ha espanso: il muratore non agisce"
    print(f"  [3] muratore ON: a_mean={st['a_mean']:.4f} a_max={st['a_max']:.4f} "
          f"voxel_tot={st['voxel_total']:.1f} H_mean={st['H_mean']:.2e} "
          f"|chi|max={np.abs(chi).max():.1f} -> PASS")


def test_g_emergente_stabile():
    """G emergente attiva (beta <- rigidezza fisica = beta_baseline*a^2): il feedback
    espansione->G->espansione e' STABILE (no runaway), regolato dalla diluizione ~1/a^2."""
    from test_soglia_formazione import make
    np.random.seed(42)
    c = make(1, chi_mean=50, level=2)
    blk = None
    def f(n):
        nonlocal blk
        from wqt_oop.segmento_quantistico import SegmentoQuantistico
        if n.children and isinstance(n.children[0], SegmentoQuantistico):
            blk = blk or n
        else:
            for ch in n.children:
                f(ch)
    f(c)
    amp = 1.8 * c.physics.chi_stable
    for i, leaf in enumerate(blk.children):
        leaf.chi = amp if i % 2 == 0 else -amp
    c.set_g_emergent(True)                         # beta ~ a^2 + muratore
    for _ in range(200):
        c.compute_hamiltonian(); c.evolve_with_muratore(0.02)
    st = c.get_expansion_state(); chi = _leaves_chi(c)
    assert not np.any(np.isnan(chi)), "G emergente ON: NaN"
    assert np.abs(chi).max() < 1e4, f"G emergente ON: runaway |chi|max={np.abs(chi).max():.2e}"
    assert st["a_max"] < 10.0, f"G emergente ON: runaway a_max={st['a_max']:.2e}"
    print(f"  [4] G emergente ON stabile (no runaway): a_max={st['a_max']:.6f} "
          f"beta_eff~beta0*a^2 |chi|max={np.abs(chi).max():.1f} -> PASS")


def main():
    print("=" * 60)
    print("  GATE MURATORE DI PLANCK (additivita' + auto-regolazione)")
    print("=" * 60)
    test_modulo_muratore()
    test_gate_ab_off()
    test_autoregolazione_on()
    test_g_emergente_stabile()
    print("  TUTTI I TEST PASS")


if __name__ == "__main__":
    main()
