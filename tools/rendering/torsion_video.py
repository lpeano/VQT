#!/usr/bin/env python3
"""
torsion_video.py — Video MP4 della torsione chirale del manifold VQT.

Layout per frame:
  [sinistra] 3D scatter colorato per ρ_i + frecce grandi della torsione K·t
  [destra]   Streamplot 2D della proiezione XY del campo K·t (evolve nel tempo)
  [basso]    Strip HUD: σ_VM(t) e ρ̄(t) con cursore

Uso:
    python -X utf8 torsion_video.py cosmo_L2_variational.h5
    python -X utf8 torsion_video.py cosmo_L2_variational.h5 --fps 12 --step 1
"""

import argparse, sys
from pathlib import Path

import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib import colors as mcolors
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401
from scipy.interpolate import RBFInterpolator


# ── Fisica ────────────────────────────────────────────────────────────────────
RHO_0, LAMBDA, GAMMA = 0.85, 0.2, 0.05

def compute_rho_i(tau, K):
    tau_range = float(np.max(tau) - np.min(tau))
    f_cl = (np.ones(len(tau)) if tau_range < 1e-12
            else 1.0 - np.abs(tau - np.mean(tau)) / tau_range)
    K2 = K ** 2
    K2_bar = max(float(np.mean(K2)), 1e-12)
    Omega = K2 * np.roll(K2, -1)
    return np.clip(0.5 * f_cl + 0.5 / (1.0 + Omega / K2_bar), 0.0, 1.0)

def sigma_vm(vel, K, rho):
    K2 = K**2; K2b = max(float(np.mean(K2)), 1e-12)
    Om = K2 * np.roll(K2, -1)
    Ttt = 0.5*vel**2 + LAMBDA*(rho-RHO_0)**2 + GAMMA*Om
    Txx = 0.5*K2    + GAMMA*Om
    return np.abs(Txx - Ttt)

def torsion_vectors3d(pos, K):
    """Vettore torsione 3D: K_i × tangente locale (normalizzata)."""
    t = np.empty_like(pos)
    t[1:-1] = pos[2:] - pos[:-2]
    t[0]    = pos[1]  - pos[0]
    t[-1]   = pos[-1] - pos[-2]
    n = np.linalg.norm(t, axis=1, keepdims=True)
    t /= np.where(n < 1e-12, 1.0, n)
    return t * K[:, None]          # shape (N,3): magn=|K|, dir=tangente

def streamfield2d(pos, K, tang3d, grid=60):
    """Campo K·t proiettato XY → griglia per streamplot."""
    lo, hi = pos[:, :2].min(0), pos[:, :2].max(0)
    x1 = np.linspace(lo[0], hi[0], grid)
    y1 = np.linspace(lo[1], hi[1], grid)
    Xg, Yg = np.meshgrid(x1, y1, indexing='xy')
    flat   = np.column_stack([Xg.ravel(), Yg.ravel()])
    pts2d  = pos[:, :2]
    uvec   = tang3d[:, :2] * K[:, None]           # torsion vector in XY
    rbf_u  = RBFInterpolator(pts2d, uvec[:,0], kernel='linear', smoothing=8.0)
    rbf_v  = RBFInterpolator(pts2d, uvec[:,1], kernel='linear', smoothing=8.0)
    U = rbf_u(flat).reshape(grid, grid)
    V = rbf_v(flat).reshape(grid, grid)
    return x1, y1, U, V


# ── Caricamento dati ──────────────────────────────────────────────────────────
def load_hdf5(path):
    with h5py.File(path, 'r') as f:
        fkeys = sorted(f['frames'].keys(), key=lambda x: int(x.split('_')[1]))
        frames = []
        for fk in fkeys:
            g = f['frames'][fk]
            frames.append({'pos': g['positions'][:].astype(float),
                           'K':   g['contorsione_locale'][:].astype(float),
                           'tau': g['tau_locale'][:].astype(float),
                           'vel': g['velocities'][:].astype(float)})
        tv = f['topological_validation']
        topo = {'time':  tv['time'][:].astype(float),
                'rho':   tv['mean_constraint_density'][:].astype(float),
                'phase': [p.decode() if isinstance(p,bytes) else p
                          for p in tv['phase_label'][:]]}
        S = None
        if 'variational_force' in f:
            Sr = f['variational_force']['potential_S'][:].astype(float)
            n  = len(topo['time'])
            S  = Sr[1::2][:n] if len(Sr) >= 2*n else Sr[:n]
    sv = max(1, len(topo['time']) // len(frames))
    return frames, topo, S, sv


# ── Main ──────────────────────────────────────────────────────────────────────
def make_video(hdf5_path, output=None, fps=10, step=2,
               quiver_n=120, grid=60, dpi=110,
               elev=28.0, azim_start=40.0, azim_delta=2.0):

    path   = Path(hdf5_path)
    output = output or f'{path.stem}_torsion.mp4'
    frames, topo, S, sv = load_hdf5(path)

    frame_idxs = list(range(0, len(frames), max(1, step)))
    N          = frames[0]['pos'].shape[0]

    # Pre-calcola ρ e σ_VM per tutti i frame selezionati (per il raster HUD)
    print("Pre-calcolo ρ e σ_VM per tutti i frame...")
    rho_series  = []
    sigvm_series= []
    for fi in frame_idxs:
        fr   = frames[fi]
        rho  = compute_rho_i(fr['tau'], fr['K'])
        sv_  = sigma_vm(fr['vel'], fr['K'], rho)
        rho_series.append(rho.mean())
        sigvm_series.append(sv_.mean())

    # Range globale per colorscale costante nel tempo
    rho_all = np.concatenate([compute_rho_i(frames[fi]['tau'], frames[fi]['K'])
                               for fi in frame_idxs[::max(1,len(frame_idxs)//10)]])
    vmin_r, vmax_r = rho_all.min(), rho_all.max()

    t_series = [topo['time'][min(fi*sv + sv - 1, len(topo['time'])-1)]
                for fi in frame_idxs]

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 6.5), facecolor='#f8f8f8')
    gs  = gridspec.GridSpec(2, 2, figure=fig,
                            height_ratios=[4, 1],
                            hspace=0.08, wspace=0.28,
                            left=0.04, right=0.97, top=0.93, bottom=0.07)

    ax3d  = fig.add_subplot(gs[0, 0], projection='3d')
    ax2d  = fig.add_subplot(gs[0, 1])
    ax_r  = fig.add_subplot(gs[1, 0])
    ax_s  = fig.add_subplot(gs[1, 1])

    ax3d.set_facecolor('#f0f0f0')
    ax2d.set_facecolor('#ffffff')
    for ax_ in [ax_r, ax_s]:
        ax_.set_facecolor('#f8f8f8')

    title_txt = fig.suptitle('', fontsize=9, fontweight='bold')

    # HUD strip (statici, aggiorno solo vline)
    t_hud = np.array(t_series)
    ax_r.plot(t_hud, rho_series,   color='royalblue', lw=1.4)
    ax_r.set_ylabel('ρ̄', fontsize=7); ax_r.set_xlabel('t [Planck]', fontsize=7)
    ax_r.tick_params(labelsize=6);    ax_r.grid(True, alpha=0.3)
    vl_r = ax_r.axvline(t_hud[0], color='red', lw=1.2)

    ax_s.plot(t_hud, sigvm_series, color='darkorange', lw=1.4)
    ax_s.set_ylabel('σ̄_VM', fontsize=7); ax_s.set_xlabel('t [Planck]', fontsize=7)
    ax_s.tick_params(labelsize=6);        ax_s.grid(True, alpha=0.3)
    vl_s = ax_s.axvline(t_hud[0], color='red', lw=1.2)

    print(f"Rendering {len(frame_idxs)} frame → {output} ...")

    def update(anim_idx):
        fi   = frame_idxs[anim_idx]
        fr   = frames[fi]
        pos  = fr['pos']; K = fr['K']; tau = fr['tau']; vel = fr['vel']
        rho  = compute_rho_i(tau, K)
        tang = torsion_vectors3d(pos, K)     # (N,3)  magn=|K|
        t_cur= t_series[anim_idx]
        ti   = min(fi*sv + sv - 1, len(topo['time'])-1)
        phase= topo['phase'][ti]
        S_lbl= (f"  S/N={S[ti]/N:.2f}" if S is not None else "")

        title_txt.set_text(
            f"Torsione chirale K·t — {path.stem}    "
            f"t={t_cur:.3f} Planck  |  ρ̄={rho.mean():.4f} [{phase}]{S_lbl}"
        )

        # ── Pannello 3D ──────────────────────────────────────────────────────
        ax3d.cla()
        ax3d.set_facecolor('#f0f0f0')

        # Scatter: colore = ρ_i, dimensione proporzionale a ρ
        ax3d.scatter(*pos.T, c=rho, cmap='plasma',
                     vmin=vmin_r, vmax=vmax_r,
                     s=14 + rho*28, alpha=0.70, linewidths=0, zorder=2)

        # Quiver torsione: GRANDI, CIANOFORTE, chiaramente visibili
        K_abs  = np.abs(K)
        K_p99  = float(np.percentile(K_abs, 99)) + 1e-10
        # Subsample proporzionale a |K| — mostra dove la torsione è più intensa
        prob   = K_abs / K_abs.sum()
        idx_q  = np.random.choice(N, min(quiver_n, N), replace=False, p=prob)

        uvw    = tang[idx_q]               # già scalato per K_i
        scale  = 4.0 / (K_p99 + 1e-10)    # normalizza per bbox
        ax3d.quiver(pos[idx_q,0], pos[idx_q,1], pos[idx_q,2],
                    uvw[:,0]*scale, uvw[:,1]*scale, uvw[:,2]*scale,
                    color='#00ccff', linewidth=1.2, arrow_length_ratio=0.35,
                    alpha=0.85, zorder=3)

        # Punti ad alta torsione evidenziati in rosso
        hot = K_abs > np.percentile(K_abs, 90)
        ax3d.scatter(*pos[hot].T, c='#ff3333', s=30, alpha=0.9,
                     linewidths=0.5, edgecolors='white', zorder=4)

        ax3d.set_title('Scatter ρ_i  +  vettori K·t (ciano)\n'
                       'rosso = top-10% torsione', fontsize=7, pad=2)
        ax3d.set_axis_off()
        ax3d.view_init(elev=elev, azim=azim_start + anim_idx*azim_delta)

        # ── Pannello 2D streamlines ───────────────────────────────────────────
        ax2d.cla()
        ax2d.set_facecolor('#ffffff')
        try:
            x1, y1, U, V = streamfield2d(pos, K, tang, grid=grid)
            speed = np.sqrt(U**2 + V**2) + 1e-10
            # Sfondo: intensità torsione interpolata
            ax2d.imshow(speed.T, origin='lower', cmap='YlOrRd', aspect='auto',
                        extent=[x1[0], x1[-1], y1[0], y1[-1]],
                        alpha=0.55, zorder=0)
            # Streamlines del campo K·t
            lw = 0.5 + 2.0 * (speed / speed.max())
            ax2d.streamplot(x1, y1, U.T, V.T,
                            color=speed.T, cmap='cool',
                            linewidth=lw.T, density=2.2,
                            arrowsize=1.0, arrowstyle='->', zorder=1)
            # Overlay punti caldi
            ax2d.scatter(pos[hot,0], pos[hot,1], c='#ff3333',
                         s=18, alpha=0.8, linewidths=0, zorder=2)
        except Exception:
            ax2d.text(0.5, 0.5, 'interpolazione non conv.',
                      ha='center', va='center', transform=ax2d.transAxes)

        ax2d.set_xlabel('x [Planck]', fontsize=7)
        ax2d.set_ylabel('y [Planck]', fontsize=7)
        ax2d.set_title('Streamlines K·t (proiezione XY)\nsfondo: intensità |K·t| interpolata',
                       fontsize=7)
        ax2d.tick_params(labelsize=6)

        # Aggiorna cursori HUD
        vl_r.set_xdata([t_cur, t_cur])
        vl_s.set_xdata([t_cur, t_cur])
        return []

    anim = FuncAnimation(fig, update, frames=len(frame_idxs),
                         interval=1000//fps, blit=False)

    writer = FFMpegWriter(fps=fps, bitrate=2500,
                          extra_args=['-pix_fmt', 'yuv420p', '-crf', '20'])
    anim.save(output, writer=writer, dpi=dpi)
    plt.close(fig)
    print(f"Video salvato: {Path(output).resolve()}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('hdf5')
    p.add_argument('--output', '-o', default=None)
    p.add_argument('--fps',          type=int,   default=10)
    p.add_argument('--step',         type=int,   default=2,   help='Passo frame')
    p.add_argument('--quiver',       type=int,   default=120, help='Max frecce torsione')
    p.add_argument('--grid',         type=int,   default=60,  help='Risoluzione streamplot')
    p.add_argument('--dpi',          type=int,   default=110)
    p.add_argument('--elev',         type=float, default=28.0)
    p.add_argument('--azim',         type=float, default=40.0)
    p.add_argument('--azim-delta',   type=float, default=2.0)
    p.add_argument('--seed',         type=int,   default=42)
    return p.parse_args()

def main():
    args = parse_args()
    np.random.seed(args.seed)
    make_video(args.hdf5, output=args.output,
               fps=args.fps, step=args.step,
               quiver_n=args.quiver, grid=args.grid, dpi=args.dpi,
               elev=args.elev, azim_start=args.azim, azim_delta=args.azim_delta)

if __name__ == '__main__':
    sys.exit(main())
