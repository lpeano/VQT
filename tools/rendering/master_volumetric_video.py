#!/usr/bin/env python3
"""
master_volumetric_video.py — Video volumetrico L1→L2→L3 con PyVista + linee di forza

Pipeline per frame:
  1. PyVista off-screen: isosuperfici ρ + streamlines 3D K·t + volume σ_VM
  2. Alpha-composite numpy per cross-fade tra livelli
  3. HUD matplotlib incollato a destra: livello, ρ̄(t), fase, timeline
  4. imageio FFMpeg → MP4

Strategia performance:
  - Pre-render tutte le scene 3D uniche in memoria
  - Transition = alpha-blend di 2 pre-render (no render extra)
  - L1 (N=24): grid=35, solo glyph (N troppo piccolo per RBF volumetrico)
  - L2 (N=576): grid=50, pipeline completa
  - L3 (N=13824): grid=40, neighbors=24, streamlines ridotte

Stima tempi: ~25-40 min in background (seg=5→~20min, seg=8→~35min)

Uso:
    python -X utf8 master_volumetric_video.py
    python -X utf8 master_volumetric_video.py --seg-frames 5 --trans-frames 8 --fps 6
    python -X utf8 master_volumetric_video.py --l3 cosmo_L3_full.h5 --seg-frames 8
"""

import argparse, sys, io, time, warnings
from pathlib import Path

import h5py
import numpy as np
import imageio
from PIL import Image

import pyvista as pv
from scipy.interpolate import RBFInterpolator

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings('ignore', category=RuntimeWarning)

pv.global_theme.background = '#f0f0f0'
pv.global_theme.allow_empty_mesh = True

# ── Costanti fisiche ───────────────────────────────────────────────────────────
RHO_0, LAMBDA, GAMMA = 0.85, 0.2, 0.05
RHO_0_EFF  = {1: 0.860, 2: 0.852, 3: 0.850}
N_SEGS     = {1: 24,    2: 576,   3: 13824}
ZOOM_FACT  = 24 ** (1/3)
LV_COLOR   = {1: '#3a86ff', 2: '#8338ec', 3: '#ff006e'}
LV_DIST    = {1: 7.0,   2: 9.5,   3: 13.0}
ELEV       = 28.0

# Griglia e vicini RBF per livello
GRID_RES   = {1: 35,  2: 50,  3: 40}
NEIGHBORS  = {1: 20,  2: 48,  3: 24}
ISO_VALS   = (0.50, 0.80)
WIN_3D     = [1040, 780]
WIN_HUD_W  = 360
WIN_H      = 780


# ── Fisica ────────────────────────────────────────────────────────────────────
def compute_rho_i(tau, K):
    tau_r = float(np.max(tau) - np.min(tau))
    f_cl  = (np.ones(len(tau)) if tau_r < 1e-12
             else 1.0 - np.abs(tau - np.mean(tau)) / tau_r)
    K2    = K**2; K2b = max(float(np.mean(K2)), 1e-12)
    Omega = K2 * np.roll(K2, -1)
    return np.clip(0.5 * f_cl + 0.5 / (1.0 + Omega / K2b), 0.0, 1.0)

def compute_ricci(pos):
    e_in  = pos - np.roll(pos,  1, axis=0)
    e_out = np.roll(pos, -1, axis=0) - pos
    for e in [e_in, e_out]:
        n = np.linalg.norm(e, axis=1, keepdims=True)
        e /= np.where(n < 1e-12, 1.0, n)
    return 1.0 - np.clip(np.sum(e_in * e_out, axis=1), -1.0, 1.0)

def compute_sigma_vm(vel, K, rho):
    K2    = K**2; K2b = max(float(np.mean(K2)), 1e-12)
    Omega = K2 * np.roll(K2, -1)
    T_tt  = 0.5*vel**2 + LAMBDA*(rho-RHO_0)**2 + GAMMA*Omega
    T_xx  = 0.5*K2    + GAMMA*Omega
    return np.abs(T_xx - T_tt)

def torsion_vecs(pos, K):
    if len(pos) < 2:
        return np.zeros_like(pos)
    t = np.empty_like(pos)
    t[1:-1] = pos[2:] - pos[:-2]
    t[0]    = pos[1]  - pos[0]
    t[-1]   = pos[-1] - pos[-2]
    n = np.linalg.norm(t, axis=1, keepdims=True)
    t /= np.where(n < 1e-12, 1.0, n)
    return t * K[:, None]


# ── Caricamento + pre-calcolo fisica ─────────────────────────────────────────
def load_level(h5_path, level, max_frames=60):
    with h5py.File(h5_path, 'r') as f:
        fkeys = sorted(f['frames'].keys(), key=lambda x: int(x.split('_')[1]))[:max_frames]
        tv    = f['topological_validation']
        t_arr = tv['time'][:].astype(float)
        rho_t = tv['mean_constraint_density'][:].astype(float)
        ph_t  = [p.decode() if isinstance(p, bytes) else p for p in tv['phase_label'][:]]
        S_arr = None
        if 'variational_force' in f:
            Sr = f['variational_force']['potential_S'][:].astype(float)
            n  = len(t_arr)
            S_arr = Sr[1::2][:n] if len(Sr) >= 2*n else Sr[:n]
        raws = []
        for fk in fkeys:
            g = f['frames'][fk]
            raws.append({'pos': g['positions'][:].astype(float),
                         'K':   g['contorsione_locale'][:].astype(float),
                         'tau': g['tau_locale'][:].astype(float),
                         'vel': g['velocities'][:].astype(float)})

    si  = max(1, len(t_arr) // max(1, len(raws)))
    # Normalizza posizioni (CoM + bbox → [-1,1]³)
    all_pos    = np.concatenate([r['pos'] for r in raws], axis=0)
    com        = all_pos.mean(0)
    span       = np.abs(all_pos - com).max() + 1e-10
    scale_norm = 1.0 / span

    frames = []
    for i, r in enumerate(raws):
        pos_n = (r['pos'] - com) * scale_norm
        K     = r['K']
        rho   = compute_rho_i(r['tau'], K)
        kap   = compute_ricci(pos_n)
        svm   = compute_sigma_vm(r['vel'], K, rho)
        tor   = torsion_vecs(pos_n, K)
        ti    = min(i*si + si - 1, len(t_arr)-1)
        S_lbl = (f"S/N={S_arr[ti]/len(K):.2f}" if S_arr is not None else "")
        frames.append({'pos_n': pos_n, 'K': K, 'rho': rho, 'kappa': kap,
                       'sigma_vm': svm, 'torsion': tor,
                       'rho_mean': rho.mean(), 'sigma_mean': svm.mean(),
                       't_planck': t_arr[ti], 'phase': ph_t[ti],
                       'S_lbl': S_lbl, 'level': level})

    series = {'t': t_arr[:len(raws)*si:si][:len(raws)],
              'rho': rho_t[:len(raws)*si:si][:len(raws)]}
    print(f"  L{level}: {len(frames)} frame  N={raws[0]['pos'].shape[0]}  "
          f"t=[{t_arr[0]:.3f}..{t_arr[min((len(raws)-1)*si, len(t_arr)-1)]:.3f}]")
    return frames, series


# ── Scene builder PyVista ──────────────────────────────────────────────────────
def build_pv_scene(plotter, fr, level, seed=42):
    """
    Costruisce scena PyVista completa:
      - N>=50: griglia RBF → isosuperfici ρ (coolwarm κ) + volume σ_VM + streamlines K·t
      - N<50:  solo scatter + glyph arrows (griglia RBF non significativa)
    """
    np.random.seed(seed)
    pos = fr['pos_n'].astype(np.float32)
    rho = fr['rho'].astype(np.float32)
    kap = fr['kappa'].astype(np.float32)
    svm = fr['sigma_vm'].astype(np.float32)
    tor = fr['torsion'].astype(np.float32)
    N   = len(pos)

    # ── Point cloud sempre visibile ────────────────────────────────────────────
    cloud = pv.PolyData(pos)
    cloud['rho'] = rho
    plotter.add_mesh(cloud, scalars='rho', cmap='plasma', clim=[0.0, 1.0],
                     point_size=5 if N < 50 else 3,
                     render_points_as_spheres=True, opacity=0.55)

    # Top-10% torsione in rosso
    K_abs = np.linalg.norm(tor, axis=1)
    hot   = K_abs > np.percentile(K_abs, 90)
    if hot.any():
        plotter.add_points(pos[hot], color='#ff2222',
                           point_size=8 if N < 50 else 5,
                           render_points_as_spheres=True, opacity=0.90)

    if N < 50:
        # Glyph arrows per torsione (invece di streamlines)
        g_cloud = pv.PolyData(pos)
        K_p99   = float(np.percentile(K_abs, 99)) + 1e-10
        g_cloud['vectors'] = tor * (0.15 / K_p99)
        g_cloud.set_active_vectors('vectors')
        glyphs = g_cloud.glyph(orient='vectors', scale=False, factor=1.0,
                                geom=pv.Arrow())
        plotter.add_mesh(glyphs, color='#00ccff', opacity=0.85)
        return

    # ── Pipeline volumetrica (N >= 50) ────────────────────────────────────────
    gr  = GRID_RES[level]
    nb  = NEIGHBORS[level]
    sm  = N * 0.05

    lo  = pos.min(0) - 0.06 * (pos.max(0) - pos.min(0))
    hi  = pos.max(0) + 0.06 * (pos.max(0) - pos.min(0))
    sp  = (hi - lo) / (gr - 1)

    grid = pv.ImageData()
    grid.dimensions = (gr, gr, gr)
    grid.origin     = tuple(lo)
    grid.spacing    = tuple(sp)

    xi = np.linspace(lo[0], hi[0], gr)
    yi = np.linspace(lo[1], hi[1], gr)
    zi = np.linspace(lo[2], hi[2], gr)
    Xg, Yg, Zg = np.meshgrid(xi, yi, zi, indexing='ij')
    gpts = np.column_stack([Xg.ravel(), Yg.ravel(), Zg.ravel()])

    k = min(nb, N-1)
    print(f"    RBF {N}→{gr}³  neighbors={k}", end=' ', flush=True)
    t0 = time.time()
    svm_cap = np.clip(svm, 0, float(np.percentile(svm, 99)))

    for name, vals in [('rho', rho), ('kappa', kap), ('sigma_vm', svm_cap)]:
        rbf = RBFInterpolator(pos, vals.astype(float),
                              kernel='linear', neighbors=k, smoothing=sm)
        grid.point_data[name] = rbf(gpts).astype(np.float32)

    tor_interp = np.zeros((len(gpts), 3), dtype=np.float32)
    for d in range(3):
        rbf = RBFInterpolator(pos, tor[:, d].astype(float),
                              kernel='linear', neighbors=k, smoothing=sm)
        tor_interp[:, d] = rbf(gpts).astype(np.float32)
    grid.point_data['torsion'] = tor_interp
    print(f"{time.time()-t0:.1f}s")

    # Isosuperfici ρ colorate per κ_Ricci
    for iso_v, alpha in zip(ISO_VALS, [0.22, 0.46]):
        iso = grid.contour([iso_v], scalars='rho')
        if iso.n_points > 0:
            iso_d = iso.sample(grid)
            plotter.add_mesh(iso_d, scalars='kappa', cmap='coolwarm',
                             clim=[0.0, 2.0], opacity=alpha,
                             smooth_shading=True, lighting=True,
                             specular=0.5, specular_power=18,
                             diffuse=0.8, ambient=0.2)

    # Volume σ_VM (glow)
    s_min = float(grid.point_data['sigma_vm'].min())
    s_max = float(grid.point_data['sigma_vm'].max()) + 1e-10
    op_fn = 0.35 / (1.0 + np.exp(-12.0 * (np.linspace(0, 1, 50) - 0.55)))
    try:
        plotter.add_volume(grid, scalars='sigma_vm', cmap='YlOrRd',
                           opacity=op_fn, shade=True,
                           diffuse=0.9, specular=0.4, ambient=0.25)
    except Exception as e:
        print(f"    [warn] volume: {e}")

    # Streamlines 3D K·t
    grid.set_active_vectors('torsion')
    tmag = np.linalg.norm(grid.point_data['torsion'], axis=1)
    if tmag.max() > 1e-10:
        bbox_r  = float(np.linalg.norm(pos.max(0) - pos.min(0))) * 0.35
        center  = pos.mean(0).tolist()
        n_seeds = 10 if level == 3 else 14
        seeds   = pv.Sphere(radius=bbox_r, center=center,
                             theta_resolution=n_seeds,
                             phi_resolution=n_seeds)
        try:
            sl = grid.streamlines_from_source(seeds, vectors='torsion',
                                              max_length=bbox_r * 2.5,
                                              initial_step_length=0.04,
                                              terminal_speed=1e-5)
            if sl.n_points > 0:
                tube_r = bbox_r * 0.006
                plotter.add_mesh(sl.tube(radius=tube_r),
                                 color='#00d4ff', opacity=0.78,
                                 smooth_shading=True, lighting=True,
                                 specular=0.7)
        except Exception as e:
            print(f"    [warn] streamlines: {e}")


def render_3d(fr, azim, level):
    """Render PyVista off-screen → numpy RGB (WIN_H × WIN_3D[0] × 3)."""
    pl = pv.Plotter(off_screen=True, window_size=WIN_3D)
    pl.set_background('#f0f0f0')
    build_pv_scene(pl, fr, level)
    pl.reset_camera()
    pl.camera.azimuth   = azim
    pl.camera.elevation = ELEV
    pl.render()
    img = pl.screenshot(return_img=True)
    pl.close()
    return img


# ── HUD panel ─────────────────────────────────────────────────────────────────
def render_hud(fr, level_a, level_b, alpha_a, alpha_b,
               series_all: dict, is_trans: bool) -> np.ndarray:
    """Pannello HUD verticale: indicatore livello + ρ̄(t) + info."""
    fig = plt.figure(figsize=(WIN_HUD_W / 100, WIN_H / 100),
                     dpi=100, facecolor='#1a1a2e')
    gs  = gridspec.GridSpec(3, 1, figure=fig,
                            height_ratios=[3, 2, 2],
                            hspace=0.15,
                            left=0.08, right=0.95,
                            top=0.97, bottom=0.05)

    # ── Indicatore livello ─────────────────────────────────────────────────────
    ax_lv = fig.add_subplot(gs[0])
    ax_lv.set_facecolor('#0d0d1a')
    ax_lv.axis('off')

    if is_trans:
        ax_lv.text(0.5, 0.78, f'L{level_a}', ha='center', va='center',
                   fontsize=38, fontweight='bold',
                   color=LV_COLOR[level_a], alpha=float(alpha_a),
                   transform=ax_lv.transAxes)
        ax_lv.text(0.5, 0.78, f'L{level_b}', ha='center', va='center',
                   fontsize=38, fontweight='bold',
                   color=LV_COLOR[level_b], alpha=float(alpha_b),
                   transform=ax_lv.transAxes)
        ax_lv.text(0.5, 0.50, '⟶', ha='center', va='center',
                   fontsize=20, color='#aaaaaa',
                   transform=ax_lv.transAxes)
        ax_lv.text(0.5, 0.32,
                   f'{N_SEGS[level_a]:,} → {N_SEGS[level_b]:,} segm.',
                   ha='center', va='center', fontsize=9, color='#cccccc',
                   transform=ax_lv.transAxes)
        ax_lv.text(0.5, 0.14,
                   f'zoom-out {ZOOM_FACT:.2f}×',
                   ha='center', va='center', fontsize=8, color='#888888',
                   transform=ax_lv.transAxes)
    else:
        ax_lv.text(0.5, 0.72, f'L{level_a}', ha='center', va='center',
                   fontsize=48, fontweight='bold',
                   color=LV_COLOR[level_a], transform=ax_lv.transAxes)
        ax_lv.text(0.5, 0.50,
                   f'N = 24^{level_a}\n= {N_SEGS[level_a]:,}',
                   ha='center', va='center', fontsize=10, color='#dddddd',
                   transform=ax_lv.transAxes)
        ax_lv.text(0.5, 0.28,
                   f'ρ₀_eff = {RHO_0_EFF[level_a]:.4f}',
                   ha='center', va='center', fontsize=9, color='#aaaaaa',
                   transform=ax_lv.transAxes)
        ax_lv.text(0.5, 0.12,
                   f'DOF = {2*N_SEGS[level_a]:,}',
                   ha='center', va='center', fontsize=8, color='#777777',
                   transform=ax_lv.transAxes)

    # Bordo colorato
    for sp in ax_lv.spines.values():
        sp.set_edgecolor(LV_COLOR[level_a])
        sp.set_linewidth(2.5)

    # ── Timeline ρ̄(t) ─────────────────────────────────────────────────────────
    ax_t = fig.add_subplot(gs[1])
    ax_t.set_facecolor('#0d0d1a')
    for lv, (t_s, rho_s) in series_all.items():
        if len(t_s) > 0:
            ax_t.plot(t_s, rho_s, color=LV_COLOR[lv], lw=1.2,
                      label=f'L{lv}', alpha=0.9)
    ax_t.axvline(fr['t_planck'], color='#ff4466', lw=1.4)
    ax_t.set_xlabel('t [Planck]', fontsize=7, color='#aaaaaa')
    ax_t.set_ylabel('ρ̄', fontsize=7, color='#aaaaaa')
    ax_t.tick_params(labelsize=6, colors='#888888')
    ax_t.legend(fontsize=6, loc='lower right',
                framealpha=0.3, labelcolor='#cccccc')
    ax_t.set_facecolor('#0d0d1a')
    ax_t.spines['bottom'].set_color('#444444')
    ax_t.spines['left'].set_color('#444444')
    ax_t.spines['top'].set_visible(False)
    ax_t.spines['right'].set_visible(False)
    ax_t.grid(True, alpha=0.15, color='#444444')
    ax_t.set_title('ρ̄ (constraint density)', fontsize=7,
                   color='#aaaaaa', pad=2)

    # ── Info fisici ────────────────────────────────────────────────────────────
    ax_i = fig.add_subplot(gs[2])
    ax_i.set_facecolor('#0d0d1a')
    ax_i.axis('off')
    lines = [
        (f't = {fr["t_planck"]:.3f} Planck', '#cccccc', 10),
        (f'fase: {fr["phase"].upper()}', '#ff9944', 11),
        (f'ρ̄ = {fr["rho_mean"]:.4f}', '#aaddff', 10),
        (f'σ̄_VM = {fr["sigma_mean"]:.2f}', '#ffcc44', 9),
        (fr['S_lbl'] or '', '#888888', 8),
        ('',  '#ffffff', 6),
        ('isosuperfici ρ: 0.50 / 0.80', '#888888', 7),
        ('colore: κ_Ricci (coolwarm)', '#888888', 7),
        ('linee: campo K·t (ciano)', '#00d4ff', 7),
        ('glow: σ_VM (YlOrRd)', '#ffaa44', 7),
    ]
    y = 0.97
    for txt, col, fs in lines:
        if txt:
            ax_i.text(0.07, y, txt, transform=ax_i.transAxes,
                      fontsize=fs, color=col, va='top')
        y -= 0.095

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    hud = np.array(Image.open(buf).convert('RGB'))
    plt.close(fig)
    return hud


# ── Compositing ────────────────────────────────────────────────────────────────
def alpha_blend(img_a: np.ndarray, img_b: np.ndarray,
                alpha_a: float, alpha_b: float) -> np.ndarray:
    """Alpha-composite due frame RGB."""
    a = img_a.astype(np.float32)
    b = img_b.astype(np.float32)
    return np.clip(alpha_a * a + alpha_b * b, 0, 255).astype(np.uint8)


def assemble_frame(img_3d: np.ndarray, img_hud: np.ndarray,
                   target_h: int) -> np.ndarray:
    """Ridimensiona HUD all'altezza target e concatena orizzontalmente."""
    h3, w3 = img_3d.shape[:2]
    if h3 != target_h:
        img_3d = np.array(Image.fromarray(img_3d).resize(
            (int(w3 * target_h / h3), target_h), Image.LANCZOS))
    hh, hw = img_hud.shape[:2]
    if hh != target_h:
        img_hud = np.array(Image.fromarray(img_hud).resize(
            (int(hw * target_h / hh), target_h), Image.LANCZOS))
    return np.concatenate([img_3d, img_hud], axis=1)


# ── Main ──────────────────────────────────────────────────────────────────────
def make_volumetric_video(l1_path, l2_path, l3_path,
                          output='vqt_volumetric_L1_L2_L3.mp4',
                          fps: int = 6,
                          seg_frames: int = 5,
                          trans_frames: int = 8,
                          seed: int = 42):
    np.random.seed(seed)
    t0 = time.time()

    # ── Caricamento dati ──────────────────────────────────────────────────────
    print("Caricamento dati...")
    d1, s1 = load_level(l1_path, 1, max_frames=60)
    d2, s2 = load_level(l2_path, 2, max_frames=100)
    d3, s3 = load_level(l3_path, 3, max_frames=60)
    series_all = {1: (s1['t'], s1['rho']),
                  2: (s2['t'], s2['rho']),
                  3: (s3['t'], s3['rho'])}

    def pick(data, n):
        idxs = np.linspace(0, len(data)-1, n, dtype=int)
        return [data[i] for i in idxs]

    seg1 = pick(d1, seg_frames)
    seg2 = pick(d2, seg_frames)
    seg3 = pick(d3, seg_frames)

    # Azimuth globale continuo
    azim0     = 35.0
    azim_step = 3.5
    total_seg_frames = seg_frames * 3 + trans_frames * 2
    azimuths  = [azim0 + i * azim_step for i in range(total_seg_frames + trans_frames * 2)]

    ai = [0]
    def next_azim():
        a = azimuths[ai[0]]
        ai[0] += 1
        return a

    # ── Pre-render scene 3D ───────────────────────────────────────────────────
    n_renders = seg_frames * 3 + 2  # seg×3 + first_frame_L2 + first_frame_L3
    print(f"\nPre-rendering {n_renders} scene 3D PyVista "
          f"(stimato {n_renders*70//60}-{n_renders*120//60} min)...")

    renders_l1 = []
    print(f"\n[L1] {seg_frames} frame:")
    for i, fr in enumerate(seg1):
        az = next_azim()
        print(f"  L1 frame {i+1}/{seg_frames}  azim={az:.1f}°  ", end='')
        renders_l1.append(render_3d(fr, az, 1))
    azim_trans12 = azimuths[ai[0]]   # azimuth fisso per tutta la transizione L1→L2

    print(f"\n[Trans L1→L2] pre-render L2 frame 0 @ azim={azim_trans12:.1f}°  ", end='')
    render_l2_first = render_3d(seg2[0], azim_trans12, 2)
    ai[0] += trans_frames            # salta gli azimuth della transizione

    renders_l2 = []
    print(f"\n[L2] {seg_frames} frame:")
    for i, fr in enumerate(seg2):
        az = next_azim()
        print(f"  L2 frame {i+1}/{seg_frames}  azim={az:.1f}°  ", end='')
        renders_l2.append(render_3d(fr, az, 2))
    azim_trans23 = azimuths[ai[0]]

    print(f"\n[Trans L2→L3] pre-render L3 frame 0 @ azim={azim_trans23:.1f}°  ", end='')
    render_l3_first = render_3d(seg3[0], azim_trans23, 3)
    ai[0] += trans_frames

    renders_l3 = []
    print(f"\n[L3] {seg_frames} frame:")
    for i, fr in enumerate(seg3):
        az = next_azim()
        print(f"  L3 frame {i+1}/{seg_frames}  azim={az:.1f}°  ", end='')
        renders_l3.append(render_3d(fr, az, 3))

    print(f"\nPre-rendering completato in {(time.time()-t0)/60:.1f} min")

    # ── Assemblaggio video ────────────────────────────────────────────────────
    print(f"\nAssemblaggio video frames...")
    writer = imageio.get_writer(output, fps=fps, quality=9,
                                macro_block_size=None,
                                ffmpeg_params=['-pix_fmt', 'yuv420p', '-crf', '17'])

    def write_frame(img_3d, fr, la, lb, aa, ab, is_t):
        hud = render_hud(fr, la, lb, aa, ab, series_all, is_t)
        frm = assemble_frame(img_3d, hud, WIN_H)
        writer.append_data(frm)

    # Segmento L1
    for i, (fr, img) in enumerate(zip(seg1, renders_l1)):
        write_frame(img, fr, 1, 1, 1.0, 0.0, False)

    # Transizione L1→L2
    img_a = renders_l1[-1]
    img_b = render_l2_first
    for i in range(trans_frames):
        t       = i / max(trans_frames-1, 1)
        aa      = (1.0 - t) ** 1.5
        ab      = t ** 1.5
        blended = alpha_blend(img_a, img_b, aa, ab)
        # Camera dist interpolata: non visibile nel blend ma annotata nell'HUD
        write_frame(blended, seg2[0], 1, 2, aa, ab, True)

    # Segmento L2
    for i, (fr, img) in enumerate(zip(seg2, renders_l2)):
        write_frame(img, fr, 2, 2, 1.0, 0.0, False)

    # Transizione L2→L3
    img_a = renders_l2[-1]
    img_b = render_l3_first
    for i in range(trans_frames):
        t       = i / max(trans_frames-1, 1)
        aa      = (1.0 - t) ** 1.5
        ab      = t ** 1.5
        blended = alpha_blend(img_a, img_b, aa, ab)
        write_frame(blended, seg3[0], 2, 3, aa, ab, True)

    # Segmento L3
    for i, (fr, img) in enumerate(zip(seg3, renders_l3)):
        write_frame(img, fr, 3, 3, 1.0, 0.0, False)

    writer.close()
    total = (time.time() - t0) / 60
    n_frames = seg_frames*3 + trans_frames*2
    print(f"\nVideo salvato: {Path(output).resolve()}")
    print(f"Totale: {n_frames} frame, {n_frames/fps:.1f}s @ {fps}fps | {total:.1f} min")


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Video volumetrico VQT L1→L2→L3 con PyVista + linee di forza'
    )
    p.add_argument('--l1',           default='cosmo_L1_topo.h5')
    p.add_argument('--l2',           default='cosmo_L2_variational.h5')
    p.add_argument('--l3',           default='cosmo_L3_probe.h5')
    p.add_argument('--output', '-o', default='vqt_volumetric_L1_L2_L3.mp4')
    p.add_argument('--fps',          type=int, default=6)
    p.add_argument('--seg-frames',   type=int, default=5,
                   help='Frame per livello (= render PyVista unici per livello)')
    p.add_argument('--trans-frames', type=int, default=8,
                   help='Frame di cross-fade per transizione')
    p.add_argument('--seed',         type=int, default=42)
    return p.parse_args()


def main():
    args = parse_args()
    for attr, path in [('l1', args.l1), ('l2', args.l2), ('l3', args.l3)]:
        if not Path(path).exists():
            print(f"ERRORE: {path} non trovato (--{attr})")
            return 1
    make_volumetric_video(
        l1_path=args.l1, l2_path=args.l2, l3_path=args.l3,
        output=args.output, fps=args.fps,
        seg_frames=args.seg_frames, trans_frames=args.trans_frames,
        seed=args.seed,
    )
    return 0

if __name__ == '__main__':
    sys.exit(main())
