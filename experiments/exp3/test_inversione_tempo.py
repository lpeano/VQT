"""
================================================================================
TEST LUNGO: uno dei due tempi propri (materia SX / spazio DX) INVERTE?
================================================================================

Sul MOTORE COMPLETO (EC integrato: torsione dallo spin, 180/720, tempo proprio attivo).
I due tempi propri diagnostici accumulano  tau_sx += dt*f*rho_SX,  tau_dx += dt*f*rho_DX,
con f = 1 - <K2_spin>/rho* (proper_time_factor) e rho_SX/DX >= 0.

-> L'UNICA via per cui uno dei due INVERTE (incremento < 0) e' f < 0, cioe' K2_spin > rho*.
   Ma la saturazione EC (bounce) allinea gli spin dove K2 > rho* -> dovrebbe cap-parlo a rho*
   -> f >= 0 -> nessuna inversione. QUESTO TEST LO VERIFICA (non lo assume): traccia il
   MINIMO di f su tutti i blocchi e nel tempo, e segnala se un tempo proprio mai decresce.

Configurazione: materia forte (kink con overshoot) per stressare la torsione al massimo.

ESECUZIONE:  python experiments/exp3/test_inversione_tempo.py [--steps N] [--amp A]
================================================================================
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import argparse
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=800)
    ap.add_argument("--amp", type=float, default=2.0, help="ampiezza kink (in chi0): overshoot")
    ap.add_argument("--dt", type=float, default=0.02)
    args = ap.parse_args()

    np.random.seed(7)
    root = make(1, chi_mean=50, level=2)
    chi0 = root.physics.chi_stable
    blocks = _l1_blocks(root)
    amp = args.amp * chi0
    # meta' blocchi: PARETE con OVERSHOOT (kink sharp +amp/-amp) -> torsione massima.
    for j, b in enumerate(blocks):
        for i, leaf in enumerate(b.children):
            half = len(b.children) // 2
            leaf.chi = (amp if i < half else -amp) if j < len(blocks)//2 else chi0
            leaf.vel = 0.0
            leaf.tau_locale = 0.0; leaf.tau_sx = 0.0; leaf.tau_dx = 0.0
    root.set_ec_integrato(1e-3)

    print("=" * 74)
    print(f"  TEST DIREZIONE DEL TEMPO (motore completo): steps={args.steps} amp={args.amp}*chi0")
    print("  IPOTESI di Luca: tempo NETTO = tau_DX - tau_SX (spazio avanti, materia indietro)")
    print("  = integrale di f*cos(theta). Inverte dove la MATERIA domina (theta>pi/2 -> cos<0),")
    print("  mentre lo spazio attorno va avanti: i due si compensano nell'integrazione.")
    print("=" * 74)
    print(f"  {'step':>5} {'netto medio':>12} {'voxel indietro%':>16} {'voxel mat(theta>pi/2)%':>22}")

    leaves = [lf for b in blocks for lf in b.children]
    Ntot = len(leaves)
    for s in range(args.steps):
        root.compute_hamiltonian(); root.evolve_with_muratore(args.dt)
        root.measure_chirality_proper_time(args.dt)
        if s % max(1, args.steps // 12) == 0 or s == args.steps - 1:
            net = np.array([lf.tau_dx - lf.tau_sx for lf in leaves])   # tempo NETTO per voxel
            theta = np.array([lf.theta_spin for lf in leaves])
            back = float(np.mean(net < 0)) * 100.0                     # % voxel a tempo indietro
            matter = float(np.mean(theta > np.pi / 2)) * 100.0         # % voxel materia-dominati
            print(f"  {s:>5} {net.mean():>12.4f} {back:>15.1f}% {matter:>21.1f}%")

    net = np.array([lf.tau_dx - lf.tau_sx for lf in leaves])
    print()
    print(f"  tempo NETTO globale (somma) = {net.sum():.3f}  (>0 = freccia in avanti)")
    print(f"  voxel con tempo INDIETRO (netto<0, materia) = {int(np.sum(net<0))}/{Ntot}")
    print(f"  -> netto globale {'AVANTI' if net.sum()>0 else 'INDIETRO'}; alcuni voxel (materia)")
    print("     vanno indietro, lo spazio attorno avanti, l'integrazione da' la direzione.")
    print("     Inversione GLOBALE -> servirebbe un blocco materia-dominato (theta>pi/2 ovunque).")


if __name__ == "__main__":
    main()
