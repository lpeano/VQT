#!/usr/bin/env python3
"""
manifold_viz3d.py — ManifoldViz3D: Visualizzazione 3D del manifold VQT

Legge un file HDF5 generato da generate_topological_dataset.py e produce:
  --mode grid    : griglia PNG di snapshot 3D + metriche globali
  --mode animate : animazione GIF/MP4 con HUD laterale

Formule fisiche implementate:
  ρ_i  = ½ f_closure,i + ½ f_detorsion,i  [Eq. RHO-1]
  f_closure,i = 1 - |τ_i - τ̄| / τ_range  [Eq. FC-1]
  Ω_i  = K_i² × K_{i+1}²                  [Eq. OM-1]
  f_detorsion,i = 1 / (1 + Ω_i / K̄²)     [Eq. FD-1]

Uso:
    python -X utf8 manifold_viz3d.py cosmo_L2_variational.h5
    python -X utf8 manifold_viz3d.py cosmo_L2_variational.h5 --mode animate --output manifold.gif
"""

import argparse
import sys
from pathlib import Path

import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colorbar as mcolorbar
from matplotlib import colors as mcolors
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


# ─── Fisica [TOPOLOGICAL_DYNAMICS.md] ───────────────────────────────────────

def compute_rho_i(tau: np.ndarray, K: np.ndarray) -> np.ndarray:
    """
    Densità di vincolo per segmento.
    ρ_i = ½ f_closure,i + ½ f_detorsion,i  [Eq. RHO-1]
    """
    tau_range = float(np.max(tau) - np.min(tau))
    if tau_range < 1e-12:
        f_cl = np.ones(len(tau))
    else:
        f_cl = 1.0 - np.abs(tau - np.mean(tau)) / tau_range          # [Eq. FC-1]

    K2 = K ** 2
    K2_bar = float(np.mean(K2))
    if K2_bar < 1e-12:
        K2_bar = 1.0
    Omega = K2 * np.roll(K2, -1)                                      # [Eq. OM-1]
    f_dt = 1.0 / (1.0 + Omega / K2_bar)                               # [Eq. FD-1]

    return np.clip(0.5 * f_cl + 0.5 * f_dt, 0.0, 1.0)                # [Eq. RHO-1]


def torsion_vectors(pos: np.ndarray, K: np.ndarray) -> tuple:
    """
    Vettori quiver: tangente locale × |K_i|.
    Tangente i = (pos[i+1] - pos[i-1]) normalizzata.
    Restituisce (x,y,z, u,v,w) pronti per ax.quiver.
    """
    tang = np.empty_like(pos)
    tang[1:-1] = pos[2:] - pos[:-2]
    tang[0] = pos[1] - pos[0]
    tang[-1] = pos[-1] - pos[-2]
    nrm = np.linalg.norm(tang, axis=1, keepdims=True)
    nrm = np.where(nrm < 1e-12, 1.0, nrm)
    tang /= nrm
    uvw = tang * np.abs(K[:, None])
    return (pos[:, 0], pos[:, 1], pos[:, 2],
            uvw[:, 0], uvw[:, 1], uvw[:, 2])


# ─── Classe principale ───────────────────────────────────────────────────────

class ManifoldViz3D:
    """Visualizzatore 3D del manifold VQT da file HDF5."""

    CMAP = 'plasma'

    def __init__(self, hdf5_path: str):
        self.path = Path(hdf5_path)
        self._load()

    # ------------------------------------------------------------------
    def _load(self):
        with h5py.File(self.path, 'r') as f:
            frame_keys = sorted(f['frames'].keys(),
                                key=lambda x: int(x.split('_')[1]))
            self.n_frames = len(frame_keys)
            self.frames: list[dict] = []
            for fk in frame_keys:
                g = f['frames'][fk]
                self.frames.append({
                    'pos': g['positions'][:].astype(float),
                    'K':   g['contorsione_locale'][:].astype(float),
                    'tau': g['tau_locale'][:].astype(float),
                })

            tv = f['topological_validation']
            self.topo = {
                'step':    tv['step'][:].astype(float),
                'time':    tv['time'][:].astype(float),
                'rho':     tv['mean_constraint_density'][:].astype(float),
                'rho_std': tv['constraint_density_std'][:].astype(float),
                'H':       tv['H_total_emergent'][:].astype(float),
                'closure': tv['closure_error_deg'][:].astype(float),
                'phase':   np.array([p.decode() if isinstance(p, bytes) else p
                                     for p in tv['phase_label'][:]]),
            }

            if 'variational_force' in f:
                vf = f['variational_force']
                S_raw = vf['potential_S'][:].astype(float)
                n = len(self.topo['step'])
                self.S = S_raw[1::2][:n] if len(S_raw) >= 2 * n else S_raw[:n]
            else:
                self.S = None

        self.N = self.frames[0]['pos'].shape[0]
        n_topo = len(self.topo['step'])
        self.save_interval = max(1, n_topo // self.n_frames)

        # Pre-calcola ρ_i per ogni frame  [Eq. RHO-1]
        self.rho_seg = [compute_rho_i(fr['tau'], fr['K']) for fr in self.frames]

        print(f"  {self.path.name}: {self.n_frames} frame, {n_topo} step topologici")
        print(f"  N_seg={self.N}, save_interval={self.save_interval}")

    # ------------------------------------------------------------------
    def _topo_idx(self, frame_idx: int) -> int:
        """frame_idx -> indice nell'array topological_validation."""
        return min(frame_idx * self.save_interval + self.save_interval - 1,
                   len(self.topo['step']) - 1)

    # ------------------------------------------------------------------
    def _draw_3d(self, ax, frame_idx: int, n_quiver: int = 80,
                 elev: float = 25.0, azim: float = 45.0,
                 vmin: float = 0.0, vmax: float = 1.0, show_title: bool = True):
        """Disegna un singolo pannello 3D."""
        fr = self.frames[frame_idx]
        rho = self.rho_seg[frame_idx]
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap(self.CMAP)

        sz = np.clip(10 + rho * 30, 5, 60)
        sc = ax.scatter(fr['pos'][:, 0], fr['pos'][:, 1], fr['pos'][:, 2],
                        c=rho, cmap=self.CMAP, vmin=vmin, vmax=vmax,
                        s=sz, alpha=0.75, linewidths=0)

        # Quiver (subsampled)
        n_q = min(n_quiver, self.N)
        idx = np.sort(np.random.choice(self.N, n_q, replace=False))
        qx, qy, qz, qu, qv, qw = torsion_vectors(fr['pos'][idx], fr['K'][idx])
        K_abs = np.abs(fr['K'][idx])
        K_norm_val = K_abs / (K_abs.max() + 1e-12)
        q_colors = cmap(norm(np.clip(rho[idx], vmin, vmax)))
        ax.quiver(qx, qy, qz, qu, qv, qw,
                  length=2.0, normalize=True,
                  colors=q_colors, alpha=0.35, linewidth=0.5)

        if show_title:
            ti = self._topo_idx(frame_idx)
            phase = self.topo['phase'][ti]
            rho_m = self.topo['rho'][ti]
            t_v = self.topo['time'][ti]
            eps = self.topo['closure'][ti]
            S_label = (f"S/N={self.S[ti]/self.N:.2f}" if self.S is not None else "")
            ax.set_title(
                f"t={t_v:.2f} | ρ={rho_m:.3f} [{phase[:4]}]\n"
                f"ε={eps:.0f}° | {S_label}",
                fontsize=7, pad=1
            )

        ax.set_axis_off()
        ax.view_init(elev=elev, azim=azim)
        return sc

    # ------------------------------------------------------------------
    def plot_grid(
        self,
        n_snap: int = 10,
        output: str | None = None,
        dpi: int = 130,
        n_quiver: int = 80,
        elev: float = 25.0,
        azim: float = 45.0,
    ):
        """
        Griglia di n_snap snapshot 3D + striscia metriche globali.

        Layout:
          Riga superiore  : n_snap pannelli 3D
          Riga inferiore  : ρ(t) | S/N(t) | ε_closure(t)
        """
        output = output or f'{self.path.stem}_grid.png'
        frame_idxs = np.linspace(0, self.n_frames - 1, n_snap, dtype=int)

        rho_flat = np.concatenate(self.rho_seg)
        vmin, vmax = rho_flat.min(), rho_flat.max()

        fig = plt.figure(figsize=(n_snap * 3.0, 8.5))
        fig.suptitle(
            f'ManifoldViz3D — {self.path.stem}  (N={self.N} segmenti)',
            fontsize=11, fontweight='bold', y=0.99
        )

        gs_top = gridspec.GridSpec(1, n_snap, figure=fig,
                                   top=0.91, bottom=0.37, hspace=0, wspace=0.02)
        gs_bot = gridspec.GridSpec(1, 3, figure=fig,
                                   top=0.30, bottom=0.06, wspace=0.35)

        axes_3d = []
        for col, fi in enumerate(frame_idxs):
            ax = fig.add_subplot(gs_top[0, col], projection='3d')
            sc = self._draw_3d(ax, int(fi), n_quiver=n_quiver,
                               elev=elev, azim=azim, vmin=vmin, vmax=vmax)
            axes_3d.append(ax)

        # Colorbar comune
        cax = fig.add_axes([0.92, 0.38, 0.008, 0.52])
        norm_cb = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cb = mcolorbar.ColorbarBase(cax, cmap=self.CMAP, norm=norm_cb,
                                    orientation='vertical')
        cb.set_label('ρ_constraint', fontsize=8)
        cb.ax.axhline(0.3, color='white', lw=0.8, ls='--', alpha=0.7)
        cb.ax.axhline(0.6, color='white', lw=0.8, ls='--', alpha=0.7)
        cb.ax.text(1.05, 0.3, 'vacuum↔trans', transform=cb.ax.transAxes,
                   fontsize=5, va='center', color='gray')
        cb.ax.text(1.05, 0.6, 'trans↔cond', transform=cb.ax.transAxes,
                   fontsize=5, va='center', color='gray')

        t = self.topo['time']
        frame_times = [self.topo['time'][self._topo_idx(int(fi))] for fi in frame_idxs]

        def mark_frames(ax_):
            for ft in frame_times:
                ax_.axvline(ft, color='silver', lw=0.4, alpha=0.6, zorder=0)

        # ρ(t)
        ax_rho = fig.add_subplot(gs_bot[0, 0])
        ax_rho.fill_between(t,
                            self.topo['rho'] - self.topo['rho_std'],
                            self.topo['rho'] + self.topo['rho_std'],
                            alpha=0.18, color='royalblue')
        ax_rho.plot(t, self.topo['rho'], color='royalblue', lw=1.5, label='ρ̄')
        mark_frames(ax_rho)
        ax_rho.set_xlabel('Tempo [Planck]', fontsize=8)
        ax_rho.set_ylabel('ρ_constraint', fontsize=8)
        ax_rho.set_title('Omeostasi ρ(t)', fontsize=9)
        ax_rho.grid(True, alpha=0.3)

        # S/N(t)
        ax_S = fig.add_subplot(gs_bot[0, 1])
        if self.S is not None:
            ax_S.plot(t, self.S / self.N, color='darkorange', lw=1.5)
        ax_S.set_xlabel('Tempo [Planck]', fontsize=8)
        ax_S.set_ylabel('S / N  (per segmento)', fontsize=8)
        ax_S.set_title('Potenziale variazionale S/N  [Eq. S-1]', fontsize=9)
        mark_frames(ax_S)
        ax_S.grid(True, alpha=0.3)

        # ε_closure(t)
        ax_cl = fig.add_subplot(gs_bot[0, 2])
        ax_cl.plot(t, self.topo['closure'], color='mediumseagreen', lw=1.2)
        ax_cl.axhline(15.0, color='tomato', lw=0.9, ls='--', label='soglia 15°')
        mark_frames(ax_cl)
        ax_cl.set_xlabel('Tempo [Planck]', fontsize=8)
        ax_cl.set_ylabel('ε_closure [°]', fontsize=8)
        ax_cl.set_title('Chiusura spinoriale 720°', fontsize=9)
        ax_cl.legend(fontsize=7)
        ax_cl.grid(True, alpha=0.3)

        out = Path(output)
        fig.savefig(out, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        print(f"Griglia salvata: {out.resolve()}")

    # ------------------------------------------------------------------
    def animate(
        self,
        output: str | None = None,
        fps: int = 8,
        frame_step: int = 1,
        dpi: int = 90,
        n_quiver: int = 60,
        elev: float = 25.0,
        azim_start: float = 30.0,
        azim_delta: float = 1.5,
    ):
        """
        Animazione GIF (Pillow) o MP4 (ffmpeg) del manifold 3D.

        Layout: scatter 3D (sinistra) | ρ(t) + vline corrente | S/N(t) + vline
        """
        from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter

        output = output or f'{self.path.stem}_animate.gif'
        out = Path(output)

        frame_idxs = list(range(0, self.n_frames, max(1, frame_step)))
        n_anim = len(frame_idxs)

        rho_flat = np.concatenate(self.rho_seg)
        vmin, vmax = rho_flat.min(), rho_flat.max()
        t = self.topo['time']

        fig = plt.figure(figsize=(13, 5))
        fig.patch.set_facecolor('#0d0d1a')
        gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.38,
                               left=0.04, right=0.97, top=0.90, bottom=0.12)

        ax3d = fig.add_subplot(gs[0, 0], projection='3d')
        ax3d.set_facecolor('#0d0d1a')
        fig.suptitle(f'ManifoldViz3D — {self.path.stem}', color='white',
                     fontsize=10, fontweight='bold')

        ax_rho = fig.add_subplot(gs[0, 1])
        ax_rho.set_facecolor('#12122a')
        ax_S = fig.add_subplot(gs[0, 2])
        ax_S.set_facecolor('#12122a')

        for ax_ in [ax_rho, ax_S]:
            ax_.tick_params(colors='#aaaaaa', labelsize=7)
            for sp in ax_.spines.values():
                sp.set_color('#333366')

        # Plot statici delle metriche
        ax_rho.fill_between(t,
                            self.topo['rho'] - self.topo['rho_std'],
                            self.topo['rho'] + self.topo['rho_std'],
                            alpha=0.2, color='#4488ff')
        ax_rho.plot(t, self.topo['rho'], color='#4488ff', lw=1.2)
        ax_rho.set_xlabel('Tempo [Planck]', fontsize=7, color='#aaaaaa')
        ax_rho.set_ylabel('ρ̄', fontsize=8, color='#aaaaaa')
        ax_rho.set_title('Omeostasi ρ(t)', fontsize=8, color='white')
        ax_rho.grid(True, alpha=0.2, color='#333366')
        vl_rho = ax_rho.axvline(t[0], color='#ff4444', lw=1.3, zorder=5)

        if self.S is not None:
            ax_S.plot(t, self.S / self.N, color='#ffaa33', lw=1.2)
        ax_S.set_xlabel('Tempo [Planck]', fontsize=7, color='#aaaaaa')
        ax_S.set_ylabel('S / N', fontsize=8, color='#aaaaaa')
        ax_S.set_title('Potenziale S/N', fontsize=8, color='white')
        ax_S.grid(True, alpha=0.2, color='#333366')
        vl_S = ax_S.axvline(t[0], color='#ff4444', lw=1.3, zorder=5)

        def update(anim_idx: int):
            fi = frame_idxs[anim_idx]
            ti = self._topo_idx(fi)
            t_cur = self.topo['time'][ti]

            ax3d.cla()
            ax3d.set_facecolor('#0d0d1a')
            self._draw_3d(ax3d, fi, n_quiver=n_quiver,
                          elev=elev, azim=azim_start + anim_idx * azim_delta,
                          vmin=vmin, vmax=vmax, show_title=True)

            vl_rho.set_xdata([t_cur, t_cur])
            vl_S.set_xdata([t_cur, t_cur])
            return []

        anim = FuncAnimation(fig, update, frames=n_anim,
                             interval=1000 // fps, blit=False)

        suffix = out.suffix.lower()
        if suffix == '.gif':
            writer = PillowWriter(fps=fps)
        else:
            try:
                writer = FFMpegWriter(fps=fps, bitrate=2000,
                                     extra_args=['-pix_fmt', 'yuv420p'])
            except Exception:
                print("ffmpeg non disponibile, salvo come GIF")
                out = out.with_suffix('.gif')
                writer = PillowWriter(fps=fps)

        print(f"Rendering {n_anim} frame -> {out.name} ...")
        anim.save(out, writer=writer, dpi=dpi)
        plt.close(fig)
        print(f"Animazione salvata: {out.resolve()}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description='ManifoldViz3D — Visualizzazione 3D del manifold VQT',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument('hdf5',           help='File HDF5 input (generate_topological_dataset.py)')
    p.add_argument('--mode', '-m',   choices=['grid', 'animate'], default='grid')
    p.add_argument('--output', '-o', default=None,  help='File output (auto se omesso)')
    p.add_argument('--n-snap',       type=int,   default=10,   help='Snapshot nella griglia')
    p.add_argument('--fps',          type=int,   default=8,    help='Frame/s animazione')
    p.add_argument('--frame-step',   type=int,   default=1,    help='Passo frame animazione')
    p.add_argument('--dpi',          type=int,   default=130)
    p.add_argument('--elev',         type=float, default=25.0, help='Elevazione vista 3D [°]')
    p.add_argument('--azim',         type=float, default=45.0, help='Azimuth iniziale [°]')
    p.add_argument('--azim-delta',   type=float, default=1.5,  help='Rot. azimuth/frame [°]')
    p.add_argument('--quiver',       type=int,   default=80,   help='Max vettori K visibili')
    p.add_argument('--seed',         type=int,   default=0,    help='Seed per subsample quiver')
    return p.parse_args()


def main():
    args = parse_args()
    np.random.seed(args.seed)

    print(f"ManifoldViz3D — {args.hdf5}")
    viz = ManifoldViz3D(args.hdf5)

    if args.mode == 'grid':
        viz.plot_grid(
            n_snap=args.n_snap,
            output=args.output,
            dpi=args.dpi,
            n_quiver=args.quiver,
            elev=args.elev,
            azim=args.azim,
        )
    else:
        viz.animate(
            output=args.output,
            fps=args.fps,
            frame_step=args.frame_step,
            dpi=args.dpi,
            n_quiver=args.quiver,
            elev=args.elev,
            azim_start=args.azim,
            azim_delta=args.azim_delta,
        )
    return 0


if __name__ == '__main__':
    sys.exit(main())
