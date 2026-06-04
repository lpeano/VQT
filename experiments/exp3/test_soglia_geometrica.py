"""
================================================================================
SOGLIA GEOMETRICA — curva di localizzazione n_loc(chi_mean) [gemello di Task A]
================================================================================

Cosa fa e perche':
  Task A ha mappato la soglia ENERGETICA (kink se M_tot>1): chi_c/chi_stable=1.338.
  Questo script mappa la soglia GEOMETRICA (difetto localizzato se loc_ratio>5)
  con lo STESSO protocollo (sweep + N seed), per misurare il RAPPORTO DI GAP
  TOPOLOGICO [V5]: chi_c_geometrico vs chi_c_energetico.

  Le due soglie sono fisicamente distinte (doppia transizione):
    - geometrica (loc_ratio>5): il difetto si CONCENTRA (localizzazione)
    - energetica (M_tot>1): il difetto ha ENERGIA sufficiente (kink massivo)
  Atteso: chi_c_geometrico < chi_c_energetico (~67). Da test laterali ~57-62.

  Metrica: loc_ratio = IPR*N sulle foglie congelate (da compute_hierarchical_mass).
  "Localizzato" se loc_ratio > LOC_MIN.

Persistenza: ResumeManager crash-safe (riprende da interruzione).
Analisi: usa analyze_termodinamica.py NON direttamente (metrica diversa); questo
  script fa il proprio fit logistico inline.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_soglia_geometrica.py
  python experiments/exp3/test_soglia_geometrica.py --seeds 15 --chi-means 50,54,58,62,66
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

from wqt_oop.energy_metrics import freeze_and_measure_mass, compute_hierarchical_mass
from test_soglia_formazione import make
from resume_manager import ResumeManager

FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)
RESUME_DIR = os.path.join(ROOT, "experiments", "exp3", "resume")
LOC_MIN = 5.0        # loc_ratio sopra cui il difetto e' "localizzato"
CHI_STABLE = 50.0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Soglia geometrica: curva n_loc(chi_mean)")
    ap.add_argument("--level", type=int, default=2, help="livello (default 2)")
    ap.add_argument("--seeds", type=int, default=15, help="seed per punto (default 15)")
    ap.add_argument("--chi-means", type=str, default="50,54,58,62,66",
                    help="sweep chi_mean (CSV). Zona transizione geometrica ~57-62")
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    chi_means = [float(x) for x in args.chi_means.split(",")]
    dt = 0.01
    N = 24 ** args.level

    print("=" * 76)
    print("  SOGLIA GEOMETRICA - curva n_loc(chi_mean) (difetto localizzato se loc>%.0f)" % LOC_MIN)
    print(f"  L{args.level} (N={N})  |  {len(seeds)} seed/punto  |  {len(chi_means)} punti")
    print("=" * 76)
    print(f"  {'chi_mean':>8} {'n_loc/tot':>10} {'frazione':>9}")
    print("  " + "-" * 32)

    chi_arr, frac_arr = [], []
    for cm in chi_means:
        rm = ResumeManager(os.path.join(RESUME_DIR,
            f"geometrica_L{args.level}_cm{cm:.0f}.json"), verbose=False)
        n_loc = 0
        for seed in seeds:
            if rm.has(seed):
                lr = rm.get(seed)["mtot"]  # riuso campo 'mtot' per loc_ratio
            else:
                sol = make(seed, chi_mean=cm, level=args.level)
                for _ in range(args.pre):
                    sol.compute_hamiltonian(); sol.evolve(dt)
                r = freeze_and_measure_mass(sol, max_steps=args.quench_steps,
                                            dt=dt, return_frozen=True)
                lr = compute_hierarchical_mass(r["frozen"])["localization_ratio"]
                rm.save(seed, mtot=lr, neff_dict={})
            if lr > LOC_MIN:
                n_loc += 1
        rm.archive()
        frac = n_loc / len(seeds)
        chi_arr.append(cm); frac_arr.append(frac)
        bar = "#" * int(frac * 20)
        print(f"  {cm:>8.0f} {n_loc:>4}/{len(seeds):<4} {frac:>9.2f}  {bar}")

    chi_arr = np.array(chi_arr, float); frac_arr = np.array(frac_arr)

    # --- fit logistico ---
    print("\n  " + "=" * 60)
    from scipy.optimize import curve_fit
    def logistic(x, xc, w): return 1.0/(1.0+np.exp(-(x-xc)/w))
    chi_c = None
    if np.any(frac_arr > 0.5) and np.any(frac_arr < 0.5):
        try:
            guess = chi_arr[np.argmin(np.abs(frac_arr-0.5))]
            popt, pcov = curve_fit(logistic, chi_arr, frac_arr, p0=[guess,1.0], maxfev=5000)
            perr = np.sqrt(np.diag(pcov))
            chi_c, w = float(popt[0]), float(abs(popt[1]))
            print(f"  chi_c_geometrico = {chi_c:.2f} +- {perr[0]:.2f}  "
                  f"(chi_c/chi_stable = {chi_c/CHI_STABLE:.3f})")
            print(f"  larghezza w = {w:.2f}")
            print(f"\n  RAPPORTO DI GAP TOPOLOGICO [V5]:")
            print(f"    chi_c_geometrico/chi_stable = {chi_c/CHI_STABLE:.3f}")
            print(f"    chi_c_energetico/chi_stable = 1.338 (da Task A)")
            print(f"    rapporto E/G = {1.338/(chi_c/CHI_STABLE):.3f}")
        except Exception as e:
            print(f"  fit fallito: {e}")
    elif np.all(frac_arr >= 0.5):
        print("  chi_c sotto il range (estendere sweep verso il basso)")
    else:
        print("  chi_c sopra il range (estendere sweep verso l'alto)")

    # grafico
    fig, ax = plt.subplots(figsize=(7,5))
    ax.plot(chi_arr, frac_arr, "o", color="#9467bd", ms=9, label="n_loc (geometrica)")
    if chi_c is not None:
        xf = np.linspace(chi_arr.min(), chi_arr.max(), 200)
        ax.plot(xf, logistic(xf, chi_c, w), "-", color="#9467bd", alpha=0.6,
                label=f"logistica chi_c={chi_c:.1f}")
        ax.axvline(chi_c, color="#9467bd", ls="--", alpha=0.5)
    ax.axvline(66.92, color="#d62728", ls="--", alpha=0.6, label="chi_c energetico (67)")
    ax.axhline(0.5, color="gray", ls=":", alpha=0.5)
    ax.set_xlabel("chi_mean"); ax.set_ylabel("frazione localizzati (loc>5)")
    ax.set_title(f"Soglia geometrica vs energetica L{args.level}")
    ax.set_ylim(-0.05,1.05); ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"soglia_geometrica_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
