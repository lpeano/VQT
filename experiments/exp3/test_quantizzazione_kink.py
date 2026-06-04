"""
================================================================================
QUANTIZZAZIONE DEL KINK — i livelli energetici sono dettati dai divisori di 24?
================================================================================

Ipotesi (2026-06-03): il blocco L1 e' una ring di 24 nodi con coupling circolante.
Gli autovettori di una matrice circolante sono le armoniche discrete exp(2pi*i*m*k/24).
Un kink di larghezza w e' stabile se w divide 24 (commensurabilita' con la ring),
analogamente ai livelli degli orbitali atomici dalla simmetria discreta Z_24.

Divisori di 24: {1, 2, 3, 4, 6, 8, 12, 24}
Il kink osservato ha ~6 nodi = 24/4 (modo m=4, quarto armonico).

Test: su 100 seed a chi_mean=74 (fase robusta, 100% nucleazione), l'istogramma di
M_tot mostra picchi DISCRETI (quantizzazione) o una distribuzione CONTINUA?

Se discreto: la larghezza del kink e' quantizzata dai divisori di 24.
Se continuo: la larghezza e' determinata solo dal rapporto coupling/potenziale.

Aggiunta: calcolo degli "orbitali" teorici dal Laplaciano 24x24 (SpectralBasis)
e stima dell'energia attesa per ogni larghezza permessa.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_quantizzazione_kink.py
  python experiments/exp3/test_quantizzazione_kink.py --seeds 50 --chi-mean 68
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
from matplotlib.gridspec import GridSpec

from wqt_oop.energy_metrics import freeze_and_measure_mass, compute_hierarchical_mass
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.spectral_coupling import SpectralBasis
from test_soglia_formazione import make

CHI_STABLE = 50.0
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)

DIVISORS_24 = [1, 2, 3, 4, 6, 8, 12, 24]


def collect_chi_profile(frozen_root):
    """Chi di ogni foglia, con indice blocco e posizione nel blocco."""
    data = []
    for b_idx, L1 in enumerate(frozen_root.children):
        if isinstance(L1, SolitoneComposito):
            for l_idx, seg in enumerate(L1.children):
                if isinstance(seg, SegmentoQuantistico):
                    data.append((b_idx, l_idx, float(seg.chi)))
    return data  # lista di (block, leaf, chi)


def kink_width(frozen_root, chi_stable=CHI_STABLE, dev_thresh=0.5):
    """
    Numero di foglie con |chi - chi_stable| > dev_thresh * chi_stable.
    dev_thresh=0.5: conta nodi con chi < 25 o chi > 75 (nella zona di transizione).
    """
    data = collect_chi_profile(frozen_root)
    threshold = dev_thresh * chi_stable
    return sum(1 for _, _, c in data if abs(c - chi_stable) > threshold)


def spectral_kink_energies(sol_L2, chi_stable=CHI_STABLE):
    """
    Stima dell'energia del kink per ogni larghezza w = divisore di 24,
    basata sugli autovalori del Laplaciano del coupling del primo blocco L1.

    Per un kink di larghezza w su una ring discreta con coupling W:
      E_kink(w) ~ alpha_K * sum_{i nel kink} rho_tors_i
    In approssimazione: il kink di larghezza w ha w nodi con chi che varia
    linearmente da +chi_stable a -chi_stable. La densita' di torsione per nodo e':
      rho_tors ~ W_nn * (2*chi_stable/w)^2
    dove W_nn e' il coupling nearest-neighbor.
    E_kink(w) ~ w * W_nn * (2*chi_stable/w)^2 = 4 * W_nn * chi_stable^2 / w

    -> E_kink ~ 1/w: kink piu' stretti hanno piu' energia (come gradiente piu' ripido).
    """
    L1_first = None
    for child in sol_L2.children:
        if isinstance(child, SolitoneComposito):
            L1_first = child
            break
    if L1_first is None:
        return {}
    W = L1_first.coupling_matrix
    Wd = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
    alpha_K = L1_first.physics.alpha_K
    # Coupling nearest-neighbor (off-diagonal vicino)
    W_nn = float(np.mean([Wd[i, (i+1) % 24] for i in range(24)]))
    energies = {}
    for w in DIVISORS_24:
        E = 4.0 * alpha_K * W_nn * chi_stable**2 / w
        energies[w] = E
    return energies, W_nn, alpha_K


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--chi-mean", type=float, default=74.0)
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    ap.add_argument("--dev-thresh", type=float, default=0.5,
                    help="soglia di deviazione da chi_stable per contare nodi kink")
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    dt = 0.01
    N = 24 ** args.level

    print("=" * 80)
    print("  QUANTIZZAZIONE KINK - i livelli energetici seguono i divisori di 24?")
    print(f"  L{args.level} (N={N})  |  chi_mean={args.chi_mean:.0f}  |  {len(seeds)} seed")
    print(f"  nodo 'kink' se |chi - {CHI_STABLE}| > {args.dev_thresh*CHI_STABLE:.0f}")
    print("=" * 80)

    # --- calcolo teorico livelli orbitali ---
    sol_ref = make(1, chi_mean=args.chi_mean, level=args.level)
    result_spec = spectral_kink_energies(sol_ref)
    energies_th, W_nn, alpha_K = result_spec
    print(f"\n  Coupling nearest-neighbor W_nn = {W_nn:.4f}  alpha_K = {alpha_K:.4f}")
    print(f"  Livelli energetici teorici E_kink ~ 4*alpha_K*W_nn*chi_stable^2 / w:")
    print(f"  {'w (nodi)':>10} {'modo m=24/w':>12} {'E_kink (teorico)':>18}")
    print("  " + "-" * 44)
    for w in DIVISORS_24:
        m = 24 // w
        print(f"  {w:>10} {m:>12} {energies_th[w]:>18.2f}")

    # --- raccolta dati ---
    print(f"\n  Raccolta dati: {len(seeds)} seed... (ogni punto = 1 quench L{args.level})")
    mtots, widths = [], []
    for i, seed in enumerate(seeds):
        sol = make(seed, chi_mean=args.chi_mean, level=args.level)
        for _ in range(args.pre):
            sol.compute_hamiltonian(); sol.evolve(dt)
        r = freeze_and_measure_mass(sol, max_steps=args.quench_steps, dt=dt,
                                    return_frozen=True)
        frozen = r["frozen"]
        h = compute_hierarchical_mass(frozen)
        w = kink_width(frozen, dev_thresh=args.dev_thresh)
        mtots.append(h["M_tot"])
        widths.append(w)
        if (i + 1) % 10 == 0:
            print(f"  ... {i+1}/{len(seeds)} completati")

    mtots = np.array(mtots)
    widths = np.array(widths)

    # --- analisi ---
    print("\n  " + "=" * 76)
    print("  ANALISI: quantizzazione o distribuzione continua?")
    print("  " + "-" * 76)

    # distribuzione di widths
    w_vals, w_counts = np.unique(widths, return_counts=True)
    print(f"\n  Larghezze kink osservate (n nodi con |chi-{CHI_STABLE:.0f}|>{args.dev_thresh*CHI_STABLE:.0f}):")
    print(f"  {'w':>5} {'conteggio':>10} {'div 24?':>10} {'M_tot medio':>13} {'M_tot std':>11}")
    print("  " + "-" * 54)
    for wv, wc in zip(w_vals, w_counts):
        mask = widths == wv
        is_div = "SI" if wv in DIVISORS_24 else "no"
        print(f"  {wv:>5} {wc:>10} {is_div:>10} "
              f"{mtots[mask].mean():>13.2e} {mtots[mask].std():>11.2e}")

    # frazione di larghezze che sono divisori di 24
    frac_div = np.mean([w in DIVISORS_24 for w in widths])
    print(f"\n  Frazione kink con larghezza = divisore di 24: {frac_div:.2f}")
    if frac_div > 0.8:
        print("  -> FORTE SEGNALE DI QUANTIZZAZIONE: le larghezze preferiscono i divisori.")
    elif frac_div > 0.5:
        print("  -> Segnale moderato (piu' divisori del caso, ma non esclusivo).")
    else:
        print("  -> NESSUNA quantizzazione: larghezze distribuite continuamente.")

    # test su M_tot: picchi discreti?
    log_mtot = np.log10(mtots[mtots > 1e-6] + 1e-30)
    print(f"\n  Distribuzione M_tot (log10): min={log_mtot.min():.1f}  "
          f"mean={log_mtot.mean():.1f}  max={log_mtot.max():.1f}")
    # cerca gap nella distribuzione (zone a bassa densita' tra picchi)
    hist, edges = np.histogram(log_mtot, bins=30)
    gaps = np.where(hist == 0)[0]
    if len(gaps) > 0:
        gap_positions = [(edges[g] + edges[g+1]) / 2 for g in gaps]
        print(f"  Gap (zone vuote) in log10(M_tot): {[f'{g:.1f}' for g in gap_positions]}")
        print(f"  -> {len(gaps)} gap trovati -> possibile struttura discreta.")
    else:
        print("  Nessun gap: distribuzione M_tot continua (no quantizzazione).")

    # --- grafici ---
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.35)

    # 1: istogramma M_tot in scala log (il test principale)
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.hist(log_mtot, bins=40, color="#2ca02c", edgecolor="k", alpha=0.8)
    # linee verticali per i livelli teorici
    for w, E in energies_th.items():
        if E > 0:
            lE = np.log10(E + 1e-30)
            if log_mtot.min() - 1 < lE < log_mtot.max() + 1:
                ax1.axvline(lE, color="red", ls="--", alpha=0.6, lw=1.2,
                            label=f"w={w} (E_th={E:.0f})" if w <= 8 else "")
    ax1.set_xlabel("log10(M_tot)")
    ax1.set_ylabel("n seed")
    ax1.set_title("Istogramma M_tot: picchi discreti = quantizzazione dei livelli")
    ax1.legend(fontsize=7, loc="upper left"); ax1.grid(alpha=0.3)

    # 2: larghezza kink vs M_tot (scatter)
    ax2 = fig.add_subplot(gs[0, 2])
    real = mtots > 1.0
    ax2.scatter(widths[real], np.log10(mtots[real] + 1e-30),
                c="#d62728", s=20, alpha=0.5, edgecolor="none", label="difetto reale")
    ax2.scatter(widths[~real], np.log10(mtots[~real] + 1e-30),
                c="#aec7e8", s=10, alpha=0.4, edgecolor="none", label="cicatrice fredda")
    for w in DIVISORS_24:
        ax2.axvline(w, color="orange", ls=":", alpha=0.5, lw=0.8)
    ax2.set_xlabel("larghezza kink (nodi con |chi-50|>25)")
    ax2.set_ylabel("log10(M_tot)")
    ax2.set_title("Larghezza vs energia: divisori = arancione")
    ax2.legend(fontsize=7); ax2.grid(alpha=0.3)

    # 3: conteggio larghezze (bar)
    ax3 = fig.add_subplot(gs[1, 0])
    colors_bar = ["#d62728" if wv in DIVISORS_24 else "#1f77b4" for wv in w_vals]
    ax3.bar(w_vals, w_counts, color=colors_bar, edgecolor="k", alpha=0.8)
    ax3.set_xlabel("larghezza kink (nodi)"); ax3.set_ylabel("n seed")
    ax3.set_title("Distribuzione larghezze (rosso = divisore di 24)")
    ax3.grid(alpha=0.3, axis="y")

    # 4: M_tot medio per larghezza (verifica ~ 1/w)
    ax4 = fig.add_subplot(gs[1, 1])
    for wv in w_vals:
        mask = (widths == wv) & real
        if mask.sum() >= 2:
            ax4.errorbar(wv, np.mean(mtots[mask]), yerr=np.std(mtots[mask]),
                         fmt="o", color="#2ca02c", capsize=4)
    w_th = np.array(DIVISORS_24, float)
    E_th = np.array([energies_th[w] for w in DIVISORS_24])
    scale = np.nanmedian(mtots[real]) / np.median(E_th) if real.sum() else 1
    ax4.plot(w_th, E_th * scale, "r--", label=f"E~1/w (scaled)", alpha=0.7)
    ax4.set_xlabel("larghezza kink"); ax4.set_ylabel("M_tot medio")
    ax4.set_title("M_tot vs larghezza: segue E~1/w?")
    ax4.legend(fontsize=7); ax4.grid(alpha=0.3)

    # 5: livelli teorici vs osservati
    ax5 = fig.add_subplot(gs[1, 2])
    if real.sum():
        observed_levels = sorted(set(widths[real]))
        theoretical = DIVISORS_24
        in_both = [w for w in observed_levels if w in theoretical]
        only_obs = [w for w in observed_levels if w not in theoretical]
        only_th = [w for w in theoretical if w not in observed_levels]
        ax5.barh(in_both, [1]*len(in_both), color="#2ca02c", alpha=0.8, label="osservato & teorico")
        ax5.barh(only_obs, [1]*len(only_obs), color="#ff7f0e", alpha=0.8, label="solo osservato")
        ax5.barh(only_th, [0.3]*len(only_th), color="#d62728", alpha=0.4, label="solo teorico")
        ax5.set_xlabel("presenza"); ax5.set_ylabel("larghezza w")
        ax5.set_title("Livelli: osservati vs divisori di 24")
        ax5.legend(fontsize=7); ax5.grid(alpha=0.3, axis="x")

    fig.suptitle(
        f"Quantizzazione kink: divisori di 24 come livelli energetici? [L{args.level}, cm={args.chi_mean:.0f}, {len(seeds)} seed]",
        fontweight="bold")
    out = os.path.join(FIGDIR, f"quantizzazione_kink_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
