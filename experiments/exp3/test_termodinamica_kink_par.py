"""
================================================================================
TERMODINAMICA DELLE PARETI — versione PARALLELA (multiprocessing sui seed)
================================================================================

Versione parallela di test_termodinamica_kink.py. I seed sono fisicamente
INDIPENDENTI (cooperativity=1.00 misurata): girarli in parallelo da' lo STESSO
identico risultato del seriale, solo piu' veloce. Nessuna modifica al motore
fisico (evolve/freeze_and_measure_mass restano intatti): codice ADDITIVO.

GARANZIA DI EQUIVALENZA:
  Ogni seed e' deterministico (np.random.default_rng(seed) dentro make()).
  Quindi worker paralleli e calcolo seriale producono M_tot IDENTICI seed-per-seed.
  Verificare sempre con test_equivalenza_parallelo.py prima di fidarsi su L3.

PARALLELISMO CONFIGURABILE:
  --workers N  : numero di processi paralleli (default = core fisici - 1).
  Ogni worker forza OMP/MKL_NUM_THREADS=1 per evitare oversubscription dei
  thread interni di numpy (altrimenti N_proc * N_thread > N_core = thrashing).

RESUME CRASH-SAFE:
  Ogni risultato (seed completato) viene salvato su disco APPENA pronto, tramite
  ResumeManager (file rotanti main/.tmp/.bak). In caso di chiusura volontaria
  (Ctrl-C) o crash, rilanciare lo STESSO comando: i seed gia' completati vengono
  saltati, il calcolo riprende dai mancanti. I worker scrivono nel processo
  MAIN (non in parallelo sul file) per evitare corruzione: ogni risultato che
  arriva dal pool viene persistito subito dal main.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_termodinamica_kink_par.py \
    --level 3 --seeds 5 --chi-means 60,66,72,78 --workers 5 --quench-steps 500
  # Ripresa dopo interruzione: STESSO comando.
================================================================================
"""

import sys, os
# --- forza thread singolo nei worker numpy PRIMA di importare numpy ---
# (deve stare prima di 'import numpy' per avere effetto)
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import warnings, logging, time
import multiprocessing as mp

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESUME_DIR = os.path.join(ROOT, "experiments", "exp3", "resume")
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)
MTOT_MIN = 1.0
CHI_STABLE = 50.0


# ---------------------------------------------------------------------------
# WORKER: calcola M_tot per un singolo (chi_mean, seed). Funzione top-level
# (necessario per il pickling di multiprocessing su Windows/spawn).
# ---------------------------------------------------------------------------
def _quench_one(task):
    """task = (cm, seed, level, pre, quench_steps, dt). Ritorna (cm, seed, M_tot)."""
    cm, seed, level, pre, quench_steps, dt = task
    # import dentro il worker (spawn ricarica il modulo da zero)
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))
    from wqt_oop.energy_metrics import freeze_and_measure_mass, compute_hierarchical_mass
    from test_soglia_formazione import make
    sol = make(seed, chi_mean=cm, level=level)
    for _ in range(pre):
        sol.compute_hamiltonian(); sol.evolve(dt)
    r = freeze_and_measure_mass(sol, max_steps=quench_steps, dt=dt, return_frozen=True)
    mt = compute_hierarchical_mass(r["frozen"])["M_tot"]
    return (cm, seed, float(mt))


def main():
    import argparse
    from resume_manager import ResumeManager
    ap = argparse.ArgumentParser(
        description="Termodinamica delle pareti PARALLELA (multiprocessing sui seed)")
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=5, help="seed per punto")
    ap.add_argument("--chi-means", type=str, default="60,66,72,78")
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    ap.add_argument("--workers", type=int, default=0,
                    help="processi paralleli (0 = auto: core fisici - 1)")
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    chi_means = [float(x) for x in args.chi_means.split(",")]
    dt = 0.01
    N = 24 ** args.level

    # numero worker: default = core fisici - 1 (lascia un core per il SO)
    n_phys = mp.cpu_count() // 2 if mp.cpu_count() > 2 else 1  # 12 logici -> 6 fisici
    n_workers = args.workers if args.workers > 0 else max(1, n_phys - 1)

    print("=" * 80)
    print("  TERMODINAMICA PARALLELA - curva n(chi_mean)")
    print(f"  L{args.level} (N={N})  |  {len(seeds)} seed/punto  |  "
          f"{len(chi_means)} punti  |  workers={n_workers}")
    print(f"  kink se M_tot > {MTOT_MIN}  |  quench-steps={args.quench_steps}")
    print("=" * 80)

    # --- 1. raccogli i task MANCANTI consultando i resume (skip dei gia' fatti) ---
    resume = {}   # cm -> ResumeManager
    pending = []  # lista di task da calcolare
    n_cached = 0
    for cm in chi_means:
        rm = ResumeManager(os.path.join(RESUME_DIR,
            f"termodinamica_L{args.level}_cm{cm:.0f}.json"), verbose=False)
        resume[cm] = rm
        for seed in seeds:
            if rm.has(seed):
                n_cached += 1
            else:
                pending.append((cm, seed, args.level, args.pre, args.quench_steps, dt))

    total = len(chi_means) * len(seeds)
    print(f"\n  Task totali: {total}  |  gia' fatti (resume): {n_cached}  |  "
          f"da calcolare: {len(pending)}")
    if pending:
        print(f"  Avvio pool con {n_workers} worker...\n")
        t0 = time.time()
        done = 0
        # imap_unordered: i risultati arrivano appena pronti -> li salvo subito
        ctx = mp.get_context("spawn")  # spawn = sicuro su Windows
        with ctx.Pool(processes=n_workers) as pool:
            try:
                for (cm, seed, mt) in pool.imap_unordered(_quench_one, pending):
                    resume[cm].save(seed, mtot=mt, neff_dict={})  # persistenza immediata
                    done += 1
                    el = time.time() - t0
                    eta = el / done * (len(pending) - done)
                    flag = "KINK" if mt > MTOT_MIN else "----"
                    print(f"  [{done:>3}/{len(pending)}] cm{cm:.0f} seed{seed:<2} "
                          f"M_tot={mt:.2e} {flag}  | elapsed {el/60:.1f}min "
                          f"ETA {eta/60:.1f}min", flush=True)
            except KeyboardInterrupt:
                print("\n  INTERROTTO (Ctrl-C). Stato salvato: rilanciare lo stesso "
                      "comando per riprendere.")
                pool.terminate(); pool.join()
                return
        print(f"\n  Calcolo completato in {(time.time()-t0)/60:.1f} min.")
    else:
        print("  Tutti i seed gia' calcolati (resume completo).")

    # --- 2. aggrega + fit logistico (modello corretto per prob. di nucleazione) ---
    from scipy.optimize import curve_fit
    def logistic(x, xc, w): return 1.0/(1.0+np.exp(-(x-xc)/w))

    chi_arr, frac_arr = [], []
    print(f"\n  {'chi_mean':>8} {'n_kink/tot':>11} {'frazione':>9}")
    print("  " + "-" * 32)
    for cm in chi_means:
        rm = resume[cm]
        mt = np.array([rm.get(s)["mtot"] for s in seeds if rm.has(s)])
        nk = int(np.sum(mt > MTOT_MIN))
        frac = nk / len(mt) if len(mt) else 0.0
        chi_arr.append(cm); frac_arr.append(frac)
        bar = "#" * int(frac * 20)
        print(f"  {cm:>8.0f} {nk:>4}/{len(mt):<5} {frac:>9.2f}  {bar}")
        rm.archive()

    chi_arr = np.array(chi_arr, float); frac_arr = np.array(frac_arr)

    print("\n  " + "=" * 60)
    chi_c = w = None
    if np.any(frac_arr > 0.5) and np.any(frac_arr < 0.5):
        try:
            guess = chi_arr[np.argmin(np.abs(frac_arr-0.5))]
            popt, pcov = curve_fit(logistic, chi_arr, frac_arr, p0=[guess,2.0], maxfev=5000)
            perr = np.sqrt(np.diag(pcov))
            chi_c, w = float(popt[0]), float(abs(popt[1]))
            print(f"  FIT LOGISTICO:  chi_c = {chi_c:.2f} +- {perr[0]:.2f}  "
                  f"(chi_c/chi_stable = {chi_c/CHI_STABLE:.3f})")
            print(f"    larghezza w = {w:.2f}")
            print(f"\n  CONFRONTO DI SCALA (data collapsing V1/V2):")
            print(f"    chi_c/chi_stable L{args.level} = {chi_c/CHI_STABLE:.3f}")
            print(f"    chi_c/chi_stable L2          = 1.338 (da Task A)")
            print(f"    se coincidono -> universalita' [verso OSS]; se no -> scala finita")
        except Exception as e:
            print(f"  fit fallito: {e}")
    elif np.all(frac_arr < 0.5):
        print("  chi_c sopra il range (estendere sweep verso l'alto)")
    elif np.all(frac_arr > 0.5):
        print("  chi_c sotto il range (estendere sweep verso il basso)")

    # grafico
    fig, ax = plt.subplots(figsize=(7,5))
    ax.plot(chi_arr, frac_arr, "o", color="#d62728", ms=9, label=f"L{args.level} dati")
    if chi_c is not None:
        xf = np.linspace(chi_arr.min(), chi_arr.max(), 200)
        ax.plot(xf, logistic(xf, chi_c, w), "-", color="#1f77b4",
                label=f"logistica chi_c={chi_c:.1f}")
        ax.axvline(chi_c, color="blue", ls="--", alpha=0.5)
    ax.axhline(0.5, color="gray", ls=":", alpha=0.5)
    ax.set_xlabel("chi_mean"); ax.set_ylabel("frazione nucleazione (M_tot>1)")
    ax.set_title(f"Curva di nucleazione energetica L{args.level} (parallelo)")
    ax.set_ylim(-0.05,1.05); ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"termodinamica_par_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
