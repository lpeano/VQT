"""
================================================================================
CARATTERIZZAZIONE DELLA "FEBBRE": legge di scala o artefatto?
================================================================================

OSSERVAZIONE (robusta a: serbatoio off, lambda off, TUTTI i coupling piatti):
la KE per-foglia cresce con la taglia del sistema   L1~625  L2~744  L3~832 ...
NON e' equipartizione banale (quella sarebbe INTENSIVA = piatta tra L). C'e' un
ECCESSO di energia per-nodo che cresce con N = 24^L.

IPOTESI DI LUCA: la febbre = la NECESSITA' DELLO SPAZIO DI ESPANDERSI. Piu' nodi
= piu' spazio = il "muratore di Planck" emette voxel = energia di espansione.

TEST: "puo' rappresentare" diventa "rappresenta" SOLO se la febbre segue una LEGGE
pulita e scale-coerente. Questo script:
  1. Misura KE/foglia a EQUILIBRIO (media sugli ultimi W step), L1..Lmax, multi-seed.
     -> conferma che e' uno STATO STAZIONARIO (eccesso), non un transiente che esplode.
  2. Fitta leggi candidate per KE_perleaf(L) con N=24^L:
       - potenza:  KE = A * N^a      (log KE lineare in L)   -> espansione "a potenza"
       - log:      KE = A + B*L       (lineare nel livello)
       - saturante: KE = Kinf - C r^L (tende a un asintoto)  -> taglia finita/artefatto
     Riporta R^2: una legge pulita (R^2~1, esponente semplice) = espansione;
     un numero che sbanda tra seed/livelli = artefatto.
  3. Diagnostica "equazione di stato": l'eccesso per-nodo e' costante (Lambda-like),
     cresce, o cala col volume? -> che TIPO di espansione.

Regime: chi_mean=54 (vuoto, dove la febbre si vede pulita), coupling LEGACY (la
febbre non dipende dai coupling: gia' verificato). Parallelo + resume.

ESECUZIONE:
  python experiments/exp3/test_legge_febbre.py --levels 1,2,3 --seeds 5 --steps 150
  python experiments/exp3/test_legge_febbre.py --levels 1,2,3,4 --seeds 3 --include-l4
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
SUMMARY = os.path.join(ROOT, "experiments", "exp3", "rg_summary", "legge_febbre.json")
os.makedirs(os.path.dirname(SUMMARY), exist_ok=True)


def _measure(task):
    level, seed, steps, warm_frac, chi_mean, dt = task
    sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))
    import numpy as _np
    _np.random.seed(int(seed) + 7919 * int(level))
    from test_soglia_formazione import make
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    t0 = time.time()
    sol = make(seed, chi_mean=chi_mean, level=level)

    def leaf_ke():
        vs, m = [], [None]
        def w(n):
            if isinstance(n, SegmentoQuantistico):
                vs.append(n.vel); m[0] = n.mass
            else:
                for c in n.children:
                    w(c)
        w(sol)
        v = _np.asarray(vs)
        return 0.5 * m[0] * float((v ** 2).mean()), len(v)

    warm = int(steps * warm_frac)
    traj = []          # KE/foglia campionata (per verificare stazionarieta')
    samples = []       # media a equilibrio
    for s in range(steps):
        sol.compute_hamiltonian(); sol.evolve(dt)
        ke, nleaf = leaf_ke()
        if s % max(1, steps // 12) == 0:
            traj.append(round(ke, 2))
        if s >= warm:
            samples.append(ke)
    ke_eq = float(_np.mean(samples)); ke_sd = float(_np.std(samples))
    return {"level": level, "seed": seed, "N": nleaf,
            "ke_perleaf": ke_eq, "ke_sd": ke_sd,
            "ke_total": ke_eq * nleaf, "traj": traj, "t_s": time.time() - t0}


def _fit_report(results, levels):
    # media su seed per livello
    L = np.array(levels, float)
    ke = np.array([np.mean([r["ke_perleaf"] for r in results if r["level"] == l]) for l in levels])
    sd = np.array([np.std([r["ke_perleaf"] for r in results if r["level"] == l]) for l in levels])
    N = np.array([24.0 ** l for l in levels])
    print("\n  KE/foglia a equilibrio (eccesso = crescita; equipartizione = piatto):")
    for i, l in enumerate(levels):
        print(f"    L{l}: N={int(N[i]):>8}  KE/foglia = {ke[i]:8.2f} +/- {sd[i]:5.2f}"
              + (f"   x{ke[i]/ke[0]:.3f} vs L1" if i else ""))
    if len(levels) < 2:
        return
    # rapporti tra livelli consecutivi
    rr = [ke[i+1]/ke[i] for i in range(len(ke)-1)]
    print(f"\n  rapporti consecutivi KE(L+1)/KE(L): {[round(x,3) for x in rr]}")
    print("    (costante -> legge a potenza pulita;  calante -> satura;  irregolare -> rumore)")

    def r2(y, yhat):
        ss = np.sum((y - np.mean(y))**2)
        return 1.0 - np.sum((y - yhat)**2)/ss if ss > 0 else float("nan")
    print("\n  FIT leggi candidate per KE/foglia(L):")
    # 1) potenza: log ke = log A + a*log N
    a, logA = np.polyfit(np.log(N), np.log(ke), 1)
    yhat = np.exp(logA + a*np.log(N))
    print(f"    potenza  KE = {np.exp(logA):.2f} * N^{a:.4f}   R^2={r2(ke,yhat):.4f}"
          f"   (a piccolo>0 = espansione debole; a~0 = intensivo)")
    # 2) log: ke = A + B*L
    B, A = np.polyfit(L, ke, 1)
    yhat = A + B*L
    print(f"    log/lin  KE = {A:.2f} + {B:.2f}*L                R^2={r2(ke,yhat):.4f}")
    # 3) saturante (se >=3 livelli): ke = Kinf - C r^L, stima grezza via rapporti diff
    if len(levels) >= 3:
        d = np.diff(ke)
        if d[0] != 0 and np.all(d > 0):
            r = d[1]/d[0]
            if 0 < r < 1:
                Kinf = ke[-1] + d[-1]*r/(1-r)
                print(f"    saturante KE -> Kinf ~ {Kinf:.1f} (r={r:.3f})"
                      f"   -> ASINTOTO FINITO = sospetto taglia finita/artefatto")
            else:
                print(f"    saturante: r={r:.3f} (>=1) -> NON satura -> cresce davvero")
    # --- analisi ENERGIA IN ECCESSO tra livelli (proposta Gemini) ---
    # E_tot(L) = KE/foglia(L) * N(L); eccesso(L) = E_tot(L) - E_tot(L-1).
    # Classifica: ~costante (vuoto/cosmologica) | ~N(L) (densita' costante) |
    #             ~E_tot(L-1) (cascata moltiplicativa).
    if len(levels) >= 3:
        Etot = ke * N
        exc = np.diff(Etot)                 # eccesso L2-L1, L3-L2, ...
        Nhi = N[1:]; Eprev = Etot[:-1]
        print("\n  ENERGIA IN ECCESSO tra livelli  eccesso(L)=E_tot(L)-E_tot(L-1):")
        for i in range(len(exc)):
            print(f"    L{levels[i]}->L{levels[i+1]}: eccesso={exc[i]:.3e}  "
                  f"eccesso/N(L)={exc[i]/Nhi[i]:.3f}  eccesso/E_tot(L-1)={exc[i]/Eprev[i]:.3f}")
        if len(exc) >= 2:
            cv_const = np.std(exc)/(np.mean(exc)+1e-30)
            cv_perN  = np.std(exc/Nhi)/(np.mean(exc/Nhi)+1e-30)
            cv_casc  = np.std(exc/Eprev)/(np.mean(exc/Eprev)+1e-30)
            print(f"\n  stabilita' (CV piu' basso = legge piu' pulita):")
            print(f"    eccesso ~ costante         CV={cv_const:.3f}  (vuoto/cosmologica)")
            print(f"    eccesso ~ N(L)             CV={cv_perN:.3f}  (densita' costante)")
            print(f"    eccesso ~ E_tot(L-1)       CV={cv_casc:.3f}  (cascata moltiplicativa)")
            best = min([("costante/cosmologica", cv_const), ("densita' costante ~N", cv_perN),
                        ("cascata moltiplicativa ~E(L-1)", cv_casc)], key=lambda x: x[1])
            print(f"    -> legge piu' compatibile: {best[0]} (CV={best[1]:.3f})")

    print("\n  LETTURA: legge pulita (R^2~1, esponente/rapporto stabile, NON satura)")
    print("    -> compatibile con ESPANSIONE.  Asintoto finito o rumore -> artefatto.")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=str, default="1,2,3")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--warm-frac", type=float, default=0.6)
    ap.add_argument("--chi-mean", type=float, default=54.0)
    ap.add_argument("--include-l4", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    levels = [int(x) for x in args.levels.split(",")]
    if 4 in levels and not args.include_l4:
        print("  L4 escluso (costoso). Usa --include-l4 per includerlo."); levels = [l for l in levels if l != 4]
    seeds = list(range(1, args.seeds + 1)); dt = 0.01

    cache = {}
    if os.path.exists(SUMMARY):
        try:
            cache = {r["__key"]: r for r in json.load(open(SUMMARY))}
        except Exception:
            cache = {}
    tasks = []
    for lev in levels:
        for seed in seeds:
            key = f"L{lev}_s{seed}_st{args.steps}_cm{args.chi_mean:.0f}"
            if key not in cache:
                tasks.append((lev, seed, args.steps, args.warm_frac, args.chi_mean, dt))

    print("=" * 74)
    print("  LEGGE DELLA FEBBRE: KE/foglia vs taglia (espansione o artefatto?)")
    print(f"  levels={levels} seeds={seeds} steps={args.steps} chi_mean={args.chi_mean}")
    print(f"  task: {len(tasks)} (cache {len(cache)}), workers={args.workers}")
    print("=" * 74)

    results = list(cache.values())
    if tasks:
        ctx = mp.get_context("spawn")
        t0 = time.time(); done = 0
        with ctx.Pool(args.workers) as pool:
            for r in pool.imap_unordered(_measure, tasks):
                r["__key"] = f"L{r['level']}_s{r['seed']}_st{args.steps}_cm{args.chi_mean:.0f}"
                results.append(r); done += 1
                el = time.time() - t0
                print(f"  [{done}/{len(tasks)}] L{r['level']} s{r['seed']} "
                      f"KE/foglia={r['ke_perleaf']:.1f}+/-{r['ke_sd']:.1f} N={r['N']} "
                      f"t={r['t_s']:.0f}s ETA {el/done*(len(tasks)-done)/60:.1f}m", flush=True)
                json.dump(results, open(SUMMARY, "w"))
        print(f"\n  completato in {(time.time()-t0)/60:.1f} min")

    _fit_report([r for r in results if r["level"] in levels], levels)
    print(f"\n  Summary: {SUMMARY}")


if __name__ == "__main__":
    main()
