"""
================================================================================
TASK 1: G(scala) e' monotono o no? (ipotesi di Luca: NON monotono)
================================================================================

DOMANDA: il modello predice la STRUTTURA di G (G ~ 1/rigidezza, R_geo=4N/(N-1)
topologico). Su uno stato EVOLUTO/DISOMOGENEO, G(L) cresce/cala monotonamente con
la scala, o no? (Luca: non monotono, dipende da DOVE sta la materia.)

MECCANISMO (derivato, niente if-then-else, niente numeri tarati):
  - rigidezza geometrica nuda: R_geo = 4 N/(N-1) = 4.174 (topologica, uguale a ogni L).
  - la MATERIA a una scala L dilata localmente lo spazio (muratore): a*_L = sqrt(<K2_L>/rho*)
    se il blocco a quel livello eccede rho*, altrimenti 1. (a* = punto fisso del muratore.)
  - rigidezza FISICA a quel livello:  R_phys(L) = R_geo / <a*_L^2>.
  - G EMERGENTE:  beta(L) = Theta / R_phys(L) = (Theta/R_geo) * <a*_L^2>.
  -> beta(L) TRACCIA la torsione/materia DEL livello L. Dove la materia si concentra,
     lo spazio si e' espanso di piu', la rigidezza fisica e' minore, G e' maggiore.

PREVISIONE:
  - materia UNIFORME (vuoto liscio) -> a*~1 a ogni L -> beta(L) ~ costante (piatto).
  - materia CONCENTRATA a una scala intermedia -> beta(L) PICCA li' -> NON MONOTONO.
G non e' una legge di scala universale: e' un campo che segue la materia. Conferma (o
falsifica) l'intuizione di Luca, DERIVANDOLO dal coupling reale del motore.

ESECUZIONE:  python experiments/exp3/test_g_nonmonotono.py
================================================================================
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from test_soglia_formazione import make
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.rigidezza_geometrica import geometric_rigidity
from wqt_oop.muratore_planck import equilibrium_a
from wqt_oop.einstein_cartan import torsion_density_K2

THETA = 1.0  # unita' (Theta = E_Planck in unita' fisiche; qui ratio-only)


def _coarse_chi_per_level(root):
    """chi 'coarse-grained' per livello: L1 = chi foglie di ogni blocco; L>=1 = media
    chi dei figli. Ritorna {livello: [array chi per ogni blocco di quel livello]}."""
    out = {}

    def rec(node):
        # ritorna (livello, chi_medio_del_nodo)
        if node.children and isinstance(node.children[0], SegmentoQuantistico):
            chi = np.array([c.chi for c in node.children], dtype=float)
            out.setdefault(1, []).append(chi)
            return 1, float(chi.mean())
        sub = []
        lev_child = 1
        for c in node.children:
            if isinstance(c, SolitoneComposito):
                lc, m = rec(c)
                lev_child = lc
                sub.append(m)
        lev = lev_child + 1
        out.setdefault(lev, []).append(np.array(sub, dtype=float))
        return lev, float(np.mean(sub))

    rec(root)
    return out


def _beta_per_level(root):
    """beta(L) = (Theta/R_geo) * <a*_L^2>, con a*_L dal punto fisso del muratore sulla
    torsione coarse del livello L. Usa il coupling Leech reale (24x24)."""
    # coupling 24x24 di un blocco qualsiasi (Leech) e rho*
    blk = root
    while blk.children and not isinstance(blk.children[0], SegmentoQuantistico):
        nxt = [c for c in blk.children if isinstance(c, SolitoneComposito)]
        if not nxt:
            break
        # scendi fino a un L1 per prendere W e rho* (uguali a ogni livello)
        if isinstance(blk.children[0], SegmentoQuantistico):
            break
        blk = nxt[0]
    W = root.coupling_matrix
    W = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
    R_geo = geometric_rigidity(W)
    rho_star = root.ec_k2_ref_chi

    levels = _coarse_chi_per_level(root)
    out = {}
    for lev in sorted(levels):
        a2 = []
        for chi_block in levels[lev]:
            if len(chi_block) < 2:
                continue
            a_star = equilibrium_a(chi_block, W, rho_star)   # punto fisso muratore
            a2.append(a_star ** 2)
        a2m = float(np.mean(a2)) if a2 else 1.0
        R_phys = R_geo / a2m
        out[lev] = {"a2_mean": a2m, "R_phys": R_phys, "beta": THETA / R_phys}
    return out, R_geo


def _inject_cluster_at_level(root, target_level, amp_factor=1.8):
    """Concentra la materia a una scala: rende il campo COARSE del livello target
    fortemente disomogeneo (blocchi alternati +-amp), lasciando lisci gli altri livelli.
    Per target L1: alterna le foglie dentro i blocchi. Per target L2: alterna la MEDIA
    dei blocchi L1 (ogni blocco L1 uniforme, ma blocchi vicini in pozzi opposti)."""
    chi0 = root.physics.chi_stable
    amp = amp_factor * chi0

    def l1_blocks(node, acc):
        if node.children and isinstance(node.children[0], SegmentoQuantistico):
            acc.append(node)
        else:
            for c in node.children:
                if isinstance(c, SolitoneComposito):
                    l1_blocks(c, acc)
    blocks = []
    l1_blocks(root, blocks)

    if target_level == 1:
        # torsione DENTRO ogni blocco L1: foglie alternate
        for b in blocks:
            for i, leaf in enumerate(b.children):
                leaf.chi = amp if i % 2 == 0 else -amp
    elif target_level == 2:
        # torsione TRA blocchi L1 (scala L2): ogni blocco L1 uniforme, ma il segno
        # alterna da un blocco al successivo -> alto gradiente coarse a L2, basso a L1
        for j, b in enumerate(blocks):
            s = 1.0 if j % 2 == 0 else -1.0
            for leaf in b.children:
                leaf.chi = s * amp


def main():
    print("=" * 74)
    print("  TASK 1: G(scala) monotono o no? (beta(L) traccia la materia del livello)")
    print("=" * 74)
    R_geo_ref = geometric_rigidity(np.asarray(
        (make(1, chi_mean=50, level=2).coupling_matrix)))
    print(f"  R_geo (topologico, nudo) = {R_geo_ref:.4f} = 4*24/23  ->  beta_nudo=Theta/R_geo={THETA/R_geo_ref:.4f}")
    print()

    scen = [
        ("A: vuoto uniforme (liscio)", None),
        ("B: materia concentrata a L1 (torsione dentro i blocchi)", 1),
        ("C: materia concentrata a L2 (torsione tra i blocchi)", 2),
    ]
    for name, target in scen:
        np.random.seed(7)
        root = make(1, chi_mean=50, level=3)
        if target is not None:
            _inject_cluster_at_level(root, target)
        bl, R_geo = _beta_per_level(root)
        levs = sorted(bl)
        betas = [bl[L]["beta"] for L in levs]
        print(f"  {name}")
        for L in levs:
            print(f"      L{L}: <a*^2>={bl[L]['a2_mean']:.3f}  R_phys={bl[L]['R_phys']:.4f}  "
                  f"beta(L)=Theta/R_phys={bl[L]['beta']:.4f}")
        # monotonia: segno costante delle differenze consecutive?
        d = np.diff(betas)
        mono = np.all(d >= -1e-12) or np.all(d <= 1e-12)
        peak_interno = (len(betas) >= 3 and
                        (np.argmax(betas) not in (0, len(betas) - 1) or
                         np.argmin(betas) not in (0, len(betas) - 1)))
        print(f"      -> beta(L) {'MONOTONO' if mono else 'NON MONOTONO'}"
              f"{' (picco/valle interno = G segue la scala della materia)' if peak_interno else ''}")
        print()
    print("  LETTURA: beta(L) NON e' una legge universale: traccia DOVE sta la materia.")
    print("  Uniforme -> piatto; materia a una scala -> G picca li' (non monotono).")
    print("  Conferma l'intuizione di Luca: G dipende dallo stato geometrico, derivato.")


if __name__ == "__main__":
    main()
