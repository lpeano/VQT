#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_comparison_animation.py
Video comparativo L1 / L2 / L3 del manifold VQT.

Layout (widescreen 20x11):
  Riga superiore : 3 pannelli 3D affiancati (L1 | L2 | L3)
  Riga inferiore : 4 grafici di confronto
                   [sigma(rho) vs t] [omega medio vs t]
                   [istogramma chi fused] [scatter DOF vs sigma]

Sincronizzazione temporale: range comune t in [0, 5 P].
  L1 : 100 frame (stride 1), delta_t = 0.05 P/frame
  L2 : 100 frame (stride 1), delta_t = 0.05 P/frame
  L3 : 100 frame (stride 5), delta_t = 0.05 P/frame

Uso:
  cd VQT_repo
  python experiments/render_comparison_animation.py
  python experiments/render_comparison_animation.py --fps 30 --dpi 110 --rotate
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import h5py

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_REPO_ROOT  = Path(__file__).resolve().parent.parent
_EXP_DIR    = _REPO_ROOT / 'experiments' / 'exp1'

_FILES = {
    'L1': _EXP_DIR / 'cosmo_L1.h5',
    'L2': _EXP_DIR / 'cosmo_L2.h5',
    'L3': _EXP_DIR / 'cosmo_L3_ext3.h5',
}
_DEFAULT_OUT = _EXP_DIR / 'comparison_L1_L2_L3.mp4'

# Palette livelli (colore principale di ogni livello)
_LEVEL_COLOR = {'L1': '#ffcc44', 'L2': '#44ccff', 'L3': '#88ff88'}

_BG         = '#06080c'
_PANEL_BG   = '#0e1520'
_GRID_C     = '#1c2838'
_TEXT_C     = '#c8d8e8'
_ACCENT     = '#ffcc44'

# Numero di frame animati per livello (comune)
_N_ANIM = 100

# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--fps',        type=int,   default=24)
    p.add_argument('--dpi',        type=int,   default=110)
    p.add_argument('--percentile', type=float, default=75.0,
                   help='Soglia contorsione per L3 (default 75)')
    p.add_argument('--output',     default=str(_DEFAULT_OUT))
    p.add_argument('--rotate',     action='store_true',
                   help='Ruota camera di 120 deg durante animazione')
    p.add_argument('--max-frames', type=int, default=None,
                   help='Tronca a N frame (debug)')
    return p.parse_args()

# -----------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------

def load_level(path: Path, n_anim: int, percentile: float, label: str):
    """
    Carica posizioni, chi, contorsione per un livello.
    Ritorna n_anim frame sincronizzati al range temporale del livello.
    Scala chi in [0,1] centrata sulla mediana globale del livello.
    """
    print(f'[load {label}] {path.name} ...', flush=True)
    t0 = time.time()

    with h5py.File(path, 'r') as f:
        frame_keys = sorted(f['frames'].keys())
        n_total = len(frame_keys)
        fr0 = f['frames'][frame_keys[0]]
        n_nodes = fr0['positions'].shape[0]

        # Carica tutti i frame raw
        positions_raw  = np.empty((n_total, n_nodes, 3), dtype=np.float32)
        chi_raw        = np.empty((n_total, n_nodes),    dtype=np.float32)
        contors_raw    = np.empty((n_total, n_nodes),    dtype=np.float32)

        for idx, key in enumerate(frame_keys):
            fr = f['frames'][key]
            positions_raw[idx] = fr['positions'][()]
            chi_raw[idx]       = fr['chi_values'][()]
            contors_raw[idx]   = fr['contorsione_locale'][()]

        # Topological validation (serie temporale)
        tv      = f['topological_validation']
        tv_t    = tv['time'][:]
        tv_step = tv['step'][:]
        tv_sig  = tv['constraint_density_std'][:]
        tv_rho  = tv['mean_constraint_density'][:]

    # Seleziona n_anim frame nel range [0, max_t_common]
    # Usa stride uniforme
    stride = max(1, n_total // n_anim)
    indices = list(range(0, n_total, stride))[:n_anim]
    # Se non bastano (es. n_total < n_anim), usa tutti
    if len(indices) < n_anim:
        indices = list(range(n_total))

    positions = positions_raw[indices]
    chi       = chi_raw[indices]
    contors   = contors_raw[indices]

    # Mappa temporale per ogni frame animato
    # frame_t[i] = tempo Planck del frame animato i
    frame_t = np.array([tv_t[min(idx, len(tv_t)-1)] for idx in indices], dtype=float)

    # Normalizzazione chi per questo livello: centrata alla mediana, ±3sigma
    chi_flat   = chi_raw.ravel()
    chi_med    = float(np.median(chi_flat))
    chi_sig    = float(chi_flat.std())
    chi_lo     = chi_med - 3.0 * chi_sig
    chi_hi     = chi_med + 3.0 * chi_sig
    chi_norm   = Normalize(vmin=chi_lo, vmax=chi_hi)

    # Soglia contorsione: p75 GLOBALE su tutti i frame del livello
    cont_flat      = contors_raw.ravel()
    cont_threshold = float(np.percentile(cont_flat, percentile)) if n_nodes > 24 else 0.0
    cont_cap       = float(np.percentile(cont_flat, 99))

    # Media omega (contorsione solitonica) per frame animato
    mean_omega = np.array([
        float(contors[i][contors[i] >= cont_threshold].mean())
        if (contors[i] >= cont_threshold).any() else 0.0
        for i in range(len(indices))
    ])

    elapsed = time.time() - t0
    n_sol_mean = int(np.mean([(contors[i] >= cont_threshold).sum() for i in range(len(indices))]))
    print(f'  {n_total} frame totali -> {len(indices)} animati | '
          f'{n_nodes} nodi | threshold={cont_threshold:.1f} deg | '
          f'media solitoni/frame={n_sol_mean} | {elapsed:.1f}s', flush=True)

    return {
        'label':      label,
        'positions':  positions,   # (n_anim, n_nodes, 3)
        'chi':        chi,         # (n_anim, n_nodes)
        'contors':    contors,     # (n_anim, n_nodes)
        'frame_t':    frame_t,     # (n_anim,)
        'tv_t':       tv_t,
        'tv_sig':     tv_sig,
        'tv_rho':     tv_rho,
        'chi_norm':   chi_norm,
        'chi_lo':     chi_lo,
        'chi_hi':     chi_hi,
        'chi_med':    chi_med,
        'cont_thresh': cont_threshold,
        'cont_cap':   cont_cap,
        'mean_omega': mean_omega,
        'n_nodes':    n_nodes,
        'n_frames_total': n_total,
    }


# -----------------------------------------------------------------------
# Figure & Axes
# -----------------------------------------------------------------------

def build_figure():
    """
    Layout:
      Row 0 (ratio 3.8): tre subplot 3D + colonna colorbar stretta
      Row 1 (ratio 1.0): quattro pannelli analisi affiancati
    """
    fig = plt.figure(figsize=(20, 11), facecolor=_BG)

    gs_outer = gridspec.GridSpec(
        2, 1, figure=fig,
        height_ratios=[3.8, 1.0],
        hspace=0.08
    )

    # --- Riga 3D: 3 pannelli + 1 colorbar ---
    gs_top = gridspec.GridSpecFromSubplotSpec(
        1, 4,
        subplot_spec=gs_outer[0],
        width_ratios=[1, 1, 1, 0.03],
        wspace=0.04
    )
    ax3d_L1 = fig.add_subplot(gs_top[0, 0], projection='3d')
    ax3d_L2 = fig.add_subplot(gs_top[0, 1], projection='3d')
    ax3d_L3 = fig.add_subplot(gs_top[0, 2], projection='3d')
    cax     = fig.add_subplot(gs_top[0, 3])

    # --- Riga analisi: 4 pannelli ---
    gs_bot = gridspec.GridSpecFromSubplotSpec(
        1, 4,
        subplot_spec=gs_outer[1],
        wspace=0.32
    )
    ax_sig   = fig.add_subplot(gs_bot[0, 0])
    ax_omega = fig.add_subplot(gs_bot[0, 1])
    ax_chi_c = fig.add_subplot(gs_bot[0, 2])
    ax_dof   = fig.add_subplot(gs_bot[0, 3])

    axes_3d  = [ax3d_L1, ax3d_L2, ax3d_L3]
    axes_bot = [ax_sig, ax_omega, ax_chi_c, ax_dof]

    _style_3d_axes(axes_3d)
    _style_bot_axes(axes_bot)

    return fig, axes_3d, axes_bot, cax


def _style_3d_axes(axes_3d):
    for ax in axes_3d:
        ax.set_facecolor(_BG)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor(_GRID_C)
        ax.yaxis.pane.set_edgecolor(_GRID_C)
        ax.zaxis.pane.set_edgecolor(_GRID_C)
        ax.tick_params(colors=_GRID_C, labelsize=4)


def _style_bot_axes(axes_bot):
    for ax in axes_bot:
        ax.set_facecolor(_PANEL_BG)
        for sp in ax.spines.values():
            sp.set_edgecolor(_GRID_C)
        ax.tick_params(colors=_TEXT_C, labelsize=6)
        ax.xaxis.label.set_color(_TEXT_C)
        ax.yaxis.label.set_color(_TEXT_C)
        ax.title.set_color(_TEXT_C)


def _setup_colorbar(fig, cax):
    """Colorbar condivisa RdBu_r (chiralita' relativa normalizzata)."""
    norm = Normalize(vmin=0, vmax=1)
    sm = plt.cm.ScalarMappable(cmap='RdBu_r', norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax, orientation='vertical')
    cb.set_label('chi relativa', color=_TEXT_C, fontsize=6, labelpad=4)
    cb.ax.tick_params(colors=_TEXT_C, labelsize=5)
    mid = 0.5
    cb.ax.axhline(mid, color=_TEXT_C, lw=0.6, ls='--', alpha=0.5)
    cb.ax.text(1.8, mid, 'med', transform=cb.ax.transAxes,
               color=_TEXT_C, fontsize=4.5, va='center')
    return cb


# -----------------------------------------------------------------------
# Pre-compute axis limits per livello (fissi)
# -----------------------------------------------------------------------

def compute_limits(data):
    pos = data['positions'].reshape(-1, 3)
    m = 1.5
    return (
        (float(pos[:,0].min())-m, float(pos[:,0].max())+m),
        (float(pos[:,1].min())-m, float(pos[:,1].max())+m),
        (float(pos[:,2].min())-m, float(pos[:,2].max())+m),
    )


# -----------------------------------------------------------------------
# Static bottom panels (once)
# -----------------------------------------------------------------------

def draw_static_bottom(axes_bot, levels, dof_sigma_data):
    ax_sig, ax_omega, ax_chi_c, ax_dof = axes_bot

    # Sigma(rho) — serie completa sfumata per ogni livello
    for d in levels:
        lc = _LEVEL_COLOR[d['label']]
        ax_sig.plot(d['tv_t'], d['tv_sig'], color=lc, lw=0.7, alpha=0.35,
                    label=d['label'])
    ax_sig.set_title('sigma(rho) vs t', fontsize=7)
    ax_sig.set_xlabel('t [P]', fontsize=6)
    ax_sig.legend(fontsize=5.5, loc='upper right',
                  facecolor=_PANEL_BG, edgecolor=_GRID_C, labelcolor=_TEXT_C)
    ax_sig.set_xlim(0, max(d['tv_t'].max() for d in levels))
    ax_sig.set_ylim(0, max(d['tv_sig'].max() for d in levels) * 1.1)

    # Omega medio — serie completa sfumata
    for d in levels:
        lc = _LEVEL_COLOR[d['label']]
        ax_omega.plot(d['frame_t'], d['mean_omega'], color=lc, lw=0.8, alpha=0.35,
                      label=d['label'])
    ax_omega.set_title('<Omega> solitoni vs t', fontsize=7)
    ax_omega.set_xlabel('t [P]', fontsize=6)
    ax_omega.legend(fontsize=5.5, loc='upper right',
                    facecolor=_PANEL_BG, edgecolor=_GRID_C, labelcolor=_TEXT_C)
    ax_omega.set_xlim(0, max(d['frame_t'].max() for d in levels))

    # Scatter DOF vs sigma(rho) finale
    dofs   = [d['n_nodes'] * (2 if d['label']!='L3' else 2) for d in levels]
    sigmas = [float(d['tv_sig'].mean()) for d in levels]
    labels = [d['label'] for d in levels]
    colors = [_LEVEL_COLOR[d['label']] for d in levels]
    for x, y, lab, c in zip(dofs, sigmas, labels, colors):
        ax_dof.scatter(x, y, color=c, s=80, zorder=5)
        ax_dof.text(x, y*1.04, lab, color=c, fontsize=6, ha='center')
    ax_dof.set_xscale('log')
    ax_dof.set_title('DOF vs <sigma(rho)>', fontsize=7)
    ax_dof.set_xlabel('N nodi', fontsize=6)
    ax_dof.set_ylabel('sigma medio', fontsize=6)
    ax_dof.set_facecolor(_PANEL_BG)

    # ax_chi_c rimane per overlay dinamico (aggiornato per frame)


# -----------------------------------------------------------------------
# Update function (per frame animazione)
# -----------------------------------------------------------------------

def make_update(fig, axes_3d, axes_bot, cax, levels, limits_per_level,
                n_anim, args, time_text):

    ax3d_L1, ax3d_L2, ax3d_L3 = axes_3d
    ax_sig, ax_omega, ax_chi_c, ax_dof = axes_bot

    axes_map = {
        'L1': (ax3d_L1, limits_per_level['L1']),
        'L2': (ax3d_L2, limits_per_level['L2']),
        'L3': (ax3d_L3, limits_per_level['L3']),
    }

    state = {'count': 0, 'tstart': time.time()}

    def update(frame_idx):
        # ---- aggiorna ogni pannello 3D ----
        for d in levels:
            label = d['label']
            ax, (xlim, ylim, zlim) = axes_map[label]
            i = min(frame_idx, len(d['positions']) - 1)

            # Dati frame
            pos    = d['positions'][i]
            chi_v  = d['chi'][i]
            cont_v = d['contors'][i]

            # Filtro solitonico (solo per L3 in pratica; L1/L2 mostrano tutti)
            thresh = d['cont_thresh']
            mask = (cont_v >= thresh) if thresh > 0 else np.ones(len(cont_v), bool)
            if mask.sum() < 5:
                mask = np.ones(len(cont_v), bool)

            pos_f  = pos[mask]
            chi_f  = chi_v[mask]
            cont_f = cont_v[mask]

            c_vals = d['chi_norm'](chi_f)
            # Dimensione: minimo 12, max 180 per L1 (pochi nodi), 80 per L3
            max_size = 180 if d['n_nodes'] <= 24 else (100 if d['n_nodes'] <= 576 else 80)
            sizes = 10.0 + max_size * np.clip(cont_f / (d['cont_cap'] + 1e-9), 0, 1) ** 1.3

            ax.cla()
            ax.set_facecolor(_BG)
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.xaxis.pane.set_edgecolor(_GRID_C)
            ax.yaxis.pane.set_edgecolor(_GRID_C)
            ax.zaxis.pane.set_edgecolor(_GRID_C)
            ax.tick_params(colors=_GRID_C, labelsize=4)

            ax.scatter(pos_f[:,0], pos_f[:,1], pos_f[:,2],
                       c=c_vals, cmap='RdBu_r', s=sizes,
                       alpha=0.75, edgecolors='none',
                       vmin=0.0, vmax=1.0)

            ax.set_xlim(xlim); ax.set_ylim(ylim); ax.set_zlim(zlim)
            ax.set_xlabel('X', color=_GRID_C, fontsize=5, labelpad=-2)
            ax.set_ylabel('Y', color=_GRID_C, fontsize=5, labelpad=-2)
            ax.set_zlabel('Z', color=_GRID_C, fontsize=5, labelpad=-2)

            if args.rotate:
                azim = 25.0 + 120.0 * (frame_idx / max(n_anim - 1, 1))
            else:
                azim = 30.0
            ax.view_init(elev=22, azim=azim)

            t_cur = float(d['frame_t'][i])
            lc = _LEVEL_COLOR[label]
            ax.set_title(
                f'{label}  ({d["n_nodes"]:,} nodi)\n'
                f't={t_cur:.2f}P   <chi>={chi_f.mean():.1f}   sol={mask.sum()}',
                color=lc, fontsize=8, pad=6
            )

        # ---- cursori pannelli inferiori ----
        t_cur_common = float(levels[0]['frame_t'][min(frame_idx, len(levels[0]['frame_t'])-1)])

        # Sigma(rho) con cursore
        ax_sig.cla()
        _style_bot_axes([ax_sig])
        for d in levels:
            lc = _LEVEL_COLOR[d['label']]
            ax_sig.plot(d['tv_t'], d['tv_sig'], color=lc, lw=0.7, alpha=0.4,
                        label=d['label'])
            # Punto corrente
            idx_tv = np.searchsorted(d['tv_t'], t_cur_common)
            idx_tv = min(idx_tv, len(d['tv_t'])-1)
            ax_sig.scatter([d['tv_t'][idx_tv]], [d['tv_sig'][idx_tv]],
                           color=lc, s=18, zorder=6)
        ax_sig.axvline(t_cur_common, color=_ACCENT, lw=0.9, alpha=0.8)
        ax_sig.set_title('sigma(rho)', fontsize=7)
        ax_sig.set_xlabel('t [P]', fontsize=6)
        ax_sig.legend(fontsize=5.5, loc='upper right',
                      facecolor=_PANEL_BG, edgecolor=_GRID_C, labelcolor=_TEXT_C)
        ax_sig.set_xlim(0, max(d['tv_t'].max() for d in levels))

        # Omega con cursore
        ax_omega.cla()
        _style_bot_axes([ax_omega])
        for d in levels:
            lc = _LEVEL_COLOR[d['label']]
            ax_omega.plot(d['frame_t'], d['mean_omega'], color=lc, lw=0.8, alpha=0.45,
                          label=d['label'])
            i_cur = min(frame_idx, len(d['mean_omega'])-1)
            ax_omega.scatter([d['frame_t'][i_cur]], [d['mean_omega'][i_cur]],
                             color=lc, s=18, zorder=6)
        ax_omega.axvline(t_cur_common, color=_ACCENT, lw=0.9, alpha=0.8)
        ax_omega.set_title('<Omega> solitoni', fontsize=7)
        ax_omega.set_xlabel('t [P]', fontsize=6)
        ax_omega.legend(fontsize=5.5, loc='upper right',
                        facecolor=_PANEL_BG, edgecolor=_GRID_C, labelcolor=_TEXT_C)
        ax_omega.set_xlim(0, max(d['frame_t'].max() for d in levels))

        # Istogrammi chi sovrapposti (frame corrente)
        ax_chi_c.cla()
        _style_bot_axes([ax_chi_c])
        for d in levels:
            lc = _LEVEL_COLOR[d['label']]
            i_cur = min(frame_idx, len(d['chi'])-1)
            mask_c = d['contors'][i_cur] >= d['cont_thresh']
            if mask_c.sum() < 5:
                mask_c = np.ones(len(d['chi'][i_cur]), bool)
            ax_chi_c.hist(d['chi'][i_cur][mask_c], bins=30,
                          color=lc, alpha=0.55, density=True,
                          label=d['label'], histtype='stepfilled')
        ax_chi_c.set_title('Distrib. chi  [solitoni]', fontsize=7)
        ax_chi_c.set_xlabel('chi', fontsize=6)
        ax_chi_c.legend(fontsize=5.5, loc='upper right',
                        facecolor=_PANEL_BG, edgecolor=_GRID_C, labelcolor=_TEXT_C)

        # DOF vs sigma (statico, ma riplot per reset stile dopo cla)
        ax_dof.cla()
        _style_bot_axes([ax_dof])
        for d in levels:
            lc = _LEVEL_COLOR[d['label']]
            idx_tv = np.searchsorted(d['tv_t'], t_cur_common)
            idx_tv = min(idx_tv, len(d['tv_sig'])-1)
            sigma_cur = d['tv_sig'][idx_tv]
            ax_dof.scatter(d['n_nodes'], sigma_cur, color=lc, s=60, zorder=5)
            ax_dof.text(d['n_nodes'], sigma_cur*1.06, d['label'],
                        color=lc, fontsize=6, ha='center')
        ax_dof.set_xscale('log')
        ax_dof.set_title('DOF vs sigma', fontsize=7)
        ax_dof.set_xlabel('N nodi', fontsize=6)
        ax_dof.set_ylabel('sigma(rho)', fontsize=6)
        ax_dof.set_xlim(10, 30000)

        # Timestamp globale
        time_text.set_text(
            f't = {t_cur_common:5.2f} P   |   frame {frame_idx+1}/{n_anim}'
        )

        # Progress
        state['count'] += 1
        c = state['count']
        if c % 20 == 0 or c == n_anim:
            el = time.time() - state['tstart']
            eta = el / c * (n_anim - c) if c < n_anim else 0
            print(f'  [{c:3d}/{n_anim}]  {el:.0f}s  ETA {eta:.0f}s', flush=True)

        return []

    return update


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    args = parse_args()
    out  = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    # ---- carica i tre livelli ----
    levels_data = []
    for label, path in _FILES.items():
        if not path.exists():
            print(f'[warn] {path} non trovato, skip {label}', flush=True)
            continue
        d = load_level(path, _N_ANIM, args.percentile, label)
        levels_data.append(d)

    if len(levels_data) == 0:
        print('[error] Nessun file trovato.', flush=True)
        return 1

    n_anim = _N_ANIM if args.max_frames is None else min(args.max_frames, _N_ANIM)

    # ---- limiti assi fissi per livello ----
    limits_per_level = {d['label']: compute_limits(d) for d in levels_data}

    # ---- costruzione figura ----
    fig, axes_3d, axes_bot, cax = build_figure()
    fig.patch.set_facecolor(_BG)

    _setup_colorbar(fig, cax)

    # Titolo globale e timestamp
    fig.text(0.5, 0.985, 'VQT Manifold — Confronto L1 / L2 / L3   (respiro topologico)',
             color=_TEXT_C, fontsize=11, ha='center', va='top', fontweight='bold')
    fig.text(0.01, 0.985,
             f'L1: {levels_data[0]["n_nodes"] if len(levels_data)>0 else "-"} nodi  '
             f'| L2: {levels_data[1]["n_nodes"] if len(levels_data)>1 else "-"} nodi  '
             f'| L3: {levels_data[2]["n_nodes"] if len(levels_data)>2 else "-"} nodi',
             color=_TEXT_C, fontsize=7, ha='left', va='top')

    time_text = fig.text(0.99, 0.985, '', color=_ACCENT,
                         fontsize=9, ha='right', va='top',
                         fontfamily='monospace', fontweight='bold')

    update_fn = make_update(fig, axes_3d, axes_bot, cax,
                            levels_data, limits_per_level,
                            n_anim, args, time_text)

    anim_obj = animation.FuncAnimation(
        fig, update_fn,
        frames=n_anim,
        interval=max(1, 1000 // args.fps),
        blit=False
    )

    # ---- writer ----
    print(f'\n[render] {n_anim} frame  |  {args.fps} FPS  |  durata ~{n_anim/args.fps:.1f}s',
          flush=True)
    print('[render] Avvio rendering ...', flush=True)
    t_r = time.time()

    try:
        writer = animation.FFMpegWriter(
            fps=args.fps, bitrate=7000,
            extra_args=[
                '-vcodec', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '17',
                '-preset', 'medium',
                '-movflags', '+faststart'
            ]
        )
        anim_obj.save(str(out), writer=writer, dpi=args.dpi,
                      savefig_kwargs={'facecolor': _BG})
    except Exception as e:
        print(f'[warn] FFMpeg: {e}')
        gif_out = out.with_suffix('.gif')
        print(f'[warn] Salvo GIF fallback: {gif_out}')
        anim_obj.save(str(gif_out),
                      writer=animation.PillowWriter(fps=args.fps),
                      dpi=args.dpi)
        plt.close(fig)
        return 1

    plt.close(fig)
    elapsed = time.time() - t_r
    size_mb = out.stat().st_size / 1e6

    print()
    print('=' * 62)
    print(f'Output    : {out}')
    print(f'Dimensione: {size_mb:.1f} MB')
    print(f'Durata    : {n_anim/args.fps:.1f}s  |  {n_anim} frame  |  {args.fps} FPS')
    print(f'Rendering : {elapsed:.0f}s  ({elapsed/n_anim:.1f}s/frame)')
    print('=' * 62)
    return 0


if __name__ == '__main__':
    sys.exit(main())
