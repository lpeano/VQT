#!/usr/bin/env python3
"""
Analisi dati topologici da file HDF5 generati con generate_topological_dataset.py.

Usa ConstraintDensityPlaybackEngine per caricare i dati e produce
un plot a 4 pannelli:
  1. ρ_constraint media nel tempo (con banda ±σ)
  2. H_total emergente nel tempo
  3. Errore chiusura 720° nel tempo
  4. σ(ρ) come indicatore di clustering spaziale eterogeneity
"""

import sys
import argparse
import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# Framework VQT
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))  # repo root (auto-shim)

from wqt_oop.hdf5_playback import ConstraintDensityPlaybackEngine


def parse_args():
    p = argparse.ArgumentParser(
        description="Analisi dataset topologico VQT (HDF5)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input",  "-i", default="cosmo_L2_topo.h5",
                   help="File HDF5 di input")
    p.add_argument("--output", "-o", default="topo_analysis.png",
                   help="File PNG output del plot")
    p.add_argument("--title",  "-t", default=None,
                   help="Titolo del plot (default: ricavato dal nome file)")
    p.add_argument("--dpi",    type=int, default=150)
    p.add_argument("--no-plot", action="store_true",
                   help="Stampa solo il summary, non genera PNG")
    return p.parse_args()


def decode_phases(phase_arr):
    return [
        p.decode('utf-8').rstrip('\x00') if isinstance(p, bytes) else str(p)
        for p in phase_arr
    ]


def main():
    args = parse_args()
    filepath = Path(args.input)

    if not filepath.exists():
        print(f"Errore: file non trovato: {filepath}")
        return 1

    # ---------------------------------------------------------------
    # Carica engine
    # ---------------------------------------------------------------
    print(f"\nCaricamento {filepath} ...")
    engine = ConstraintDensityPlaybackEngine(filepath, follow_mode=False)
    engine.print_topological_summary()

    topo = engine._topo_data
    if not topo:
        print("Nessun dato topologico nel file.")
        return 1

    # ---------------------------------------------------------------
    # Estrai serie temporali
    # ---------------------------------------------------------------
    steps      = topo['step'].astype(float)
    time_arr   = topo['time'].astype(float)
    rho_mean   = topo['mean_constraint_density'].astype(float)
    rho_std    = topo['constraint_density_std'].astype(float)
    H_emergent = topo['H_total_emergent'].astype(float)
    closure    = topo['closure_error_deg'].astype(float)
    Q_topo     = topo['topology_charge'].astype(float)
    phases     = decode_phases(topo['phase_label'])
    transitions = topo['transition_detected'].astype(bool)
    N_dof      = int(topo['N_dof'][0]) if len(topo['N_dof']) else 0

    # Normalizza H per visualizzazione leggibile
    H0 = H_emergent[0] if H_emergent[0] != 0 else 1.0
    H_rel = (H_emergent - H0) / abs(H0) * 100.0   # drift % rispetto a H_0

    # Trend lineare ρ
    if len(rho_mean) > 2:
        slope, intercept = np.polyfit(steps, rho_mean, 1)
    else:
        slope = 0.0

    transition_steps = steps[transitions]

    # ---------------------------------------------------------------
    # Stampa analisi numerica
    # ---------------------------------------------------------------
    print("=" * 60)
    print("  ANALISI QUANTITATIVA")
    print("=" * 60)
    print(f"  DOF:                 {N_dof}")
    print(f"  Steps totali:        {int(steps[-1])}")
    print(f"  Tempo fisico:        {time_arr[-1]:.3f} [Planck]")
    print()
    print(f"  ρ_constraint iniziale: {rho_mean[0]:.4f}")
    print(f"  ρ_constraint finale:   {rho_mean[-1]:.4f}")
    print(f"  ρ min/max:             {rho_mean.min():.4f} / {rho_mean.max():.4f}")
    print(f"  ρ media:               {rho_mean.mean():.4f}  ±  {rho_mean.std():.4f}")
    print(f"  Trend ρ:               {slope:+.6f} / step")
    print()
    print(f"  H_emergent iniziale:   {H_emergent[0]:.4e}")
    print(f"  H_emergent finale:     {H_emergent[-1]:.4e}")
    print(f"  Drift H:               {H_rel[-1]:+.2f}%")
    print()
    print(f"  Closure err medio:     {closure.mean():.1f}°")
    print(f"  Closure err min/max:   {closure.min():.1f}° / {closure.max():.1f}°")
    print()
    print(f"  Q_topologica iniziale: {Q_topo[0]:.1f}")
    print(f"  Q_topologica finale:   {Q_topo[-1]:.1f}")
    print(f"  ΔQ:                    {Q_topo[-1]-Q_topo[0]:+.1f}")
    print()
    print(f"  Transizioni rilevate:  {int(transitions.sum())}")
    if len(transition_steps):
        print(f"  Step transizioni:      {transition_steps.astype(int).tolist()}")
    print("=" * 60)

    if args.no_plot:
        return 0

    # ---------------------------------------------------------------
    # Plot 4 pannelli
    # ---------------------------------------------------------------
    title = args.title or filepath.stem.replace('_', ' ').upper()

    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(
        f"{title}   |   DOF={N_dof}   |   steps={int(steps[-1])}",
        fontsize=13, fontweight='bold', y=0.98
    )
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.32)

    # colori fase
    PHASE_COLORS = {
        'vacuum':     '#4e91d9',
        'transition': '#f0a500',
        'condensed':  '#d94e4e',
        'unknown':    '#888888',
    }
    phase_colors = [PHASE_COLORS.get(ph, '#888888') for ph in phases]

    # ---- Pannello 1: ρ_mean(t) ± σ ----
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.fill_between(steps, rho_mean - rho_std, rho_mean + rho_std,
                     alpha=0.25, color='steelblue', label='±σ')
    ax1.plot(steps, rho_mean, color='steelblue', lw=1.5, label='ρ_mean')
    # Linee di soglia di fase
    ax1.axhline(0.6, color='orange', ls='--', lw=0.8, label='transition threshold')
    ax1.axhline(0.3, color='royalblue', ls='--', lw=0.8, label='vacuum threshold')
    # Trend lineare
    trend_line = slope * steps + intercept
    ax1.plot(steps, trend_line, color='navy', ls=':', lw=1.0,
             label=f'trend {slope:+.2e}/step')
    # Transizioni
    for ts in transition_steps:
        ax1.axvline(ts, color='red', lw=1.2, alpha=0.6)
    ax1.set_xlabel('Step')
    ax1.set_ylabel('ρ_constraint (mean)')
    ax1.set_title('Densità Vincolo Topologico')
    ax1.legend(fontsize=7, loc='lower left')
    ax1.set_ylim(max(0, rho_mean.min() - 0.05), min(1.05, rho_mean.max() + 0.05))
    ax1.grid(True, alpha=0.3)

    # ---- Pannello 2: H_emergente (drift %) ----
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(steps, H_rel, color='crimson', lw=1.2)
    ax2.axhline(0, color='black', lw=0.6, ls='-')
    for ts in transition_steps:
        ax2.axvline(ts, color='red', lw=1.2, alpha=0.6)
    ax2.set_xlabel('Step')
    ax2.set_ylabel('ΔH / H₀  (%)')
    ax2.set_title('Energia Emergente H_total (drift %)')
    ax2.grid(True, alpha=0.3)

    # ---- Pannello 3: Errore chiusura 720° ----
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.scatter(steps, closure, c=phase_colors, s=3, alpha=0.6, linewidths=0)
    ax3.axhline(15.0, color='green', ls='--', lw=0.8, label='tol=15°')
    for ts in transition_steps:
        ax3.axvline(ts, color='red', lw=1.2, alpha=0.6)
    ax3.set_xlabel('Step')
    ax3.set_ylabel('Closure error (°)')
    ax3.set_title('Chiusura Spinoriale 720°  (Σ τᵢ mod 4π)')
    # Legenda fasi
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=PHASE_COLORS[ph], label=ph)
        for ph in ['vacuum', 'transition', 'condensed']
        if ph in phases
    ]
    if legend_elements:
        ax3.legend(handles=legend_elements, fontsize=7, loc='upper right')
    ax3.set_ylim(-5, 370)
    ax3.grid(True, alpha=0.3)

    # ---- Pannello 4: σ(ρ) — eterogeneità clustering ----
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(steps, rho_std, color='mediumpurple', lw=1.2)
    ax4.fill_between(steps, 0, rho_std, alpha=0.25, color='mediumpurple')
    for ts in transition_steps:
        ax4.axvline(ts, color='red', lw=1.2, alpha=0.6, label='transition')
    ax4.set_xlabel('Step')
    ax4.set_ylabel('σ(ρ_constraint)')
    ax4.set_title('Eterogeneità Spaziale  σ(ρ)  [clustering]')
    ax4.grid(True, alpha=0.3)

    # Legenda globale transizioni
    if len(transition_steps):
        fig.text(0.5, 0.01,
                 f"Linee rosse = transizioni di fase rilevate ({int(transitions.sum())} totali)",
                 ha='center', fontsize=9, color='red')

    # ---- Salva ----
    out_path = Path(args.output)
    fig.savefig(out_path, dpi=args.dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"\nPlot salvato: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
