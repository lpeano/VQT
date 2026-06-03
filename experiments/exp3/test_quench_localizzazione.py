"""
================================================================================
LOCALIZZAZIONE OLTRE sqrt(2) — la prova del nove: materia dal vuoto?
================================================================================

Domanda decisiva (Task 3, 2026-06-03): con l'aggregatore non-distorto
(compute_hierarchical_mass, IPR sulle FOGLIE), se spingo il sistema OLTRE la
soglia sqrt(2)*chi_stable e poi lo congelo (quench T->0), l'IPR SCHIZZA verso
l'alto (difetto localizzato = particella) oppure resta basso (campo distribuito)?

Aspettativa fisica: transizione
  - chi_max/stable < sqrt(2)  ->  campo di frustrazione uniforme (pre-materia),
    loc_ratio ~1-2 (osservato a pre=60: 1.65)
  - chi_max/stable > sqrt(2)  ->  difetto LOCALIZZATO che sopravvive al quench,
    loc_ratio >> 1 (cicatrice = particella)

Protocollo (additivo, usa l'infrastruttura esistente):
  Per ogni chi_mean nello sweep (sub- e super-critico) e per ogni seed:
    1. make(seed, chi_mean, level) -> stato iniziale.
    2. pre-evoluzione: registra il PICCO di chi_max/stable raggiunto.
    3. PRE-quench: compute_hierarchical_mass -> loc_ratio_pre (campo dinamico).
    4. QUENCH (freeze_and_measure_mass return_frozen=True) -> stato congelato.
    5. POST-quench: compute_hierarchical_mass sul congelato -> loc_ratio_post,
       M_tot, rho_M (la cicatrice residua).
  Poi: loc_ratio_post vs chi_max_peak. Salto a sqrt(2) -> materia dal vuoto.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_quench_localizzazione.py            # L1, sweep default
  python experiments/exp3/test_quench_localizzazione.py --level 2 --seeds 3
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wqt_oop.energy_metrics import compute_hierarchical_mass, freeze_and_measure_mass
from test_soglia_formazione import make, chi_max

SQRT2 = np.sqrt(2)
CHI_STABLE = 50.0
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--seeds", type=int, default=6)
    # sweep di chi_mean: copre sub-sqrt(2) (~1.0) fino a super-sqrt(2) (~1.6+)
    ap.add_argument("--chi-means", type=str, default="45,55,65,72,80,90,100")
    ap.add_argument("--pre", type=int, default=40, help="step di pre-evoluzione")
    ap.add_argument("--quench-steps", type=int, default=1500)
    args = ap.parse_args()

    level = args.level
    chi_means = [float(x) for x in args.chi_means.split(",")]
    seeds = list(range(1, args.seeds + 1))
    dt = 0.01

    print("=" * 80)
    print("  LOCALIZZAZIONE OLTRE sqrt(2) - quench e IPR sulle foglie (materia dal vuoto?)")
    print(f"  soglia: sqrt(2)*{CHI_STABLE:.0f} = {SQRT2*CHI_STABLE:.2f}  |  "
          f"L{level} (N={24**level})  |  {len(seeds)} seed/punto")
    print("=" * 80)
    print(f"\n  {'chi_mean':>8} {'chimax/st_peak':>14} {'loc_pre':>9} {'loc_post':>9} "
          f"{'M_tot_post':>11} {'rho_M_post':>11} {'regime_post':>12}")
    print("  " + "-" * 82)

    rows = []  # (peak, loc_pre, loc_post, Mtot, rhoM, regime)
    for cm in chi_means:
        peaks, lpre, lpost, mtots, rhos, regs = [], [], [], [], [], []
        for seed in seeds:
            sol = make(seed, chi_mean=cm, level=level)
            peak = chi_max(sol) / CHI_STABLE
            for _ in range(args.pre):
                sol.compute_hamiltonian()
                sol.evolve(dt)
                peak = max(peak, chi_max(sol) / CHI_STABLE)

            h_pre = compute_hierarchical_mass(sol)
            r = freeze_and_measure_mass(sol, max_steps=args.quench_steps, dt=dt,
                                        return_frozen=True)
            h_post = compute_hierarchical_mass(r["frozen"])

            peaks.append(peak)
            lpre.append(h_pre["localization_ratio"])
            lpost.append(h_post["localization_ratio"])
            mtots.append(h_post["M_tot"])
            rhos.append(h_post["rho_M"])
            regs.append(h_post["regime"])

        peak_m = float(np.mean(peaks))
        lpre_m = float(np.mean(lpre))
        lpost_m = float(np.mean(lpost))
        mtot_m = float(np.mean(mtots))
        rho_m = float(np.mean(rhos))
        # regime di maggioranza
        reg = max(set(regs), key=regs.count)
        rows.append((peak_m, lpre_m, lpost_m, mtot_m, rho_m, reg))
        print(f"  {cm:>8.0f} {peak_m:>14.3f} {lpre_m:>9.2f} {lpost_m:>9.2f} "
              f"{mtot_m:>11.3e} {rho_m:>11.3e} {reg:>12}")

    # --- analisi: FINESTRA di localizzazione (risonanza), non soglia sqrt(2) ---
    # La storia non e' "sub vs super sqrt(2)" ma una FINESTRA in super-criticalita':
    #   troppo poco -> niente massa; punto giusto -> particella localizzata;
    #   troppo (sovra-saturazione) -> campo uniforme ad alta energia.
    print("\n  " + "=" * 76)
    print("  ANALISI: FINESTRA di localizzazione (loc_post vs picco super-critico)")
    print("  " + "-" * 76)
    peaks = np.array([r[0] for r in rows])
    lpost = np.array([r[2] for r in rows])
    mtots_arr = np.array([r[3] for r in rows])

    imax = int(np.argmax(lpost))
    loc_peak = float(lpost[imax])
    peak_at = float(peaks[imax])
    N_lvl = 24 ** level
    n_eff_peak = N_lvl / (loc_peak + 1e-30)
    print(f"  picco di localizzazione: loc_post = {loc_peak:.1f} a chimax/st = {peak_at:.3f}")
    print(f"  -> n_eff ~ {n_eff_peak:.0f} nodi caldi su {N_lvl} "
          f"({100*n_eff_peak/N_lvl:.1f}% del reticolo)")

    # base "campo" = media dei punti lontani dal picco (estremi dello sweep)
    field_mask = np.abs(np.arange(len(lpost)) - imax) >= 2
    base = float(np.mean(lpost[field_mask])) if np.any(field_mask) else 1.0
    contrast = loc_peak / (base + 1e-30)
    print(f"  base 'campo' (lontano dal picco): {base:.2f}  ->  contrasto picco/campo: {contrast:.1f}x")

    if loc_peak > 10 and contrast > 4:
        print("  -> PARTICELLA: il quench condensa un DIFETTO LOCALIZZATO in una FINESTRA")
        print(f"     di super-criticalita' (~{peak_at:.2f}). Sopra e sotto -> campo distribuito.")
        print("     La localizzazione e' un fenomeno DI SCALA + DI FINESTRA, non a sqrt(2).")
    elif loc_peak > 4:
        print("  -> Localizzazione MODERATA (segnale presente ma non netto a questo livello).")
        print("     Probabile risoluzione insufficiente: piu' nodi (livello superiore) o piu' seed.")
    else:
        print("  -> NESSUNA localizzazione: resta campo distribuito (confinamento o sotto-risoluzione).")

    # --- grafico ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    lpre = np.array([r[1] for r in rows])
    ax1.plot(peaks, lpre, "o--", color="#1f77b4", label="loc_ratio PRE-quench (dinamico)")
    ax1.plot(peaks, lpost, "s-", color="#d62728", label="loc_ratio POST-quench (cicatrice)")
    ax1.axvline(SQRT2, color="k", ls=":", label=f"sqrt(2) = {SQRT2:.3f}")
    ax1.axhline(1.0, color="gray", ls="-", alpha=0.4, label="uniforme (campo)")
    ax1.set_xlabel("chi_max/chi_stable (picco raggiunto)")
    ax1.set_ylabel("localization_ratio = IPR * N")
    ax1.set_title("Finestra di localizzazione del difetto (picco = particella)")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    mtots = np.array([r[3] for r in rows])
    ax2.plot(peaks, mtots, "^-", color="#2ca02c")
    ax2.axvline(SQRT2, color="k", ls=":")
    ax2.set_xlabel("chi_max/chi_stable (picco)")
    ax2.set_ylabel("M_tot residua (post-quench)")
    ax2.set_title("Massa residua congelata vs soglia")
    ax2.grid(alpha=0.3)

    fig.suptitle(f"Materia dal vuoto: quench oltre sqrt(2) [L{level}]", fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"quench_localizzazione_L{level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
