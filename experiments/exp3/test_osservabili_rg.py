"""
================================================================================
P1 — STRUMENTO MULTI-OSSERVABILE per il PROGRAMMA RG (METODO_SCALING_RG.md)
================================================================================

SCOPO: misurare, allo STESSO livello L e sullo stesso ensemble di quench, TUTTI
gli osservabili che "fluiscono" con la scala, cosi' da poterli confrontare tra
L2, L3, L4 (i tre punti del flusso RG). E' il prerequisito di:
  - CNG A (invarianza di Gamma / rho_M = punto fisso RG)
  - CNG B (stabilita' della chiusura: Psi_L = M_tot / N_dof, closure_err)
  - il fit FSS di chi_c e l'esponente di scala di E_Psi
Riferimenti: docs/peano/METODO_SCALING_RG.md (P1-P5),
             basimatematiche/teorema_peano_vqt.md (CNG A/B, TEO 2).

COSA MISURA (per ogni quench (chi_mean, seed), su STATO CONGELATO):
  - M_tot            : massa topologica aggregata (compute_hierarchical_mass)
  - rho_M            : densita' di massa = M_tot / n_foglie  [CNG A: ~invariante?]
  - Psi_L            : difetto di chiusura = M_tot / N_dof    [CNG B: ->0?]
  - localization_ratio, regime : particella vs campo
  - E_RX (=E_tors), E_psi_anchored, frustration (CV)          [triade, TEO 4]
  - closure_err_norm, detorsion_quality : misure di chiusura  [TEO 3 / CNG B]
  - n_def            : nodi deviati dal pozzo dominante (per esponente p)
  - t_quench_s       : tempo di parete del quench  [decide se serve vettorizzare L4]

NB SCOPO VETTORIZZAZIONE: girando P1 a L4 si ottiene t_quench_s REALE a L4 -> e'
il numero che decide se la Strategia B (vettorizzazione leggera) serve davvero
per la campagna di calibrazione, o se il parallelismo gia' presente basta.

CODICE ADDITIVO: nessuna modifica al motore. Riusa freeze_and_measure_mass,
compute_hierarchical_mass, compute_geometric_E_psi (intatti) + lo scheletro
parallelo/resume gia' validato (test_termodinamica_kink_par.py, GATE PASS).

DETERMINISMO: np.random.seed(seed + 100003*cm) per-task (come gli altri script
paralleli) -> riproducibile e seriale == parallelo.

ESECUZIONE:
  cd VQT_repo
  # smoke test L2 (veloce):
  python experiments/exp3/test_osservabili_rg.py --level 2 --seeds 3 \
      --chi-means 64,68,72 --workers 4
  # campagna L3:
  python experiments/exp3/test_osservabili_rg.py --level 3 --seeds 10 \
      --chi-means 58,60,62,64,66,68 --workers 6
  # singolo quench L4 per il TEMPO (decide vettorizzazione):
  python experiments/exp3/test_osservabili_rg.py --level 4 --seeds 1 \
      --chi-means 62 --workers 1
  # Ripresa dopo interruzione: STESSO comando (resume crash-safe).
================================================================================
"""

import sys, os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import warnings, logging, time, json
import multiprocessing as mp

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))

RESUME_DIR = os.path.join(ROOT, "experiments", "exp3", "resume")
SUMMARY_DIR = os.path.join(ROOT, "experiments", "exp3", "rg_summary")
os.makedirs(SUMMARY_DIR, exist_ok=True)
MTOT_MIN = 1.0
CHI_STABLE = 50.0


# ---------------------------------------------------------------------------
# PERSISTENZA RESUME (minimale, crash-safe). ResumeManager e' specializzato
# (salva solo mtot + neff_dict di conteggi), qui servono osservabili arbitrari.
# Un file JSON per (livello, chi_mean): { str(seed): obs_dict }.
# Scrittura atomica via .tmp + os.replace; copia .bak prima di sovrascrivere.
# ---------------------------------------------------------------------------
import shutil

def _resume_path(level, cm):
    return os.path.join(RESUME_DIR, f"osservabili_L{level}_cm{cm:.0f}.json")

def _load_resume(path):
    for p in (path, path + ".bak"):
        if os.path.exists(p):
            try:
                with open(p) as fh:
                    return json.load(fh)
            except Exception:
                continue
    return {}

def _save_resume(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh)
    if os.path.exists(path):
        try:
            shutil.copy2(path, path + ".bak")
        except Exception:
            pass
    os.replace(tmp, path)   # rename atomico


# ---------------------------------------------------------------------------
# WORKER: misura TUTTI gli osservabili per un singolo (chi_mean, seed).
# Funzione top-level (pickling multiprocessing su Windows/spawn).
# ---------------------------------------------------------------------------
def _measure_one(task):
    cm, seed, level, pre, quench_steps, dt = task
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))
    import numpy as _np
    _np.random.seed(int(seed) + 100003 * int(round(cm)))  # determinismo per-task
    from wqt_oop.energy_metrics import (freeze_and_measure_mass,
                                        compute_hierarchical_mass,
                                        compute_geometric_E_psi)
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    from test_soglia_formazione import make

    t0 = time.time()
    sol = make(seed, chi_mean=cm, level=level)
    for _ in range(pre):
        sol.compute_hamiltonian(); sol.evolve(dt)
    r = freeze_and_measure_mass(sol, max_steps=quench_steps, dt=dt, return_frozen=True)
    frozen = r["frozen"]
    hm = compute_hierarchical_mass(frozen)
    gp = compute_geometric_E_psi(frozen)        # closure/torsione al top
    t_quench = time.time() - t0

    # --- conteggio difetti puntuali sulle FOGLIE (per esponente p) ---
    chi0 = getattr(frozen.physics, "chi_stable", CHI_STABLE)
    leaves = []
    def _walk(n):
        if isinstance(n, SegmentoQuantistico):
            leaves.append(float(n.chi))
        else:
            for c in n.children:
                _walk(c)
    _walk(frozen)
    chi = _np.asarray(leaves)
    pozzo = chi0 * (1.0 if _np.mean(chi) >= 0 else -1.0)
    n_def = int(_np.sum(_np.abs(chi - pozzo) > 0.6 * chi0))

    n_leaves = int(hm["n_leaves"])
    N_dof = 2 * n_leaves
    M_tot = float(hm["M_tot"])

    obs = {
        "M_tot": M_tot,
        "rho_M": float(hm["rho_M"]),
        "Psi_L": M_tot / max(N_dof, 1),                 # CNG B: difetto chiusura / dof
        "localization_ratio": float(hm["localization_ratio"]),
        "regime": str(hm["regime"]),
        "IPR": float(hm["IPR"]),
        "n_eff": float(hm["n_eff"]),
        "E_RX": float(gp["E_tors"]),                    # energia reattiva (torsione)
        "E_psi_anchored": float(gp["E_psi_anchored"]),
        "frustration": float(gp["frustration"]),
        "closure_err_norm": float(gp["closure_err_norm"]),
        "detorsion_quality": float(gp["detorsion_quality"]),
        "n_def": n_def,
        "n_leaves": n_leaves,
        "converged": bool(r["converged"]),
        "t_quench_s": float(t_quench),
    }
    return (cm, seed, obs)


# ---------------------------------------------------------------------------
def _sem(a):
    a = np.asarray(a, float)
    return float(a.std() / np.sqrt(len(a))) if len(a) > 1 else 0.0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="P1 - osservabili multi-scala per RG")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--chi-means", type=str, default="62,64,66,68,70,72")
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

    print("=" * 80)
    print("  P1 - OSSERVABILI MULTI-SCALA (programma RG)")
    print(f"  L{args.level} (N={N})  |  {len(seeds)} seed/punto  |  "
          f"{len(chi_means)} punti  |  workers={n_workers}")
    print("=" * 80)

    # --- raccogli i task mancanti (resume) ---
    resume, paths, pending, n_cached = {}, {}, [], 0
    for cm in chi_means:
        p = _resume_path(args.level, cm)
        paths[cm] = p
        resume[cm] = _load_resume(p)
        for seed in seeds:
            if str(seed) in resume[cm]:
                n_cached += 1
            else:
                pending.append((cm, seed, args.level, args.pre, args.quench_steps, dt))

    total = len(chi_means) * len(seeds)
    print(f"\n  Task totali: {total}  |  gia' fatti: {n_cached}  |  "
          f"da calcolare: {len(pending)}")

    if pending:
        print(f"  Avvio pool con {n_workers} worker...\n")
        t0 = time.time(); done = 0
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=n_workers) as pool:
            try:
                for (cm, seed, obs) in pool.imap_unordered(_measure_one, pending):
                    resume[cm][str(seed)] = obs
                    _save_resume(paths[cm], resume[cm])   # persistenza immediata
                    done += 1
                    el = time.time() - t0
                    eta = el / done * (len(pending) - done)
                    flag = "KINK" if obs["M_tot"] > MTOT_MIN else "----"
                    print(f"  [{done:>3}/{len(pending)}] cm{cm:.0f} seed{seed:<2} "
                          f"M_tot={obs['M_tot']:.2e} {flag} "
                          f"tq={obs['t_quench_s']:.1f}s | "
                          f"el {el/60:.1f}m ETA {eta/60:.1f}m", flush=True)
            except KeyboardInterrupt:
                print("\n  INTERROTTO. Stato salvato: rilanciare lo stesso comando.")
                pool.terminate(); pool.join(); return
        print(f"\n  Calcolo completato in {(time.time()-t0)/60:.1f} min.")
    else:
        print("  Tutti i seed gia' calcolati (resume completo).")

    # --- AGGREGAZIONE per livello ---
    from scipy.optimize import curve_fit
    def logistic(x, xc, w): return 1.0 / (1.0 + np.exp(-(x - xc) / w))

    rows = []   # per chi_mean: medie + sem degli osservabili
    fields = ["rho_M", "Psi_L", "localization_ratio", "E_RX", "E_psi_anchored",
              "frustration", "closure_err_norm", "detorsion_quality", "n_def",
              "t_quench_s"]
    chi_arr, frac_arr = [], []
    for cm in chi_means:
        recs = [resume[cm][str(s)] for s in seeds if str(s) in resume[cm]]
        if not recs:
            continue
        mt = np.array([r["M_tot"] for r in recs])
        frac = float(np.mean(mt > MTOT_MIN))
        chi_arr.append(cm); frac_arr.append(frac)
        row = {"chi_mean": cm, "n_seed": len(recs), "frac_kink": frac}
        for f in fields:
            vals = [r[f] for r in recs if f in r]
            row[f"{f}_mean"] = float(np.mean(vals)) if vals else float("nan")
            row[f"{f}_sem"] = _sem(vals) if vals else 0.0
        rows.append(row)

    chi_arr = np.array(chi_arr, float); frac_arr = np.array(frac_arr)

    # --- chi_c dalla frazione di nucleazione (logistico) ---
    chi_c = chi_c_err = w = None
    if np.any(frac_arr > 0.5) and np.any(frac_arr < 0.5):
        try:
            guess = chi_arr[np.argmin(np.abs(frac_arr - 0.5))]
            popt, pcov = curve_fit(logistic, chi_arr, frac_arr, p0=[guess, 2.0], maxfev=8000)
            perr = np.sqrt(np.diag(pcov))
            chi_c, chi_c_err, w = float(popt[0]), float(perr[0]), float(abs(popt[1]))
        except Exception as e:
            print(f"  fit chi_c fallito: {e}")

    # --- STAMPA tabella osservabili ---
    print("\n  " + "=" * 76)
    print(f"  OSSERVABILI L{args.level} (media +- sem per chi_mean)")
    print("  " + "-" * 76)
    print(f"  {'chi':>4} {'frac':>5} {'rho_M':>8} {'Psi_L':>9} {'loc_r':>7} "
          f"{'clos_err':>8} {'n_def':>6} {'tq(s)':>7}")
    for r in rows:
        print(f"  {r['chi_mean']:>4.0f} {r['frac_kink']:>5.2f} "
              f"{r['rho_M_mean']:>8.3f} {r['Psi_L_mean']:>9.2e} "
              f"{r['localization_ratio_mean']:>7.1f} "
              f"{r['closure_err_norm_mean']:>8.4f} "
              f"{r['n_def_mean']:>6.1f} {r['t_quench_s_mean']:>7.1f}")

    # medie globali degli osservabili "di scala" (per il confronto inter-livello)
    def _gmean(f):
        vals = [r[f"{f}_mean"] for r in rows if not np.isnan(r[f"{f}_mean"])]
        return float(np.mean(vals)) if vals else float("nan")

    tq_mean = _gmean("t_quench_s")
    print("\n  " + "=" * 76)
    if chi_c is not None:
        print(f"  chi_c/chi_stable L{args.level} = {chi_c/CHI_STABLE:.3f} "
              f"(chi_c={chi_c:.2f} +- {chi_c_err:.2f}, w={w:.2f})")
        print(f"    confronto: L2=1.338, L3=1.240 (da sessioni precedenti)")
    else:
        print(f"  chi_c non determinato (frazione non attraversa 0.5 nel range)")
    print(f"  TEMPO MEDIO per quench a L{args.level}: {tq_mean:.1f} s")
    if args.level >= 4:
        print(f"    -> NUMERO CHIAVE per decidere la vettorizzazione (Strategia B).")
        print(f"    Campagna esempio (10 punti x 30 seed = 300 quench) / {n_workers} "
              f"worker ~ {300*tq_mean/n_workers/3600:.1f} h.")

    # --- SALVA summary JSON (per il fit RG inter-livello, P2/P3) ---
    summary = {
        "level": args.level, "N": N, "n_dof": 2 * N,
        "chi_c": chi_c, "chi_c_err": chi_c_err, "chi_c_over_stable":
            (chi_c / CHI_STABLE if chi_c else None),
        "t_quench_s_mean": tq_mean,
        "rho_M_global": _gmean("rho_M"),
        "Psi_L_global": _gmean("Psi_L"),
        "rows": rows,
    }
    out = os.path.join(SUMMARY_DIR, f"osservabili_L{args.level}.json")
    with open(out, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\n  Summary salvato: {out}")
    print(f"  (P2/P3 leggeranno i summary L2/L3/L4 per il fit di flusso RG.)")


if __name__ == "__main__":
    main()
