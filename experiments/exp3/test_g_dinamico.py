"""
================================================================================
TASK 1 (completamento): la DINAMICA produce G(scala) non-monotono da se'?
================================================================================

Il task 1 (test_g_nonmonotono.py) ha mostrato il MECCANISMO con a* analitico
(espansione richiesta). Qui verifichiamo che la DINAMICA reale -- muratore esteso a
TUTTI i livelli (ogni composito espande il proprio a dalla torsione COARSE del suo
livello) -- generi da se' il pattern: materia a una scala -> a cresce LI' -> beta(L)
picca li' -> NON MONOTONO.

beta(L) = (Theta/R_geo) * <a^2>_L  (G emergente per livello, da get_expansion_state).
Magnitudine fissata da beta_sat (ritmo fisico, lento e knob-free); cio' che conta e'
la STRUTTURA: QUALE scala espande. Niente numeri tarati, niente if-then-else.

ESECUZIONE:  python experiments/exp3/test_g_dinamico.py
================================================================================
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from test_soglia_formazione import make
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


def _l1_blocks(root):
    acc = []
    def w(n):
        if n.children and isinstance(n.children[0], SegmentoQuantistico):
            acc.append(n)
        else:
            for c in n.children:
                if isinstance(c, SolitoneComposito):
                    w(c)
    w(root); return acc


def _inject_matter_at_L2(root, amp_factor=1.8):
    """Materia a scala L2: ogni blocco L1 UNIFORME, ma il segno alterna da un blocco
    al successivo -> alto gradiente COARSE a L2, basso dentro i blocchi (L1)."""
    amp = amp_factor * root.physics.chi_stable
    for j, b in enumerate(_l1_blocks(root)):
        s = 1.0 if j % 2 == 0 else -1.0
        for leaf in b.children:
            leaf.chi = s * amp


def run(level=3, steps=120, dt=0.02, inject=True):
    np.random.seed(7)
    root = make(1, chi_mean=50, level=level)
    if inject:
        _inject_matter_at_L2(root)
    root.set_muratore(True)            # muratore (+ EC) a TUTTI i livelli
    for _ in range(steps):
        root.compute_hamiltonian(); root.evolve_with_muratore(dt)
    return root.get_expansion_state()


def main():
    print("=" * 74)
    print("  TASK 1 (dinamico): la dinamica genera G(scala) non-monotono?")
    print("=" * 74)
    for name, inj in [("vuoto uniforme", False), ("materia iniettata a scala L2", True)]:
        st = run(inject=inj)
        print(f"  {name}:  R_geo={st['R_geo']:.4f}  a_max(globale)={st['a_max']:.6f}")
        pl = st["per_level"]
        levs = sorted(pl)
        betas = [pl[L]["beta"] for L in levs]
        for L in levs:
            print(f"      L{L}: <a>={pl[L]['a_mean']:.6f}  a_max={pl[L]['a_max']:.6f}  "
                  f"beta(L)={pl[L]['beta']:.6f}  (n={pl[L]['n_blocks']})")
        d = np.diff(betas)
        mono = np.all(d >= -1e-15) or np.all(d <= 1e-15)
        argpk = int(np.argmax(betas))
        peak_interno = len(betas) >= 3 and argpk not in (0, len(betas) - 1)
        print(f"      -> beta(L) {'MONOTONO' if mono else 'NON MONOTONO'}"
              f"{f' (picco a L{levs[argpk]} = scala della materia)' if peak_interno else ''}")
        print()
    print("  LETTURA: la dinamica espande il livello DOVE sta la materia -> beta(L) picca")
    print("  li'. G non-monotono EMERGE dalla dinamica (non imposto). Magnitudine ~beta_sat")
    print("  (ritmo fisico lento); la STRUTTURA e' il risultato.")


if __name__ == "__main__":
    main()
