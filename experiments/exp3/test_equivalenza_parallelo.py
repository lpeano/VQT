"""
================================================================================
GATE — equivalenza SERIALE vs PARALLELO (multiprocessing sui seed)
================================================================================

Verifica che il calcolo parallelo di test_termodinamica_kink_par.py produca
M_tot IDENTICI al calcolo seriale, seed-per-seed. Poiche' ogni seed e'
deterministico (np.random.default_rng(seed) dentro make()), il parallelismo
NON deve cambiare NULLA: deve essere identita' bit-per-bit (o entro l'epsilon
di macchina dovuto a eventuali differenze d'ordine in riduzioni numpy).

Se questo GATE passa, il parallelo e' fisicamente equivalente al seriale e puo'
essere usato su L3 con la stessa fiducia.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_equivalenza_parallelo.py
  python experiments/exp3/test_equivalenza_parallelo.py --level 2 --seeds 4 --chi-mean 68
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

from test_termodinamica_kink_par import _quench_one


def main():
    import argparse
    ap = argparse.ArgumentParser(description="GATE equivalenza seriale vs parallelo")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--chi-mean", type=float, default=68.0)
    ap.add_argument("--quench-steps", type=int, default=500)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tol", type=float, default=1e-9,
                    help="tolleranza relativa max ammessa (default 1e-9)")
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    tasks = [(args.chi_mean, s, args.level, 40, args.quench_steps, 0.01) for s in seeds]

    print("=" * 68)
    print(f"  GATE EQUIVALENZA seriale vs parallelo  [L{args.level}, cm={args.chi_mean:.0f}]")
    print(f"  {len(seeds)} seed, quench-steps={args.quench_steps}, workers={args.workers}")
    print("=" * 68)

    # --- seriale ---
    print("\n  SERIALE...")
    t0 = time.time()
    serial = {}
    for t in tasks:
        cm, seed, mt = _quench_one(t)
        serial[seed] = mt
        print(f"    seed{seed}: M_tot={mt:.10e}")
    t_serial = time.time() - t0

    # --- parallelo ---
    print(f"\n  PARALLELO ({args.workers} worker)...")
    t0 = time.time()
    parallel = {}
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=args.workers) as pool:
        for (cm, seed, mt) in pool.imap_unordered(_quench_one, tasks):
            parallel[seed] = mt
            print(f"    seed{seed}: M_tot={mt:.10e}")
    t_par = time.time() - t0

    # --- confronto ---
    print("\n  " + "=" * 60)
    print(f"  {'seed':>5} {'seriale':>16} {'parallelo':>16} {'err_rel':>12}")
    print("  " + "-" * 56)
    max_err = 0.0
    for seed in seeds:
        s, p = serial[seed], parallel[seed]
        denom = max(abs(s), 1e-30)
        err = abs(s - p) / denom
        max_err = max(max_err, err)
        print(f"  {seed:>5} {s:>16.8e} {p:>16.8e} {err:>12.2e}")

    print("\n  " + "=" * 60)
    print(f"  errore relativo MAX: {max_err:.2e}  (tolleranza: {args.tol:.0e})")
    print(f"  tempo seriale:   {t_serial:.1f}s")
    print(f"  tempo parallelo: {t_par:.1f}s   (speedup {t_serial/max(t_par,1e-9):.1f}x)")
    if max_err < args.tol:
        print("\n  [GATE PASS] parallelo IDENTICO al seriale entro tolleranza.")
        print("  -> il parallelo e' fisicamente equivalente, usabile su L3.")
    else:
        print("\n  [GATE FAIL] divergenza oltre tolleranza! NON usare il parallelo.")
        sys.exit(1)


if __name__ == "__main__":
    main()
