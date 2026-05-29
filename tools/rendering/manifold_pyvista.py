#!/usr/bin/env python3
"""
manifold_pyvista.py — Rendering volumetrico del manifold VQT con PyVista/VTK.

Il manifold VQT è trattato come un fluido viscoso-elastico:
  - Isosuperfici ρ (density shells) semitrasparenti, colorate per curvatura κ_Ricci
  - Volume rendering σ_VM (pressione topologica) come "bagliore" nelle zone di tensione
  - Streamlines 3D del campo K·t (torsione come flusso chirale)
  - Point cloud ρ_i per i segmenti originali del manifold

Pipeline dati:
  pos(N,3) + K(N) + τ(N) + v(N)
    → ρ(N), κ(N), σ_VM(N), K·t(N,3)
    → RBF interpolation con neighbors-sparse → ImageData(grid_res³)
    → isosuperfici + streamlines 3D + volume rendering
    → PNG statico / GIF animato

Uso:
    python -X utf8 manifold_pyvista.py cosmo_L2_variational.h5
    python -X utf8 manifold_pyvista.py cosmo_L2_variational.h5 --frame 25 --grid 80
    python -X utf8 manifold_pyvista.py cosmo_L2_variational.h5 --animate --step 4 --fps 8
    python -X utf8 manifold_pyvista.py cosmo_L3_probe.h5 --grid 60 --neighbors 32

Gestione memoria GPU/CPU:
    L2 (N=576):   grid=80, neighbors=64  → ~1 GB RAM, <2 min/frame
    L3 (N=13824): grid=60, neighbors=32  → ~2 GB RAM, ~5 min/frame
    Usare --grid 40 --neighbors 16 per preview rapido su hardware limitato.
"""

import argparse, sys, warnings
from pathlib import Path

import h5py
import numpy as np
import imageio
import pyvista as pv
from scipy.interpolate import RBFInterpolator

warnings.filterwarnings('ignore', category=RuntimeWarning)

pv.global_theme.background = '#f5f5f5'
pv.global_theme.font.color = '#111111'
pv.global_theme.font.size = 11
pv.global_theme.allow_empty_mesh = True

# ── Costanti fisiche ───────────────────────────────────────────────────────────
RHO_0, LAMBDA, GAMMA = 0.85, 0.2, 0.05


# ── Fisica ────────────────────────────────────────────────────────────────────
def compute_rho_i(tau, K):
    """Densità di vincolo ρ_i ∈ [0,1] — Eq. RHO-1 / FC-1 / FD-1."""
    tau_range = float(np.max(tau) - np.min(tau))
    f_cl = (np.ones(len(tau)) if tau_range < 1e-12
            else 1.0 - np.abs(tau - np.mean(tau)) / tau_range)
    K2     = K ** 2
    K2_bar = max(float(np.mean(K2)), 1e-12)
    Omega  = K2 * np.roll(K2, -1)
    f_dt   = 1.0 / (1.0 + Omega / K2_bar)
    return np.clip(0.5 * f_cl + 0.5 * f_dt, 0.0, 1.0)


def compute_ricci(pos):
    """Curvatura di Ricci discreta κ_i = 1 − cos(θ_i) ∈ [0, 2]."""
    e_in  = pos - np.roll(pos,  1, axis=0)
    e_out = np.roll(pos, -1, axis=0) - pos
    n_in  = np.linalg.norm(e_in,  axis=1, keepdims=True)
    n_out = np.linalg.norm(e_out, axis=1, keepdims=True)
    e_in  /= np.where(n_in  < 1e-12, 1.0, n_in)
    e_out /= np.where(n_out < 1e-12, 1.0, n_out)
    cos_theta = np.clip(np.sum(e_in * e_out, axis=1), -1.0, 1.0)
    return 1.0 - cos_theta


def compute_sigma_vm(vel, K, rho):
    """Von Mises anisotropy σ_VM = |T_xx − T_tt|."""
    K2    = K ** 2
    K2b   = max(float(np.mean(K2)), 1e-12)
    Omega = K2 * np.roll(K2, -1)
    T_tt  = 0.5 * vel**2 + LAMBDA * (rho - RHO_0)**2 + GAMMA * Omega
    T_xx  = 0.5 * K2    + GAMMA * Omega
    return np.abs(T_xx - T_tt)


def torsion_vectors3d(pos, K):
    """K_i × tangente locale normalizzata → vettore torsione (N,3)."""
    t = np.empty_like(pos)
    t[1:-1] = pos[2:]  - pos[:-2]
    t[0]    = pos[1]   - pos[0]
    t[-1]   = pos[-1]  - pos[-2]
    n = np.linalg.norm(t, axis=1, keepdims=True)
    t /= np.where(n < 1e-12, 1.0, n)
    return t * K[:, None]           # magnitude = |K_i|


# ── Griglia volumetrica ────────────────────────────────────────────────────────
def build_volume_grid(pos, scalars: dict, vectors: dict,
                      grid_res: int = 80, neighbors: int = 64,
                      pad: float = 0.07) -> pv.ImageData:
    """
    Interpola dati discreti su una griglia ImageData PyVista (grid_res³).

    Usa RBFInterpolator con kernel 'linear' e campionamento sparse (neighbors)
    per limitare la memoria: complessità O(N × neighbors) invece di O(N²).

    Args:
        pos:       (N,3) posizioni dei segmenti
        scalars:   dict name → array(N)  (valori scalari da interpolare)
        vectors:   dict name → array(N,3) (campi vettoriali da interpolare)
        grid_res:  risoluzione per asse della griglia
        neighbors: numero di vicini per RBF sparse (↓ per L3 su RAM limitata)
        pad:       padding percentuale del bounding box
    """
    lo = pos.min(0)
    hi = pos.max(0)
    span = hi - lo
    lo -= pad * span
    hi += pad * span
    span = hi - lo

    spacing = tuple(span / (grid_res - 1))

    grid = pv.ImageData()
    grid.dimensions = (grid_res,) * 3
    grid.origin     = tuple(lo)
    grid.spacing    = spacing

    # Griglia come array di punti (grid_res³, 3)
    xi = np.linspace(lo[0], hi[0], grid_res)
    yi = np.linspace(lo[1], hi[1], grid_res)
    zi = np.linspace(lo[2], hi[2], grid_res)
    Xg, Yg, Zg = np.meshgrid(xi, yi, zi, indexing='ij')
    gpts = np.column_stack([Xg.ravel(), Yg.ravel(), Zg.ravel()])

    N = len(pos)
    k = min(neighbors, N - 1)
    sm = N * 0.05           # smoothing: riduce oscillazioni RBF su cluster densi

    print(f"  RBF interpolazione: {N} punti → {grid_res}³={grid_res**3} "
          f"celle  (neighbors={k}, smoothing={sm:.1f})")

    for name, vals in scalars.items():
        rbf = RBFInterpolator(pos, vals.astype(float),
                              kernel='linear', neighbors=k, smoothing=sm)
        grid.point_data[name] = rbf(gpts).astype(np.float32)

    for name, vecs in vectors.items():
        out = np.zeros((len(gpts), 3), dtype=np.float32)
        for d in range(3):
            rbf = RBFInterpolator(pos, vecs[:, d].astype(float),
                                  kernel='linear', neighbors=k, smoothing=sm)
            out[:, d] = rbf(gpts).astype(np.float32)
        grid.point_data[name] = out

    return grid


# ── Scene builder ──────────────────────────────────────────────────────────────
def build_scene(plotter: pv.Plotter, pos, rho, kappa, sigma_vm, torsion,
                grid_res: int = 80, neighbors: int = 64,
                iso_vals=(0.50, 0.80), stream_seeds: int = 250):
    """
    Costruisce la scena PyVista:
      1. Griglia volumetrica RBF
      2. Isosuperfici ρ (colorate κ_Ricci, divergente coolwarm)
      3. Volume rendering σ_VM (glow effect, opacità sigmoid)
      4. Streamlines 3D campo K·t (fluido chirale ciano)
      5. Point cloud originale (plasma, ρ_i)
    """

    # ── 1. Interpolazione volumetrica ─────────────────────────────────────────
    sigma_cap = np.clip(sigma_vm, 0.0,
                        float(np.percentile(sigma_vm, 99)))   # rimuove outlier

    grid = build_volume_grid(
        pos,
        scalars={'rho': rho, 'kappa': kappa, 'sigma_vm': sigma_cap},
        vectors={'torsion': torsion},
        grid_res=grid_res, neighbors=neighbors
    )

    # ── 2. Isosuperfici ρ ─────────────────────────────────────────────────────
    iso_styles = [
        (iso_vals[0], 0.22, 'outer shell (ρ={:.2f})'.format(iso_vals[0])),
        (iso_vals[1], 0.48, 'inner core  (ρ={:.2f})'.format(iso_vals[1])),
    ]
    for iso_val, alpha, label in iso_styles:
        iso = grid.contour([iso_val], scalars='rho')
        if iso.n_points == 0:
            continue
        iso_data = iso.sample(grid)     # porta κ e σ_VM sulla superficie
        plotter.add_mesh(
            iso_data, scalars='kappa', cmap='coolwarm',
            clim=[0.0, 2.0],
            opacity=alpha,
            smooth_shading=True,
            lighting=True,
            specular=0.55, specular_power=20,
            diffuse=0.8,
            ambient=0.2,
            label=label
        )

    # ── 3. Volume rendering σ_VM (glow) ───────────────────────────────────────
    sigma_grid = grid.copy()
    sigma_grid.set_active_scalars('sigma_vm')

    # Funzione opacità personalizzata: lineare 0→0.01, plateau 0.01→max → 0.35
    s_min = float(sigma_grid.point_data['sigma_vm'].min())
    s_max = float(sigma_grid.point_data['sigma_vm'].max()) + 1e-10
    n_pts = 50
    opacity_fn = np.zeros(n_pts)
    t = np.linspace(0, 1, n_pts)
    # Sigmoid centrata a 60° percentile → zone alta tensione "incandescenti"
    opacity_fn = 0.38 / (1.0 + np.exp(-12.0 * (t - 0.55)))

    try:
        plotter.add_volume(
            sigma_grid,
            scalars='sigma_vm',
            cmap='YlOrRd',
            opacity=opacity_fn,
            shade=True,
            diffuse=0.9,
            specular=0.4,
            ambient=0.25,
        )
    except Exception as e:
        print(f"  [warn] volume rendering non disponibile: {e}")

    # ── 4. Streamlines 3D K·t ─────────────────────────────────────────────────
    center = pos.mean(0)
    bbox_r = float(np.linalg.norm(pos.max(0) - pos.min(0))) * 0.35

    grid.set_active_vectors('torsion')
    tors_mag = np.linalg.norm(grid.point_data['torsion'], axis=1)
    if tors_mag.max() > 1e-10:
        seed_sphere = pv.Sphere(
            radius=bbox_r,
            center=center.tolist(),
            theta_resolution=14,
            phi_resolution=14
        )
        try:
            sl = grid.streamlines_from_source(
                seed_sphere,
                vectors='torsion',
                max_length=bbox_r * 2.5,
                initial_step_length=0.04,
                terminal_speed=1e-5,
            )
            if sl.n_points > 0:
                tube_r = bbox_r * 0.005
                plotter.add_mesh(
                    sl.tube(radius=tube_r),
                    color='#00d4ff',
                    opacity=0.65,
                    smooth_shading=True,
                    lighting=True,
                    specular=0.7,
                    label='streamlines K·t'
                )
        except Exception as e:
            print(f"  [warn] streamlines non calcolate: {e}")

    # ── 5. Point cloud originale ───────────────────────────────────────────────
    cloud = pv.PolyData(pos.astype(np.float32))
    cloud.point_data['rho'] = rho.astype(np.float32)

    # Punti ad alta torsione in rosso
    K_abs = np.linalg.norm(torsion, axis=1)
    hot   = K_abs > np.percentile(K_abs, 90)
    if hot.any():
        plotter.add_points(pos[hot].astype(np.float32),
                           color='#ff2222', point_size=7,
                           render_points_as_spheres=True, opacity=0.9)

    plotter.add_mesh(
        cloud, scalars='rho', cmap='plasma',
        clim=[0.0, 1.0],
        point_size=3,
        render_points_as_spheres=True,
        opacity=0.45,
        label='segmenti (ρ_i)'
    )

    return grid


# ── Caricamento HDF5 ──────────────────────────────────────────────────────────
def load_hdf5(path):
    with h5py.File(path, 'r') as f:
        fkeys = sorted(f['frames'].keys(), key=lambda x: int(x.split('_')[1]))
        frames = []
        for fk in fkeys:
            g = f['frames'][fk]
            frames.append({
                'pos': g['positions'][:].astype(float),
                'K':   g['contorsione_locale'][:].astype(float),
                'tau': g['tau_locale'][:].astype(float),
                'vel': g['velocities'][:].astype(float),
            })
        tv   = f['topological_validation']
        topo = {
            'time':  tv['time'][:].astype(float),
            'rho':   tv['mean_constraint_density'][:].astype(float),
            'phase': [p.decode() if isinstance(p, bytes) else p
                      for p in tv['phase_label'][:]],
        }
        S = None
        if 'variational_force' in f:
            Sr = f['variational_force']['potential_S'][:].astype(float)
            n  = len(topo['time'])
            S  = Sr[1::2][:n] if len(Sr) >= 2 * n else Sr[:n]
    sv = max(1, len(topo['time']) // len(frames))
    return frames, topo, S, sv


# ── Render singolo frame ───────────────────────────────────────────────────────
def render_frame_png(frame, output_path: str,
                     grid_res: int = 80, neighbors: int = 64,
                     window_size=(1400, 900),
                     elev: float = 28.0, azim: float = 45.0,
                     topo_info: str = '',
                     iso_vals=(0.50, 0.80)):
    """Rende un singolo frame come PNG off-screen."""
    pos  = frame['pos']
    K    = frame['K']
    tau  = frame['tau']
    vel  = frame['vel']
    rho  = compute_rho_i(tau, K)
    kap  = compute_ricci(pos)
    svm  = compute_sigma_vm(vel, K, rho)
    tor  = torsion_vectors3d(pos, K)

    plotter = pv.Plotter(off_screen=True, window_size=list(window_size))
    plotter.set_background('#f5f5f5')

    print(f"  Costruzione scena (N={len(pos)}, grid={grid_res}³) ...")
    build_scene(plotter, pos, rho, kap, svm, tor,
                grid_res=grid_res, neighbors=neighbors, iso_vals=iso_vals)

    # Camera: reset automatico + rotazione azimuth/elevation
    plotter.reset_camera()
    plotter.camera.azimuth   = azim
    plotter.camera.elevation = elev

    # Legenda fisica
    lines = [
        f'ρ̄ = {rho.mean():.4f}   κ̄ = {kap.mean():.3f}   σ̄_VM = {svm.mean():.2f}',
        f'{topo_info}',
        f'N = {len(pos)} segmenti | griglia {grid_res}³',
        f'Isosuperfici ρ = {iso_vals[0]:.2f} (shell) / {iso_vals[1]:.2f} (core)',
        f'Colore κ_Ricci: blu=bassa curv., rosso=alta curv.',
    ]
    plotter.add_text('\n'.join(lines), position='lower_left',
                     font_size=9, color='#222222', shadow=True)
    plotter.add_text('VQT Manifold — Rendering Volumetrico PyVista/VTK',
                     position='upper_edge', font_size=12,
                     color='#111111')

    plotter.render()
    img = plotter.screenshot(output_path, return_img=True)
    plotter.close()
    print(f"  Salvato: {output_path}")
    return img


# ── Animazione GIF ────────────────────────────────────────────────────────────
def animate_gif(frames_list, frame_idxs, topo, S, sv, output: str,
                grid_res: int = 80, neighbors: int = 64, fps: int = 6,
                azim_start: float = 40.0, azim_delta: float = 3.0,
                elev: float = 28.0, iso_vals=(0.50, 0.80)):
    """Genera GIF animato iterando sui frame HDF5 selezionati."""
    images = []
    for ani_idx, fi in enumerate(frame_idxs):
        fr     = frames_list[fi]
        t_idx  = min(fi * sv + sv - 1, len(topo['time']) - 1)
        t_val  = topo['time'][t_idx]
        phase  = topo['phase'][t_idx]
        rho_m  = topo['rho'][t_idx]
        S_lbl  = (f'  S/N={S[t_idx]/fr["pos"].shape[0]:.2f}' if S is not None else '')
        info   = f't={t_val:.3f} Planck | {phase} | ρ̄={rho_m:.4f}{S_lbl}'
        azim   = azim_start + ani_idx * azim_delta

        tmp_png = f'_pyvista_tmp_{ani_idx:04d}.png'
        print(f"\nFrame {ani_idx+1}/{len(frame_idxs)}  fi={fi}  azim={azim:.1f}°")
        img = render_frame_png(fr, tmp_png,
                               grid_res=grid_res, neighbors=neighbors,
                               azim=azim, elev=elev,
                               topo_info=info, iso_vals=iso_vals)
        images.append(img)

    ext = Path(output).suffix.lower()
    if ext in ('.mp4', '.avi', '.mov'):
        writer = imageio.get_writer(output, fps=fps, quality=8,
                                    macro_block_size=None,
                                    ffmpeg_params=['-pix_fmt', 'yuv420p'])
        for img in images:
            writer.append_data(img)
        writer.close()
        print(f"\nVideo MP4 salvato: {Path(output).resolve()}")
    else:
        dur = int(1000 / fps)
        imageio.mimsave(output, images, duration=dur, loop=0)
        print(f"\nGIF animato salvato: {Path(output).resolve()}")

    # Pulizia PNG temporanei
    for ani_idx in range(len(frame_idxs)):
        p = Path(f'_pyvista_tmp_{ani_idx:04d}.png')
        if p.exists():
            p.unlink()


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Rendering volumetrico PyVista del manifold VQT'
    )
    p.add_argument('hdf5', help='File HDF5 VQT')
    p.add_argument('--output', '-o',  default=None,
                   help='File output (.png statico, .gif o .mp4 animato)')
    p.add_argument('--frame',         type=int,   default=None,
                   help='Indice frame (default: ultimo disponibile)')
    p.add_argument('--grid',          type=int,   default=80,
                   help='Risoluzione griglia per asse (grid³ punti totali)')
    p.add_argument('--neighbors',     type=int,   default=64,
                   help='Vicini RBF sparse (↓ per L3 su RAM limitata)')
    p.add_argument('--animate',       action='store_true',
                   help='Genera GIF animato invece di PNG statico')
    p.add_argument('--step',          type=int,   default=4,
                   help='Passo frame per animazione')
    p.add_argument('--fps',           type=int,   default=6,
                   help='Frame al secondo per GIF')
    p.add_argument('--elev',          type=float, default=28.0,
                   help='Elevazione camera [gradi]')
    p.add_argument('--azim',          type=float, default=45.0,
                   help='Azimuth iniziale camera [gradi]')
    p.add_argument('--azim-delta',    type=float, default=3.0,
                   help='Rotazione azimuth per frame animazione [gradi]')
    p.add_argument('--iso-low',       type=float, default=0.50,
                   help='Isovalore ρ shell esterna (traslucida)')
    p.add_argument('--iso-high',      type=float, default=0.80,
                   help='Isovalore ρ core interno (semi-opaco)')
    p.add_argument('--width',         type=int,   default=1400)
    p.add_argument('--height',        type=int,   default=900)
    return p.parse_args()


def main():
    args = parse_args()
    path   = Path(args.hdf5)
    stem   = path.stem
    iso_v  = (args.iso_low, args.iso_high)

    print(f"Caricamento {path} ...")
    frames, topo, S, sv = load_hdf5(path)
    print(f"  {len(frames)} frame HDF5, N={frames[0]['pos'].shape[0]} segmenti")

    if args.animate:
        output = args.output or f'{stem}_pyvista.mp4'
        idxs   = list(range(0, len(frames), max(1, args.step)))
        print(f"Animazione: {len(idxs)} frame → {output}  (fps={args.fps})")
        animate_gif(frames, idxs, topo, S, sv, output,
                    grid_res=args.grid, neighbors=args.neighbors,
                    fps=args.fps,
                    azim_start=args.azim, azim_delta=args.azim_delta,
                    elev=args.elev, iso_vals=iso_v)
    else:
        fi     = args.frame if args.frame is not None else len(frames) - 1
        fi     = min(fi, len(frames) - 1)
        output = args.output or f'{stem}_pyvista_f{fi:04d}.png'

        t_idx  = min(fi * sv + sv - 1, len(topo['time']) - 1)
        t_val  = topo['time'][t_idx]
        phase  = topo['phase'][t_idx]
        rho_m  = topo['rho'][t_idx]
        S_lbl  = (f'  S/N={S[t_idx]/frames[fi]["pos"].shape[0]:.2f}'
                  if S is not None else '')
        info   = f't={t_val:.3f} Planck | {phase} | ρ̄={rho_m:.4f}{S_lbl}'

        print(f"Rendering frame {fi}  ({info}) → {output}")
        render_frame_png(frames[fi], output,
                         grid_res=args.grid, neighbors=args.neighbors,
                         window_size=(args.width, args.height),
                         elev=args.elev, azim=args.azim,
                         topo_info=info, iso_vals=iso_v)


if __name__ == '__main__':
    sys.exit(main())
