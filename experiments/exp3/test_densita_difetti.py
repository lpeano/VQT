"""
================================================================================
DENSITA' DI DIFETTI PUNTUALI vs ENERGIA — n_def(chi_mean) [parallelo]
================================================================================

Cosa fa e perche':
  Dopo aver scoperto che il difetto VQT e' PUNTUALE (single-site, V4), la domanda
  giusta non e' "quanto e' largo" ma "QUANTI difetti puntuali si formano in
  funzione dell'energia iniettata (chi_mean)?".

  Per ogni chi_mean, per N seed, quench T->0, conta n_def = numero di FOGLIE
  che hanno lasciato il pozzo dominante (|chi - pozzo_dom| > THRESH). Il pozzo
  dominante e' sign(median(chi))*chi_stable.

  Atteso (3 regimi):
    - sotto chi_c (~62): n_def = 0 (vuoto)
    - poco sopra chi_c: n_def piccolo (1-pochi difetti puntuali)
    - molto sopra (sovra-saturazione): n_def grande -> il concetto di "difetto
      puntuale" si dissolve in un campo distribuito (plasma)

  E' statistica termodinamica pura (densita' di difetti), dominio solido.
  Estende la curva di nucleazione (frazione binaria) al CONTEGGIO dei difetti.

  Metrica robusta al rumore: media di n_def su N seed (sistema stocastico,
  seeding deterministico per riproducibilita').

RESUME crash-safe + parallelismo (--workers). Riusa l'infrastruttura verificata.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_densita_difetti.py --level 2 --seeds 10 \
    --chi-means 60,64,68,72,76,80,85,90 --workers 6
================================================================================
"""

import sys, os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
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
CHI_STABLE = 50.0
THRESH = 0.6 * CHI_STABLE   # nodo "difetto" se |chi - pozzo_dominante| > 30


def _count_defects(task):
    """task=(cm,seed,level,pre,quench_steps,dt). Ritorna (cm,seed,n_def,M_tot)."""
    cm, seed, level, pre, quench_steps, dt = task
    sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))
    import numpy as _np
    _np.random.seed(int(seed) + 100003 * int(round(cm)))  # determinismo per-task
    from wqt_oop.energy_metrics import freeze_and_measure_mass, compute_hierarchical_mass
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    from test_soglia_formazione import make
    sol = make(seed, chi_mean=cm, level=level)
    for _ in range(pre):
        sol.compute_hamiltonian(); sol.evolve(dt)
    r = freeze_and_measure_mass(sol, max_steps=quench_steps, dt=dt, return_frozen=True)
    fr = r["frozen"]
    # raccogli chi di tutte le foglie
    chi = []
    def _walk(n):
        if n.children and isinstance(n.children[0], SegmentoQuantistico):
            chi.extend(c.chi for c in n.children)
        else:
            for c in n.children:
                if hasattr(c, "children"): _walk(c)
    _walk(fr)
    chi = _np.array(chi)
    pozzo = _np.sign(_np.median(chi)) * CHI_STABLE
    if pozzo == 0: pozzo = CHI_STABLE
    n_def = int(_np.sum(_np.abs(chi - pozzo) > THRESH))
    mt = float(compute_hierarchical_mass(fr)["M_tot"])
    return (cm, seed, n_def, mt)


def main():
    import argparse
    from resume_manager import ResumeManager
    ap = argparse.ArgumentParser(description="Densita' difetti puntuali vs energia")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--chi-means", type=str, default="60,64,68,72,76,80,85,90")
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    ap.add_argument("--workers", type=int, default=0)
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    chi_means = [float(x) for x in args.chi_means.split(",")]
    dt = 0.01
    N = 24 ** args.level
    n_phys = mp.cpu_count() // 2 if mp.cpu_count() > 2 else 1
    n_workers = args.workers if args.workers > 0 else max(1, n_phys - 1)

    print("=" * 78)
    print("  DENSITA' DI DIFETTI PUNTUALI vs ENERGIA  n_def(chi_mean)")
    print(f"  L{args.level} (N={N})  |  {len(seeds)} seed  |  {len(chi_means)} punti  |"
          f"  workers={n_workers}  |  difetto se |chi-pozzo|>{THRESH:.0f}")
    print("=" * 78)

    # resume: campo 'mtot' del ResumeManager riusato per n_def (intero); M_tot separato
    resume = {}
    pending = []
    n_cached = 0
    for cm in chi_means:
        rm = ResumeManager(os.path.join(RESUME_DIR,
            f"densita_L{args.level}_cm{cm:.0f}.json"), verbose=False)
        resume[cm] = rm
        for seed in seeds:
            if rm.has(seed): n_cached += 1
            else: pending.append((cm, seed, args.level, args.pre, args.quench_steps, dt))

    total = len(chi_means) * len(seeds)
    print(f"\n  Task: {total} totali, {n_cached} da resume, {len(pending)} da calcolare\n")
    if pending:
        t0 = time.time(); done = 0
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=n_workers) as pool:
            try:
                for (cm, seed, n_def, mt) in pool.imap_unordered(_count_defects, pending):
                    # salvo n_def nel campo mtot del resume (e' un intero)
                    resume[cm].save(seed, mtot=float(n_def), neff_dict={"M": {"n_eff": mt, "n_blocks": 0}})
                    done += 1
                    el = time.time() - t0; eta = el/done*(len(pending)-done)
                    print(f"  [{done:>3}/{len(pending)}] cm{cm:.0f} seed{seed:<2} "
                          f"n_def={n_def:<3} M={mt:.1e} | {el/60:.0f}min ETA{eta/60:.0f}min", flush=True)
            except KeyboardInterrupt:
                print("\n  INTERROTTO. Rilanciare per riprendere."); pool.terminate(); pool.join(); return
        print(f"\n  Completato in {(time.time()-t0)/60:.1f} min.")

    # aggrega
    print(f"\n  {'chi_mean':>8} {'n_def medio':>12} {'std':>7} {'min-max':>9} {'frac>0':>7}")
    print("  " + "-" * 50)
    chi_arr, ndef_mean, ndef_std = [], [], []
    for cm in chi_means:
        rm = resume[cm]
        nd = np.array([rm.get(s)["mtot"] for s in seeds if rm.has(s)])
        chi_arr.append(cm); ndef_mean.append(nd.mean()); ndef_std.append(nd.std())
        frac = np.mean(nd > 0)
        print(f"  {cm:>8.0f} {nd.mean():>12.2f} {nd.std():>7.2f} "
              f"{int(nd.min())}-{int(nd.max()):<6} {frac:>7.2f}")
        rm.archive()

    chi_arr = np.array(chi_arr); ndef_mean = np.array(ndef_mean); ndef_std = np.array(ndef_std)

    # grafico
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    ax1.errorbar(chi_arr, ndef_mean, yerr=ndef_std, fmt="o-", color="#d62728",
                 capsize=4, ms=7)
    ax1.set_xlabel("chi_mean"); ax1.set_ylabel("n difetti puntuali (medio)")
    ax1.set_title(f"Densita' di difetti vs energia L{args.level}")
    ax1.grid(alpha=0.3)
    # log per vedere la crescita
    ax2.semilogy(chi_arr, np.maximum(ndef_mean, 0.1), "o-", color="#1f77b4", ms=7)
    ax2.set_xlabel("chi_mean"); ax2.set_ylabel("n difetti (log)")
    ax2.set_title("Crescita (log): lineare? esponenziale? a soglia?")
    ax2.grid(alpha=0.3, which="both")
    fig.suptitle(f"Densita' di difetti puntuali L{args.level} (1 difetto -> plasma)",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"densita_difetti_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
