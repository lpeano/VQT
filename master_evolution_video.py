#!/usr/bin/env python3
"""
master_evolution_video.py — Visualizzazione Frattale Multi-Scala VQT

Sequenza animata:
  [L1]  N=24    (sparse) → Super-Zoom L1→L2 (cross-fade + zoom-out 2.88×)
  [L2]  N=576   (medio)  → Super-Zoom L2→L3 (cross-fade + zoom-out 2.88×)
  [L3]  N=13824 (denso)  → rotazione finale

Effetti:
  - Centratura CoM: ogni livello traslato all'origine
  - Scaling inverso: manifold occupa sempre lo stesso volume apparente
  - Cross-fade geometrico: alpha L(n) 1→0 mentre L(n+1) 0→1
  - Camera Super-Zoom: zoom-out sincronizzato con 24^(1/3)≈2.88×
  - HUD multi-scala: aggiornamento dinamico di L, N, ρ₀_eff
  - Colormap coerente: plasma per ρ, coolwarm per κ_Ricci (stesso range fisico)

Uso:
    python -X utf8 master_evolution_video.py
    python -X utf8 master_evolution_video.py --l1 cosmo_L1_topo.h5 --l2 cosmo_L2_variational.h5 --l3 cosmo_L3_probe.h5
    python -X utf8 master_evolution_video.py --fps 12 --seg-frames 20 --trans-frames 15
"""

import argparse, sys, time
from pathlib import Path

import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib import colors as mcolors
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

# ── Costanti fisiche ───────────────────────────────────────────────────────────
RHO_0, LAMBDA, GAMMA = 0.85, 0.2, 0.05
ZOOM_FACTOR = 24 ** (1/3)        # ≈ 2.884 per ogni livello frattale
RHO_0_EFF   = {1: 0.860, 2: 0.852, 3: 0.850}   # Legge FA [Eq. FA-2]
N_SEGMENTS  = {1: 24, 2: 576, 3: 13824}
LAMBDA_VALS = {1: 0.2, 2: 0.2, 3: 0.2}

# ── Palette colori coerente ────────────────────────────────────────────────────
CMAP_RHO   = 'plasma'
CMAP_KAPPA = 'coolwarm'
COLOR_TORS = '#00ccff'
COLOR_HOT  = '#ff3333'
BG_COLOR   = '#f9f9f9'
PANEL_BG   = '#f0f0f0'

LEVEL_COLORS = {1: '#3a86ff', 2: '#8338ec', 3: '#ff006e'}   # colori identità livello


# ── Fisica ────────────────────────────────────────────────────────────────────
def compute_rho_i(tau, K):
    tau_range = float(np.max(tau) - np.min(tau))
    f_cl = (np.ones(len(tau)) if tau_range < 1e-12
            else 1.0 - np.abs(tau - np.mean(tau)) / tau_range)
    K2     = K ** 2
    K2_bar = max(float(np.mean(K2)), 1e-12)
    Omega  = K2 * np.roll(K2, -1)
    return np.clip(0.5 * f_cl + 0.5 / (1.0 + Omega / K2_bar), 0.0, 1.0)


def sigma_vm(vel, K, rho):
    K2    = K**2
    K2b   = max(float(np.mean(K2)), 1e-12)
    Omega = K2 * np.roll(K2, -1)
    T_tt  = 0.5*vel**2 + LAMBDA*(rho - RHO_0)**2 + GAMMA*Omega
    T_xx  = 0.5*K2    + GAMMA*Omega
    return np.abs(T_xx - T_tt)


def torsion_vectors(pos, K):
    t = np.empty_like(pos)
    t[1:-1] = pos[2:]  - pos[:-2]
    t[0]    = pos[1]   - pos[0]
    t[-1]   = pos[-1]  - pos[-2]
    n = np.linalg.norm(t, axis=1, keepdims=True)
    t /= np.where(n < 1e-12, 1.0, n)
    return t * K[:, None]


# ── Caricamento e normalizzazione ──────────────────────────────────────────────
def load_level(h5_path, level: int, max_frames: int = 60):
    """
    Carica dataset HDF5, centra al CoM, scala per livello.

    Restituisce lista di dict con dati pre-calcolati:
      pos_n:   posizioni normalizzate (centrate + scalate)
      rho:     densità di vincolo
      torsion: vettori K·t (N,3)
      hot:     maschera top-10% torsione
      rho_mean, sigma_mean, t_planck, phase
    """
    with h5py.File(h5_path, 'r') as f:
        fkeys  = sorted(f['frames'].keys(), key=lambda x: int(x.split('_')[1]))
        fkeys  = fkeys[:max_frames]
        tv     = f['topological_validation']
        t_arr  = tv['time'][:].astype(float)
        rho_arr= tv['mean_constraint_density'][:].astype(float)
        phase_arr = [p.decode() if isinstance(p, bytes) else p
                     for p in tv['phase_label'][:]]
        save_int = max(1, len(t_arr) // max(1, len(fkeys)))

        S_arr = None
        if 'variational_force' in f:
            Sr = f['variational_force']['potential_S'][:].astype(float)
            n  = len(t_arr)
            S_arr = Sr[1::2][:n] if len(Sr) >= 2*n else Sr[:n]

        frames_raw = []
        for fk in fkeys:
            g = f['frames'][fk]
            frames_raw.append({
                'pos': g['positions'][:].astype(float),
                'K':   g['contorsione_locale'][:].astype(float),
                'tau': g['tau_locale'][:].astype(float),
                'vel': g['velocities'][:].astype(float),
            })

    print(f"  L{level}: {len(frames_raw)} frame caricati da {h5_path}")

    # Calcola CoM e bbox globale (su tutti i frame) per normalizzazione stabile
    all_pos = np.concatenate([fr['pos'] for fr in frames_raw], axis=0)
    com_global  = all_pos.mean(0)
    span_global = np.abs(all_pos - com_global).max()          # metà lato bbox
    scale_norm  = 1.0 / (span_global + 1e-10)                  # → [-1,1]
    # Scala corretta per livello: L1 occupa stesso volume di L2/L3
    # (tutti normalizzati a ±1, poi il renderer usa dist camera per zoom)

    out = []
    for i, fr in enumerate(frames_raw):
        pos_c  = fr['pos'] - com_global                         # centra CoM
        pos_n  = pos_c * scale_norm                             # normalizza [-1,1]
        K      = fr['K']
        rho    = compute_rho_i(fr['tau'], K)
        tor    = torsion_vectors(pos_n, K)
        K_abs  = np.abs(K)
        hot    = K_abs > np.percentile(K_abs, 90)
        ti     = min(i * save_int + save_int - 1, len(t_arr) - 1)
        svm    = sigma_vm(fr['vel'], K, rho)
        S_lbl  = (f"  S/N={S_arr[ti]/len(K):.2f}" if S_arr is not None else "")
        out.append({
            'pos_n':      pos_n,
            'K':          K,
            'rho':        rho,
            'torsion':    tor,
            'hot':        hot,
            'K_abs':      K_abs,
            'rho_mean':   rho.mean(),
            'sigma_mean': svm.mean(),
            't_planck':   t_arr[ti],
            'phase':      phase_arr[ti],
            'S_lbl':      S_lbl,
            'level':      level,
        })

    # Pre-calcola serie temporali per HUD
    series = {
        't':      t_arr[:len(fkeys)*save_int:save_int][:len(fkeys)],
        'rho':    rho_arr[:len(fkeys)*save_int:save_int][:len(fkeys)],
    }
    return out, series, scale_norm


# ── Rendering di un manifold su assi 3D ───────────────────────────────────────
def draw_manifold(ax, fr: dict, alpha: float,
                  quiver_n: int = 80, scale_q: float = 0.08,
                  vmin_r: float = 0.0, vmax_r: float = 1.0):
    """
    Disegna scatter ρ + quiver torsione su assi 3D matplotlib.
    alpha controlla la trasparenza globale (usato per cross-fade).
    """
    pos   = fr['pos_n']
    rho   = fr['rho']
    tor   = fr['torsion']
    hot   = fr['hot']
    K_abs = fr['K_abs']
    N     = len(pos)

    # Scatter principale colorato per ρ
    sz = 6 + rho * 18
    ax.scatter(pos[:, 0], pos[:, 1], pos[:, 2],
               c=rho, cmap=CMAP_RHO, vmin=vmin_r, vmax=vmax_r,
               s=sz, alpha=alpha * 0.75, linewidths=0, zorder=2)

    # Quiver torsione: campionamento proporzionale a |K|
    K_prob = K_abs / (K_abs.sum() + 1e-10)
    n_q    = min(quiver_n, N)
    idx_q  = np.random.choice(N, n_q, replace=False, p=K_prob)
    K_p99  = float(np.percentile(K_abs, 99)) + 1e-10
    uvw    = tor[idx_q]
    sc     = scale_q / (K_p99 + 1e-10)
    ax.quiver(pos[idx_q, 0], pos[idx_q, 1], pos[idx_q, 2],
              uvw[:, 0]*sc, uvw[:, 1]*sc, uvw[:, 2]*sc,
              color=COLOR_TORS, linewidth=0.9, arrow_length_ratio=0.30,
              alpha=alpha * 0.85, zorder=3)

    # Punti ad alta torsione in rosso
    if hot.any():
        ax.scatter(pos[hot, 0], pos[hot, 1], pos[hot, 2],
                   c=COLOR_HOT, s=22, alpha=alpha * 0.95,
                   linewidths=0.4, edgecolors='white', zorder=4)


# ── HUD testuale ──────────────────────────────────────────────────────────────
def hud_lines(fr: dict, alpha_from: float = 1.0, fr_next: dict = None,
              alpha_to: float = 0.0) -> str:
    """Testo HUD con blend durante la transizione."""
    L    = fr['level']
    N    = N_SEGMENTS[L]
    r0   = RHO_0_EFF.get(L, 0.85)
    lam  = LAMBDA_VALS.get(L, 0.2)
    lines = [
        f"Livello frattale:  L{L}   →   N = 24^{L} = {N:,}",
        f"λ = {lam:.2f}   γ = {GAMMA:.2f}   ρ₀_eff(L{L}) = {r0:.4f}",
        f"t = {fr['t_planck']:.3f} Planck     fase: {fr['phase']}",
        f"ρ̄ = {fr['rho_mean']:.4f}     σ̄_VM = {fr['sigma_mean']:.2f}{fr['S_lbl']}",
    ]
    if fr_next is not None and alpha_to > 0.05:
        L2_next = fr_next['level']
        lines.append(
            f"\n→ Super-Zoom L{L}→L{L2_next}: "
            f"zoom-out {ZOOM_FACTOR:.2f}×   "
            f"N: {N:,} → {N_SEGMENTS[L2_next]:,}"
        )
    return '\n'.join(lines)


# ── Costruzione sequenza frame ─────────────────────────────────────────────────
def build_sequence(data_l1, data_l2, data_l3,
                   seg_frames: int, trans_frames: int) -> list:
    """
    Costruisce la lista ordinata di 'event' per ogni frame del video.

    Ogni evento è un dict:
      type:       'level' | 'transition'
      fr_a:       frame dati corrente (livello A)
      fr_b:       frame dati livello B (solo per 'transition')
      alpha_a:    opacità A
      alpha_b:    opacità B
      azim:       azimuth camera
      dist:       distanza camera (zoom)
      level_a, level_b
    """
    def pick_frames(data, n):
        """Seleziona n frame equidistanti."""
        idxs = np.linspace(0, len(data)-1, n, dtype=int)
        return [data[i] for i in idxs]

    seq = []
    azim_base = 30.0
    azim_step = 2.5

    # Distanza camera per livello (L1: vicino, L3: lontano)
    dist_l  = {1: 7.0, 2: 9.5, 3: 13.0}
    frame_l = {1: pick_frames(data_l1, seg_frames),
               2: pick_frames(data_l2, seg_frames),
               3: pick_frames(data_l3, min(seg_frames, len(data_l3)))}

    total_anim_idx = [0]

    def add_segment(level, frames_list):
        d    = dist_l[level]
        for i, fr in enumerate(frames_list):
            azim = azim_base + total_anim_idx[0] * azim_step
            seq.append({'type': 'level',
                        'fr_a': fr, 'fr_b': None,
                        'alpha_a': 1.0, 'alpha_b': 0.0,
                        'azim': azim, 'dist': d,
                        'level_a': level, 'level_b': level})
            total_anim_idx[0] += 1

    def add_transition(level_from, level_to, frames_a, frames_b):
        d_start = dist_l[level_from]
        d_end   = dist_l[level_to]
        fr_a    = frames_a[-1]     # ultimo frame del livello uscente
        fr_b    = frames_b[0]      # primo frame del livello entrante
        for i in range(trans_frames):
            t = i / (trans_frames - 1)
            alpha_a = 1.0 - t                    # ease-in
            alpha_a = alpha_a ** 1.5             # curva non lineare (ease-in)
            alpha_b = t ** 1.5
            dist_i  = d_start + (d_end - d_start) * t
            azim    = azim_base + total_anim_idx[0] * azim_step
            seq.append({'type': 'transition',
                        'fr_a': fr_a, 'fr_b': fr_b,
                        'alpha_a': alpha_a, 'alpha_b': alpha_b,
                        'azim': azim, 'dist': dist_i,
                        'level_a': level_from, 'level_b': level_to})
            total_anim_idx[0] += 1

    # Segmento L1
    add_segment(1, frame_l[1])
    # Transizione L1→L2
    add_transition(1, 2, frame_l[1], frame_l[2])
    # Segmento L2
    add_segment(2, frame_l[2])
    # Transizione L2→L3
    add_transition(2, 3, frame_l[2], frame_l[3])
    # Segmento L3
    add_segment(3, frame_l[3])

    return seq


# ── Main ──────────────────────────────────────────────────────────────────────
def make_master_video(l1_path, l2_path, l3_path,
                      output='vqt_master_evolution.mp4',
                      fps: int = 10,
                      seg_frames: int = 18,
                      trans_frames: int = 12,
                      quiver_n: int = 80,
                      dpi: int = 120,
                      seed: int = 42):
    np.random.seed(seed)
    t0 = time.time()

    # ── Caricamento dati ──────────────────────────────────────────────────────
    print("Caricamento dati per tutti i livelli...")
    data_l1, series_l1, sc1 = load_level(l1_path,  1, max_frames=60)
    data_l2, series_l2, sc2 = load_level(l2_path,  2, max_frames=100)
    data_l3, series_l3, sc3 = load_level(l3_path,  3, max_frames=60)

    print(f"  Dati caricati in {time.time()-t0:.1f}s")

    # ── Sequenza animazione ───────────────────────────────────────────────────
    seq = build_sequence(data_l1, data_l2, data_l3, seg_frames, trans_frames)
    total_frames = len(seq)
    print(f"Sequenza: {total_frames} frame totali "
          f"(L1×{seg_frames} + trans×{trans_frames} + L2×{seg_frames} + trans×{trans_frames} + L3×{seg_frames})")

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 8.5), facecolor=BG_COLOR)
    gs  = gridspec.GridSpec(2, 3, figure=fig,
                            height_ratios=[5, 1],
                            width_ratios=[4, 1.5, 1.5],
                            hspace=0.06, wspace=0.18,
                            left=0.03, right=0.98,
                            top=0.92, bottom=0.06)

    ax3d   = fig.add_subplot(gs[0, 0], projection='3d')
    ax_lv  = fig.add_subplot(gs[0, 1])   # indicatore livello + info
    ax_hud = fig.add_subplot(gs[0, 2])   # ρ̄(t) strip per livello corrente
    ax_r   = fig.add_subplot(gs[1, 0])   # timeline globale
    ax_s   = fig.add_subplot(gs[1, 1])   # σ_VM(t) strip
    ax_sl  = fig.add_subplot(gs[1, 2])   # vuoto / livelli label

    ax3d.set_facecolor('#ebebeb')
    for ax_ in [ax_lv, ax_hud, ax_r, ax_s, ax_sl]:
        ax_.set_facecolor(PANEL_BG)

    # HUD striscia ρ̄: prepara serie concatenata
    # Costruisce timeline globale (normalizzata su t_Planck)
    t_l1 = series_l1['t'];    rho_l1 = series_l1['rho']
    t_l2 = series_l2['t'];    rho_l2 = series_l2['rho']
    t_l3_arr = series_l3['t'] if len(series_l3['t']) > 1 else np.array([0.0, 0.06])
    rho_l3_arr= series_l3['rho'] if len(series_l3['rho']) > 1 else np.array([data_l3[0]['rho_mean']]*2)

    ax_r.plot(t_l1, rho_l1, color=LEVEL_COLORS[1], lw=1.3, label='L1')
    ax_r.plot(t_l2, rho_l2, color=LEVEL_COLORS[2], lw=1.3, label='L2')
    ax_r.plot(t_l3_arr, rho_l3_arr, color=LEVEL_COLORS[3], lw=1.3, label='L3')
    ax_r.set_ylabel('ρ̄', fontsize=7)
    ax_r.set_xlabel('t [Planck]', fontsize=7)
    ax_r.tick_params(labelsize=6)
    ax_r.grid(True, alpha=0.3)
    ax_r.legend(fontsize=6, loc='lower right', framealpha=0.7)
    vl_r = ax_r.axvline(0, color='red', lw=1.2)

    ax_sl.axis('off')

    title_txt = fig.suptitle('', fontsize=10, fontweight='bold', color='#111111')

    print(f"Rendering {total_frames} frame → {output} ...")

    def update(fidx):
        ev   = seq[fidx]
        fr_a = ev['fr_a']
        fr_b = ev['fr_b']
        La   = ev['level_a']
        Lb   = ev['level_b']
        a_a  = ev['alpha_a']
        a_b  = ev['alpha_b']
        dist = ev['dist']
        azim = ev['azim']

        # ── 3D ────────────────────────────────────────────────────────────────
        ax3d.cla()
        ax3d.set_facecolor('#ebebeb')
        ax3d.set_axis_off()

        draw_manifold(ax3d, fr_a, alpha=a_a, quiver_n=quiver_n)
        if fr_b is not None and a_b > 0.02:
            draw_manifold(ax3d, fr_b, alpha=a_b, quiver_n=quiver_n)

        ax3d.set_xlim(-1.1, 1.1)
        ax3d.set_ylim(-1.1, 1.1)
        ax3d.set_zlim(-1.1, 1.1)
        ax3d.dist = dist
        ax3d.view_init(elev=28, azim=azim)

        # Titolo pannello 3D con scala
        is_trans = ev['type'] == 'transition'
        if is_trans:
            ax3d.set_title(
                f'Super-Zoom L{La} → L{Lb}  '
                f'(N: {N_SEGMENTS[La]:,} → {N_SEGMENTS[Lb]:,}  '
                f'{ZOOM_FACTOR:.2f}× zoom-out)',
                fontsize=8, pad=3, color='#333333'
            )
        else:
            ax3d.set_title(
                f'L{La}  N={N_SEGMENTS[La]:,}  '
                f't={fr_a["t_planck"]:.3f} Planck  '
                f'fase: {fr_a["phase"]}',
                fontsize=8, pad=3, color=LEVEL_COLORS[La]
            )

        # ── Pannello indicatore livello ────────────────────────────────────────
        ax_lv.cla()
        ax_lv.set_facecolor(PANEL_BG)
        ax_lv.axis('off')

        if is_trans:
            # Mostra entrambi i livelli con alpha blend
            ax_lv.text(0.5, 0.80, f'L{La}', ha='center', va='center',
                       fontsize=48, fontweight='bold',
                       color=LEVEL_COLORS[La], alpha=a_a,
                       transform=ax_lv.transAxes)
            ax_lv.text(0.5, 0.80, f'L{Lb}', ha='center', va='center',
                       fontsize=48, fontweight='bold',
                       color=LEVEL_COLORS[Lb], alpha=a_b,
                       transform=ax_lv.transAxes)
            ax_lv.text(0.5, 0.55, '↓', ha='center', va='center',
                       fontsize=28, color='#666666',
                       transform=ax_lv.transAxes)
            ax_lv.text(0.5, 0.38,
                       f'N: {N_SEGMENTS[La]:,} → {N_SEGMENTS[Lb]:,}\n'
                       f'DOF: {2*N_SEGMENTS[La]:,} → {2*N_SEGMENTS[Lb]:,}',
                       ha='center', va='center', fontsize=10,
                       color='#444444', transform=ax_lv.transAxes)
            ax_lv.text(0.5, 0.18,
                       f'zoom-out {ZOOM_FACTOR:.2f}×\ncamera dist {dist:.1f}',
                       ha='center', va='center', fontsize=9, color='#888888',
                       transform=ax_lv.transAxes)
        else:
            N_cur = N_SEGMENTS[La]
            ax_lv.text(0.5, 0.75, f'L{La}', ha='center', va='center',
                       fontsize=56, fontweight='bold',
                       color=LEVEL_COLORS[La],
                       transform=ax_lv.transAxes)
            ax_lv.text(0.5, 0.52,
                       f'N = 24^{La} = {N_cur:,}',
                       ha='center', va='center', fontsize=11,
                       color='#333333', transform=ax_lv.transAxes)
            ax_lv.text(0.5, 0.38,
                       f'DOF = {2*N_cur:,}',
                       ha='center', va='center', fontsize=10,
                       color='#555555', transform=ax_lv.transAxes)
            ax_lv.text(0.5, 0.23,
                       f'ρ₀_eff = {RHO_0_EFF.get(La, 0.85):.4f}',
                       ha='center', va='center', fontsize=10,
                       color='#666666', transform=ax_lv.transAxes)
            ax_lv.text(0.5, 0.10,
                       f'λ = {LAMBDA_VALS[La]:.2f}   γ = {GAMMA:.2f}',
                       ha='center', va='center', fontsize=9,
                       color='#888888', transform=ax_lv.transAxes)

        # Bordo colorato
        for spine in ax_lv.spines.values():
            spine.set_edgecolor(LEVEL_COLORS[La if not is_trans else Lb])
            spine.set_linewidth(2.5)

        # ── Pannello ρ̄ + σ_VM del frame corrente ──────────────────────────────
        ax_hud.cla()
        ax_hud.set_facecolor(PANEL_BG)
        ax_hud.axis('off')
        info = [
            f"ρ̄  = {fr_a['rho_mean']:.4f}",
            f"σ̄_VM = {fr_a['sigma_mean']:.2f}",
            f"{fr_a['phase'].upper()}",
            f"t = {fr_a['t_planck']:.3f} P",
            fr_a['S_lbl'].strip() or '',
        ]
        for li, txt in enumerate(info):
            col = '#111111'
            fs  = 11
            if li == 2:   col = '#cc4400';  fs = 13
            ax_hud.text(0.08, 0.85 - li*0.18, txt,
                        transform=ax_hud.transAxes,
                        fontsize=fs, color=col, va='top')

        ax_s.cla()
        ax_s.set_facecolor(PANEL_BG)
        # Piccolo indicatore σ_VM
        ax_s.barh(0, fr_a['sigma_mean'], color=LEVEL_COLORS[La],
                  alpha=0.7, height=0.6)
        ax_s.set_xlim(0, 800)
        ax_s.set_yticks([])
        ax_s.set_xlabel('σ̄_VM', fontsize=7)
        ax_s.tick_params(labelsize=6)

        # ── Timeline vline ────────────────────────────────────────────────────
        vl_r.set_xdata([fr_a['t_planck'], fr_a['t_planck']])

        # ── Titolo globale ─────────────────────────────────────────────────────
        if is_trans:
            title = (f"VQT Master Evolution — Super-Zoom L{La}→L{Lb} "
                     f"[N: {N_SEGMENTS[La]:,}→{N_SEGMENTS[Lb]:,}] "
                     f"zoom-out {ZOOM_FACTOR:.2f}×")
        else:
            title = (f"VQT Master Evolution — L{La} "
                     f"N={N_SEGMENTS[La]:,}  DOF={2*N_SEGMENTS[La]:,}  "
                     f"t={fr_a['t_planck']:.3f} Planck  ρ̄={fr_a['rho_mean']:.4f}")
        title_txt.set_text(title)

        return []

    anim = FuncAnimation(fig, update,
                         frames=total_frames,
                         interval=1000 // fps,
                         blit=False)

    writer = FFMpegWriter(fps=fps, bitrate=3000,
                          extra_args=['-pix_fmt', 'yuv420p', '-crf', '18'])
    anim.save(output, writer=writer, dpi=dpi)
    plt.close(fig)

    elapsed = time.time() - t0
    print(f"\nVideo salvato: {Path(output).resolve()}")
    print(f"Durata video: {total_frames/fps:.1f}s   Tempo render: {elapsed:.0f}s")


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Visualizzazione Frattale Multi-Scala VQT L1→L2→L3'
    )
    p.add_argument('--l1',          default='cosmo_L1_topo.h5')
    p.add_argument('--l2',          default='cosmo_L2_variational.h5')
    p.add_argument('--l3',          default='cosmo_L3_probe.h5')
    p.add_argument('--output','-o', default='vqt_master_evolution.mp4')
    p.add_argument('--fps',         type=int,   default=10)
    p.add_argument('--seg-frames',  type=int,   default=18,
                   help='Frame per segmento di ciascun livello')
    p.add_argument('--trans-frames',type=int,   default=12,
                   help='Frame per ogni transizione Super-Zoom')
    p.add_argument('--quiver',      type=int,   default=80,
                   help='Numero max frecce torsione per frame')
    p.add_argument('--dpi',         type=int,   default=120)
    p.add_argument('--seed',        type=int,   default=42)
    return p.parse_args()


def main():
    args = parse_args()
    for attr, path in [('l1', args.l1), ('l2', args.l2), ('l3', args.l3)]:
        if not Path(path).exists():
            print(f"ERRORE: file {path} non trovato (--{attr}={path})")
            return 1
    make_master_video(
        l1_path=args.l1, l2_path=args.l2, l3_path=args.l3,
        output=args.output,
        fps=args.fps,
        seg_frames=args.seg_frames,
        trans_frames=args.trans_frames,
        quiver_n=args.quiver,
        dpi=args.dpi,
        seed=args.seed,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
