"""
================================================================================
BIOPSIA DEL DIFETTO - struttura geometrica dei ~10 nodi caldi (chi_mean=74)
================================================================================

Domanda (2026-06-03): i ~10 nodi caldi della FASE ROBUSTA (peak~1.96, chi_mean=74)
sono disposti in modo geometrico specifico (icosaedrico/5-fold, cubottaedrico) o
casuale? Tre test indipendenti:

  TEST 1 - CONCENTRAZIONE A BLOCCO: i nodi caldi sono in 1 solo blocco L1 (difetto
  localizzato gerarchicamente) o sparsi su piu' blocchi? Conta le foglie hot per
  blocco L1 e misura l'IPR a livello di blocco.

  TEST 2 - PATTERN INTRA-BLOCCO: nel/i blocco/i caldo/i, quali posizioni (0-23)
  sono hot? Se e' icosaedrico: pattern regolare con gap (l'icosaedro ha 12 vertici
  su una sfera, il cubottaedro 12 su un cubo). Se e' casuale: nessun pattern.
  Misura: distribuzione angolare dei nodi hot (assumendo anello circolare
  per il coupling 24x24 circulant).

  TEST 3 - CHIUSURA TOPOLOGICA del cluster: Στ_hot (mod 4pi) = residuo di chiusura.
  Un difetto topologico PROTETTO (disclination) chiude con residuo multiplo di
  pi (es. 2pi = 360, 4pi = 720 deg). Un grumo casuale non chiude.
  Misura la firma 720 degrees (4pi) vs una distribuzione uniforme di tau.

Protocollo: ri-congela 10 seed indipendenti a chi_mean=74, estrae i nodi hot,
misura la geometria per-seed, aggrega le statistiche.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_biopsia_difetto.py
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
CHI_MEAN = 74.0       # fase particella robusta
HOT_PCT = 97.0        # percentile sopra cui un nodo e' "caldo"
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)


def extract_leaves_with_coords(root):
    """
    Restituisce lista di dict {block_idx, leaf_idx, rho, tau, chi} per ogni foglia.
    block_idx = indice del L1 block che la contiene (0-23 a L2).
    leaf_idx  = posizione all'interno del L1 block (0-23).
    """
    records = []
    block_idx = 0
    for L1 in root.children:
        if isinstance(L1, SolitoneComposito):
            chi = np.array([c.chi for c in L1.children])
            tau = np.array([c.tau_locale for c in L1.children])
            W = L1.coupling_matrix
            Wd = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
            rho = np.sum(Wd * (chi[:, None] - chi[None, :]) ** 2, axis=1)
            for leaf_idx, (r, t, c) in enumerate(zip(rho, tau, chi)):
                records.append(dict(block=block_idx, leaf=leaf_idx,
                                    rho=float(r), tau=float(t), chi=float(c)))
        block_idx += 1
    return records


def analyse_biopsy(records, hot_pct=HOT_PCT):
    """Estrae metriche geometriche dai record di una configurazione congelata."""
    rho_vals = np.array([r["rho"] for r in records])
    threshold = np.percentile(rho_vals, hot_pct)
    hot = [r for r in records if r["rho"] >= threshold]
    cold = [r for r in records if r["rho"] < threshold]
    n_hot = len(hot)
    n_total = len(records)

    # TEST 1: concentrazione a blocco
    hot_blocks = [r["block"] for r in hot]
    block_ids, block_counts = np.unique(hot_blocks, return_counts=True)
    n_hot_blocks = len(block_ids)
    # IPR a livello di blocco (quanto e' concentrata la frustrazione tra i blocchi)
    hot_per_block = np.zeros(24)
    for b, c in zip(block_ids, block_counts):
        hot_per_block[b] = c
    p_block = hot_per_block / (hot_per_block.sum() + 1e-30)
    ipr_block = float(np.sum(p_block ** 2)) if hot_per_block.sum() > 0 else 0.0
    n_eff_block = 1.0 / (ipr_block + 1e-30)
    # 1 = tutto in 1 blocco (max localizzazione); 1/24 = uniforme

    # TEST 2: pattern intra-blocco (posizioni angolari nel blocco caldo)
    # Se il coupling e' a anello (circulant), leaf_idx mappa a un angolo 2pi*k/24
    hot_angles = []
    for r in hot:
        angle = 2.0 * np.pi * r["leaf"] / 24.0
        hot_angles.append(angle)
    hot_angles = np.array(hot_angles)
    # uniformita': se casuale l'entropia angolare e' massima
    # Binning in 12 settori
    bin_counts, _ = np.histogram(hot_angles, bins=12, range=(0, 2 * np.pi))
    p_ang = bin_counts / (bin_counts.sum() + 1e-30)
    entropy_ang = -float(np.sum(p_ang * np.log(p_ang + 1e-30)))
    entropy_max = np.log(12)  # distribuzione uniforme su 12 settori
    uniformity = entropy_ang / (entropy_max + 1e-30)
    # uniformity ~ 1 = casuale; << 1 = clustered (struttura)

    # TEST 3: chiusura topologica del cluster hot
    tau_hot = np.array([r["tau"] for r in hot])
    tau_cold = np.array([r["tau"] for r in cold])
    sum_tau_hot = float(np.sum(tau_hot))
    four_pi = 4.0 * np.pi
    residual = sum_tau_hot % four_pi
    closure_err_rad = min(residual, four_pi - residual)
    closure_err_deg = float(np.degrees(closure_err_rad))
    # interpretazione: residuo vicino a 0 (o 4pi) = chiusura 720 deg esatta
    # residuo vicino a 2pi = meta' chiusura (180 deg di frustrazione)
    closes_720 = closure_err_deg < 30.0  # entro 30 deg da un multiplo di 4pi
    closes_360 = abs(np.degrees(sum_tau_hot % (2 * np.pi)) -
                     np.degrees(np.pi)) < 30.0

    return dict(
        n_hot=n_hot, threshold=float(threshold),
        # TEST 1
        n_hot_blocks=int(n_hot_blocks),
        ipr_block=ipr_block, n_eff_block=float(n_eff_block),
        hot_blocks=hot_blocks, hot_per_block=hot_per_block,
        # TEST 2
        hot_angles=hot_angles, uniformity=float(uniformity), entropy_ang=entropy_ang,
        # TEST 3
        sum_tau_hot=sum_tau_hot, closure_err_deg=closure_err_deg,
        closes_720=closes_720, closes_360=closes_360,
        tau_hot=tau_hot, tau_cold=tau_cold,
    )


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--chi-mean", type=float, default=CHI_MEAN)
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    ap.add_argument("--hot-pct", type=float, default=HOT_PCT)
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    dt = 0.01
    N_blocks = 24 ** (args.level - 1)  # blocchi L1 a questo livello

    print("=" * 80)
    print("  BIOPSIA DEL DIFETTO - struttura geometrica dei nodi caldi")
    print(f"  L{args.level} (N={24**args.level})  |  chi_mean={args.chi_mean:.0f}  |"
          f"  {len(seeds)} seed  |  hot = top {100-args.hot_pct:.0f}% rho_tors")
    print("=" * 80)

    all_n_hot_blocks, all_ipr_block, all_n_eff_block = [], [], []
    all_uniformity, all_closure_err, all_closes_720 = [], [], []
    all_hot_per_block = []

    for seed in seeds:
        sol = make(seed, chi_mean=args.chi_mean, level=args.level)
        for _ in range(args.pre):
            sol.compute_hamiltonian(); sol.evolve(dt)
        r = freeze_and_measure_mass(sol, max_steps=args.quench_steps, dt=dt,
                                    return_frozen=True)
        records = extract_leaves_with_coords(r["frozen"])
        m = analyse_biopsy(records, hot_pct=args.hot_pct)

        all_n_hot_blocks.append(m["n_hot_blocks"])
        all_ipr_block.append(m["ipr_block"])
        all_n_eff_block.append(m["n_eff_block"])
        all_uniformity.append(m["uniformity"])
        all_closure_err.append(m["closure_err_deg"])
        all_closes_720.append(m["closes_720"])
        all_hot_per_block.append(m["hot_per_block"])

        print(f"  seed {seed:>2}: hot_blocks={m['n_hot_blocks']:>2}/{N_blocks}  "
              f"n_eff_block={m['n_eff_block']:.1f}  "
              f"uniformity={m['uniformity']:.2f}  "
              f"closure_err={m['closure_err_deg']:.1f}deg  "
              f"720deg={'SI' if m['closes_720'] else 'NO'}")

    # --- riepilogo ---
    print("\n  " + "=" * 76)
    print("  RIEPILOGO: struttura geometrica (media su tutti i seed)")
    print("  " + "-" * 76)
    nhb = np.array(all_n_hot_blocks)
    neb = np.array(all_n_eff_block)
    uni = np.array(all_uniformity)
    clo = np.array(all_closure_err)
    frac_720 = np.mean(all_closes_720)
    print(f"\n  TEST 1 - Concentrazione a blocco:")
    print(f"    n_hot_blocks: media={nhb.mean():.1f} +- {nhb.std():.1f}  "
          f"min={nhb.min()}  max={nhb.max()}")
    print(f"    n_eff_block (blocchi 'caldi' effettivi): {neb.mean():.1f} +- {neb.std():.1f}")
    if nhb.mean() < 3:
        print("    -> CONCENTRATO: il difetto vive in 1-2 blocchi L1 (super-localizzato).")
    elif nhb.mean() < N_blocks / 4:
        print("    -> LOCALIZZATO: pochi blocchi caldi su {N_blocks}.")
    else:
        print(f"    -> DISTRIBUITO su ~{nhb.mean():.0f}/{N_blocks} blocchi.")

    print(f"\n  TEST 2 - Pattern intra-blocco (uniformita' angolare):")
    print(f"    uniformity: media={uni.mean():.2f} +- {uni.std():.2f}  "
          f"(1=casuale, 0=clustered)")
    if uni.mean() > 0.85:
        print("    -> CASUALE: nessun pattern geometrico regolare.")
    elif uni.mean() > 0.6:
        print("    -> PARZIALMENTE STRUTTURATO (uniformita' intermedia).")
    else:
        print("    -> STRUTTURATO: i nodi caldi hanno un pattern non-uniforme.")

    print(f"\n  TEST 3 - Chiusura topologica:")
    print(f"    closure_err (gradi da multiplo 4pi): media={clo.mean():.1f} +- {clo.std():.1f}")
    print(f"    frazione seed con chiusura 720deg (entro 30deg): {frac_720:.2f}")
    if frac_720 > 0.7:
        print("    -> DIFETTO TOPOLOGICO: il cluster chiude a 720 deg (firma spinoriale).")
    elif frac_720 > 0.3:
        print("    -> Chiusura PARZIALE (potrebbe essere rumore o chiusura approssimata).")
    else:
        print("    -> NESSUNA chiusura spinoriale: il cluster non e' un difetto topologico puro.")

    # --- grafici ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Grafico 1: distribuzione delle n_hot_blocks per seed
    axes[0].hist(nhb, bins=range(0, int(nhb.max()) + 2), color="#1f77b4", edgecolor="k", alpha=0.8)
    axes[0].axvline(nhb.mean(), color="red", ls="--", label=f"media={nhb.mean():.1f}")
    axes[0].set_xlabel("n blocchi L1 con nodi caldi")
    axes[0].set_ylabel("conteggio seed")
    axes[0].set_title("TEST 1: concentrazione a blocco")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)

    # Grafico 2: mappa calore media di hot_per_block su tutti i seed
    mean_hpb = np.mean(np.stack(all_hot_per_block), axis=0)
    axes[1].bar(range(N_blocks), mean_hpb, color="#2ca02c", edgecolor="k", alpha=0.8)
    axes[1].set_xlabel("indice blocco L1 (0-23)")
    axes[1].set_ylabel("nodi caldi medi")
    axes[1].set_title("TEST 1: distribuzione nodi caldi per blocco")
    axes[1].grid(alpha=0.3, axis="y")

    # Grafico 3: distribuzione errore di chiusura topologica
    axes[2].hist(clo, bins=18, range=(0, 180), color="#d62728", edgecolor="k", alpha=0.8)
    axes[2].axvline(30, color="green", ls="--", label="soglia 720deg (30deg)")
    axes[2].set_xlabel("errore chiusura (gradi da multiplo 4pi)")
    axes[2].set_ylabel("conteggio seed")
    axes[2].set_title("TEST 3: chiusura topologica del cluster")
    axes[2].legend(fontsize=8); axes[2].grid(alpha=0.3)

    fig.suptitle(f"Biopsia del difetto: geometria dei nodi caldi [L{args.level}, cm={args.chi_mean:.0f}]",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"biopsia_difetto_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
