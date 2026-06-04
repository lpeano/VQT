"""
================================================================================
QUANTIZZAZIONE GERARCHICA — verifica dell'ipotesi divisori Z_24 a ogni livello
================================================================================

Ipotesi (2026-06-03, Peano): a ogni livello L della gerarchia, il numero di
sotto-blocchi che ospitano il kink appartiene all'insieme dei divisori di 24
con valore STRETTAMENTE MINORE di L:

  L=2: divisori < 2 = {1}       -> kink in ESATTAMENTE 1 blocco L1
  L=3: divisori < 3 = {1, 2}    -> kink in 1 O 2 blocchi L2
  L=4: divisori < 4 = {1, 2, 3} -> kink in 1, 2 O 3 blocchi L3
  ...

Analogia: "numero quantico principale" = L, "numero quantico angolare" = divisori
attivi (come negli orbitali atomici: n=1 solo s, n=2 aggiunge p, n=3 aggiunge d).

Verifica attuale:
  L2 (gia' misurato): n_eff_block_L1 = 1.4 ~= 1 blocco. PREDIZIONE {1} CONFERMATA.
  L3 (questo script): misura n_eff_block_L2 (= quanti blocchi L2 ospitano il kink).
    PREDIZIONE: n_eff_block_L2 in {1, 2}. Mai 3 o piu'.

Metodo: per ogni blocco L2 (24 in totale in un sistema L3), somma la rho_tors
di tutte le sue foglie -> vettore di 24 "masse per blocco L2" -> IPR.
n_eff_block_L2 = 1 / IPR * 24.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_quantizzazione_gerarchica.py          # default 5 seed L3
  python experiments/exp3/test_quantizzazione_gerarchica.py --level 2 --seeds 20  # L2 check
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
from wqt_oop.energy_metrics import freeze_and_measure_mass, compute_hierarchical_mass
from test_soglia_formazione import make

CHI_STABLE = 50.0
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)
DIVISORS_24 = {1, 2, 3, 4, 6, 8, 12, 24}


def rho_per_L1_block(root, hot_pct=None):
    """rho_tors per ogni blocco L1, strutturato per livello gerarchico.

    hot_pct: se specificato (es. 99.0), conta solo i nodi HOT (top hot_pct%)
    nella somma per blocco. Questo evita che il rumore di fondo "spalmi"
    la misura su molti blocchi e permette di confrontare con la biopsia v2.
    Se None: somma tutti i nodi (come prima).

    Ritorna dict {percorso: rho_misura} dove percorso identifica il blocco L1.
    """
    # raccolta dati flat per la soglia globale
    all_records = []  # (path, leaf_idx, rho_val)

    def _walk(node, path=()):
        if node.children and isinstance(node.children[0], SegmentoQuantistico):
            chi = np.array([c.chi for c in node.children])
            W = node.coupling_matrix
            Wd = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
            rho = np.sum(Wd * (chi[:, None] - chi[None, :]) ** 2, axis=1)
            for i, r in enumerate(rho):
                all_records.append((path, i, float(r)))
        else:
            for i, c in enumerate(node.children):
                if isinstance(c, SolitoneComposito):
                    _walk(c, path + (i,))
    _walk(root)

    if not all_records:
        return {}

    if hot_pct is not None:
        rho_vals = np.array([r[2] for r in all_records])
        threshold = np.percentile(rho_vals, hot_pct)
        selected = [(p, r) for p, _, r in all_records if r >= threshold]
    else:
        selected = [(p, r) for p, _, r in all_records]

    totals = {}
    for path, r in selected:
        totals[path] = totals.get(path, 0.0) + r
    return totals


def hierarchical_neff(root, hot_pct=99.0):
    """
    Per ogni livello gerarchico (1, 2, ..., level-1), calcola n_eff_block:
    quanto e' concentrata la massa tra i sotto-blocchi a quella profondita'.

    Ritorna dict {depth: n_eff} dove depth=1 e' il livello L1 (foglie dirette
    dei blocchi L2), depth=2 e' il livello L2 (figli diretti del root L3), etc.

    Convenzione: depth = livello contato DAL BASSO (1 = foglie L1, 2 = L2, ...).
    """
    totals = rho_per_L1_block(root, hot_pct=hot_pct)
    if not totals:
        return {}

    # profondita' massima = lunghezza del percorso piu' lungo
    max_depth = max(len(k) for k in totals)
    result = {}

    for target_depth in range(1, max_depth + 1):
        # aggrega i path al livello target_depth
        # target_depth=1: chiave = primo indice del path
        # target_depth=2: chiave = (primo, secondo) indice
        # etc.
        agg = {}
        for path, rho in totals.items():
            key = path[:max_depth - target_depth + 1] if target_depth <= len(path) else path
            # raggruppa per i primi (max_depth - target_depth + 1) livelli
            # equivalentemente: key = path del padre a profondita' target_depth
            key = path[:target_depth]
            agg[key] = agg.get(key, 0.0) + rho

        vals = np.array(list(agg.values()))
        total = vals.sum()
        if total < 1e-30:
            result[target_depth] = {'n_eff': np.nan, 'n_blocks': len(vals), 'ipr': np.nan}
            continue
        p = vals / total
        ipr = float(np.sum(p ** 2))
        n_eff = 1.0 / (ipr + 1e-30)
        result[target_depth] = {
            'n_eff': float(n_eff),
            'n_blocks': int(len(vals)),
            'ipr': float(ipr),
            'vals': vals,
        }
    return result


def allowed_widths(level):
    """Divisori di 24 strettamente < level (ipotesi di quantizzazione)."""
    return sorted([d for d in DIVISORS_24 if d < level])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--chi-mean", type=float, default=74.0,
                    help="chi_mean nella fase robusta (100%% nucleazione)")
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    ap.add_argument("--hot-pct", type=float, default=99.0,
                    help="percentile per nodi hot (default 99 = top 1%%)")
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    dt = 0.01
    N = 24 ** args.level

    print("=" * 82)
    print("  QUANTIZZAZIONE GERARCHICA - n_eff_block a ogni livello vs divisori di 24")
    print(f"  L{args.level} (N={N})  |  chi_mean={args.chi_mean:.0f}  |  {len(seeds)} seed")
    print("=" * 82)

    print("\n  PREDIZIONE dell'ipotesi:")
    for lev in range(2, args.level + 1):
        aw = allowed_widths(lev)
        print(f"    L{lev}: n_eff_block_L{lev-1} in {aw}  (divisori di 24 < {lev})")

    print(f"\n  Avvio raccolta dati ({len(seeds)} seed × 1 quench L{args.level})...")

    # per ogni seed: n_eff a ogni profondita'
    all_neff = []  # lista di dict {depth: n_eff}
    all_mtot = []

    for seed in seeds:
        print(f"  seed {seed}/{len(seeds)}...", end=" ", flush=True)
        sol = make(seed, chi_mean=args.chi_mean, level=args.level)
        for _ in range(args.pre):
            sol.compute_hamiltonian(); sol.evolve(dt)
        r = freeze_and_measure_mass(sol, max_steps=args.quench_steps, dt=dt,
                                    return_frozen=True)
        frozen = r["frozen"]
        h = compute_hierarchical_mass(frozen)
        neff_dict = hierarchical_neff(frozen, hot_pct=args.hot_pct)
        all_neff.append(neff_dict)
        all_mtot.append(h["M_tot"])
        depths = sorted(neff_dict.keys())
        summary = "  ".join(f"L{d}:{neff_dict[d]['n_eff']:.1f}/{neff_dict[d]['n_blocks']}"
                            for d in depths)
        print(f"M_tot={h['M_tot']:.2e}  [{summary}]")

    # --- analisi ---
    print("\n  " + "=" * 78)
    print("  VERDETTO: n_eff_block per livello vs predizione")
    print("  " + "-" * 78)

    depths = sorted(all_neff[0].keys()) if all_neff else []
    for d in depths:
        neffs = np.array([nd[d]['n_eff'] for nd in all_neff if d in nd and
                          np.isfinite(nd[d]['n_eff'])])
        if len(neffs) == 0:
            continue
        n_blocks = all_neff[0][d]['n_blocks'] if d in all_neff[0] else '?'
        prediction = allowed_widths(d + 1)  # a profondita' d, il livello e' d+1
        # (depth 1 = L1-blocks dentro L2 = level 2; depth 2 = L2-blocks dentro L3 = level 3)
        pred_level = d + 1  # profondita' 1 corrisponde a livello 2, etc.
        pred_set = allowed_widths(pred_level)

        print(f"\n  Profondita' {d} ({n_blocks} sotto-blocchi):")
        print(f"    n_eff media: {neffs.mean():.2f} +- {neffs.std():.2f}  "
              f"(min={neffs.min():.2f}  max={neffs.max():.2f})")
        print(f"    Predizione (divisori < {pred_level}): {pred_set}")
        if len(pred_set) == 0:
            print("    -> Nessun modo attivo a questo livello (livello troppo basso).")
            continue
        in_pred = [ne for ne in neffs if any(abs(ne - p) < 0.6 for p in pred_set)]
        frac = len(in_pred) / len(neffs)
        print(f"    Frazione seed con n_eff in predizione (+/- 0.6): {frac:.2f}")
        if frac > 0.8:
            print(f"    -> CONFERMATO: n_eff concentrato nel set predetto {pred_set}.")
        elif frac > 0.5:
            print(f"    -> PARZIALMENTE confermato.")
        else:
            any_above = np.mean(neffs > max(pred_set) + 0.6) if pred_set else 0
            print(f"    -> NON confermato. {any_above:.0%} seed con n_eff > max({pred_set}).")

    # --- grafico ---
    fig, axes = plt.subplots(1, len(depths), figsize=(5 * len(depths), 5))
    if len(depths) == 1:
        axes = [axes]

    for ax, d in zip(axes, depths):
        neffs = np.array([nd[d]['n_eff'] for nd in all_neff if d in nd and
                          np.isfinite(nd[d]['n_eff'])])
        pred_set = allowed_widths(d + 1)
        n_blocks = all_neff[0][d]['n_blocks'] if all_neff and d in all_neff[0] else 24

        ax.scatter(range(len(neffs)), neffs, s=60, color="#d62728", zorder=3)
        for p in pred_set:
            ax.axhline(p, color="green", ls="--", alpha=0.7,
                       label=f"predetto: {p}")
        ax.axhline(1.0, color="gray", ls=":", alpha=0.5, label="min (1 blocco)")
        ax.axhline(n_blocks, color="blue", ls=":", alpha=0.3, label=f"max ({n_blocks})")
        ax.set_xlabel("seed"); ax.set_ylabel("n_eff_block")
        ax.set_title(f"Profondita' {d}: n_eff tra {n_blocks} sotto-blocchi\n"
                     f"Predizione (divisori<{d+1}): {pred_set}")
        ax.legend(fontsize=7); ax.grid(alpha=0.3)
        ax.set_ylim(0, min(n_blocks + 1, max(neffs.max() * 1.2 + 1, max(pred_set) * 1.5)
                           if len(neffs) else 5))

    fig.suptitle(
        f"Quantizzazione gerarchica: n_eff vs divisori di 24 [L{args.level}, cm={args.chi_mean:.0f}]",
        fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"quantizzazione_gerarchica_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
