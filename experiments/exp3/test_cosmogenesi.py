"""
================================================================================
TASK 2: COSMOGENESI - universo da origine simmetrica + seme stocastico (i dadi)
================================================================================

IDEA DI LUCA: all'origine lo spazio e' strutturalmente NULLO (campo simmetrico chi~0,
il massimo instabile del doppio pozzo: nessuna materia, nessuna chiralita' rotta). Una
FLUTTUAZIONE stocastica (i "dadi" = il rumore) rompe la simmetria (SSB) -> il campo
rotola nei pozzi +-chi0 in domini -> pareti = kink (materia/torsione) -> il muratore
espande lo spazio dove la torsione si concentra. L'universo NASCE da una fluttuazione.

NON e' a=0 (singolare: 1/a^2 nel muratore). L'origine e' il campo SIMMETRICO + dadi;
l'espansione (a cresce da 1) e' la creazione di spazio mentre la struttura si forma.

OSSERVABILI nel tempo:
  - ordine = <|chi|>/chi0:  0 = simmetrico (origine);  ->1 = simmetria rotta (universo).
  - frac_rotta = frazione nodi con |chi| > chi0/2 (domini formati).
  - a_max, H_mean (espansione del muratore, get_expansion_state per livello).

PREVISIONE: simmetrico+dadi -> SSB (ordine 0->~1) -> struttura -> espansione (a>1) EMERGE.
Senza dadi (rumore->0) il campo resta sul massimo instabile: niente universo.
Magnitudine espansione ~beta_sat (lento, knob-free); la STRUTTURA e' il risultato.

ESECUZIONE:  python experiments/exp3/test_cosmogenesi.py
================================================================================
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from test_soglia_formazione import make
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


def _leaves(root):
    out = []
    def w(n):
        if isinstance(n, SegmentoQuantistico):
            out.append(n)
        else:
            for c in n.children:
                w(c)
    w(root); return out


def _set_symmetric_origin(root, noise, seed):
    """Origine: campo SIMMETRICO chi~0 + seme stocastico (i dadi). noise=ampiezza del
    rumore; noise->0 = nessun dado (massimo instabile, niente SSB)."""
    rng = np.random.default_rng(seed)
    for lf in _leaves(root):
        lf.chi = float(noise * rng.standard_normal())
        lf.vel = 0.0


def run(noise, level=2, steps=200, dt=0.02, seed=1):
    np.random.seed(seed)
    root = make(1, chi_mean=0, level=level)
    _set_symmetric_origin(root, noise, seed)
    root.set_muratore(True)
    chi0 = root.physics.chi_stable
    traj = []
    for s in range(steps):
        root.compute_hamiltonian(); root.evolve_with_muratore(dt)
        if s % max(1, steps // 10) == 0 or s == steps - 1:
            chi = np.array([lf.chi for lf in _leaves(root)])
            st = root.get_expansion_state()
            traj.append((s, float(np.mean(np.abs(chi))) / chi0,
                         float(np.mean(np.abs(chi) > chi0 / 2)),
                         st["a_max"], st["H_mean"]))
    return traj, root.get_expansion_state(), chi0


def main():
    print("=" * 74)
    print("  TASK 2: COSMOGENESI - origine simmetrica + dadi -> SSB + espansione?")
    print("=" * 74)
    for label, noise in [("CON dadi (rumore=2.0)", 2.0),
                         ("dadi minimi (rumore=0.1)", 0.1),
                         ("SENZA dadi (rumore=0)", 0.0)]:
        traj, st, chi0 = run(noise)
        print(f"\n  {label}:   chi0={chi0:.0f}")
        print(f"    {'step':>5} {'ordine<|chi|>/chi0':>18} {'frac_rotta':>11} "
              f"{'a_max':>10} {'H_mean':>10}")
        for s, order, frac, amax, hmean in traj:
            print(f"    {s:>5} {order:>18.3f} {frac:>11.3f} {amax:>10.6f} {hmean:>10.2e}")
        order_peak = max(t[1] for t in traj)      # picco (l'ordine OSCILLA, no ultimo)
        amax_f = traj[-1][3]
        ssb = order_peak > 0.5
        exp = amax_f > 1.0
        print(f"    -> SSB (ordine PICCO={order_peak:.2f} ->1) {'SI' if ssb else 'NO'};  "
              f"espansione (a>1) {'SI' if exp else 'NO'} (a cricca su mentre l'ordine respira)")
    print("\n  LETTURA: con i dadi -> SSB (ordine 0->~1, domini) -> struttura -> il")
    print("  muratore espande (a>1). Senza dadi -> resta simmetrico (niente universo).")
    print("  L'universo NASCE da una fluttuazione. Magnitudine espansione ~beta_sat.")


if __name__ == "__main__":
    main()
