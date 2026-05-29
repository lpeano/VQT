#!/usr/bin/env python3
"""
Confronto run L2: baseline statico vs variazionale.

Uso:
    python -X utf8 compare_l2_runs.py \
        --baseline cosmo_L2_topo.h5 \
        --var      cosmo_L2_variational.h5 \
        --output   compare_L2.png
"""

import argparse
import sys
from pathlib import Path

import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


def load_topo(hf):
    tv = hf['topological_validation']
    return {
        'time':    tv['time'][:].astype(float),
        'rho':     tv['mean_constraint_density'][:].astype(float),
        'rho_std': tv['constraint_density_std'][:].astype(float),
        'closure': tv['closure_error_deg'][:].astype(float),
        'H':       tv['H_total_emergent'][:].astype(float),
        'Q':       tv['topology_charge'][:].astype(float),
    }


def parse_args():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('--baseline', '-b', default='cosmo_L2_topo.h5')
    p.add_argument('--var',      '-v', default='cosmo_L2_variational.h5')
    p.add_argument('--output',   '-o', default='compare_L2.png')
    p.add_argument('--rho-0',    type=float, default=0.85,
                   help='Set-point variazionale (linea di riferimento)')
    p.add_argument('--dpi',      type=int,   default=150)
    return p.parse_args()


def main():
    args = parse_args()

    for path in [args.baseline, args.var]:
        if not Path(path).exists():
            print(f"File non trovato: {path}")
            return 1

    with h5py.File(args.baseline, 'r') as f1, h5py.File(args.var, 'r') as f2:
        d1 = load_topo(f1)
        d2 = load_topo(f2)

        # potential_S ha 2 entry per step (pre-kick + post-kick)
        # Prendiamo solo i post-kick (indici dispari) e allineiamo a t2
        S_raw = f2['variational_force']['potential_S'][:].astype(float)
        F_raw = f2['variational_force']['force_rms'][:].astype(float)

        n_steps = len(d2['time'])
        if len(S_raw) == 2 * n_steps:
            S2 = S_raw[1::2]   # post-kick: indice 1, 3, 5, ...
            F2 = F_raw[1::2]
        else:
            S2 = S_raw[:n_steps]
            F2 = F_raw[:n_steps]

    t1, t2 = d1['time'], d2['time']

    # Normalizza H baseline per drift %
    H1 = d1['H']
    H1_rel = (H1 - H1[0]) / (abs(H1[0]) + 1e-30) * 100.0

    # ---------------------------------------------------------------
    # Stampa summary numerica
    # ---------------------------------------------------------------
    print("=" * 60)
    print("  CONFRONTO L2: BASELINE vs VARIAZIONALE")
    print("=" * 60)
    print(f"  Baseline:     {args.baseline}  ({len(t1)} step)")
    print(f"  Variazionale: {args.var}  ({len(t2)} step)")
    print()
    print(f"  rho baseline:    {d1['rho'][0]:.4f} -> {d1['rho'][-1]:.4f}  "
          f"(mean={d1['rho'].mean():.4f}  std={d1['rho'].std():.4f})")
    print(f"  rho variaz.:     {d2['rho'][0]:.4f} -> {d2['rho'][-1]:.4f}  "
          f"(mean={d2['rho'].mean():.4f}  std={d2['rho'].std():.4f})")
    print(f"  rho_0 set-point: {args.rho_0:.4f}")
    print()
    print(f"  S iniziale:  {S2[0]:.4e}")
    print(f"  S finale:    {S2[-1]:.4e}")
    print(f"  DeltaS:      {(S2[-1]-S2[0]):+.4e}  "
          f"({'decrescente (minimizz. OK)' if S2[-1] < S2[0] else 'crescente'})")
    print()
    print(f"  |F|_rms inizio: {F2[0]:.4e}")
    print(f"  |F|_rms fine:   {F2[-1]:.4e}")
    print()
    print(f"  Closure baseline (mean): {d1['closure'].mean():.1f} deg")
    print(f"  Closure variaz.  (mean): {d2['closure'].mean():.1f} deg")
    print("=" * 60)

    # ---------------------------------------------------------------
    # Plot 2x3 pannelli
    # ---------------------------------------------------------------
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(
        "L2 Baseline vs Variazionale — VQT Topological Dynamics",
        fontsize=13, fontweight='bold', y=0.99,
    )
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.34)

    # ---- P1: rho(t) confronto ----
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.fill_between(t1, d1['rho'] - d1['rho_std'], d1['rho'] + d1['rho_std'],
                     alpha=0.15, color='steelblue')
    ax1.plot(t1, d1['rho'], color='steelblue', lw=1.2, alpha=0.8, label='Baseline')
    ax1.fill_between(t2, d2['rho'] - d2['rho_std'], d2['rho'] + d2['rho_std'],
                     alpha=0.15, color='crimson')
    ax1.plot(t2, d2['rho'], color='crimson', lw=1.8, label='Variazionale')
    ax1.axhline(args.rho_0, color='black', ls='--', lw=1.0, label=f'rho_0={args.rho_0}')
    ax1.set_xlabel('Tempo [Planck]')
    ax1.set_ylabel('rho_constraint (mean)')
    ax1.set_title('Omeostasi: densita\' vincolo')
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # ---- P2: sigma(rho) confronto ----
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(t1, d1['rho_std'], color='steelblue', lw=1.2, alpha=0.8, label='Baseline')
    ax2.plot(t2, d2['rho_std'], color='crimson', lw=1.8, label='Variazionale')
    ax2.set_xlabel('Tempo [Planck]')
    ax2.set_ylabel('sigma(rho)')
    ax2.set_title('Clusterizzazione: sigma(rho)')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ---- P3: Potenziale S ----
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(t2, S2, color='darkorchid', lw=1.5, label='S[chi,tau]')
    ax3.axhline(S2.min(), color='green', ls=':', lw=0.8, label=f'S_min={S2.min():.2e}')
    ax3.set_xlabel('Tempo [Planck]')
    ax3.set_ylabel('S  [Eq. S-1]')
    ax3.set_title('Minimizzazione potenziale S')
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # ---- P4: H emergente (drift %) ----
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.plot(t1, H1_rel, color='steelblue', lw=1.2, alpha=0.8, label='Baseline')
    H2 = d2['H']
    H2_rel = (H2 - H2[0]) / (abs(H2[0]) + 1e-30) * 100.0
    ax4.plot(t2, H2_rel, color='crimson', lw=1.8, label='Variazionale')
    ax4.axhline(0, color='black', lw=0.5)
    ax4.set_xlabel('Tempo [Planck]')
    ax4.set_ylabel('DeltaH / H_0  (%)')
    ax4.set_title('H emergente (non e\' un vincolo)')
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    # ---- P5: Closure error confronto ----
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.plot(t1, d1['closure'], color='steelblue', lw=0.8, alpha=0.6, label='Baseline')
    ax5.plot(t2, d2['closure'], color='crimson', lw=1.2, alpha=0.8, label='Variazionale')
    ax5.axhline(15.0, color='green', ls='--', lw=0.8, label='tol=15 deg')
    ax5.set_xlabel('Tempo [Planck]')
    ax5.set_ylabel('Closure error (deg)')
    ax5.set_title('Chiusura spinoriale 720 deg')
    ax5.legend(fontsize=8)
    ax5.set_ylim(-5, 370)
    ax5.grid(True, alpha=0.3)

    # ---- P6: |F|_rms variazionale ----
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.semilogy(t2, F2, color='darkorange', lw=1.5, label='|F_top|_rms')
    ax6.set_xlabel('Tempo [Planck]')
    ax6.set_ylabel('|F_top|_rms  (log)')
    ax6.set_title('Intensita\' forza topologica')
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3, which='both')

    out = Path(args.output)
    fig.savefig(out, dpi=args.dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"\nPlot salvato: {out.resolve()}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
