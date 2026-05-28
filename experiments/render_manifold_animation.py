#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_manifold_animation.py
Animazione MP4 3D del manifold L3 VQT — visualizzazione del 'respiro topologico'.

Layout: pannello 3D principale + distribuzione chi + tracker temporale Omega.
Filtro solitonico: solo nodi con contorsione_locale >= percentile 75.
Chiralità: RdBu_r centrato sulla mediana globale di chi_values.

Uso rapido:
  python experiments/render_manifold_animation.py
Opzioni:
  --input   FILE.h5     (default: experiments/exp1/cosmo_L3_ext3.h5)
  --output  OUT.mp4     (default: experiments/exp1/manifold_animation.mp4)
  --step    N           stride tra frame HDF5 (default: 3 → 200 frame animati)
  --fps     N           frame/s del video (default: 24)
  --dpi     N           risoluzione (default: 120)
  --rotate              ruota camera 180° durante l'animazione
  --max-frames N        tronca per debug rapido
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import h5py

import sys
# Forza UTF-8 su stdout Windows per caratteri non-ASCII nei print
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_INPUT = _REPO_ROOT / 'experiments' / 'exp1' / 'cosmo_L3_ext3.h5'
_DEFAULT_OUTPUT = _REPO_ROOT / 'experiments' / 'exp1' / 'manifold_animation.mp4'

_BG = '#080c10'
_GRID_COLOR = '#1a2030'
_TEXT_COLOR = '#c8d8e8'
_ACCENT = '#ffcc44'


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description='Animazione 3D manifold VQT L3')
    p.add_argument('--input',      default=str(_DEFAULT_INPUT))
    p.add_argument('--output',     default=str(_DEFAULT_OUTPUT))
    p.add_argument('--step',       type=int,   default=3,
                   help='Frame stride HDF5 (default 3 → 200 frame)')
    p.add_argument('--fps',        type=int,   default=24)
    p.add_argument('--dpi',        type=int,   default=120)
    p.add_argument('--percentile', type=float, default=75.0,
                   help='Soglia contorsione solitonica (default 75)')
    p.add_argument('--rotate',     action='store_true',
                   help='Ruota la camera di 180° durante l\'animazione')
    p.add_argument('--max-frames', type=int,   default=None,
                   help='Tronca animazione a N frame (debug)')
    p.add_argument('--no-dark',    action='store_true',
                   help='Usa sfondo bianco invece di scuro')
    return p.parse_args()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_hdf5(path: Path):
    """
    Legge tutti i frame da /frames/ e la serie temporale da /topological_validation/.
    Ritorna array pre-allocati float32 per minimizzare la memoria.
    """
    print(f'[load] Apertura {path.name} ...', flush=True)
    t0 = time.time()

    with h5py.File(path, 'r') as f:
        frame_keys = sorted(f['frames'].keys())
        n_frames = len(frame_keys)
        fr0 = f['frames'][frame_keys[0]]
        n_nodes = fr0['positions'].shape[0]

        positions    = np.empty((n_frames, n_nodes, 3), dtype=np.float32)
        chi_arr      = np.empty((n_frames, n_nodes),    dtype=np.float32)
        contors_arr  = np.empty((n_frames, n_nodes),    dtype=np.float32)

        for idx, key in enumerate(frame_keys):
            fr = f['frames'][key]
            positions[idx]   = fr['positions'][()]
            chi_arr[idx]     = fr['chi_values'][()]
            contors_arr[idx] = fr['contorsione_locale'][()]
            if (idx + 1) % 150 == 0:
                print(f'  {idx+1}/{n_frames} frame ...', flush=True)

        tv = f['topological_validation']
        tv_steps = tv['step'][:]
        tv_times = tv['time'][:]

    elapsed = time.time() - t0
    mem_mb = (positions.nbytes + chi_arr.nbytes + contors_arr.nbytes) / 1e6
    print(f'[load] {n_frames} frame × {n_nodes} nodi — {mem_mb:.0f} MB — {elapsed:.1f}s')
    return positions, chi_arr, contors_arr, tv_steps, tv_times


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def global_stats(chi_arr, contors_arr, percentile):
    """Calcola normalizzatori validi per tutti i frame."""
    # Chi: centrata alla mediana globale, range ±3σ (chiralità relativa)
    chi_flat = chi_arr.ravel()
    chi_center = float(np.median(chi_flat))
    chi_sigma  = float(chi_flat.std())
    chi_lo = chi_center - 3.0 * chi_sigma
    chi_hi = chi_center + 3.0 * chi_sigma

    # Contorsione: soglia filtro e cap display
    cont_flat        = contors_arr.ravel()
    cont_threshold   = float(np.percentile(cont_flat, percentile))
    cont_cap         = float(np.percentile(cont_flat, 99))   # cap dim. punti

    # Serie temporale: media della contorsione solitonica per frame
    mask_global = contors_arr >= cont_threshold
    mean_omega  = np.where(
        mask_global.any(axis=1),
        np.where(mask_global, contors_arr, 0.0).sum(axis=1) / mask_global.sum(axis=1).clip(1),
        0.0
    )

    print(f'[stats] chi: centro={chi_center:.2f}, sigma={chi_sigma:.2f}, '
          f'vis=[{chi_lo:.1f}, {chi_hi:.1f}]')
    print(f'[stats] contorsione: soglia(p{percentile:.0f})={cont_threshold:.2f} deg, '
          f'cap(p99)={cont_cap:.2f} deg')
    print(f'[stats] N solitoni/frame: {mask_global.sum(axis=1).mean():.0f} (media)')

    return chi_center, chi_lo, chi_hi, cont_threshold, cont_cap, mean_omega


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def make_figure(dark: bool, figsize=(18, 9)):
    bg = _BG if dark else 'white'
    txt = _TEXT_COLOR if dark else '#222222'
    grid = _GRID_COLOR if dark else '#cccccc'

    fig = plt.figure(figsize=figsize, facecolor=bg)
    gs = gridspec.GridSpec(
        3, 3, figure=fig,
        width_ratios=[3.2, 1, 0.08],
        height_ratios=[1, 1, 1],
        hspace=0.45, wspace=0.18
    )

    ax3d  = fig.add_subplot(gs[:, 0], projection='3d')
    ax_chi   = fig.add_subplot(gs[0, 1])
    ax_omega = fig.add_subplot(gs[1, 1])
    ax_hist  = fig.add_subplot(gs[2, 1])
    cax   = fig.add_subplot(gs[:, 2])

    for ax in (ax_chi, ax_omega, ax_hist):
        ax.set_facecolor(_GRID_COLOR if dark else '#f0f0f0')
        for spine in ax.spines.values():
            spine.set_edgecolor(grid)
        ax.tick_params(colors=txt, labelsize=6)
        ax.xaxis.label.set_color(txt)
        ax.yaxis.label.set_color(txt)
        ax.title.set_color(txt)

    ax3d.set_facecolor(bg)
    ax3d.xaxis.pane.fill = False
    ax3d.yaxis.pane.fill = False
    ax3d.zaxis.pane.fill = False
    ax3d.xaxis.pane.set_edgecolor(grid)
    ax3d.yaxis.pane.set_edgecolor(grid)
    ax3d.zaxis.pane.set_edgecolor(grid)
    ax3d.tick_params(colors=txt, labelsize=5)

    return fig, ax3d, ax_chi, ax_omega, ax_hist, cax, txt, bg


def setup_colorbar(fig, cax, chi_lo, chi_hi, chi_center, dark):
    txt = _TEXT_COLOR if dark else '#222222'
    norm = Normalize(vmin=chi_lo, vmax=chi_hi)
    sm = plt.cm.ScalarMappable(cmap='RdBu_r', norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax, orientation='vertical')
    cb.set_label('χ — chiralità locale', color=txt, fontsize=7, labelpad=4)
    cb.ax.tick_params(colors=txt, labelsize=6)
    cb.ax.yaxis.set_tick_params(which='both', color=txt)

    # Annota il valore neutro
    neutral_pos = (chi_center - chi_lo) / (chi_hi - chi_lo)
    cb.ax.axhline(neutral_pos, color=txt, lw=0.8, ls='--', alpha=0.6)
    cb.ax.text(1.6, neutral_pos, f'med\n{chi_center:.1f}',
               transform=cb.ax.transAxes, color=txt, fontsize=5,
               va='center', ha='left')
    return norm


def render_animation(positions, chi_arr, contors_arr, tv_steps, tv_times,
                     chi_center, chi_lo, chi_hi,
                     cont_threshold, cont_cap, mean_omega,
                     frame_indices, args):

    dark = not args.no_dark
    txt  = _TEXT_COLOR if dark else '#222222'
    bg   = _BG if dark else 'white'
    n_anim = len(frame_indices)
    fps = args.fps

    # Axis limits fissi (critici per mostrare il respiro)
    pos_flat = positions.reshape(-1, 3)
    margin = 1.0
    xlim = (float(pos_flat[:, 0].min()) - margin, float(pos_flat[:, 0].max()) + margin)
    ylim = (float(pos_flat[:, 1].min()) - margin, float(pos_flat[:, 1].max()) + margin)
    zlim = (float(pos_flat[:, 2].min()) - margin, float(pos_flat[:, 2].max()) + margin)
    del pos_flat

    chi_norm = Normalize(vmin=chi_lo, vmax=chi_hi)

    fig, ax3d, ax_chi, ax_omega, ax_hist, cax, txt_c, bg_c = make_figure(dark)
    fig.patch.set_facecolor(bg)
    norm_cb = setup_colorbar(fig, cax, chi_lo, chi_hi, chi_center, dark)

    # Timestamp video (ore fisiche in alto a sinistra)
    time_text = fig.text(0.01, 0.97, '', color=_ACCENT, fontsize=10,
                         fontweight='bold', va='top', ha='left',
                         fontfamily='monospace')

    # Serie temporale omega completa (pre-calcolata)
    t_axis = np.arange(len(mean_omega)) * 0.01  # dt = 0.01 P

    _state = {'frame_count': 0, 't_render_start': time.time()}

    def update(anim_idx):
        i = frame_indices[anim_idx]
        t_sim  = float(tv_times[i]) if i < len(tv_times) else i * 0.01
        step_n = int(tv_steps[i])   if i < len(tv_steps) else i + 1

        # ---- MASCHERA SOLITONICA ----
        mask = contors_arr[i] >= cont_threshold
        if mask.sum() < 20:
            mask = np.ones(len(contors_arr[i]), dtype=bool)

        pos_f  = positions[i][mask]
        chi_f  = chi_arr[i][mask]
        cont_f = contors_arr[i][mask]
        n_sol  = int(mask.sum())

        # ---- COLORI & DIMENSIONI ----
        c_vals = chi_norm(chi_f)
        sizes  = 8.0 + 120.0 * np.clip(cont_f / cont_cap, 0.0, 1.0) ** 1.4

        # ======================================================
        # PANNELLO 1 — scatter 3D
        # ======================================================
        ax3d.cla()
        ax3d.set_facecolor(bg)
        ax3d.xaxis.pane.fill = False
        ax3d.yaxis.pane.fill = False
        ax3d.zaxis.pane.fill = False
        ax3d.xaxis.pane.set_edgecolor(_GRID_COLOR)
        ax3d.yaxis.pane.set_edgecolor(_GRID_COLOR)
        ax3d.zaxis.pane.set_edgecolor(_GRID_COLOR)
        ax3d.tick_params(colors=txt_c, labelsize=5)

        ax3d.scatter(
            pos_f[:, 0], pos_f[:, 1], pos_f[:, 2],
            c=c_vals, cmap='RdBu_r',
            s=sizes, alpha=0.72,
            edgecolors='none',
            vmin=0.0, vmax=1.0,
            zorder=3
        )

        ax3d.set_xlim(xlim); ax3d.set_ylim(ylim); ax3d.set_zlim(zlim)
        ax3d.set_xlabel('X', color=txt_c, fontsize=6, labelpad=0)
        ax3d.set_ylabel('Y', color=txt_c, fontsize=6, labelpad=0)
        ax3d.set_zlabel('Z', color=txt_c, fontsize=6, labelpad=0)

        # Camera rotation: da 20° a 200° azimuth durante tutta l'animazione
        if args.rotate:
            azim = 20.0 + 180.0 * (anim_idx / max(n_anim - 1, 1))
        else:
            azim = 30.0
        ax3d.view_init(elev=22, azim=azim)

        # Titolo 3D
        mean_chi = float(chi_f.mean())
        mean_om  = float(cont_f.mean())
        ax3d.set_title(
            f'Manifold L3  ·  Step {step_n:4d}  ·  t = {t_sim:.2f} P\n'
            f'Solitoni: {n_sol:,} nodi  ·  ⟨χ⟩ = {mean_chi:.2f}'
            f'  ·  ⟨Ω⟩ = {mean_om:.1f}°',
            color=txt_c, fontsize=9, pad=10
        )

        # ======================================================
        # PANNELLO 2 — distribuzione chi (frame corrente)
        # ======================================================
        ax_chi.cla()
        ax_chi.set_facecolor(_GRID_COLOR if dark else '#f0f4f8')
        hist_colors = chi_norm(chi_f)
        counts, bin_edges, patches = ax_chi.hist(
            chi_f, bins=40, color='#55aaff', alpha=0.85, density=True
        )
        # Colora ogni bin secondo la colormap
        for patch, color_val in zip(patches,
                                     (0.5*(bin_edges[:-1]+bin_edges[1:]))):
            patch.set_facecolor(plt.cm.RdBu_r(chi_norm(color_val)))
            patch.set_alpha(0.85)
        ax_chi.axvline(chi_center, color=_ACCENT, lw=1.0, ls='--', alpha=0.8)
        ax_chi.axvline(mean_chi,   color='white', lw=0.7, ls=':',  alpha=0.6)
        ax_chi.set_xlim(chi_lo, chi_hi)
        ax_chi.set_title('Distrib. χ  [solitoni]', color=txt_c, fontsize=8)
        ax_chi.set_xlabel('χ', color=txt_c, fontsize=7)
        ax_chi.tick_params(colors=txt_c, labelsize=6)
        for sp in ax_chi.spines.values():
            sp.set_edgecolor(_GRID_COLOR)

        # ======================================================
        # PANNELLO 3 — time series omega con cursore
        # ======================================================
        ax_omega.cla()
        ax_omega.set_facecolor(_GRID_COLOR if dark else '#f0f4f8')
        ax_omega.plot(t_axis, mean_omega, color='#4499dd', lw=0.9, alpha=0.6)
        ax_omega.axvline(t_sim, color=_ACCENT, lw=1.2, alpha=0.9, zorder=5)
        ax_omega.scatter([t_sim], [mean_omega[i]], color=_ACCENT, s=25, zorder=6)
        ax_omega.set_title('⟨Ω⟩ solitoni — t [P]', color=txt_c, fontsize=8)
        ax_omega.set_xlabel('t [P]', color=txt_c, fontsize=7)
        ax_omega.set_ylabel('Ω medio [°]', color=txt_c, fontsize=6)
        ax_omega.tick_params(colors=txt_c, labelsize=6)
        ax_omega.set_xlim(t_axis[0], t_axis[-1])
        for sp in ax_omega.spines.values():
            sp.set_edgecolor(_GRID_COLOR)

        # ======================================================
        # PANNELLO 4 — istogramma contorsione (filtrati)
        # ======================================================
        ax_hist.cla()
        ax_hist.set_facecolor(_GRID_COLOR if dark else '#f0f4f8')
        ax_hist.hist(cont_f, bins=30, color='#ff7744', alpha=0.8, density=True)
        ax_hist.axvline(float(cont_f.mean()), color='white', lw=0.8, ls='--', alpha=0.7)
        ax_hist.set_title('Distrib. Ω  [solitoni]', color=txt_c, fontsize=8)
        ax_hist.set_xlabel('Ω [°]', color=txt_c, fontsize=7)
        ax_hist.set_xlim(0, cont_cap * 1.05)
        ax_hist.tick_params(colors=txt_c, labelsize=6)
        for sp in ax_hist.spines.values():
            sp.set_edgecolor(_GRID_COLOR)

        # ======================================================
        # Timestamp in overlay
        # ======================================================
        time_text.set_text(
            f't = {t_sim:5.2f} P   step {step_n:4d}/{int(tv_steps[-1])}   '
            f'frame {anim_idx+1:3d}/{n_anim}'
        )

        # Progress console
        _state['frame_count'] += 1
        fc = _state['frame_count']
        if fc % 25 == 0 or fc == n_anim:
            elapsed = time.time() - _state['t_render_start']
            eta = elapsed / fc * (n_anim - fc) if fc < n_anim else 0.0
            print(f'  [{fc:3d}/{n_anim}]  {elapsed:.0f}s elapsed  ETA {eta:.0f}s',
                  flush=True)

        return []

    anim = animation.FuncAnimation(
        fig, update,
        frames=n_anim,
        interval=max(1, 1000 // fps),
        blit=False
    )

    return fig, anim


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- load ----
    positions, chi_arr, contors_arr, tv_steps, tv_times = load_hdf5(input_path)

    # ---- stats ----
    chi_center, chi_lo, chi_hi, cont_threshold, cont_cap, mean_omega = global_stats(
        chi_arr, contors_arr, args.percentile
    )

    # ---- frame indices ----
    all_indices = list(range(len(positions)))
    frame_indices = all_indices[::args.step]
    if args.max_frames:
        frame_indices = frame_indices[:args.max_frames]
    n_anim = len(frame_indices)
    duration_s = n_anim / args.fps
    print(f'[anim] {n_anim} frame animati  |  {args.fps} FPS  |  durata ~{duration_s:.1f}s')

    # ---- render ----
    print('[render] Inizio rendering ...')
    t_render = time.time()
    fig, anim = render_animation(
        positions, chi_arr, contors_arr, tv_steps, tv_times,
        chi_center, chi_lo, chi_hi,
        cont_threshold, cont_cap, mean_omega,
        frame_indices, args
    )

    # ---- writer ----
    try:
        writer = animation.FFMpegWriter(
            fps=args.fps,
            bitrate=5000,
            extra_args=[
                '-vcodec', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '18',
                '-preset', 'medium',
                '-movflags', '+faststart'
            ]
        )
        anim.save(
            str(output_path), writer=writer,
            dpi=args.dpi,
            savefig_kwargs={'facecolor': _BG if not args.no_dark else 'white'}
        )
    except Exception as e_ffmpeg:
        print(f'[warn] FFMpeg fallito: {e_ffmpeg}')
        print('[warn] Tentativo con Pillow (gif fallback) ...')
        gif_path = output_path.with_suffix('.gif')
        writer_gif = animation.PillowWriter(fps=args.fps)
        anim.save(str(gif_path), writer=writer_gif, dpi=args.dpi)
        print(f'[info] GIF salvata: {gif_path}')
        plt.close(fig)
        return 1

    plt.close(fig)
    elapsed = time.time() - t_render
    size_mb = output_path.stat().st_size / 1e6

    print()
    print('=' * 60)
    print(f'Output:    {output_path}')
    print(f'Dimensione: {size_mb:.1f} MB')
    print(f'Durata:     {duration_s:.1f}s  |  {n_anim} frame  |  {args.fps} FPS')
    print(f'Rendering:  {elapsed:.0f}s  ({elapsed/n_anim:.1f}s/frame)')
    print('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
