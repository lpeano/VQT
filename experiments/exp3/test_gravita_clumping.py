"""
================================================================================
GRAVITA' EMERGENTE: i kink irrigidiscono -> i vuoti espandono -> la materia si addensa?
================================================================================

Idea di Luca: la materia (kink) irrigidisce lo spaziotempo (R_local=R_geo(1+K2/rho*)),
quindi l'espansione e' SOPPRESSA dove c'e' materia e i VUOTI espandono -> la materia si
addensa (grumi). La spinta (frame spaziotempo) = attrazione (frame materia).

TEST: blocchi DENSI (kink, alta torsione) vs VUOTI (lisci), 3 regimi:
  - muratore puro;
  - + G emergente (beta~a^2);
  - + kink-stiffening (beta /= 1+K2/rho*).
Misura il fattore di scala a per blocco denso vs vuoto.

NOTA ONESTA (verificata qui): il muratore attuale sorgenta l'espansione dall'ECCESSO
DI TORSIONE LOCALE (H ~ (K2-rho*)+), che e' ALTO sulla materia e ZERO nei vuoti. Quindi
il kink-stiffening RALLENTA l'espansione dei blocchi densi (conferma "denso->lento" di
Gemini) ma NON fa espandere i vuoti (non hanno torsione da scaricare). Per il clumping
'gravitazionale' (vuoti che espandono e spingono la materia) servirebbe un DRIVE di
fondo (l'emissione continua di voxel del muratore di Planck) modulato dalla rigidezza:
e' il pezzo mancante, identificato da questo test.

ESECUZIONE:  python experiments/exp3/test_gravita_clumping.py
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


def run(regime, n_dense=4, steps=150, dt=0.02):
    np.random.seed(7)
    root = make(1, chi_mean=50, level=2)
    blocks = _l1_blocks(root)
    amp = 1.8 * root.physics.chi_stable
    # primi n_dense blocchi DENSI (kink), il resto VUOTO (liscio a chi0)
    for j, b in enumerate(blocks):
        for i, leaf in enumerate(b.children):
            leaf.chi = (amp if i % 2 == 0 else -amp) if j < n_dense else root.physics.chi_stable
    if regime == "muratore":
        root.set_muratore(True)
    elif regime == "g_emergent":
        root.set_g_emergent(True)
    elif regime == "kink_stiff":
        root.set_kink_stiffening(True)
    for _ in range(steps):
        root.compute_hamiltonian(); root.evolve_with_muratore(dt)
    a = np.array([b.scale_factor_a for b in blocks])
    return float(a[:n_dense].mean()), float(a[n_dense:].mean())


def main():
    print("=" * 74)
    print("  GRAVITA' EMERGENTE: a(denso) vs a(vuoto) nei 3 regimi")
    print("=" * 74)
    print(f"  {'regime':>14} | {'a DENSO (materia)':>18} | {'a VUOTO':>12}")
    for reg in ["muratore", "g_emergent", "kink_stiff"]:
        ad, av = run(reg)
        print(f"  {reg:>14} | {ad:>18.6f} | {av:>12.6f}")
    print()
    print("  ATTESO: kink_stiff RALLENTA a(denso) vs g_emergent (denso->rigido->lento,")
    print("  conferma Gemini). MA a(vuoto)~1 in tutti (i vuoti non hanno torsione da")
    print("  scaricare) -> il clumping 'gravitazionale' richiede un DRIVE di fondo")
    print("  (emissione Planck) modulato dalla rigidezza: PEZZO MANCANTE.")


if __name__ == "__main__":
    main()
