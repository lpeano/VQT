"""
================================================================================
TEST DECISIVO: i coupling postulati si DISSOLVONO? (densita' difetti intensiva?)
================================================================================

Domanda (problema di ieri): la corsa di chi_c con L (1.353->1.237-><1.08) e' dovuta
ai coupling postulati (alpha_K~1/24^L, lambda~24^2L, ...)? Se SI', appiattendoli a
SCALE-INVARIANTI la densita' di difetti n_def/N a chi_mean fisso dovrebbe diventare
INTENSIVA (uguale tra L1/L2/L3) -> chi_c non corre piu' -> coupling DISSOLTI.

Confronta, allo STESSO seed (A/B pulito: cambiano solo i coupling), 3 regimi:
  - 'scaled' : legacy (coupling scala-dipendenti postulati).
  - 'flat'   : coupling SCALE-INVARIANTI (valori L1 a ogni livello), EC off.
  - 'cura'   : flat + dinamica Einstein-Cartan ON (saturazione + chiusura 720).

Osservabile INTENSIVO: n_def/N = frazione di nodi deviati dal pozzo dominante.
  - se n_def/N(flat) ~ costante tra L  -> i coupling che corrono erano l'artefatto.
  - se n_def/N(scaled) varia con L ma flat no -> conferma.

Quench manuale (per tenere EC attivo anche nel raffreddamento, cosa che
freeze_and_measure_mass non fa). Parallelo + resume.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_cura_coupling.py --chi-means 66,72 --seeds 2 --workers 6
================================================================================
"""
import sys, os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")
import numpy as np
import json, time, warnings, logging
import multiprocessing as mp
warnings.filterwarnings("ignore"); logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))
SUMMARY = os.path.join(ROOT, "experiments", "exp3", "rg_summary", "cura_coupling.json")
os.makedirs(os.path.dirname(SUMMARY), exist_ok=True)
CHI0 = 50.0
REGIMES = ("scaled", "flat", "cura")


def _flatten(root, P1, SolitoneComposito):
    from dataclasses import replace as dc_replace
    def w(n):
        if isinstance(n, SolitoneComposito):
            n.physics = dc_replace(n.physics, alpha_K=P1.alpha_K,
                kappa_coupling=P1.kappa_coupling, lambda_exchange=P1.lambda_exchange,
                gamma_damping_base=P1.gamma_damping_base)
            for c in n.children:
                w(c)
    w(root)


def _measure(task):
    cm, seed, level, regime, pre, quench_steps, dt = task
    sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))
    import numpy as _np
    # SEED IDENTICO per i 3 regimi (stesso (cm,seed,level)) -> A/B pulito
    _np.random.seed(int(seed) + 100003 * int(round(cm)) + 7919 * int(level))
    from test_soglia_formazione import make
    from wqt_oop.physics_context import PhysicsContext
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    from wqt_oop.solitone_composito import SolitoneComposito
    P1 = PhysicsContext.for_level(1)

    t0 = time.time()
    sol = make(seed, chi_mean=cm, level=level)
    if regime in ("flat", "cura"):
        _flatten(sol, P1, SolitoneComposito)
    if regime == "cura":
        sol.set_ec_dynamics(True)
    step = sol.evolve_with_ec if regime == "cura" else sol.evolve

    # pre-evoluzione
    for _ in range(pre):
        sol.compute_hamiltonian(); step(dt)
    # quench manuale (raffreddamento velocita') -> congela i difetti
    def cool(node, f):
        if isinstance(node, SegmentoQuantistico):
            node.vel *= f
        else:
            for c in node.children:
                cool(c, f)
    for _ in range(quench_steps):
        sol.compute_hamiltonian(); step(dt); cool(sol, 0.9)

    # conta difetti sulle foglie
    leaves = []
    def walk(n):
        if isinstance(n, SegmentoQuantistico):
            leaves.append(float(n.chi))
        else:
            for c in n.children:
                walk(c)
    walk(sol)
    chi = _np.asarray(leaves)
    pozzo = CHI0 * (1.0 if _np.mean(chi) >= 0 else -1.0)
    n_def = int(_np.sum(_np.abs(chi - pozzo) > 0.6 * CHI0))
    n_leaves = len(chi)
    return {"cm": cm, "seed": seed, "level": level, "regime": regime,
            "n_def": n_def, "n_leaves": n_leaves, "dens": n_def / n_leaves,
            "chi_abs_max": float(_np.abs(chi).max()),
            "nan": bool(_np.any(_np.isnan(chi))), "t_s": time.time() - t0}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--chi-means", type=str, default="66,72")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--levels", type=str, default="1,2,3")
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=200)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    cms = [float(x) for x in args.chi_means.split(",")]
    levels = [int(x) for x in args.levels.split(",")]
    seeds = list(range(1, args.seeds + 1))
    dt = 0.01

    cache = {}
    if os.path.exists(SUMMARY):
        try:
            cache = {r["__key"]: r for r in json.load(open(SUMMARY))}
        except Exception:
            cache = {}

    tasks = []
    for cm in cms:
        for seed in seeds:
            for lev in levels:
                for reg in REGIMES:
                    key = f"{reg}_L{lev}_cm{cm:.0f}_s{seed}"
                    if key not in cache:
                        tasks.append((cm, seed, lev, reg, args.pre, args.quench_steps, dt))

    print("=" * 74)
    print("  TEST CURA: dissoluzione coupling (densita' difetti intensiva?)")
    print(f"  cm={cms} seeds={seeds} levels={levels} regimi={REGIMES}")
    print(f"  task da fare: {len(tasks)} (cache: {len(cache)}), workers={args.workers}")
    print("=" * 74)

    results = list(cache.values())
    if tasks:
        ctx = mp.get_context("spawn")
        t0 = time.time(); done = 0
        with ctx.Pool(args.workers) as pool:
            for r in pool.imap_unordered(_measure, tasks):
                r["__key"] = f"{r['regime']}_L{r['level']}_cm{r['cm']:.0f}_s{r['seed']}"
                results.append(r)
                done += 1
                el = time.time() - t0
                print(f"  [{done}/{len(tasks)}] {r['__key']:>22} dens={r['dens']:.4f} "
                      f"ndef={r['n_def']} nan={r['nan']} tq={r['t_s']:.0f}s "
                      f"ETA {el/done*(len(tasks)-done)/60:.1f}m", flush=True)
                json.dump(results, open(SUMMARY, "w"))
        print(f"\n  completato in {(time.time()-t0)/60:.1f} min")

    # --- AGGREGAZIONE: densita' media per (regime, level), su cm e seed ---
    print("\n  DENSITA' DIFETTI n_def/N media (intensiva se ~costante tra L):")
    print(f"  {'regime':>8} | " + " ".join(f"L{l:>8}" for l in levels))
    for reg in REGIMES:
        row = []
        for lev in levels:
            vals = [r["dens"] for r in results if r["regime"] == reg and r["level"] == lev]
            row.append(np.mean(vals) if vals else float("nan"))
        # coefficiente di variazione tra livelli (0 = perfettamente intensivo)
        rr = np.array(row); cv = (np.std(rr) / (np.mean(rr) + 1e-30)) if np.all(~np.isnan(rr)) else float("nan")
        print(f"  {reg:>8} | " + " ".join(f"{v:>9.4f}" for v in row) + f"   CV_tra_L={cv:.2f}")
    print("\n  LETTURA: se 'flat' ha CV_tra_L << 'scaled' -> appiattire i coupling rende")
    print("  la densita' INTENSIVA -> i coupling che corrono erano l'artefatto (dissolti).")
    print("  Se 'scaled' e 'flat' hanno CV simile -> la corsa di chi_c NON e' i coupling.")
    print(f"  Summary: {SUMMARY}")


if __name__ == "__main__":
    main()
