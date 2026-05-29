#!/usr/bin/env python3
"""
Confronto cross-scala: L1, L2, L3 — validazione Legge FA [Eq. FA-2].

Normalizza le quantità per N (numero segmenti) per confrontare
comportamenti su scale diverse. Se la Legge FA è corretta, le
curve normalizzate devono colassare sullo stesso andamento.

Uso:
    python -X utf8 compare_scales.py \
        --l2  cosmo_L2_variational.h5 \
        --l3  cosmo_L3_probe.h5 \
        --output compare_scales.png
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


# ---- Legge FA [Eq. FA-2] ---------------------------------------------------
RHO_0_BASE       = 0.85
DELTA_RHO_FRACTAL = 0.05

def rho_0_eff(level: int) -> float:
    n = 24 ** level
    return RHO_0_BASE + DELTA_RHO_FRACTAL / (n ** 0.5)

def rho_star_empirical(level: int) -> float:
    """Densita' di equilibrio empirica (fit da dati baseline)."""
    return 0.952 - 0.345 / (24 ** (level / 2.0))

# ---- Colori per livello -----------------------------------------------------
LEVEL_COLORS = {1: '#2196F3', 2: '#E53935', 3: '#43A047', 4: '#7B1FA2'}


def load_file(path: str) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    with h5py.File(p, 'r') as hf:
        tv = hf['topological_validation']
        data = {
            'steps':    tv['step'][:].astype(float),
            'time':     tv['time'][:].astype(float),
            'rho':      tv['mean_constraint_density'][:].astype(float),
            'rho_std':  tv['constraint_density_std'][:].astype(float),
            'H':        tv['H_total_emergent'][:].astype(float),
            'N_dof':    int(tv['N_dof'][0]),
            'N_seg':    int(tv['N_segments'][0]) if 'N_segments' in tv else int(tv['N_dof'][0]) // 2,
        }
        if 'variational_force' in hf:
            vg = hf['variational_force']
            S_raw = vg['potential_S'][:].astype(float)
            F_raw = vg['force_rms'][:].astype(float)
            n_steps = len(data['steps'])
            if len(S_raw) == 2 * n_steps:
                data['S'] = S_raw[1::2]   # post-kick
                data['F'] = F_raw[1::2]
            else:
                data['S'] = S_raw[:n_steps]
                data['F'] = F_raw[:n_steps]
        else:
            data['S'] = None
            data['F'] = None
    return data


def parse_args():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('--l1',  default=None,                    help='File HDF5 L1 (opzionale)')
    p.add_argument('--l2',  default='cosmo_L2_variational.h5')
    p.add_argument('--l3',  default='cosmo_L3_probe.h5')
    p.add_argument('--output', '-o', default='compare_scales.png')
    p.add_argument('--dpi',    type=int, default=150)
    return p.parse_args()


def main():
    args = parse_args()

    datasets = {}
    level_files = [(1, args.l1), (2, args.l2), (3, args.l3)]
    for lv, path in level_files:
        if path:
            d = load_file(path)
            if d:
                datasets[lv] = d
                print(f"  L{lv}: {path}  ({d['N_seg']} segmenti, {len(d['steps'])} step)")
            else:
                print(f"  L{lv}: {path} — NON TROVATO")

    if not datasets:
        print("Nessun file trovato.")
        return 1

    # -----------------------------------------------------------------------
    # Tabella Legge FA
    # -----------------------------------------------------------------------
    print()
    print("=" * 65)
    print("  LEGGE FA — confronto previsioni vs osservazioni")
    print("=" * 65)
    print(f"  {'L':>3}  {'N':>7}  {'rho_0_eff':>10}  {'rho*_pred':>10}  "
          f"{'rho_iniz':>10}  {'rho_fin':>10}  {'Pressione':>10}")
    print(f"  {'-'*3}  {'-'*7}  {'-'*10}  {'-'*10}  "
          f"{'-'*10}  {'-'*10}  {'-'*10}")
    for lv, d in sorted(datasets.items()):
        N = d['N_seg']
        r0 = rho_0_eff(lv)
        rs = rho_star_empirical(lv)
        ri = d['rho'][0]
        rf = d['rho'][-1]
        press = ri - r0
        print(f"  {lv:>3}  {N:>7}  {r0:>10.4f}  {rs:>10.4f}  "
              f"{ri:>10.4f}  {rf:>10.4f}  {press:>+10.4f}")

    for lv, d in sorted(datasets.items()):
        N = d['N_seg']
        if d['S'] is not None:
            S0, Sf = d['S'][0], d['S'][-1]
            S_per_N0, S_per_Nf = S0 / N, Sf / N
            print(f"\n  L{lv} S: {S0:.2e} -> {Sf:.2e}  "
                  f"({(Sf-S0)/S0*100:+.1f}%)  "
                  f"[per segmento: {S_per_N0:.4f} -> {S_per_Nf:.4f}]")
    print("=" * 65)

    # -----------------------------------------------------------------------
    # Plot 2x3
    # -----------------------------------------------------------------------
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("Confronto Cross-Scala L2/L3 — Validazione Legge FA [Eq. FA-2]",
                 fontsize=13, fontweight='bold', y=0.99)
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.34)

    # P1: rho(t)
    ax1 = fig.add_subplot(gs[0, 0])
    for lv, d in sorted(datasets.items()):
        c = LEVEL_COLORS.get(lv, 'gray')
        ax1.fill_between(d['time'], d['rho'] - d['rho_std'],
                         d['rho'] + d['rho_std'], alpha=0.12, color=c)
        ax1.plot(d['time'], d['rho'], color=c, lw=1.8, label=f'L{lv} (N={d["N_seg"]})')
        # rho_0_eff orizzontale punteggiato per ogni livello
        ax1.axhline(rho_0_eff(lv), color=c, ls=':', lw=0.8)
    ax1.set_xlabel('Tempo [Planck]')
    ax1.set_ylabel('rho_constraint (mean)')
    ax1.set_title('Omeostasi: rho(t) per livello')
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # P2: sigma(rho)
    ax2 = fig.add_subplot(gs[0, 1])
    for lv, d in sorted(datasets.items()):
        c = LEVEL_COLORS.get(lv, 'gray')
        ax2.plot(d['time'], d['rho_std'], color=c, lw=1.5, label=f'L{lv}')
    ax2.set_xlabel('Tempo [Planck]')
    ax2.set_ylabel('sigma(rho)')
    ax2.set_title('Clusterizzazione sigma(rho)')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # P3: S per segmento (normalizzato)
    ax3 = fig.add_subplot(gs[0, 2])
    has_S = False
    for lv, d in sorted(datasets.items()):
        if d['S'] is not None:
            c = LEVEL_COLORS.get(lv, 'gray')
            S_norm = d['S'] / d['N_seg']
            ax3.plot(d['time'], S_norm, color=c, lw=1.5, label=f'L{lv}')
            has_S = True
    if has_S:
        ax3.set_xlabel('Tempo [Planck]')
        ax3.set_ylabel('S / N  (per segmento)')
        ax3.set_title('Potenziale S normalizzato — Legge FA')
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3)
    else:
        ax3.set_visible(False)

    # P4: H per segmento (normalizzato)
    ax4 = fig.add_subplot(gs[1, 0])
    for lv, d in sorted(datasets.items()):
        c = LEVEL_COLORS.get(lv, 'gray')
        H_norm = d['H'] / d['N_seg']
        ax4.plot(d['time'], H_norm, color=c, lw=1.5, label=f'L{lv}')
    ax4.set_xlabel('Tempo [Planck]')
    ax4.set_ylabel('H / N  (per segmento)')
    ax4.set_title('H emergente normalizzato')
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    # P5: |F|_rms per segmento
    ax5 = fig.add_subplot(gs[1, 1])
    has_F = False
    for lv, d in sorted(datasets.items()):
        if d['F'] is not None:
            c = LEVEL_COLORS.get(lv, 'gray')
            F_norm = d['F'] / (d['N_seg'] ** 0.5)
            ax5.semilogy(d['time'], F_norm, color=c, lw=1.5, label=f'L{lv}')
            has_F = True
    if has_F:
        ax5.set_xlabel('Tempo [Planck]')
        ax5.set_ylabel('|F|_rms / sqrt(N)  (log)')
        ax5.set_title('Intensita\' forza topologica (normalizzata)')
        ax5.legend(fontsize=8)
        ax5.grid(True, alpha=0.3, which='both')
    else:
        ax5.set_visible(False)

    # P6: Pressione topologica (rho - rho_0_eff) per livello
    ax6 = fig.add_subplot(gs[1, 2])
    for lv, d in sorted(datasets.items()):
        c = LEVEL_COLORS.get(lv, 'gray')
        pressure = d['rho'] - rho_0_eff(lv)
        ax6.plot(d['time'], pressure, color=c, lw=1.5,
                 label=f'L{lv}  [rho_0_eff={rho_0_eff(lv):.4f}]')
    ax6.axhline(0, color='black', lw=0.6, ls='-')
    ax6.set_xlabel('Tempo [Planck]')
    ax6.set_ylabel('rho - rho_0_eff  (pressione)')
    ax6.set_title('Pressione topologica omeostatica [Eq. FA-2]')
    ax6.legend(fontsize=7)
    ax6.grid(True, alpha=0.3)

    out = Path(args.output)
    fig.savefig(out, dpi=args.dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"\nPlot salvato: {out.resolve()}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
