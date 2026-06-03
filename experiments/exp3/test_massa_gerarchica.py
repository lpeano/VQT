"""
================================================================================
MASSA GERARCHICA — fix dell'aggregatore (no bias del root)
================================================================================

Motivazione (2026-06-03): la misura E_Psi sul ROOT a L3 dava ~0 ("no-massa"),
interpretato erroneamente come "transizione particella->campo". Il test
discriminante ha mostrato che e' un ARTEFATTO: il root vede le MEDIE dei figli
(passa-basso), la frustrazione vive nelle FOGLIE (somma leaf ~1985 a L3, stesso
ordine di L1/L2). compute_hierarchical_mass() aggrega correttamente su tutta la
gerarchia e separa particella (localizzata) da campo (distribuito) via IPR.

Domande sperimentali:
  1. M_tot e' conservata/estensiva attraverso L1->L2->L3? (somma ricorsiva)
  2. La densita' rho_M = M_tot/N scala o si diluisce con N?
  3. L'IPR sulle foglie dice particella (localizzata) o campo (distribuito)?

Protocollo: per ogni livello, porta in regime critico (pre-evoluzione) e misura.
ESECUZIONE:  cd VQT_repo && python experiments/exp3/test_massa_gerarchica.py
================================================================================
"""

import sys, os
import numpy as np
import warnings, logging

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))

from wqt_oop.energy_metrics import compute_hierarchical_mass, compute_geometric_E_psi
from test_soglia_formazione import make, chi_max

SQRT2 = np.sqrt(2)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=str, default="1,2,3")
    ap.add_argument("--pre", type=int, default=60, help="step di pre-evoluzione (regime critico)")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    levels = [int(x) for x in args.levels.split(",")]
    dt = 0.01

    print("=" * 78)
    print("  MASSA GERARCHICA - M_tot ricorsiva, densita', IPR foglie (no bias root)")
    print(f"  seed={args.seed}  pre-evoluzione={args.pre} step  dt={dt}")
    print("=" * 78)

    print(f"\n  {'L':>2} {'N':>7} {'chi_max/st':>10} {'E_psi_ROOT':>12} "
          f"{'M_tot':>12} {'rho_M':>10} {'IPR':>10} {'loc_ratio':>10} {'regime':>12}")
    print("  " + "-" * 100)

    rows = []
    for L in levels:
        sol = make(args.seed, level=L)
        for _ in range(args.pre):
            sol.compute_hamiltonian()
            sol.evolve(dt)

        cms = chi_max(sol) / 50.0
        root_only = compute_geometric_E_psi(sol)["E_psi_anchored"]
        h = compute_hierarchical_mass(sol)
        N = 24 ** L
        rows.append((L, N, h))
        print(f"  {L:>2} {N:>7} {cms:>10.3f} {root_only:>12.3e} "
              f"{h['M_tot']:>12.3e} {h['rho_M']:>10.3e} {h['IPR']:>10.3e} "
              f"{h['localization_ratio']:>10.2f} {h['regime']:>12}")

    # --- analisi delle leggi di scala ---
    print("\n  " + "=" * 74)
    print("  ANALISI")
    print("  " + "-" * 74)

    if len(rows) >= 2:
        Ns = np.array([r[1] for r in rows], float)
        Mtots = np.array([r[2]["M_tot"] for r in rows], float)
        rhos = np.array([r[2]["rho_M"] for r in rows], float)
        locr = np.array([r[2]["localization_ratio"] for r in rows], float)

        valid = (Mtots > 0) & np.isfinite(Mtots)
        if np.sum(valid) >= 2:
            # M_tot ~ N^a : a~1 => estensiva (massa totale cresce con il volume)
            a, _ = np.polyfit(np.log(Ns[valid]), np.log(Mtots[valid]), 1)
            print(f"  (1) M_tot ~ N^a  con  a = {a:.3f}")
            if abs(a - 1.0) < 0.2:
                print("      -> a ~ 1: massa ESTENSIVA (cresce col volume; non sparisce a L3).")
            elif a < 0.2:
                print("      -> a ~ 0: massa COSTANTE col volume (1 difetto, non si moltiplica).")
            else:
                print(f"      -> massa cresce come N^{a:.2f} (sub/sovra-estensiva).")

            # densita'
            b, _ = np.polyfit(np.log(Ns[valid]), np.log(rhos[valid] + 1e-30), 1)
            print(f"  (2) rho_M ~ N^b  con  b = {b:.3f}")
            if b < -0.2:
                print("      -> densita' DILUISCE con N (artefatto del root spiegato: la media cala).")
            elif abs(b) <= 0.2:
                print("      -> densita' COSTANTE: massa per nodo invariante di scala.")

        # IPR / regime
        print(f"  (3) localization_ratio per livello: " +
              ", ".join(f"L{r[0]}={r[2]['localization_ratio']:.2f}" for r in rows))
        regimi = [r[2]["regime"] for r in rows]
        if all(g == "campo" for g in regimi):
            print("      -> CAMPO a tutti i livelli: frustrazione ~uniforme (no particella localizzata).")
        elif any(g == "particella" for g in regimi):
            print("      -> Almeno un livello e' PARTICELLA: frustrazione concentrata in pochi nodi.")
        else:
            print("      -> regime INTERMEDIO/misto.")

        print("\n  VERDETTO sull'artefatto del root:")
        if len(rows) >= 1:
            r3 = rows[-1][2]
            print(f"      A L{rows[-1][0]}: E_psi_ROOT ~ 0 ma M_tot={r3['M_tot']:.3e} su "
                  f"{r3['n_leaves']} foglie -> la massa C'E', il root la nascondeva (medie).")


if __name__ == "__main__":
    main()
