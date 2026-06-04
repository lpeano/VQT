"""
================================================================================
ANALISI TERMODINAMICA — aggrega tutti gli archivi e produce la curva n(chi_mean)
================================================================================

Cosa fa e perche':
  Script di ANALISI (idempotente) separato dalla RACCOLTA dati
  (test_termodinamica_kink.py). Legge tutti i file di resume archiviati
  (resume/termodinamica_L{level}_cm*_done_*.json), per ogni chi_mean prende
  l'archivio piu' recente, calcola:
    - frazione di nucleazione (kink se M_tot > MTOT_MIN)
    - cooperativity (varianza osservata / binomiale indipendente)
    - M_tot medio dei kink
  Poi stima chi_c (dove n=0.5) e l'esponente KZ nu via fit log-log, e produce
  il grafico completo della curva di nucleazione.

  Vantaggio: rieseguibile in ~1s senza ricalcolare i quench. Permette di
  cambiare MTOT_MIN o la logica di analisi senza toccare la simulazione.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/analyze_termodinamica.py
  python experiments/exp3/analyze_termodinamica.py --level 2 --mtot-min 1.0
================================================================================
"""

import sys, os, glob, re, json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESUME_DIR = os.path.join(ROOT, "experiments", "exp3", "resume")
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHI_STABLE = 50.0


def load_latest_archives(level, exclude_before=None):
    """
    Per ogni chi_mean, trova l'archivio _done_ piu' recente.
    exclude_before: stringa timestamp (es. '20260604_13'); gli archivi con
    timestamp che inizia con valori < questo vengono ignorati (per scartare
    smoke test vecchi). Default None = prende tutti.
    Ritorna dict {chi_mean: [lista mtot]}.
    """
    pattern = os.path.join(RESUME_DIR, f"termodinamica_L{level}_cm*_done_*.json")
    files = glob.glob(pattern)
    # raggruppa per chi_mean, tieni il timestamp piu' alto
    best = {}  # cm -> (timestamp_str, path)
    for f in files:
        m = re.search(rf"cm(\d+)_done_(\d+_\d+)", os.path.basename(f))
        if not m:
            continue
        cm = int(m.group(1))
        ts = m.group(2)
        if exclude_before and ts < exclude_before:
            continue
        if cm not in best or ts > best[cm][0]:
            best[cm] = (ts, f)

    # include anche eventuali file attivi (non ancora archiviati)
    active = glob.glob(os.path.join(RESUME_DIR, f"termodinamica_L{level}_cm*.json"))
    for f in active:
        if "_done_" in f:
            continue
        m = re.search(rf"cm(\d+)\.json", os.path.basename(f))
        if not m:
            continue
        cm = int(m.group(1))
        # un file attivo e' piu' recente di qualsiasi archivio
        best[cm] = ("99999999_9999", f)

    data = {}
    for cm, (ts, path) in best.items():
        d = json.load(open(path))
        data[cm] = [v["mtot"] for v in d.values()]
    return data


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Aggrega e analizza i dati termodinamici")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--mtot-min", type=float, default=1.0,
                    help="soglia M_tot per classificare un kink (default 1.0)")
    ap.add_argument("--exclude-before", type=str, default="20260604_1400",
                    help="ignora archivi con timestamp < questo (scarta smoke test vecchi)")
    args = ap.parse_args()

    data = load_latest_archives(args.level, exclude_before=args.exclude_before)
    if not data:
        print("  Nessun dato trovato in resume/. Eseguire prima test_termodinamica_kink.py")
        return

    cms = sorted(data.keys())
    print("=" * 70)
    print(f"  ANALISI TERMODINAMICA L{args.level}  |  soglia kink: M_tot > {args.mtot_min}")
    print("=" * 70)
    print(f"  {'chi_mean':>8} {'n_kink/tot':>11} {'frazione':>9} {'coop':>6} {'M_tot_medio':>12}")
    print("  " + "-" * 52)

    chi_arr, frac_arr, coop_arr = [], [], []
    for cm in cms:
        mt = np.array(data[cm])
        n = len(mt)
        nk = int(np.sum(mt > args.mtot_min))
        frac = nk / n
        # cooperativity: varianza empirica / binomiale p(1-p)
        binary = (mt > args.mtot_min).astype(float)
        var_emp = float(np.var(binary))
        var_binom = frac * (1 - frac)
        coop = var_emp / (var_binom + 1e-30) if var_binom > 1e-9 else 1.0
        km = mt[mt > args.mtot_min]
        avg = float(np.mean(km)) if len(km) else 0.0
        chi_arr.append(cm); frac_arr.append(frac); coop_arr.append(coop)
        bar = "#" * int(frac * 20)
        print(f"  {cm:>8} {nk:>5}/{n:<5} {frac:>9.2f} {coop:>6.2f} {avg:>12.2e}  {bar}")

    chi_arr = np.array(chi_arr, float)
    frac_arr = np.array(frac_arr)

    # --- chi_c (n=0.5) ---
    chi_c = None
    for i in range(len(chi_arr) - 1):
        if (frac_arr[i] - 0.5) * (frac_arr[i+1] - 0.5) <= 0 and frac_arr[i] != frac_arr[i+1]:
            t = (0.5 - frac_arr[i]) / (frac_arr[i+1] - frac_arr[i])
            chi_c = chi_arr[i] + t * (chi_arr[i+1] - chi_arr[i])
            break

    print("\n  " + "=" * 64)
    if chi_c is not None:
        print(f"  chi_c (n=0.5): {chi_c:.2f}  (chi_c/chi_stable = {chi_c/CHI_STABLE:.3f})")
    else:
        if np.all(frac_arr < 0.5):
            print(f"  chi_c NON raggiunto: tutti i punti < 50% (estendere sweep verso l'alto)")
        elif np.all(frac_arr > 0.5):
            print(f"  chi_c sotto il range (estendere sweep verso il basso)")

    # --- fit KZ ---
    nu = None
    if chi_c is not None:
        eps = (chi_arr - chi_c) / CHI_STABLE
        valid = (frac_arr > 0.05) & (frac_arr < 0.95) & (eps > 0)
        if np.sum(valid) >= 3:
            lx, ly = np.log(eps[valid]), np.log(frac_arr[valid])
            nu, lk = np.polyfit(lx, ly, 1)
            r2 = 1 - np.sum((ly - (nu*lx+lk))**2) / (np.sum((ly-ly.mean())**2)+1e-30)
            print(f"  Esponente KZ:  nu = {nu:.3f}  (R2 = {r2:.3f}, {int(np.sum(valid))} punti)")
            if abs(nu - 1.0) < 0.2:
                print("  -> nu ~ 1: coerente con phi^4 1D classico (Kibble-Zurek).")
            else:
                print(f"  -> nu = {nu:.2f}: deviazione dal phi^4 classico.")
        else:
            print(f"  Fit KZ: solo {int(np.sum(valid))} punti nella zona 5%-95% "
                  f"(servono >=3; rifinire lo sweep attorno a chi_c).")

    # --- cooperativity ---
    coop_arr = np.array(coop_arr)
    near_c = (frac_arr > 0.1) & (frac_arr < 0.9)
    if np.any(near_c):
        coop_mean = float(np.mean(coop_arr[near_c]))
        print(f"  Cooperativity media (zona transizione): {coop_mean:.2f} "
              f"(1=indipendente, >1=cooperativa)")

    # --- grafico ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    ax1.plot(chi_arr, frac_arr, "o-", color="#d62728", ms=8)
    ax1.axhline(0.5, color="gray", ls=":", alpha=0.6)
    if chi_c is not None:
        ax1.axvline(chi_c, color="blue", ls="--", label=f"chi_c={chi_c:.1f}")
    ax1.set_xlabel("chi_mean"); ax1.set_ylabel("frazione nucleazione (M_tot>1)")
    ax1.set_title(f"Curva di nucleazione energetica L{args.level}")
    ax1.set_ylim(-0.05, 1.05); ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    if nu is not None:
        eps = (chi_arr - chi_c) / CHI_STABLE
        valid = (frac_arr > 0.05) & (frac_arr < 0.95) & (eps > 0)
        ax2.loglog(eps[valid], frac_arr[valid], "o", color="#d62728", ms=8, label="dati")
        ef = np.linspace(eps[valid].min(), eps[valid].max(), 50)
        ax2.loglog(ef, np.exp(lk)*ef**nu, "--", color="#1f77b4",
                   label=f"n~eps^{nu:.2f}")
        ax2.set_xlabel("epsilon=(chi-chi_c)/chi_stable"); ax2.set_ylabel("n")
        ax2.set_title(f"Fit KZ: nu={nu:.3f}")
        ax2.legend(fontsize=8); ax2.grid(alpha=0.3, which="both")
    else:
        ax2.plot(chi_arr, coop_arr, "s-", color="#2ca02c")
        ax2.axhline(1.0, color="gray", ls=":")
        ax2.set_xlabel("chi_mean"); ax2.set_ylabel("cooperativity")
        ax2.set_title("Cooperativity (1=indip., >1=cooperativa)")
        ax2.grid(alpha=0.3)

    fig.suptitle(f"Termodinamica delle pareti L{args.level} (aggregato)",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"termodinamica_aggregata_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
