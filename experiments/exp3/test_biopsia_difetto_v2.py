"""
================================================================================
BIOPSIA DEL DIFETTO v2 - geometria corretta al punto di max localizzazione
================================================================================

Correzioni rispetto a v1 (2026-06-03):
  1. chi_mean=68 invece di 74: v1 biopsava lo stato PIU' DISTRIBUITO (n_eff~36).
     Il punto di massima localizzazione e' cm=68 (loc_ratio~125, n_eff~5). Solo
     li' la "particella puntiforme" (se esiste) e' visibile. cm=74 e' gia' oltre
     il core della finestra (lo stato si e' allargato).
  2. Test 3 CORRETTO: tau_locale misura la FASE ACCUMULATA nella traiettoria
     (tau += dt/gamma), NON la torsione geometrica dello stato congelato. La
     chiusura 720 deg va misurata sulla TORSIONE ISTANTANEA del congelato, non
     sul tempo proprio storico. Test corretto: usa chi e rho_tors per misurare
     l'asimmetria topologica dello stato congelato.
  3. Filtro per defetti reali: a cm=68 alcuni seed hanno M_tot~3e-3 (cicatrice
     fredda = no difetto vero) e altri M_tot~8e+2 (difetto energetico). Analizza
     separatamente i due sottogruppi.

Tre test (corretti):
  TEST 1: concentrazione a blocco (identico a v1, valido).
  TEST 2: pattern angolare intra-blocco per i top-N nodi hot (valido).
  TEST 3 (NUOVO): asimmetria chi del cluster hot. Un difetto topologico ha un
    "cuore" dove chi e' sistematicamente lontano da chi_stable (frustrazione
    non rilassabile). Misura: |<chi>_hot - chi_stable| / chi_stable.
    Confronto hot vs cold: se hot e' sistematicamente spostato -> difetto reale.
    Inoltre: detorsion_quality per-blocco (alternanza rho_tors +-) gia' usata
    in E_psi_anchored: e' l'indicatore di struttura topologica +-180 deg.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_biopsia_difetto_v2.py
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
from wqt_oop.energy_metrics import (compute_hierarchical_mass,
                                      freeze_and_measure_mass)
from test_soglia_formazione import make, chi_max

CHI_STABLE = 50.0
HOT_PCT = 99.0        # top 1% per cm=68 (n_eff~5 su 576 = 0.9%): piu' selettivo
MTOT_THRESH = 1.0     # separa "difetto vero" (M_tot>1) da "cicatrice fredda"
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)


def extract_leaves(root):
    """Lista di dict {block, leaf, rho, chi} per ogni foglia L1."""
    records = []
    for b_idx, L1 in enumerate(root.children):
        if isinstance(L1, SolitoneComposito):
            chi = np.array([c.chi for c in L1.children])
            W = L1.coupling_matrix
            Wd = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
            rho = np.sum(Wd * (chi[:, None] - chi[None, :]) ** 2, axis=1)
            for l_idx, (r, c) in enumerate(zip(rho, chi)):
                records.append(dict(block=b_idx, leaf=l_idx,
                                    rho=float(r), chi=float(c)))
    return records


def analyse(records, frozen_root, hot_pct=HOT_PCT, chi_stable=CHI_STABLE):
    rho_vals = np.array([r["rho"] for r in records])
    thr = np.percentile(rho_vals, hot_pct)
    hot = [r for r in records if r["rho"] >= thr]
    cold = [r for r in records if r["rho"] < thr]

    # TEST 1: concentrazione a blocco
    hot_blocks = np.array([r["block"] for r in hot])
    block_ids, bcounts = np.unique(hot_blocks, return_counts=True)
    n_hot_blocks = len(block_ids)
    hot_per_block = np.zeros(24)
    for b, c in zip(block_ids, bcounts):
        hot_per_block[b] = c
    p_block = hot_per_block / (hot_per_block.sum() + 1e-30)
    ipr_block = float(np.sum(p_block ** 2))
    n_eff_block = 1.0 / (ipr_block + 1e-30)

    # TEST 2: pattern angolare
    hot_angles = np.array([2.0 * np.pi * r["leaf"] / 24.0 for r in hot])
    bin_counts, _ = np.histogram(hot_angles, bins=12, range=(0, 2 * np.pi))
    p_ang = bin_counts / (bin_counts.sum() + 1e-30)
    uniformity = (-np.sum(p_ang * np.log(p_ang + 1e-30))) / np.log(12)

    # TEST 3 CORRETTO: asimmetria chi + detorsion quality del blocco piu' caldo
    chi_hot = np.array([r["chi"] for r in hot])
    chi_cold = np.array([r["chi"] for r in cold])
    chi_dev_hot = float(np.mean(np.abs(chi_hot - chi_stable))) / chi_stable
    chi_dev_cold = float(np.mean(np.abs(chi_cold - chi_stable))) / chi_stable
    chi_contrast = chi_dev_hot / (chi_dev_cold + 1e-30)
    # diagnostica parete di dominio: se chi_hot_mean~0 -> nodi al massimo del pozzo
    chi_hot_mean = float(np.mean(chi_hot))
    chi_cold_mean = float(np.mean(chi_cold))

    # detorsion quality del blocco piu' caldo (alternanza rho_tors +-180 deg)
    hottest_block_idx = int(np.argmax(hot_per_block))
    L1_hot = frozen_root.children[hottest_block_idx]
    chi_L1 = np.array([c.chi for c in L1_hot.children
                        if isinstance(c, SegmentoQuantistico)])
    W_L1 = L1_hot.coupling_matrix
    Wd_L1 = (W_L1.toarray() if hasattr(W_L1, "toarray") else np.asarray(W_L1))
    rho_L1 = np.sum(Wd_L1 * (chi_L1[:, None] - chi_L1[None, :]) ** 2, axis=1)
    if len(rho_L1) >= 3:
        d = np.diff(rho_L1)
        prod = d[:-1] * d[1:]
        detorsion_q = float(np.sum(prod < 0)) / float(len(prod))
    else:
        detorsion_q = 0.5

    return dict(
        n_hot=len(hot), threshold=float(thr),
        n_hot_blocks=n_hot_blocks, n_eff_block=float(n_eff_block),
        hot_per_block=hot_per_block,
        uniformity=float(uniformity),
        chi_dev_hot=chi_dev_hot, chi_dev_cold=chi_dev_cold,
        chi_contrast=float(chi_contrast),
        chi_hot_mean=chi_hot_mean, chi_cold_mean=chi_cold_mean,
        detorsion_q_hotblock=detorsion_q,
        hottest_block=hottest_block_idx,
    )


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=15)
    ap.add_argument("--chi-mean", type=float, default=68.0)
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    ap.add_argument("--hot-pct", type=float, default=HOT_PCT)
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    dt = 0.01
    N = 24 ** args.level

    print("=" * 82)
    print("  BIOPSIA v2 - max localizzazione (cm=68), test geometrici corretti")
    print(f"  L{args.level} (N={N})  |  chi_mean={args.chi_mean:.0f}  |  "
          f"{len(seeds)} seed  |  hot = top {100-args.hot_pct:.1f}%")
    print("=" * 82)
    print(f"  {'seed':>4} {'M_tot':>10} {'n_hot_blk':>10} {'n_eff_blk':>10} "
          f"{'uniformity':>11} {'chi_hot':>9} {'chi_cold':>9} {'chi_contr':>10}")
    print("  " + "-" * 78)

    mtots_all, blks_all, neff_all, uni_all, contr_all, detq_all = [], [], [], [], [], []
    chi_hot_means_all, chi_cold_means_all = [], []
    hot_pblk_all = []

    for seed in seeds:
        sol = make(seed, chi_mean=args.chi_mean, level=args.level)
        for _ in range(args.pre):
            sol.compute_hamiltonian(); sol.evolve(dt)
        r = freeze_and_measure_mass(sol, max_steps=args.quench_steps, dt=dt,
                                    return_frozen=True)
        frozen = r["frozen"]
        h = compute_hierarchical_mass(frozen)
        M_tot = h["M_tot"]
        records = extract_leaves(frozen)
        m = analyse(records, frozen, hot_pct=args.hot_pct)

        mtots_all.append(M_tot)
        blks_all.append(m["n_hot_blocks"])
        neff_all.append(m["n_eff_block"])
        uni_all.append(m["uniformity"])
        contr_all.append(m["chi_contrast"])
        detq_all.append(m["detorsion_q_hotblock"])
        chi_hot_means_all.append(m["chi_hot_mean"])
        chi_cold_means_all.append(m["chi_cold_mean"])
        hot_pblk_all.append(m["hot_per_block"])

        print(f"  {seed:>4} {M_tot:>10.2e} {m['n_hot_blocks']:>10} "
              f"{m['n_eff_block']:>10.1f} {m['uniformity']:>11.2f} "
              f"{m['chi_hot_mean']:>9.1f} {m['chi_cold_mean']:>9.1f} "
              f"{m['chi_contrast']:>10.2f}")

    mtots = np.array(mtots_all)
    blks = np.array(blks_all)
    neff = np.array(neff_all)
    uni = np.array(uni_all)
    contr = np.array(contr_all)
    detq = np.array(detq_all)

    # --- separa difetti reali da cicatrici fredde ---
    real = mtots > MTOT_THRESH
    cold_mask = ~real
    print(f"\n  Difetti 'reali' (M_tot>{MTOT_THRESH}): {real.sum()}/{len(seeds)}")
    print(f"  Cicatrici fredde (M_tot<{MTOT_THRESH}): {cold_mask.sum()}/{len(seeds)}")

    print("\n  " + "=" * 78)
    print("  RIEPILOGO (tutti seed | solo difetti reali)")
    print("  " + "-" * 78)

    def stat(arr, mask):
        a, r = arr[mask] if mask.sum() else np.array([np.nan]), arr[mask]
        return (f"{arr.mean():.2f}+-{arr.std():.2f}"
                f" | reali: {arr[mask].mean():.2f}+-{arr[mask].std():.2f}"
                if mask.sum() > 0 else f"{arr.mean():.2f}+-{arr.std():.2f} | (nessuno)")

    print(f"\n  TEST 1 - Blocchi caldi (n_hot_blocks):  {stat(blks, real)}")
    print(f"  TEST 1 - n_eff_block:                   {stat(neff, real)}")
    if real.sum():
        print(f"  -> Nei difetti reali: concentrati in {neff[real].mean():.1f} blocchi effettivi su 24.")
        if neff[real].mean() < 3:
            print("     SUPER-LOCALIZZATO: 1-2 blocchi -> candidato per geometria specifica.")
        elif neff[real].mean() < 6:
            print("     LOCALIZZATO su pochi blocchi.")
        else:
            print("     DISTRIBUITO: nessuna super-localizzazione gerarchica.")

    print(f"\n  TEST 2 - Uniformita' angolare:          {stat(uni, real)}")
    if real.sum():
        if uni[real].mean() < 0.6:
            print("     STRUTTURATO: nodi caldi formano un pattern angolare non-uniforme.")
        elif uni[real].mean() < 0.8:
            print("     PARZIALMENTE STRUTTURATO.")
        else:
            print("     CASUALE: nessun pattern angolare.")

    chi_hot_arr = np.array(chi_hot_means_all)
    chi_cold_arr = np.array(chi_cold_means_all)
    print(f"\n  TEST 3 - Contrasto chi hot/cold:        {stat(contr, real)}")
    if real.sum():
        print(f"  TEST 3 - chi medio nodi HOT  (reali):   {chi_hot_arr[real].mean():.2f} "
              f"+- {chi_hot_arr[real].std():.2f}")
        print(f"  TEST 3 - chi medio nodi COLD (reali):   {chi_cold_arr[real].mean():.2f} "
              f"+- {chi_cold_arr[real].std():.2f}")
        print(f"  TEST 3 - chi_stable = {CHI_STABLE}")
        # TEST PARETE DI DOMINIO: se chi_hot~0 e chi_cold~+-chi_stable -> domain wall
        chi_hot_m = chi_hot_arr[real].mean()
        chi_cold_m = chi_cold_arr[real].mean()
        if abs(chi_hot_m) < 0.3 * CHI_STABLE:
            print(f"  -> PARETE DI DOMINIO CONFERMATA: chi_hot~{chi_hot_m:.1f} (vicino al massimo")
            print(f"     del potenziale chi=0). I nodi caldi sono alla barriera +chi_0 / -chi_0.")
            print(f"     La 'massa' e' l'energia della frontiera Kibble-Zurek tra domini opposti.")
        elif abs(chi_hot_m) > 0.8 * CHI_STABLE:
            print(f"  -> NO parete di dominio: chi_hot~{chi_hot_m:.1f} (vicino al minimo del pozzo).")
            print(f"     Il difetto e' una regione di chi estremo (eccitazione di ampiezza).")
        else:
            print(f"  -> chi_hot intermedio ({chi_hot_m:.1f}): non puramente al massimo ne' al minimo.")
        if contr[real].mean() > 2.0:
            print("     FORTE ASIMMETRIA: i nodi caldi deviamo sistematicamente da chi_stable.")
        else:
            print("     Asimmetria chi DEBOLE.")
    print(f"  TEST 3 - Detorsion quality blocco caldo:{stat(detq, real)}")
    if real.sum():
        if detq[real].mean() > 0.7:
            print("     Detorsion quality alta: il blocco caldo mostra il pattern +-180 deg.")
        elif detq[real].mean() > 0.5:
            print("     Detorsion quality media.")
        else:
            print("     Detorsion quality bassa: nessuna alternanza +-180 nel blocco caldo.")

    # --- grafici ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # 1: concentrazione blocchi (solo difetti reali)
    if real.sum():
        axes[0].hist(blks[real], bins=range(0, 14), color="#1f77b4",
                     edgecolor="k", alpha=0.8, label="difetti reali")
    axes[0].hist(blks[cold_mask], bins=range(0, 14), color="#aec7e8",
                 edgecolor="k", alpha=0.5, label="cicatrici fredde")
    axes[0].axvline(neff[real].mean() if real.sum() else 0, color="red",
                    ls="--", label=f"n_eff medio (reali)={neff[real].mean():.1f}" if real.sum() else "")
    axes[0].set_xlabel("n blocchi L1 caldi"); axes[0].set_ylabel("n seed")
    axes[0].set_title("TEST 1: concentrazione (difetti reali vs freddi)")
    axes[0].legend(fontsize=7); axes[0].grid(alpha=0.3)

    # 2: distribuzione media hot per blocco (solo difetti reali)
    if real.sum():
        mean_hpb = np.mean(np.stack([hot_pblk_all[i] for i in range(len(seeds))
                                     if real[i]]), axis=0)
        axes[1].bar(range(24), mean_hpb, color="#2ca02c", edgecolor="k", alpha=0.8)
        axes[1].set_xlabel("blocco L1 (0-23)")
        axes[1].set_ylabel("nodi caldi medi (solo difetti reali)")
        axes[1].set_title("TEST 1: quale blocco e' il piu' caldo?")
        axes[1].grid(alpha=0.3, axis="y")
    else:
        axes[1].text(0.5, 0.5, "nessun difetto reale", transform=axes[1].transAxes,
                     ha="center", va="center")

    # 3: contrasto chi vs uniformita' (scatter)
    sc = axes[2].scatter(uni, contr,
                         c=["#d62728" if r else "#1f77b4" for r in real],
                         s=60, edgecolor="k", linewidth=0.5, zorder=3)
    axes[2].axvline(0.8, color="gray", ls=":", alpha=0.7, label="casuale (0.8)")
    axes[2].axhline(1.5, color="orange", ls=":", alpha=0.7, label="asimmetria chi (1.5x)")
    axes[2].set_xlabel("uniformita' angolare (1=casuale)")
    axes[2].set_ylabel("contrasto chi hot/cold")
    axes[2].set_title("TEST 3: asimmetria chi vs pattern angolare")
    from matplotlib.lines import Line2D
    axes[2].legend(handles=[
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d62728",
               markersize=8, label="difetto reale"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#1f77b4",
               markersize=8, label="cicatrice fredda"),
    ], fontsize=7); axes[2].grid(alpha=0.3)

    fig.suptitle(f"Biopsia v2 [L{args.level}, cm={args.chi_mean:.0f}]: "
                 "geometria corretta al punto di max localizzazione",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"biopsia_difetto_v2_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
