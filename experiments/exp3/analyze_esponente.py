"""
================================================================================
ANALISI ESPONENTE CRITICO — n_def ~ (chi-chi_c)^p, con chi_c INDIPENDENTE
================================================================================

Protocollo rigoroso (post-processing dello sweep fitto critico):
  1. chi_c determinato dalla FRAZIONE BINARIA di nucleazione (M_tot>1) via fit
     logistico -> fonte INDIPENDENTE da n_def (rompe la degenerazione p<->chi_c).
  2. Fit potenza di n_def con chi_c FISSO, solo punti SOPRA soglia (esclude il
     fondo sotto-soglia dove la legge critica non vale).
  3. TEST DI SENSIBILITA': varia chi_c entro le sue barre, mostra il range di p.
     Le barre vere su p includono questa variazione, non solo l'errore del fit.
  4. Errore standard onesto (std/sqrt(N)) per ogni punto.

Lo script e' idempotente: legge i resume densita_L2_cm*.json (campo mtot=n_def,
neff_dict.M.n_eff=M_tot). Rieseguibile in ~1s.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/analyze_esponente.py
  python experiments/exp3/analyze_esponente.py --chi-means 64,65,66,67,68,69,70,71,72,74
================================================================================
"""

import sys, os, json, glob
import numpy as np
from scipy.optimize import curve_fit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESUME_DIR = os.path.join(ROOT, "experiments", "exp3", "resume")
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHI_STABLE = 50.0


def load(level, chi_means):
    """Ritorna dict cm -> (n_def array, M_tot array)."""
    out = {}
    for cm in chi_means:
        fs = glob.glob(os.path.join(RESUME_DIR, f"densita_L{level}_cm{cm:.0f}*.json"))
        if not fs:
            continue
        # prendi il file con piu' seed (il piu' recente/completo)
        best = max(fs, key=lambda f: len(json.load(open(f))))
        d = json.load(open(best))
        ndef = np.array([v["mtot"] for v in d.values()])
        mtot = np.array([v.get("neff_dict", {}).get("M", {}).get("n_eff", np.nan)
                         for v in d.values()])
        out[cm] = (ndef, mtot)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Analisi esponente critico con chi_c indipendente")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--chi-means", type=str,
                    default="64,65,66,67,68,69,70,71,72,74")
    args = ap.parse_args()
    chi_means = [float(x) for x in args.chi_means.split(",")]

    data = load(args.level, chi_means)
    if not data:
        print("  Nessun dato. Eseguire prima test_densita_difetti.py")
        return
    cms = np.array(sorted(data.keys()))
    ndef_mean = np.array([data[c][0].mean() for c in cms])
    ndef_sem = np.array([data[c][0].std()/np.sqrt(len(data[c][0])) for c in cms])
    frac_kink = np.array([np.mean(data[c][1] > 1) for c in cms])
    nseed = np.array([len(data[c][0]) for c in cms])

    print("=" * 68)
    print(f"  ANALISI ESPONENTE CRITICO  L{args.level}")
    print("=" * 68)
    print(f"  {'chi':>5} {'n_seed':>7} {'frac_kink':>10} {'n_def':>8} {'+-sem':>7}")
    print("  " + "-" * 44)
    for c, ns, fk, nm, ne in zip(cms, nseed, frac_kink, ndef_mean, ndef_sem):
        print(f"  {c:>5.0f} {ns:>7} {fk:>10.2f} {nm:>8.2f} {ne:>7.2f}")

    # --- 1. chi_c dalla FRAZIONE BINARIA (indipendente) ---
    print("\n  [1] chi_c da frazione di nucleazione binaria (M_tot>1):")
    def logistic(x, xc, w): return 1.0/(1.0+np.exp(-(x-xc)/w))
    chi_c, chi_c_err = None, 0.5
    try:
        # serve che frac attraversi 0.5
        if frac_kink.min() < 0.5 < frac_kink.max():
            popt, pcov = curve_fit(logistic, cms, frac_kink, p0=[67, 1.0], maxfev=10000)
            chi_c, w_bin = popt
            chi_c_err = np.sqrt(pcov[0, 0])
            print(f"      chi_c = {chi_c:.2f} +- {chi_c_err:.2f}  (chi_c/stable={chi_c/CHI_STABLE:.3f})")
        else:
            chi_c = cms[np.argmin(np.abs(frac_kink-0.5))]
            print(f"      frazione non attraversa 0.5 pulito; uso chi_c~{chi_c:.0f}")
    except Exception as e:
        chi_c = 67.0
        print(f"      fit binario fallito ({e}); fallback chi_c=67")

    # --- 2. fit potenza n_def con chi_c FISSO, solo sopra soglia ---
    print(f"\n  [2] Fit potenza n_def ~ A*((chi-chi_c)/chi_c)^p  (chi_c={chi_c:.2f} fisso):")
    def power(chi, A, p, xc):
        e = np.maximum((chi-xc)/xc, 1e-9)
        return A*np.power(e, p)

    def fit_p(xc):
        mask = (cms > xc) & (ndef_mean > 0.05)  # solo sopra soglia, n_def non-zero
        if mask.sum() < 3:
            return None
        x, y, s = cms[mask], ndef_mean[mask], ndef_sem[mask]
        try:
            popt, pcov = curve_fit(lambda chi, A, p: power(chi, A, p, xc),
                                   x, y, p0=[50, 1.5], sigma=s+1e-3,
                                   absolute_sigma=True, maxfev=10000)
            pred = power(x, popt[0], popt[1], xc)
            r2 = 1-np.sum((y-pred)**2)/np.sum((y-y.mean())**2)
            return popt[1], np.sqrt(pcov[1,1]), int(mask.sum()), r2
        except Exception:
            return None

    res = fit_p(chi_c)
    if res:
        p, p_fiterr, npts, r2 = res
        print(f"      p = {p:.2f} +- {p_fiterr:.2f} (errore del fit)  R2={r2:.3f}  ({npts} punti)")
    else:
        print("      fit fallito (pochi punti sopra soglia)")
        p = None

    # --- 3. SENSIBILITA' + PROPAGAZIONE dell'incertezza VERA di chi_c ---
    # NON usare un range arbitrario +-2: usare l'incertezza REALE di chi_c
    # (chi_c_err dal fit binario). La barra vera su p = quadratura di
    # (errore del fit) e (|dp/dchi_c| * chi_c_err).
    print(f"\n  [3] Propagazione incertezza (chi_c = {chi_c:.2f} +- {chi_c_err:.2f}):")
    ps = []
    for dxc in [-2, -1, 0, 1, 2]:
        r = fit_p(chi_c+dxc)
        if r:
            ps.append((chi_c+dxc, r[0]))
    if len(ps) >= 2 and p is not None:
        xcv = np.array([a for a, _ in ps]); pv = np.array([b for _, b in ps])
        # pendenza dp/dchi_c attorno a chi_c
        slope = np.polyfit(xcv, pv, 1)[0]
        sig_from_xc = abs(slope) * chi_c_err
        sig_tot = np.sqrt(p_fiterr**2 + sig_from_xc**2)
        print(f"      dp/dchi_c ~ {slope:.2f}/unita -> contributo chi_c: +-{sig_from_xc:.2f}")
        print(f"      contributo fit: +-{p_fiterr:.2f}")
        print(f"\n  ESPONENTE:  p = {p:.2f} +- {sig_tot:.2f}  (L{args.level}, chi_c indipendente)")
        if sig_tot < 0.25:
            print(f"    -> p DETERMINATO a L{args.level}. Per universalita': confronto con L3.")
        else:
            print(f"    -> p con barra ancora larga: piu' seed o punti fitti.")
        print(f"    NB: e' UN livello. 'Esponente critico universale' richiede L3.")

    # --- grafico ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    ax1.errorbar(cms, ndef_mean, yerr=ndef_sem, fmt="o", color="#d62728", capsize=4, ms=7)
    if p is not None and chi_c is not None:
        xf = np.linspace(chi_c+0.1, cms.max(), 100)
        rfit = fit_p(chi_c)
        if rfit:
            A_=curve_fit(lambda chi,A,pp: power(chi,A,pp,chi_c),
                         cms[(cms>chi_c)&(ndef_mean>0.05)],
                         ndef_mean[(cms>chi_c)&(ndef_mean>0.05)],
                         p0=[50,1.5],maxfev=10000)[0][0]
            ax1.plot(xf, power(xf, A_, p, chi_c), "--", color="#1f77b4",
                     label=f"p={p:.2f} (chi_c={chi_c:.1f})")
    ax1.axvline(chi_c, color="gray", ls=":", alpha=0.6, label=f"chi_c={chi_c:.1f}")
    ax1.set_xlabel("chi_mean"); ax1.set_ylabel("n_def (medio +- sem)")
    ax1.set_title(f"Densita' difetti L{args.level} (fit critico)")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)
    # frazione binaria (per chi_c)
    ax2.plot(cms, frac_kink, "s-", color="#2ca02c", ms=6)
    ax2.axhline(0.5, color="gray", ls=":")
    ax2.axvline(chi_c, color="blue", ls="--", alpha=0.6, label=f"chi_c={chi_c:.1f}")
    ax2.set_xlabel("chi_mean"); ax2.set_ylabel("frazione nucleazione (M>1)")
    ax2.set_title("chi_c da frazione binaria (indipendente)")
    ax2.set_ylim(-0.05,1.05); ax2.legend(fontsize=8); ax2.grid(alpha=0.3)
    fig.suptitle(f"Esponente critico L{args.level}: chi_c indipendente + sensibilita'",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"esponente_critico_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
