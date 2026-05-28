#!/usr/bin/env python3
"""
render_graph.py — Visualizza il manifold VQT come grafo topologico.

Uso (singolo frame):
  python experiments/visualization/render_graph.py \\
    experiments/exp1/cosmo_L3_ext2.h5 --step 140 --show-torsion --output step400.png

Uso (confronto side-by-side):
  python experiments/visualization/render_graph.py \\
    experiments/exp1/cosmo_L3_ext2.h5 --step 140 \\
    --compare 340 --show-torsion --output compare_400_600.png

Note sui frame:
  I frame in cosmo_L3_ext2.h5 usano numerazione relativa (frame_000000 = step assoluto 261).
  Usa --step per step RELATIVI all'interno del file (1..340),
  oppure --frame per indice diretto del frame (0..339).
  Per il file merged (cosmo_L3_merged.h5), i frame non sono presenti: usa i file sorgente.
"""

import argparse
import sys
from pathlib import Path

import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')  # headless di default; cambia in 'TkAgg' per interattivo
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.collections import LineCollection
from scipy.spatial import cKDTree


def find_frame_by_step(frames_group, target_step: int):
    """Trova il frame_name il cui attributo 'step' corrisponde a target_step."""
    for name in sorted(frames_group.keys()):
        s = int(frames_group[name].attrs.get('step', -1))
        if s == target_step:
            return name
    return None


def load_frame(filepath: Path, step: int = None, frame_idx: int = None) -> dict:
    """Carica dati geometrici da un singolo frame HDF5."""
    with h5py.File(filepath, 'r') as f:
        frames = f['frames']
        if not frames.keys():
            raise ValueError(
                f"{filepath.name} non contiene frame geometrici.\n"
                "Usa uno dei file sorgente (cosmo_L3.h5 / ext / ext2), "
                "non il file merged."
            )

        if frame_idx is not None:
            name = f"frame_{frame_idx:06d}"
        elif step is not None:
            name = find_frame_by_step(frames, step)
            if name is None:
                # Fallback: tratta --step come frame_idx diretto
                name = f"frame_{step - 1:06d}"
        else:
            raise ValueError("Specificare --step o --frame")

        if name not in frames:
            available = sorted(frames.keys())
            raise ValueError(
                f"Frame '{name}' non trovato. "
                f"Disponibili: {available[0]} .. {available[-1]}"
            )

        fr = frames[name]
        return {
            'step': int(fr.attrs['step']),
            'time': float(fr.attrs['time']),
            'positions': fr['positions'][:],
            'chi_values': fr['chi_values'][:],
            'tau_locale': fr['tau_locale'][:],
            'contorsione_locale': fr['contorsione_locale'][:],
        }


def build_edges(positions: np.ndarray, k: int = 6):
    """k-nearest-neighbors sulle posizioni 3D → lista di archi (i, j)."""
    tree = cKDTree(positions)
    _, indices = tree.query(positions, k=k + 1)
    edges = []
    seen = set()
    for i, neighbors in enumerate(indices):
        for j in neighbors[1:]:
            key = (min(i, j), max(i, j))
            if key not in seen:
                seen.add(key)
                edges.append((i, int(j)))
    return edges


def project_2d(positions: np.ndarray) -> np.ndarray:
    """Proietta 3D → 2D via PCA (prime 2 componenti principali)."""
    centered = positions - positions.mean(axis=0)
    _, _, Vt = np.linalg.svd(centered, full_matrices=False)
    return centered @ Vt[:2].T


def _normalize(arr: np.ndarray) -> np.ndarray:
    lo, hi = arr.min(), arr.max()
    return (arr - lo) / (hi - lo + 1e-12)


def render_frame(data: dict, ax, title: str, show_torsion: bool = True,
                 k_neighbors: int = 6, subsample: int = None,
                 alpha_edge: float = 0.12):
    """Disegna un frame sul Axes fornito. Restituisce lo scatter per la colorbar."""
    pos3d = data['positions']
    tau = data['tau_locale']
    K2 = data['contorsione_locale']
    N = len(pos3d)

    # Subsample per performance su L3 (13824 nodi)
    if subsample and subsample < N:
        rng = np.random.default_rng(42)
        idx = rng.choice(N, subsample, replace=False)
        idx.sort()
        pos3d, tau, K2 = pos3d[idx], tau[idx], K2[idx]
        N = subsample

    pos2d = project_2d(pos3d)
    edges = build_edges(pos3d, k=k_neighbors)

    tau_n = _normalize(tau)
    K2_n = _normalize(K2)

    edge_cmap = cm.RdBu_r
    node_cmap = cm.coolwarm

    # Archi con LineCollection (molto più veloce di ax.plot in loop)
    segs = np.array([[pos2d[i], pos2d[j]] for i, j in edges])
    if show_torsion:
        edge_colors = edge_cmap(np.array([(K2_n[i] + K2_n[j]) / 2 for i, j in edges]))
    else:
        edge_colors = np.full((len(edges), 4), [0.5, 0.5, 0.5, alpha_edge])

    lc = LineCollection(segs, colors=edge_colors, linewidths=0.3, alpha=alpha_edge)
    ax.add_collection(lc)

    # Nodi
    sc = ax.scatter(
        pos2d[:, 0], pos2d[:, 1],
        c=tau_n if show_torsion else 'steelblue',
        cmap=node_cmap if show_torsion else None,
        s=0.8, alpha=0.7, linewidths=0,
    )

    ax.autoscale()
    ax.set_aspect('equal')
    ax.set_title(title, color='white', fontsize=9, pad=4)
    ax.axis('off')
    return sc


def main():
    p = argparse.ArgumentParser(
        description="VQT manifold graph renderer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('file', type=Path, help="File HDF5 sorgente (con frames geometrici)")
    p.add_argument('--step', type=int, default=None,
                   help="Step (relativo al file) da visualizzare")
    p.add_argument('--frame', type=int, default=None,
                   help="Indice frame 0-based (alternativo a --step)")
    p.add_argument('--compare', type=int, default=None,
                   help="Secondo step per confronto side-by-side")
    p.add_argument('--compare-file', type=Path, default=None,
                   help="File HDF5 per il secondo step (default: stesso file)")
    p.add_argument('--show-torsion', action='store_true',
                   help="Colora nodi per τ_locale, archi per K² (contorsione)")
    p.add_argument('-k', '--k-neighbors', type=int, default=6,
                   help="Nearest-neighbor per archi (default: 6)")
    p.add_argument('--subsample', type=int, default=None,
                   help="Limita a N nodi casuali (consigliato 2000-4000 per L3)")
    p.add_argument('--output', type=Path, default=None,
                   help="Salva PNG (se omesso: mostra finestra interattiva)")
    p.add_argument('--dpi', type=int, default=150)
    p.add_argument('--interactive', action='store_true',
                   help="Forza visualizzazione interattiva (richiede display)")
    args = p.parse_args()

    if args.step is None and args.frame is None:
        p.error("Specificare --step N o --frame N")

    if args.interactive:
        matplotlib.use('TkAgg')
        import importlib
        import matplotlib.pyplot as _plt
        globals()['plt'] = importlib.reload(_plt)

    # Carica frame principale
    try:
        d1 = load_frame(args.file, step=args.step, frame_idx=args.frame)
    except Exception as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)

    step_label = args.step if args.step is not None else args.frame
    title1 = f"Step {d1['step']}  t={d1['time']:.3f} P  [{args.file.name}]"

    BG = '#0d0d0d'

    if args.compare is not None:
        src2 = args.compare_file or args.file
        try:
            d2 = load_frame(src2, step=args.compare)
        except Exception as e:
            print(f"Errore frame confronto: {e}", file=sys.stderr)
            sys.exit(1)
        title2 = f"Step {d2['step']}  t={d2['time']:.3f} P  [{src2.name}]"

        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.patch.set_facecolor(BG)
        for ax in axes:
            ax.set_facecolor(BG)

        sc = render_frame(d1, axes[0], title1, args.show_torsion,
                          args.k_neighbors, args.subsample)
        render_frame(d2, axes[1], title2, args.show_torsion,
                     args.k_neighbors, args.subsample)

        if args.show_torsion and sc is not None:
            cbar = fig.colorbar(sc, ax=axes, fraction=0.02, pad=0.02)
            cbar.set_label('τ_locale (normalizzato)', color='white', fontsize=8)
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')

        sup = "VQT L3 — Confronto Manifold Topologico"
        if args.show_torsion:
            sup += "  |  nodi: τ  •  archi: K² (RdBu_r)"
        fig.suptitle(sup, color='white', fontsize=11, y=0.98)
    else:
        fig, ax = plt.subplots(figsize=(12, 12))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        sc = render_frame(d1, ax, title1, args.show_torsion,
                          args.k_neighbors, args.subsample)
        if args.show_torsion and sc is not None:
            cbar = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.01)
            cbar.set_label('τ_locale (normalizzato)', color='white', fontsize=8)
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')
        fig.suptitle("VQT L3 — Manifold Topologico", color='white', fontsize=12)

    plt.tight_layout()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(args.output, dpi=args.dpi, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        print(f"Salvato: {args.output}")
    elif args.interactive:
        plt.show()
    else:
        out = Path(f"manifold_step{step_label}.png")
        plt.savefig(out, dpi=args.dpi, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        print(f"Salvato: {out}")


if __name__ == '__main__':
    main()
