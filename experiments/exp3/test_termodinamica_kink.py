"""
================================================================================
TERMODINAMICA DELLE PARETI — curva n(chi_mean) ed esponente KZ nu
================================================================================

Cosa fa e perche':
  La fase particella (kink phi^4) esiste in una finestra di super-criticalita'.
  La domanda e': come varia la DENSITA' di kink con la distanza dalla transizione?
  Se il sistema segue la legge di Kibble-Zurek:
      n_kink ~ |epsilon|^nu,   epsilon = (chi_mean - chi_c) / chi_c
  allora il grafico log(n) vs log(|epsilon|) e' lineare con pendenza nu.

  Per il campo phi^4 in 1D classico: nu = 1.
  Il valore misurato di nu permette di classificare la transizione e prevedere
  il numero di kink in funzione del chi_mean — rendendo il modello PREDITTIVO.

  Nota: qui "n_kink" e' la FRAZIONE di seed che nucleano un kink (0..1),
  misurabile su un sistema L2 (N=576) in ~50 min per l'intero sweep.
  Per L3 (13824 nodi) lo stesso sweep richiederebbe ~15-20 ore.

Protocollo:
  Per ogni chi_mean in sweep (58, 60, 62, ..., 78):
    1. N_seeds realizzazioni indipendenti: make(seed, chi_mean, level)
    2. Pre-evoluzione (40 step) per portare al regime dinamico
    3. Quench T->0 (freeze_and_measure_mass)
    4. Classifica: "kink" se M_tot > MTOT_MIN
  Output per chi_mean: n_kink = n_massivi / N_seeds, M_tot medio

  Poi:
    - Stima chi_c = chi_mean di soglia (dove n_kink passa da 0 a >0)
    - Fit potenza: log(n_kink) vs log(chi_mean - chi_c) -> pendenza = nu
    - Confronta nu con 1.0 (phi^4 classico)

Persistenza: usa ResumeManager per recovery da interruzione. Ogni (chi_mean,
seed) viene salvato dopo il calcolo.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_termodinamica_kink.py
  python experiments/exp3/test_termodinamica_kink.py --seeds 20 --chi-means 58,60,62,64,66,68,70,72,74,76,78
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

MTOT_MIN = 1.0          # soglia per classificare "kink reale"
CHI_STABLE = 50.0


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Termodinamica delle pareti: curva n(chi_mean) ed esponente KZ")
    ap.add_argument("--level", type=int, default=2,
                    help="livello gerarchico (default 2 = L2, N=576)")
    ap.add_argument("--seeds", type=int, default=20,
                    help="seed per punto dello sweep (default 20)")
    ap.add_argument("--chi-means", type=str,
                    default="58,60,62,64,66,68,70,72,74,76,78",
                    help="sweep di chi_mean separati da virgola")
    ap.add_argument("--pre", type=int, default=40,
                    help="step di pre-evoluzione (default 40)")
    ap.add_argument("--quench-steps", type=int, default=500,
                    help="step massimi del quench (default 500)")
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    chi_means = [float(x) for x in args.chi_means.split(",")]
    dt = 0.01
    N = 24 ** args.level

    print("=" * 80)
    print("  TERMODINAMICA DELLE PARETI - curva n(chi_mean) ed esponente KZ nu")
    print(f"  L{args.level} (N={N})  |  {len(seeds)} seed/punto  |"
          f"  {len(chi_means)} punti: {chi_means[0]:.0f}..{chi_means[-1]:.0f}")
    print(f"  kink se M_tot > {MTOT_MIN}")
    print("=" * 80)

    # --- raccolta dati con resume ---
    fracs, mtot_means, mtot_stds = [], [], []

    for cm in chi_means:
        resume_file = os.path.join(RESUME_DIR,
            f"termodinamica_L{args.level}_cm{cm:.0f}.json")
        rm = ResumeManager(resume_file, verbose=False)

        n_kink = 0
        mtots_kink = []
        n_done = 0

        for seed in seeds:
            key = str(seed)
            if rm.has(seed):
                cached = rm.get(seed)
                mt = cached["mtot"]
            else:
                sol = make(seed, chi_mean=cm, level=args.level)
                for _ in range(args.pre):
                    sol.compute_hamiltonian(); sol.evolve(dt)
                r = freeze_and_measure_mass(sol, max_steps=args.quench_steps,
                                            dt=dt, return_frozen=True)
                h = compute_hierarchical_mass(r["frozen"])
                mt = h["M_tot"]
                rm.save(seed, mtot=mt, neff_dict={})
            if mt > MTOT_MIN:
                n_kink += 1
                mtots_kink.append(mt)
            n_done += 1

        rm.archive()

        frac = n_kink / len(seeds)
        n = len(seeds)
        # varianza osservata vs varianza binomiale indipendente p*(1-p)/n
        # rapporto > 1 -> super-poissoniano (cooperativo)
        # rapporto ~ 1 -> indipendente (stocastico)
        var_binom = frac * (1 - frac)          # varianza per singola realizzaz.
        var_binom_mean = var_binom / n          # varianza della media
        # varianza empirica della frazione (bootstrap semplice sui seed)
        kink_per_seed = np.array([1 if i < n_kink else 0 for i in range(n)])
        var_emp = float(np.var(kink_per_seed))
        cooperativity = var_emp / (var_binom + 1e-30)  # 1=indip., >1=cooper.
        mtot_m = float(np.mean(mtots_kink)) if mtots_kink else 0.0
        mtot_s = float(np.std(mtots_kink)) if len(mtots_kink) > 1 else 0.0
        fracs.append(frac)
        mtot_means.append(mtot_m)
        mtot_stds.append(mtot_s)
        print(f"  chi_mean={cm:>5.1f}  n_kink={n_kink}/{n}"
              f"  frac={frac:.2f}  coop={cooperativity:.2f}"
              f"  M_tot_medio={mtot_m:.2e}")

    fracs = np.array(fracs)
    chi_means_arr = np.array(chi_means)

    # --- stima chi_c e fit KZ ---
    print("\n  " + "=" * 76)
    print("  ANALISI: chi_c e esponente nu")
    print("  " + "-" * 76)

    # chi_c: interpolazione lineare dove frac = 0.5
    chi_c = None
    for i in range(len(chi_means_arr) - 1):
        if fracs[i] <= 0.5 <= fracs[i+1] or fracs[i] >= 0.5 >= fracs[i+1]:
            # interpolazione lineare
            t = (0.5 - fracs[i]) / (fracs[i+1] - fracs[i] + 1e-30)
            chi_c = chi_means_arr[i] + t * (chi_means_arr[i+1] - chi_means_arr[i])
            break
    if chi_c is None:
        if fracs[0] > 0.5:
            chi_c = chi_means_arr[0]
        else:
            chi_c = chi_means_arr[-1]

    print(f"  chi_c (n=0.5) stimato: {chi_c:.1f}  (chi_c/chi_stable = {chi_c/CHI_STABLE:.3f})")

    # fit KZ: log(n) vs log(epsilon) sui punti con 0 < n < 1
    eps = (chi_means_arr - chi_c) / CHI_STABLE
    valid = (fracs > 0.05) & (fracs < 0.95) & (eps > 0)
    nu = None
    if np.sum(valid) >= 3:
        log_eps = np.log(eps[valid])
        log_n = np.log(fracs[valid])
        nu, log_k = np.polyfit(log_eps, log_n, 1)
        r2 = 1.0 - np.sum((log_n - (nu * log_eps + log_k))**2) / (
            np.sum((log_n - np.mean(log_n))**2) + 1e-30)
        print(f"  Fit KZ:  nu = {nu:.3f}  (R2 = {r2:.3f})")
        if abs(nu - 1.0) < 0.2:
            print("  -> nu ~ 1: COERENTE con phi^4 classico 1D (Kibble-Zurek).")
        elif nu > 1.5:
            print(f"  -> nu = {nu:.2f} > 1: transizione piu' brusca del phi^4 classico.")
        elif nu < 0.5:
            print(f"  -> nu = {nu:.2f} < 0.5: transizione piu' morbida del phi^4 classico.")
        else:
            print(f"  -> nu = {nu:.2f}: deviazione dal phi^4 classico (nu=1).")
    else:
        print("  Dati insufficienti per il fit (< 3 punti nella regione 5%-95%).")
        print("  Estendere lo sweep o aumentare i seed per avere piu' punti di transizione.")

    # --- grafici ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # curva di nucleazione
    ax1.plot(chi_means_arr, fracs, "o-", color="#d62728", ms=8, label="n_kink")
    ax1.axhline(0.5, color="gray", ls=":", alpha=0.6, label="n=0.5")
    if chi_c is not None:
        ax1.axvline(chi_c, color="blue", ls="--", alpha=0.7,
                    label=f"chi_c={chi_c:.1f}")
    ax1.set_xlabel("chi_mean"); ax1.set_ylabel("frazione di nucleazione")
    ax1.set_title("Curva di nucleazione n(chi_mean)")
    ax1.set_ylim(-0.05, 1.05); ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    # fit KZ in scala log-log
    if nu is not None and np.sum(valid) >= 3:
        ax2.loglog(eps[valid], fracs[valid], "o", color="#d62728", ms=8,
                   label="dati (5% < n < 95%)")
        eps_fit = np.linspace(eps[valid].min(), eps[valid].max(), 50)
        ax2.loglog(eps_fit, np.exp(log_k) * eps_fit**nu, "--",
                   color="#1f77b4", label=f"fit: n ~ eps^{nu:.2f} (R2={r2:.3f})")
        ax2.set_xlabel("epsilon = (chi_mean - chi_c) / chi_stable")
        ax2.set_ylabel("n_kink")
        ax2.set_title(f"Fit KZ: n ~ |epsilon|^nu,  nu = {nu:.3f}")
        ax2.legend(fontsize=8); ax2.grid(alpha=0.3, which="both")
    else:
        ax2.plot(chi_means_arr, fracs, "o-", color="#d62728")
        ax2.set_xlabel("chi_mean"); ax2.set_ylabel("frazione")
        ax2.set_title("Dati insufficienti per fit log-log")
        ax2.grid(alpha=0.3)

    fig.suptitle(
        f"Termodinamica delle pareti: legge KZ  n ~ |epsilon|^nu [L{args.level}]",
        fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"termodinamica_kink_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")

    return {"chi_c": chi_c, "nu": nu, "fracs": fracs.tolist(),
            "chi_means": chi_means}


if __name__ == "__main__":
    main()
