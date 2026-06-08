"""
================================================================================
P2 — FIT DI FLUSSO RG dai summary multi-livello (METODO_SCALING_RG.md)
================================================================================

Legge i summary prodotti da P1 (test_osservabili_rg.py) in rg_summary/
(osservabili_L2.json, _L3.json, _L4.json) e:

  [A] FSS di chi_c: fit chi_c(L)/chi_stable = c_inf + a * 24^(-lambda*L)
      -> valore ASINTOTICO c_inf (L->infinito) ed esponente di avvicinamento.
      Con 2 livelli: solo tabella + stima lineare in 1/N (no fit a 3 parametri).
      Con >=3 livelli: fit completo + estrapolazione.

  [B] Osservabili che fluiscono (rho_M, Psi_L) confrontati A EPSILON RIDOTTO
      UGUALE: eps = (chi_mean - chi_c)/chi_c. NON si confronta la media globale
      (dipende da chi_mean); si interpola ogni osservabile a un eps0 comune
      (default 0.05, appena sopra soglia) e si confronta tra livelli.
      CNG A: rho_M(eps0) invariante con L = punto fisso RG.

  [C] Test di consistenza del flusso (richiede >=3 livelli): la successione
      g_L = chi_c/stable e' geometrica? Se g_{L}-g_inf ~ r^L con r costante,
      la mappa RG e' stabile (estrapolabile). Stima g_inf e r.

E' SOLO analisi: nessun motore, nessuna modifica. Rieseguibile in ~1s.
Idempotente: rilegge i JSON ogni volta.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/analyze_rg_scaling.py
  python experiments/exp3/analyze_rg_scaling.py --eps0 0.08
================================================================================
"""

import os, sys, glob, json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUMMARY_DIR = os.path.join(ROOT, "experiments", "exp3", "rg_summary")
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHI_STABLE = 50.0


def load_summaries():
    """Ritorna lista di summary dict ordinati per livello."""
    out = []
    for f in sorted(glob.glob(os.path.join(SUMMARY_DIR, "osservabili_L*.json"))):
        try:
            with open(f) as fh:
                out.append(json.load(fh))
        except Exception as e:
            print(f"  ATTENZIONE: {f} illeggibile ({e})")
    return sorted(out, key=lambda d: d["level"])


def interp_at_eps(rows, chi_c, field, eps0):
    """Interpola field_mean a eps0 = (chi-chi_c)/chi_c. None se fuori range."""
    if chi_c is None:
        return None
    pts = []
    for r in rows:
        eps = (r["chi_mean"] - chi_c) / chi_c
        v = r.get(f"{field}_mean")
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            pts.append((eps, v))
    pts.sort()
    if len(pts) < 2:
        return None
    xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
    if eps0 < xs.min() or eps0 > xs.max():
        return None   # niente estrapolazione fuori dai dati
    return float(np.interp(eps0, xs, ys))


def main():
    import argparse
    ap = argparse.ArgumentParser(description="P2 - fit di flusso RG multi-livello")
    ap.add_argument("--eps0", type=float, default=0.05,
                    help="distanza ridotta comune per confrontare rho_M/Psi_L")
    args = ap.parse_args()

    sums = load_summaries()
    if not sums:
        print("  Nessun summary in rg_summary/. Eseguire prima P1 (test_osservabili_rg.py).")
        return

    L = np.array([s["level"] for s in sums], float)
    N = np.array([s["N"] for s in sums], float)
    gc = np.array([s["chi_c_over_stable"] if s["chi_c_over_stable"] else np.nan
                   for s in sums])
    gc_err = np.array([(s["chi_c_err"] / CHI_STABLE) if s.get("chi_c_err") else np.nan
                       for s in sums])

    print("=" * 70)
    print("  P2 - FLUSSO RG: chi_c/chi_stable vs livello")
    print("=" * 70)
    print(f"  {'L':>3} {'N':>8} {'chi_c/stable':>14} {'+-err':>8} {'t_quench(s)':>12}")
    for s, g, ge in zip(sums, gc, gc_err):
        tq = s.get("t_quench_s_mean", float('nan'))
        print(f"  {s['level']:>3} {s['N']:>8.0f} {g:>14.4f} {ge:>8.4f} {tq:>12.1f}")

    valid = ~np.isnan(gc)
    nval = int(valid.sum())

    # ---------- [A] FSS ----------
    c_inf = None
    print("\n  [A] Finite-Size Scaling di chi_c/stable")
    if nval >= 3:
        from scipy.optimize import curve_fit
        # chi_c(L) = c_inf + a * 24^(-lam*L)
        def fss(Lv, c_inf, a, lam): return c_inf + a * np.power(24.0, -lam * Lv)
        try:
            p0 = [gc[valid].min(), gc[valid][0] - gc[valid].min(), 0.3]
            popt, pcov = curve_fit(fss, L[valid], gc[valid], p0=p0,
                                   sigma=np.where(np.isnan(gc_err[valid]), 0.01, gc_err[valid]),
                                   absolute_sigma=True, maxfev=20000)
            perr = np.sqrt(np.diag(pcov))
            c_inf = popt[0]
            print(f"      chi_c/stable(L->inf) = {c_inf:.4f} +- {perr[0]:.4f}")
            print(f"      a = {popt[1]:.3f},  lambda = {popt[2]:.3f} +- {perr[2]:.3f}")
            print(f"      -> il punto critico ASINTOTICO estratto da {nval} livelli.")
        except Exception as e:
            print(f"      fit FSS fallito: {e}")
    elif nval == 2:
        # stima lineare in 1/N: chi_c = c_inf + b/N
        x = 1.0 / N[valid]; y = gc[valid]
        b = (y[1] - y[0]) / (x[1] - x[0]); c_inf_lin = y[0] - b * x[0]
        print(f"      Solo 2 livelli: stima LINEARE in 1/N (non un fit FSS robusto)")
        print(f"      chi_c/stable(L->inf) ~ {c_inf_lin:.4f}  (b={b:.2f})")
        print(f"      Serve un 3o livello (L4) per il fit a 3 parametri + esponente.")
        c_inf = c_inf_lin
    else:
        print(f"      Solo {nval} livello valido: impossibile estrapolare. Servono L2,L3(,L4).")

    # ---------- [C] consistenza del flusso (geometrico) ----------
    if nval >= 3:
        print("\n  [C] Test di consistenza del flusso (g_L geometrico?)")
        g = gc[valid]
        steps = np.diff(g)                  # g_{L+1}-g_L
        ratios = steps[1:] / steps[:-1]     # rapporto tra passi successivi
        print(f"      passi g_(L+1)-g_L: {', '.join(f'{s:+.4f}' for s in steps)}")
        print(f"      rapporti passi:    {', '.join(f'{r:.3f}' for r in ratios)}")
        if np.all(np.abs(ratios) < 1):
            print(f"      |rapporto|<1 -> flusso CONVERGENTE: punto fisso esiste, estrapolabile.")
        else:
            print(f"      |rapporto|>=1 -> flusso NON convergente o emergenza (deriva). Attenzione.")

    # ---------- [B] osservabili a epsilon ridotto uguale ----------
    print(f"\n  [B] Osservabili a eps ridotto UGUALE (eps0 = {args.eps0:+.3f})")
    print(f"      [confronto RG corretto: NON la media globale, che dipende da chi_mean]")
    print(f"      {'L':>3} {'rho_M(eps0)':>12} {'Psi_L(eps0)':>12}")
    rho_at, psi_at, Ls = [], [], []
    for s in sums:
        cc = s.get("chi_c")
        rM = interp_at_eps(s["rows"], cc, "rho_M", args.eps0)
        pL = interp_at_eps(s["rows"], cc, "Psi_L", args.eps0)
        sr = f"{rM:.3f}" if rM is not None else "  n/d"
        sp = f"{pL:.3e}" if pL is not None else "  n/d"
        print(f"      {s['level']:>3} {sr:>12} {sp:>12}")
        if rM is not None:
            rho_at.append(rM); Ls.append(s["level"]); psi_at.append(pL)
    if len(rho_at) >= 2:
        cv = np.std(rho_at) / (np.mean(rho_at) + 1e-30)
        print(f"      rho_M(eps0): CV tra livelli = {cv:.3f}  "
              f"({'~INVARIANTE (CNG A favorita)' if cv < 0.1 else 'VARIA con L (flusso)'})")

    # ---------- grafico ----------
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.errorbar(L[valid], gc[valid], yerr=np.where(np.isnan(gc_err[valid]), 0, gc_err[valid]),
                fmt="o", color="#d62728", ms=9, capsize=4, label="chi_c/stable misurato")
    if c_inf is not None and nval >= 3:
        Lf = np.linspace(L[valid].min(), L[valid].max() + 3, 100)
        from scipy.optimize import curve_fit
        def fss(Lv, c_inf, a, lam): return c_inf + a * np.power(24.0, -lam * Lv)
        try:
            popt, _ = curve_fit(fss, L[valid], gc[valid], p0=[gc[valid].min(),
                                gc[valid][0]-gc[valid].min(), 0.3], maxfev=20000)
            ax.plot(Lf, fss(Lf, *popt), "--", color="#1f77b4",
                    label=f"FSS -> {popt[0]:.3f}")
            ax.axhline(popt[0], color="gray", ls=":", alpha=0.6)
        except Exception:
            pass
    elif c_inf is not None:
        ax.axhline(c_inf, color="gray", ls=":", alpha=0.6, label=f"stima inf ~{c_inf:.3f}")
    ax.set_xlabel("livello L"); ax.set_ylabel("chi_c / chi_stable")
    ax.set_title("Flusso RG del punto critico (FSS)")
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIGDIR, "rg_flow_chi_c.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")
    print(f"  (Aggiungere L3 e L4 con P1 per il fit FSS completo e il test di flusso.)")


if __name__ == "__main__":
    main()
