"""
================================================================================
TEST SOC — il vuoto e' "in ebollizione" (legge di potenza) o termico (esponenziale)?
================================================================================

Domanda (2026-06-03): nella FINESTRA di localizzazione (peak~1.8-1.95, dove il
quench condensa una particella, loc_ratio L2 ~57), la frustrazione e' distribuita
secondo una LEGGE DI POTENZA (criticalita' auto-organizzata, SOC: "vuoto in
ebollizione" che genera difetti su tutte le scale) oppure secondo una legge
ESPONENZIALE (campo termico ordinario, una scala caratteristica)?

Discriminante (rigoroso, non semplice istogramma):
  Per la distribuzione di rho_tors sulle FOGLIE (576 a L2) dello stato CONGELATO:
    - CCDF (coda cumulativa complementare) P(X > x): piu' robusta del binning.
    - Fit POTENZA:      log P(X>x) ~ -(alpha-1) log x      (lineare in log-log)
    - Fit ESPONENZIALE: log P(X>x) ~ -x / scala            (lineare in semilog-y)
    - Confronto via R^2 sulla CODA (x >= xmin = percentile p): vince il piu' alto.

CONTROLLO: stesso test nel regime SOVRA-SATURO (peak>2.2, "plasma" uniforme).
  Se SOC e' reale, la FINESTRA mostra potenza e il plasma NO (atteso esponenziale
  o coda corta). Il contrasto finestra-vs-plasma e' la prova, non il singolo fit.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_soc_distribuzione.py                 # L2 default
  python experiments/exp3/test_soc_distribuzione.py --seeds 6
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

from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.energy_metrics import freeze_and_measure_mass
from test_soglia_formazione import make, chi_max

CHI_STABLE = 50.0
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)


def collect_rho_tors(root):
    """rho_tors per OGNI foglia, raccolto da tutti i blocchi L1 (come l'aggregatore)."""
    rho_all = []

    def _walk(node):
        if node.children and isinstance(node.children[0], SegmentoQuantistico):
            chi = np.array([c.chi for c in node.children])
            W = node.coupling_matrix
            Wd = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
            rho = np.sum(Wd * (chi[:, None] - chi[None, :]) ** 2, axis=1)
            rho_all.extend(rho.tolist())
        else:
            for c in node.children:
                if isinstance(c, SolitoneComposito):
                    _walk(c)
    _walk(root)
    return np.asarray(rho_all, dtype=float)


def fit_ccdf(x, xmin_pct=60.0):
    """
    CCDF empirica e fit potenza vs esponenziale sulla coda (x >= xmin).
    Ritorna dict: xs, ccdf (per il plot), alpha, R2_pow, R2_exp, scale_exp, xmin, verdict.
    """
    x = np.sort(x[x > 0])
    n = len(x)
    if n < 20:
        return None
    # CCDF empirica: P(X >= x_i) = (n - i) / n  (i = 0..n-1)
    ccdf = 1.0 - np.arange(n) / n
    ccdf = np.clip(ccdf, 1e-12, 1.0)

    xmin = np.percentile(x, xmin_pct)
    tail = x >= xmin
    xt = x[tail]
    ct = ccdf[tail]
    # serve coda non degenere
    ok = ct > 1e-9
    xt, ct = xt[ok], ct[ok]
    if len(xt) < 8:
        return None

    # POTENZA: log(ccdf) vs log(x)
    lx, lc = np.log(xt), np.log(ct)
    sp, ip = np.polyfit(lx, lc, 1)
    pred_p = sp * lx + ip
    R2_pow = 1.0 - np.sum((lc - pred_p) ** 2) / (np.sum((lc - np.mean(lc)) ** 2) + 1e-30)
    alpha = 1.0 - sp  # esponente della PDF (ccdf ~ x^-(alpha-1))

    # ESPONENZIALE: log(ccdf) vs x
    se, ie = np.polyfit(xt, lc, 1)
    pred_e = se * xt + ie
    R2_exp = 1.0 - np.sum((lc - pred_e) ** 2) / (np.sum((lc - np.mean(lc)) ** 2) + 1e-30)
    scale_exp = -1.0 / se if se < 0 else np.inf

    if R2_pow > R2_exp + 0.02:
        verdict = "POTENZA (SOC)"
    elif R2_exp > R2_pow + 0.02:
        verdict = "ESPONENZIALE (termico)"
    else:
        verdict = "ambiguo"

    return dict(xs=x, ccdf=ccdf, xmin=xmin, alpha=alpha, R2_pow=R2_pow,
                R2_exp=R2_exp, scale_exp=scale_exp, verdict=verdict,
                slope_pow=sp, ip=ip, se=se, ie=ie)


def gather(level, chi_mean, seeds, pre, q_steps, dt):
    """Pool di rho_tors (stati congelati) su piu' seed per la coppia (livello, chi_mean)."""
    pooled = []
    peaks = []
    for seed in seeds:
        sol = make(seed, chi_mean=chi_mean, level=level)
        peak = chi_max(sol) / CHI_STABLE
        for _ in range(pre):
            sol.compute_hamiltonian(); sol.evolve(dt)
            peak = max(peak, chi_max(sol) / CHI_STABLE)
        r = freeze_and_measure_mass(sol, max_steps=q_steps, dt=dt, return_frozen=True)
        pooled.append(collect_rho_tors(r["frozen"]))
        peaks.append(peak)
    return np.concatenate(pooled), float(np.mean(peaks))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--chi-window", type=float, default=68.0, help="chi_mean nella finestra (peak~1.8-1.95)")
    ap.add_argument("--chi-plasma", type=float, default=95.0, help="chi_mean sovra-saturo (controllo)")
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=800)
    ap.add_argument("--xmin-pct", type=float, default=60.0)
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    dt = 0.01

    print("=" * 80)
    print("  TEST SOC - distribuzione di rho_tors: legge di POTENZA (SOC) vs ESPONENZIALE")
    print(f"  L{args.level} (N={24**args.level})  |  {len(seeds)} seed  |  coda x>=p{args.xmin_pct:.0f}")
    print("=" * 80)

    cases = [("FINESTRA (particella)", args.chi_window),
             ("PLASMA (sovra-saturo)", args.chi_plasma)]

    results = {}
    for label, cm in cases:
        data, peak = gather(args.level, cm, seeds, args.pre, args.quench_steps, dt)
        fit = fit_ccdf(data, xmin_pct=args.xmin_pct)
        results[label] = (data, peak, fit)
        print(f"\n  [{label}]  chi_mean={cm:.0f}  peak~{peak:.2f}  N_foglie_pool={len(data)}")
        if fit is None:
            print("    coda insufficiente per il fit.")
            continue
        print(f"    R2 potenza      = {fit['R2_pow']:.4f}   (alpha = {fit['alpha']:.2f})")
        print(f"    R2 esponenziale = {fit['R2_exp']:.4f}   (scala = {fit['scale_exp']:.1f})")
        print(f"    -> {fit['verdict']}")

    # --- verdetto comparativo finestra vs plasma ---
    print("\n  " + "=" * 76)
    print("  VERDETTO COMPARATIVO")
    print("  " + "-" * 76)
    fw = results["FINESTRA (particella)"][2]
    fp = results["PLASMA (sovra-saturo)"][2]
    if fw and fp:
        win_pow = "POTENZA" in fw["verdict"]
        plasma_not_pow = "POTENZA" not in fp["verdict"]
        if win_pow and plasma_not_pow:
            print("  -> SOC CONFERMATO: la FINESTRA segue una legge di potenza (alpha="
                  f"{fw['alpha']:.2f}) mentre il PLASMA no ({fp['verdict']}).")
            print("     La frustrazione si organizza scale-free SOLO dove nasce la particella:")
            print("     il vuoto 'bolle' (genera difetti su tutte le scale) nella finestra critica.")
        elif win_pow and not plasma_not_pow:
            print("  -> Potenza in ENTRAMBI i regimi: heavy-tail generico, non specifico della")
            print("     finestra. SOC possibile ma non discriminato dal controllo.")
        else:
            print(f"  -> SOC NON confermato nella finestra ({fw['verdict']}). La localizzazione")
            print("     della particella NON deriva da una cascata critica scale-free.")

    # --- grafici: CCDF log-log + PDF binned log-log per entrambi i regimi ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    colors = {"FINESTRA (particella)": "#d62728", "PLASMA (sovra-saturo)": "#1f77b4"}
    for label, (data, peak, fit) in results.items():
        if fit is None:
            continue
        xs, ccdf = fit["xs"], fit["ccdf"]
        ax1.loglog(xs, ccdf, ".", ms=3, color=colors[label], alpha=0.5,
                   label=f"{label} (peak~{peak:.2f})")
        # retta del fit a potenza sulla coda
        xt = xs[xs >= fit["xmin"]]
        if len(xt) > 2:
            ax1.loglog(xt, np.exp(fit["ip"]) * xt ** fit["slope_pow"], "-",
                       color=colors[label], lw=2,
                       label=f"  fit pot. alpha={fit['alpha']:.2f} (R2={fit['R2_pow']:.3f})")
    ax1.set_xlabel("rho_tors (densita' di torsione per foglia)")
    ax1.set_ylabel("CCDF  P(X >= x)")
    ax1.set_title("CCDF log-log: potenza = retta (SOC)")
    ax1.legend(fontsize=7); ax1.grid(alpha=0.3, which="both")

    # semilog-y per visualizzare l'esponenziale (esponenziale = retta qui)
    for label, (data, peak, fit) in results.items():
        if fit is None:
            continue
        xs, ccdf = fit["xs"], fit["ccdf"]
        ax2.semilogy(xs, ccdf, ".", ms=3, color=colors[label], alpha=0.5, label=label)
    ax2.set_xlabel("rho_tors")
    ax2.set_ylabel("CCDF  P(X >= x)")
    ax2.set_title("CCDF semilog-y: esponenziale = retta (termico)")
    ax2.legend(fontsize=7); ax2.grid(alpha=0.3, which="both")

    fig.suptitle(f"Test SOC: la frustrazione nella finestra e' scale-free? [L{args.level}]",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"soc_distribuzione_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
