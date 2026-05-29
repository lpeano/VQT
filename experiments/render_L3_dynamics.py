#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_L3_dynamics.py
Animazione 3D scientifica del manifold L3 VQT — respiro topologico e solitoni.

Architettura visiva (due layer distinti):
  Layer 1 — Struttura:  solitoni (contorsione > p75_globale)
                        colore   = chi_values  [RdBu_r, TwoSlopeNorm su mediana]
                        dimensione = contorsione^1.4  (mostra tensione geometrica)
                        alpha    = 0.70

  Layer 2 — Fronte d'onda:  nodi con |velocita| > p90_globale
                             colore   = bwr (blu=in-spiraling, rosso=out-spiraling)
                             dimensione = fissa piccola
                             alpha    = 0.55  (overlay trasparente)

Pannelli laterali (serie temporali, cursore giallo):
  1. vel_rms vs t  ->  attivita d'onda (picchi = fronti in transito)
  2. cont_p75 vs t ->  respiro topologico (oscillazione ~0.42/P)
  3. chi_mean vs t ->  chiralita media (deriva lenta di fase)

Pre-compute (una volta):
  chi_activity = std temporale di chi per nodo  ->  diagnosi statico/dinamico
  Regime riportato nel titolo: CRISTALLIZZATO o ONDA PROPAGANTE

Output: L3_dynamics_3D.mp4   (~ 300 frame, 30 fps, Dpi 120)

Uso:
  cd VQT_repo
  python experiments/render_L3_dynamics.py
  python experiments/render_L3_dynamics.py --stride 1 --fps 24   # full 600 frame
  python experiments/render_L3_dynamics.py --max-frames 30       # debug
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
from matplotlib.colors import TwoSlopeNorm, Normalize
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_REPO_ROOT    = Path(__file__).resolve().parent.parent
_DEFAULT_IN   = _REPO_ROOT / 'experiments' / 'exp1' / 'cosmo_L3_ext3.h5'
_DEFAULT_OUT  = _REPO_ROOT / 'experiments' / 'exp1' / 'L3_dynamics_3D.mp4'

_BG      = '#05080d'
_GRID    = '#151e2a'
_TEXT    = '#b8cce0'
_ACCENT  = '#ffd040'
_WAVE_CM = 'bwr'   # layer 2: blue=in-spiraling, red=out-spiraling


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description='Animazione 3D L3 VQT — dinamica topologica')
    p.add_argument('--input',       default=str(_DEFAULT_IN))
    p.add_argument('--output',      default=str(_DEFAULT_OUT))
    p.add_argument('--stride',      type=int,   default=2,
                   help='Stride frame HDF5 (default 2 -> 300 frame animati)')
    p.add_argument('--fps',         type=int,   default=30)
    p.add_argument('--dpi',         type=int,   default=120)
    p.add_argument('--percentile',  type=float, default=75.0,
                   help='Soglia solitoni (percentile contorsione globale, default 75)')
    p.add_argument('--wave-pct',    type=float, default=90.0,
                   help='Soglia fronte d\'onda (percentile |velocita|, default 90)')
    p.add_argument('--rotate',      action='store_true',
                   help='Ruota la camera di 180 deg durante l\'animazione')
    p.add_argument('--max-frames',  type=int,   default=None,
                   help='Tronca a N frame (debug rapido)')
    return p.parse_args()


# -----------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------

def load_all(path: Path):
    """Carica posizioni, chi, contorsione, velocities. Float32 per efficienza."""
    print(f'[load] {path.name}', flush=True)
    t0 = time.time()

    with h5py.File(path, 'r') as f:
        fkeys = sorted(f['frames'].keys())
        n_f   = len(fkeys)
        n_n   = f['frames'][fkeys[0]]['positions'].shape[0]

        pos    = np.empty((n_f, n_n, 3), dtype=np.float32)
        chi    = np.empty((n_f, n_n),    dtype=np.float32)
        cont   = np.empty((n_f, n_n),    dtype=np.float32)
        vel    = np.empty((n_f, n_n),    dtype=np.float32)

        for i, k in enumerate(fkeys):
            fr = f['frames'][k]
            pos[i]  = fr['positions'][()]
            chi[i]  = fr['chi_values'][()]
            cont[i] = fr['contorsione_locale'][()]
            vel[i]  = fr['velocities'][()]
            if (i + 1) % 200 == 0:
                print(f'  {i+1}/{n_f} frame ...', flush=True)

        tv       = f['topological_validation']
        tv_t     = tv['time'][:]
        tv_step  = tv['step'][:]
        tv_sig   = tv['constraint_density_std'][:]
        tv_rho   = tv['mean_constraint_density'][:]
        tv_H     = tv['H_total_emergent'][:]

    elapsed = time.time() - t0
    mb = (pos.nbytes + chi.nbytes + cont.nbytes + vel.nbytes) / 1e6
    print(f'  {n_f} frame x {n_n} nodi — {mb:.0f} MB — {elapsed:.1f}s', flush=True)
    return pos, chi, cont, vel, tv_t, tv_step, tv_sig, tv_rho, tv_H


# -----------------------------------------------------------------------
# Global statistics
# -----------------------------------------------------------------------

def compute_stats(chi, cont, vel, percentile, wave_pct):
    """Calcola normalizzatori e soglie una volta sola su tutti i dati."""

    # Chi: TwoSlopeNorm centrata sulla mediana globale
    chi_flat = chi.ravel()
    chi_med  = float(np.median(chi_flat))
    chi_std  = float(chi_flat.std())
    chi_lo   = chi_med - 3.0 * chi_std
    chi_hi   = chi_med + 3.0 * chi_std

    # Contorsione: soglie per solitoni e cap display
    cont_flat    = cont.ravel()
    cont_thresh  = float(np.percentile(cont_flat, percentile))
    cont_cap     = float(np.percentile(cont_flat, 99))

    # Velocities: soglia fronte d'onda e range display
    vel_abs_flat  = np.abs(vel).ravel()
    vel_wave_thr  = float(np.percentile(vel_abs_flat, wave_pct))
    vel_cap       = float(np.percentile(vel_abs_flat, 99))
    vel_norm      = Normalize(vmin=-vel_cap, vmax=vel_cap)

    # Chi norm (TwoSlopeNorm)
    chi_norm = TwoSlopeNorm(vmin=chi_lo, vcenter=chi_med, vmax=chi_hi)

    # --- Diagnosi regime dinamico ---
    # Attivita' temporale per nodo: std di chi nel tempo
    chi_activity   = chi.std(axis=0)   # (n_nodes,)
    act_mean       = float(chi_activity.mean())
    act_p75        = float(np.percentile(chi_activity, 75))
    pos_stability  = 0.0               # gia' verificato = 0 (posizioni fisse)

    # Regime:
    # - act_mean > 2.0 e vel_rms > 10 -> onde propaganti
    # - altrimenti -> struttura condensata statica
    vel_rms_global = float(np.sqrt(np.mean(vel**2)))
    regime = 'ONDE TOPOLOGICHE PROPAGANTI' if (act_mean > 1.5 and vel_rms_global > 8.0) \
             else 'STRUTTURA CONDENSATA STATICA'

    # Serie temporali (per pannelli laterali)
    vel_rms_t   = np.sqrt(np.mean(vel**2,      axis=1))
    cont_p75_t  = np.array([float(np.percentile(cont[i], 75)) for i in range(len(cont))])
    chi_mean_t  = chi.mean(axis=1)

    print(f'\n[stats] chi: centro={chi_med:.2f}, sigma={chi_std:.2f}, vis=[{chi_lo:.1f},{chi_hi:.1f}]')
    print(f'[stats] contorsione: thresh(p{percentile:.0f})={cont_thresh:.2f} deg, cap(p99)={cont_cap:.2f} deg')
    print(f'[stats] velocita: wave_thresh(p{wave_pct:.0f})={vel_wave_thr:.2f}, cap(p99)={vel_cap:.2f}')
    print(f'[stats] attivita chi per nodo: mean={act_mean:.3f}, p75={act_p75:.3f}')
    print(f'[stats] vel_rms globale: {vel_rms_global:.2f}')
    print(f'[diag]  REGIME: {regime}')
    print(f'[diag]  Posizioni: FISSE (lattice cristallizzato, campo respira sul reticolo)\n',
          flush=True)

    return {
        'chi_norm':     chi_norm,
        'chi_med':      chi_med,
        'chi_lo':       chi_lo,
        'chi_hi':       chi_hi,
        'cont_thresh':  cont_thresh,
        'cont_cap':     cont_cap,
        'vel_wave_thr': vel_wave_thr,
        'vel_cap':      vel_cap,
        'vel_norm':     vel_norm,
        'chi_activity': chi_activity,
        'regime':       regime,
        'vel_rms_t':    vel_rms_t,
        'cont_p75_t':   cont_p75_t,
        'chi_mean_t':   chi_mean_t,
    }


# -----------------------------------------------------------------------
# Figure layout
# -----------------------------------------------------------------------

def build_figure(regime: str):
    """
    Layout:
      Col 0 (larg. 5.5): pannello 3D principale
      Col 1 (larg. 1.5): 3 pannelli serie temporali
      Col 2 (larg. 0.06): colorbars (2 affiancate sottili)
    """
    fig = plt.figure(figsize=(19, 10), facecolor=_BG)

    gs = gridspec.GridSpec(
        3, 3, figure=fig,
        width_ratios=[5.5, 1.7, 0.3],
        height_ratios=[1, 1, 1],
        hspace=0.38, wspace=0.08
    )

    ax3d  = fig.add_subplot(gs[:, 0], projection='3d')
    ax_v  = fig.add_subplot(gs[0, 1])  # vel_rms
    ax_c  = fig.add_subplot(gs[1, 1])  # cont_p75
    ax_ch = fig.add_subplot(gs[2, 1])  # chi_mean
    cb_ax = fig.add_subplot(gs[:, 2])  # colorbar chi

    _style_3d(ax3d)
    for ax in (ax_v, ax_c, ax_ch):
        _style_2d(ax)

    # Titolo principale con diagnosi regime
    fig.text(0.38, 0.975,
             f'VQT L3 — Respiro Topologico  |  {regime}',
             color=_TEXT, fontsize=10, ha='center', va='top', fontweight='bold')

    fig.text(0.38, 0.955,
             'Layer 1: solitoni (contorsione > p75)  —  colore=chi  dimensione=contorsione\n'
             'Layer 2: fronti d\'onda (|vel| > p90)  —  blu=in-spiraling  rosso=out-spiraling',
             color='#8899aa', fontsize=7, ha='center', va='top', linespacing=1.5)

    return fig, ax3d, (ax_v, ax_c, ax_ch), cb_ax


def _style_3d(ax):
    ax.set_facecolor(_BG)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_edgecolor(_GRID)
    ax.tick_params(colors=_GRID, labelsize=4)


def _style_2d(ax):
    ax.set_facecolor('#0c1520')
    for sp in ax.spines.values():
        sp.set_edgecolor(_GRID)
    ax.tick_params(colors=_TEXT, labelsize=6)


def setup_colorbars(fig, cb_ax, stats):
    """Due colorbars verticali affiancate: chi (sinistra) e velocity (destra)."""
    # Dividi l'asse colorbar in due metà verticali
    gs_cb = gridspec.GridSpecFromSubplotSpec(
        1, 2, subplot_spec=cb_ax.get_subplotspec(),
        wspace=0.05
    )
    fig.delaxes(cb_ax)
    cax_chi = fig.add_subplot(gs_cb[0, 0])
    cax_vel = fig.add_subplot(gs_cb[0, 1])

    # Colorbar chi
    sm_chi = plt.cm.ScalarMappable(cmap='RdBu_r', norm=stats['chi_norm'])
    sm_chi.set_array([])
    cb_chi = fig.colorbar(sm_chi, cax=cax_chi)
    cb_chi.set_label('chi', color=_TEXT, fontsize=6, labelpad=3)
    cb_chi.ax.tick_params(colors=_TEXT, labelsize=5)
    # Marcatore mediana
    med_frac = (stats['chi_med'] - stats['chi_lo']) / (stats['chi_hi'] - stats['chi_lo'])
    cb_chi.ax.axhline(med_frac, color=_TEXT, lw=0.7, ls='--', alpha=0.6)

    # Colorbar velocity
    sm_vel = plt.cm.ScalarMappable(cmap=_WAVE_CM, norm=stats['vel_norm'])
    sm_vel.set_array([])
    cb_vel = fig.colorbar(sm_vel, cax=cax_vel)
    cb_vel.set_label('vel', color='#aabbcc', fontsize=6, labelpad=3)
    cb_vel.ax.tick_params(colors='#aabbcc', labelsize=5)
    cb_vel.ax.axhline(0.5, color='#aabbcc', lw=0.5, ls='--', alpha=0.5)


# -----------------------------------------------------------------------
# Axis limits (fissi per tutta l'animazione)
# -----------------------------------------------------------------------

def axis_limits(pos):
    """Limiti fissi calcolati sulle posizioni (che non cambiano nel tempo)."""
    m = 1.5
    p = pos[0]   # basta il primo frame — le posizioni sono identiche
    return (
        (float(p[:,0].min())-m, float(p[:,0].max())+m),
        (float(p[:,1].min())-m, float(p[:,1].max())+m),
        (float(p[:,2].min())-m, float(p[:,2].max())+m),
    )


# -----------------------------------------------------------------------
# Render loop
# -----------------------------------------------------------------------

def make_update(fig, ax3d, side_axes, pos, chi, cont, vel,
                tv_t, tv_step, tv_sig, tv_rho, tv_H,
                stats, xlim, ylim, zlim,
                frame_indices, n_anim, args):

    ax_v, ax_c, ax_ch = side_axes

    # Timestamp overlay (in alto a sinistra del 3D)
    ts = fig.text(0.01, 0.975, '', color=_ACCENT, fontsize=11,
                  ha='left', va='top', fontfamily='monospace', fontweight='bold')

    # Regime label (in basso a sinistra del 3D)
    regime_lbl = fig.text(0.01, 0.03, '', color='#88bbdd', fontsize=8,
                          ha='left', va='bottom', fontfamily='monospace')

    _state = {'n': 0, 't0': time.time()}

    def update(anim_i):
        raw_i = frame_indices[anim_i]
        i = min(raw_i, len(pos) - 1)

        t_sim   = float(tv_t[i])   if i < len(tv_t)   else i * 0.01
        step_n  = int(tv_step[i])  if i < len(tv_step) else i + 1
        sig_cur = float(tv_sig[i]) if i < len(tv_sig)  else 0.0
        H_cur   = float(tv_H[i])   if i < len(tv_H)    else 0.0

        # ================================================================
        # LAYER 1 — SOLITONI (struttura topologica)
        # ================================================================
        mask_sol = cont[i] >= stats['cont_thresh']
        if mask_sol.sum() < 10:
            mask_sol[:] = True

        pos_s  = pos[i][mask_sol]
        chi_s  = chi[i][mask_sol]
        cont_s = cont[i][mask_sol]

        c_chi  = stats['chi_norm'](chi_s)            # -> [0,1] per colormap
        sz_sol = 8.0 + 110.0 * np.clip(cont_s / stats['cont_cap'], 0, 1) ** 1.4

        # ================================================================
        # LAYER 2 — FRONTE D'ONDA (attivita' dinamica)
        # ================================================================
        vel_abs_i = np.abs(vel[i])
        mask_wave = vel_abs_i >= stats['vel_wave_thr']
        if mask_wave.sum() < 5:
            mask_wave = np.zeros(len(vel[i]), dtype=bool)

        pos_w  = pos[i][mask_wave]
        vel_w  = vel[i][mask_wave]
        c_vel  = stats['vel_norm'](vel_w)             # centrato su 0
        sz_wav = 12.0                                  # dimensione fissa piccola

        # ================================================================
        # PANNELLO 3D
        # ================================================================
        ax3d.cla()
        _style_3d(ax3d)

        # Layer 1 — struttura
        ax3d.scatter(pos_s[:,0], pos_s[:,1], pos_s[:,2],
                     c=c_chi, cmap='RdBu_r', s=sz_sol,
                     alpha=0.68, edgecolors='none', vmin=0, vmax=1,
                     depthshade=True, zorder=3)

        # Layer 2 — fronte d'onda
        if mask_wave.sum() > 0:
            ax3d.scatter(pos_w[:,0], pos_w[:,1], pos_w[:,2],
                         c=c_vel, cmap=_WAVE_CM, s=sz_wav,
                         alpha=0.52, edgecolors='none', vmin=0, vmax=1,
                         depthshade=False, zorder=5)

        ax3d.set_xlim(xlim); ax3d.set_ylim(ylim); ax3d.set_zlim(zlim)
        ax3d.set_xlabel('X', color=_GRID, fontsize=5, labelpad=-2)
        ax3d.set_ylabel('Y', color=_GRID, fontsize=5, labelpad=-2)
        ax3d.set_zlabel('Z', color=_GRID, fontsize=5, labelpad=-2)

        if args.rotate:
            azim = 25.0 + 180.0 * (anim_i / max(n_anim - 1, 1))
        else:
            azim = 30.0
        ax3d.view_init(elev=20, azim=azim)

        # Annotazione dati nel pannello 3D
        n_wave = int(mask_wave.sum())
        ax3d.set_title(
            f'Solitoni: {mask_sol.sum():,}  |  Fronti onda: {n_wave:,}\n'
            f'chi_med={chi_s.mean():.2f}   cont_mean={cont_s.mean():.1f} deg   '
            f'sig(rho)={sig_cur:.4f}   H={H_cur:.3e}',
            color=_TEXT, fontsize=8, pad=10
        )

        # ================================================================
        # PANNELLO 1 — vel_rms (attivita' dinamica)
        # ================================================================
        ax_v.cla()
        _style_2d(ax_v)
        t_ax = np.arange(len(stats['vel_rms_t'])) * 0.01
        ax_v.plot(t_ax, stats['vel_rms_t'], color='#6699ff', lw=0.85, alpha=0.5)
        ax_v.axvline(t_sim, color=_ACCENT, lw=1.0, alpha=0.85, zorder=4)
        ax_v.scatter([t_sim], [stats['vel_rms_t'][i]], color=_ACCENT, s=22, zorder=5)
        # Banda di riferimento (1 sigma attorno alla media)
        vrmean = stats['vel_rms_t'].mean()
        vrstd  = stats['vel_rms_t'].std()
        ax_v.axhline(vrmean,          color='#44aaff', lw=0.5, ls=':', alpha=0.4)
        ax_v.axhspan(vrmean-vrstd, vrmean+vrstd, color='#44aaff', alpha=0.07)
        ax_v.set_title('Attivita onda: vel_rms', color=_TEXT, fontsize=7)
        ax_v.set_xlabel('t [P]', color=_TEXT, fontsize=6)
        ax_v.set_ylabel('|v| rms', color=_TEXT, fontsize=6)
        ax_v.set_xlim(0, t_ax[-1])
        ax_v.tick_params(colors=_TEXT, labelsize=5)
        for sp in ax_v.spines.values(): sp.set_edgecolor(_GRID)

        # ================================================================
        # PANNELLO 2 — cont_p75 (respiro topologico)
        # ================================================================
        ax_c.cla()
        _style_2d(ax_c)
        ax_c.plot(t_ax, stats['cont_p75_t'], color='#ff8844', lw=0.85, alpha=0.5)
        ax_c.axvline(t_sim, color=_ACCENT, lw=1.0, alpha=0.85, zorder=4)
        ax_c.scatter([t_sim], [stats['cont_p75_t'][i]], color=_ACCENT, s=22, zorder=5)
        ax_c.set_title('Respiro: cont p75 vs t', color=_TEXT, fontsize=7)
        ax_c.set_xlabel('t [P]', color=_TEXT, fontsize=6)
        ax_c.set_ylabel('Omega p75 [deg]', color=_TEXT, fontsize=6)
        ax_c.set_xlim(0, t_ax[-1])
        ax_c.tick_params(colors=_TEXT, labelsize=5)
        for sp in ax_c.spines.values(): sp.set_edgecolor(_GRID)

        # ================================================================
        # PANNELLO 3 — chi_mean (deriva di fase)
        # ================================================================
        ax_ch.cla()
        _style_2d(ax_ch)
        ax_ch.plot(t_ax, stats['chi_mean_t'], color='#88ddbb', lw=0.85, alpha=0.5)
        ax_ch.axvline(t_sim, color=_ACCENT, lw=1.0, alpha=0.85, zorder=4)
        ax_ch.scatter([t_sim], [stats['chi_mean_t'][i]], color=_ACCENT, s=22, zorder=5)
        ax_ch.axhline(stats['chi_med'], color='#88ddbb', lw=0.5, ls='--', alpha=0.4)
        ax_ch.set_title('Chiralita media vs t', color=_TEXT, fontsize=7)
        ax_ch.set_xlabel('t [P]', color=_TEXT, fontsize=6)
        ax_ch.set_ylabel('<chi>', color=_TEXT, fontsize=6)
        ax_ch.set_xlim(0, t_ax[-1])
        ax_ch.tick_params(colors=_TEXT, labelsize=5)
        for sp in ax_ch.spines.values(): sp.set_edgecolor(_GRID)

        # ================================================================
        # OVERLAY TESTO
        # ================================================================
        ts.set_text(
            f'  t = {t_sim:5.2f} P    step {step_n:4d}    '
            f'frame {anim_i+1}/{n_anim}'
        )

        vr_cur = stats['vel_rms_t'][i]
        vr_ref = stats['vel_rms_t'].mean()
        activity_label = ('FRONTE ATTIVO' if vr_cur > vr_ref * 1.1
                          else 'QUIETE RELATIVA' if vr_cur < vr_ref * 0.9
                          else 'REGIME MEDIO')
        regime_lbl.set_text(f'  {activity_label}  |  vel_rms={vr_cur:.1f}')

        # Progress
        _state['n'] += 1
        c = _state['n']
        if c % 30 == 0 or c == n_anim:
            el  = time.time() - _state['t0']
            eta = el / c * (n_anim - c) if c < n_anim else 0
            print(f'  [{c:3d}/{n_anim}]  {el:.0f}s  ETA {eta:.0f}s', flush=True)

        return []

    return update


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    args = parse_args()
    inp  = Path(args.input)
    out  = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    # ---- carica dati ----
    pos, chi, cont, vel, tv_t, tv_step, tv_sig, tv_rho, tv_H = load_all(inp)

    # ---- statistiche globali ----
    stats = compute_stats(chi, cont, vel, args.percentile, args.wave_pct)

    # ---- frame indices ----
    frame_indices = list(range(0, len(pos), args.stride))
    if args.max_frames:
        frame_indices = frame_indices[:args.max_frames]
    n_anim   = len(frame_indices)
    duration = n_anim / args.fps
    print(f'[anim] {n_anim} frame  |  {args.fps} FPS  |  ~{duration:.1f}s di video', flush=True)

    # ---- limiti assi fissi ----
    xlim, ylim, zlim = axis_limits(pos)

    # ---- figura ----
    fig, ax3d, side_axes, cb_ax = build_figure(stats['regime'])
    setup_colorbars(fig, cb_ax, stats)

    update_fn = make_update(
        fig, ax3d, side_axes,
        pos, chi, cont, vel,
        tv_t, tv_step, tv_sig, tv_rho, tv_H,
        stats, xlim, ylim, zlim,
        frame_indices, n_anim, args
    )

    anim_obj = animation.FuncAnimation(
        fig, update_fn, frames=n_anim,
        interval=max(1, 1000 // args.fps),
        blit=False
    )

    # ---- rendering ----
    print(f'\n[render] Avvio ...', flush=True)
    t_r = time.time()

    try:
        writer = animation.FFMpegWriter(
            fps=args.fps, bitrate=6000,
            extra_args=[
                '-vcodec', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '17',
                '-preset', 'medium',
                '-movflags', '+faststart',
            ]
        )
        anim_obj.save(
            str(out), writer=writer, dpi=args.dpi,
            savefig_kwargs={'facecolor': _BG}
        )
    except Exception as e:
        print(f'[warn] FFMpeg fallito: {e}', flush=True)
        gif = out.with_suffix('.gif')
        anim_obj.save(str(gif), writer=animation.PillowWriter(fps=args.fps), dpi=args.dpi)
        print(f'[info] GIF fallback: {gif}', flush=True)
        plt.close(fig)
        return 1

    plt.close(fig)
    elapsed = time.time() - t_r
    mb = out.stat().st_size / 1e6

    print()
    print('=' * 64)
    print(f'Output    : {out}')
    print(f'Dimensione: {mb:.1f} MB')
    print(f'Durata    : {duration:.1f}s  |  {n_anim} frame  |  {args.fps} fps')
    print(f'Rendering : {elapsed:.0f}s  ({elapsed/n_anim:.1f}s/frame)')
    print(f'Regime    : {stats["regime"]}')
    print('=' * 64)
    return 0


if __name__ == '__main__':
    sys.exit(main())
