#!/usr/bin/env python3
"""
manifold_continuum.py — Visualizzazione continua del manifold VQT
con tensore di stress-energia τ_μν e curvatura di Ricci discreta.

=== Derivazione di τ_μν per L2 ===

Il sistema VQT è un campo scalare χ su un reticolo 1D (ring di N segmenti)
immerso in ℝ³. La densità Lagrangiana al sito i è:

  L_i = ½v_i² − V_Leech,i − λ(ρ_i − ρ_0)² − γΩ_i

dove ∂_t χ_i = v_i,  ∂_x χ_i ≈ K_i = (χ_{i+1} − χ_{i−1})/2  [Eq. T-1]

Per il teorema di Noether (invarianza traslazionale), il tensore canonico è:

  T_{tt,i} = ½v_i²  +  λ(ρ_i − ρ_0)²  +  γΩ_i       [densità di energia]
  T_{xx,i} = ½K_i²  +  γΩ_i                            [stress di torsione]
  T_{tx,i} = T_{xt,i} = v_i · K_i · ρ_i               [flusso di momento]

Questi definiscono τ_μν (2×2) al sito i. La proiezione in ℝ³ lungo il vettore
tangente locale t_i = (pos_{i+1} − pos_{i−1})/‖…‖ dà il tensore 3D:

  τ^3D_{μν,i} = T_{tt,i}(δ_{μν} − t_{iμ}t_{iν}) + T_{xx,i} t_{iμ}t_{iν}

Autovalori: λ_⊥ = T_{tt,i} (×2, piano trasversale),  λ_∥ = T_{xx,i} (long.)

Stress di von Mises (misura dell'anisotropia / "strain" topologico):
  σ_VM,i = |T_{xx,i} − T_{tt,i}|

Curvatura di Ricci discreta (angolo deficit nell'embedding 3D):
  κ_i = 1 − cos(θ_i),  dove θ_i = angle(e_{i−1}, e_{i+1})
       e_i = pos_{i+1} − pos_i   (vettore arco)

Comportamento critico a L→L3:
  - T_{tt} scala come H/N ≈ 257 (vs 244 a L2): +5% pressure isotropa
  - σ_VM cresce ∝ N^α (α > 1): stress anisotropo super-estensivo
  - κ_i mostra defasamento (modo quantizzato a 144°): la curvatura locale
    oscilla in fase con ε_closure, indicando che il manifold si "ripiega"
    periodicamente sotto l'effetto del potenziale S.

Uso:
    python -X utf8 manifold_continuum.py cosmo_L2_variational.h5
    python -X utf8 manifold_continuum.py cosmo_L2_variational.h5 --frame 50 --grid 80
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
from matplotlib import colors as mcolors
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import gaussian_filter


# ─── Parametri fisici ─────────────────────────────────────────────────────────

RHO_0   = 0.85
LAMBDA  = 0.2
GAMMA   = 0.05


# ─── Formule topologiche ──────────────────────────────────────────────────────

def compute_rho_i(tau: np.ndarray, K: np.ndarray) -> np.ndarray:
    tau_range = float(np.max(tau) - np.min(tau))
    f_cl = (np.ones(len(tau)) if tau_range < 1e-12
            else 1.0 - np.abs(tau - np.mean(tau)) / tau_range)
    K2 = K ** 2
    K2_bar = max(float(np.mean(K2)), 1e-12)
    Omega = K2 * np.roll(K2, -1)
    f_dt = 1.0 / (1.0 + Omega / K2_bar)
    return np.clip(0.5 * f_cl + 0.5 * f_dt, 0.0, 1.0)


# ─── Tensore di stress-energia τ_μν ──────────────────────────────────────────

def compute_stress_tensor(pos, K, tau, vel) -> dict:
    """
    Calcola τ_μν per ogni sito i.

    Restituisce:
      T_tt  : densità di energia (N,)
      T_xx  : stress di torsione (N,)
      T_tx  : flusso di momento (N,)
      sigma_VM : stress di von Mises (N,)  — misura di anisotropia
      trace : Tr(τ) = T_tt + T_xx (N,)
      det   : Det(τ) = T_tt*T_xx - T_tx² (N,) — invariante topologico
      tangent3d : vettore tangente locale in ℝ³ (N,3)
    """
    N = len(K)
    rho = compute_rho_i(tau, K)
    K2 = K ** 2
    K2_bar = max(float(np.mean(K2)), 1e-12)
    Omega = K2 * np.roll(K2, -1)

    T_tt = 0.5 * vel**2  +  LAMBDA * (rho - RHO_0)**2  +  GAMMA * Omega
    T_xx = 0.5 * K2      +  GAMMA * Omega
    T_tx = vel * K * rho

    sigma_VM = np.abs(T_xx - T_tt)   # |λ_∥ − λ_⊥|
    trace    = T_tt + T_xx
    det      = T_tt * T_xx - T_tx**2

    # Tangente locale in ℝ³ (forward per il boundary)
    tang = np.empty_like(pos)
    tang[1:-1] = pos[2:] - pos[:-2]
    tang[0]    = pos[1] - pos[0]
    tang[-1]   = pos[-1] - pos[-2]
    nrm = np.linalg.norm(tang, axis=1, keepdims=True)
    tang /= np.where(nrm < 1e-12, 1.0, nrm)

    return dict(T_tt=T_tt, T_xx=T_xx, T_tx=T_tx,
                sigma_VM=sigma_VM, trace=trace, det=det,
                tangent3d=tang, rho=rho, Omega=Omega)


# ─── Curvatura di Ricci discreta ──────────────────────────────────────────────

def compute_ricci(pos: np.ndarray) -> np.ndarray:
    """
    Curvatura di Ricci discreta κ_i = 1 − cos(θ_i).
    θ_i = angolo tra vettore arco entrante e uscente al sito i.
    κ > 0: curva verso l'interno (ellittico),  κ < 0: curva verso l'esterno.
    """
    e_in  = pos - np.roll(pos, 1, axis=0)   # arco entrante (i-1 → i)
    e_out = np.roll(pos, -1, axis=0) - pos   # arco uscente  (i → i+1)
    n_in  = np.linalg.norm(e_in,  axis=1, keepdims=True)
    n_out = np.linalg.norm(e_out, axis=1, keepdims=True)
    e_in  /= np.where(n_in  < 1e-12, 1.0, n_in)
    e_out /= np.where(n_out < 1e-12, 1.0, n_out)
    cos_theta = np.clip(np.sum(e_in * e_out, axis=1), -1.0, 1.0)
    return 1.0 - cos_theta   # 0 = linea retta, 2 = U-turn


# ─── Interpolazione continua (RBF) ────────────────────────────────────────────

def interpolate_to_grid(pos, values_dict, grid_res=80):
    """
    Interpola campi scalari da N punti discreti a una griglia grid_res³.
    Usa RBFInterpolator (thin-plate spline) — aumenta la risoluzione di
    grid_res³ / N ≈ 80³/576 ≈ 889× (quasi 3 ordini di grandezza).

    Restituisce (grid_xyz, interp_fields) dove:
      grid_xyz : tuple (X, Y, Z) di shape (G, G, G)
      interp_fields : dict name -> ndarray (G, G, G)
    """
    lo = pos.min(axis=0) - 1.0
    hi = pos.max(axis=0) + 1.0
    ax = [np.linspace(lo[k], hi[k], grid_res) for k in range(3)]
    Xg, Yg, Zg = np.meshgrid(*ax, indexing='ij')
    query_pts = np.column_stack([Xg.ravel(), Yg.ravel(), Zg.ravel()])

    interp_fields = {}
    for name, vals in values_dict.items():
        rbf = RBFInterpolator(pos, vals, kernel='thin_plate_spline', degree=1,
                              smoothing=len(pos) * 0.05)
        interp_fields[name] = rbf(query_pts).reshape(grid_res, grid_res, grid_res)

    return (Xg, Yg, Zg), interp_fields


# ─── Streamlines 2D per slice ─────────────────────────────────────────────────

def compute_streamline_slice(pos, K, tang3d, grid_res=80, z_frac=0.5):
    """
    Costruisce il campo vettoriale K·tangente proiettato sulla slice Z=z_frac
    per visualizzare le streamlines della torsione chirale.
    Restituisce (x1d, y1d, U, V) pronti per ax.streamplot.
    """
    lo = pos.min(axis=0)
    hi = pos.max(axis=0)
    z_val = lo[2] + z_frac * (hi[2] - lo[2])
    z_tol = (hi[2] - lo[2]) * 0.15   # banda di tolleranza

    mask = np.abs(pos[:, 2] - z_val) < z_tol
    if mask.sum() < 4:
        mask = np.ones(len(pos), dtype=bool)

    pts2d = pos[mask, :2]
    K_abs  = np.abs(K[mask])
    tang2d = tang3d[mask, :2]
    # Normalizza in [0,1] ma mantieni il segno di K
    K_signed = K[mask]
    uvec = tang2d * K_signed[:, None]

    x1d = np.linspace(lo[0], hi[0], grid_res)
    y1d = np.linspace(lo[1], hi[1], grid_res)
    Xg, Yg = np.meshgrid(x1d, y1d, indexing='xy')
    flat = np.column_stack([Xg.ravel(), Yg.ravel()])

    from scipy.interpolate import RBFInterpolator
    rbf_u = RBFInterpolator(pts2d, uvec[:, 0], kernel='linear', smoothing=5.0)
    rbf_v = RBFInterpolator(pts2d, uvec[:, 1], kernel='linear', smoothing=5.0)
    U = rbf_u(flat).reshape(grid_res, grid_res)
    V = rbf_v(flat).reshape(grid_res, grid_res)
    return x1d, y1d, U, V


# ─── Plot principale ──────────────────────────────────────────────────────────

def plot_continuum(hdf5_path, frame_idx=50, grid_res=80, output=None, dpi=140):
    """
    Figura a 6 pannelli:
      [0,0] 3D scatter: colore=curvatura Ricci  κ_i
      [0,1] 3D scatter: colore=von Mises σ_VM (anisotropia stress)
      [0,2] 3D scatter: colore=ρ_i (densità vincolo)
      [1,0] Slice XY con streamlines del campo K·t + sfondo σ_VM interpolato
      [1,1] Slice XY con sfondo ρ interpolato + overlay κ contours
      [1,2] Istogrammi τ_μν: T_tt, T_xx, T_tx, σ_VM
    """
    path = Path(hdf5_path)
    with h5py.File(path, 'r') as f:
        frame_keys = sorted(f['frames'].keys(), key=lambda x: int(x.split('_')[1]))
        fi = min(frame_idx, len(frame_keys) - 1)
        g = f['frames'][frame_keys[fi]]
        pos = g['positions'][:].astype(float)
        K   = g['contorsione_locale'][:].astype(float)
        tau = g['tau_locale'][:].astype(float)
        vel = g['velocities'][:].astype(float)
        tv  = f['topological_validation']
        save_iv = max(1, len(tv['step']) // len(frame_keys))
        ti = min(fi * save_iv + save_iv - 1, len(tv['step']) - 1)
        rho_mean = float(tv['mean_constraint_density'][ti])
        phase    = tv['phase_label'][ti].decode()
        t_val    = float(tv['time'][ti])
        eps_cl   = float(tv['closure_error_deg'][ti])
        H_tot    = float(tv['H_total_emergent'][ti])
        S_val    = None
        if 'variational_force' in f:
            S_raw = f['variational_force']['potential_S'][:].astype(float)
            n = len(tv['step'])
            S_arr = S_raw[1::2][:n] if len(S_raw) >= 2*n else S_raw[:n]
            S_val = float(S_arr[ti])

    N = len(pos)
    st = compute_stress_tensor(pos, K, tau, vel)
    kappa = compute_ricci(pos)

    print(f"Frame {fi} | t={t_val:.3f} | ρ̄={rho_mean:.4f} [{phase}]")
    print(f"  T_tt: {st['T_tt'].mean():.4f}±{st['T_tt'].std():.4f}")
    print(f"  T_xx: {st['T_xx'].mean():.4f}±{st['T_xx'].std():.4f}")
    print(f"  σ_VM: {st['sigma_VM'].mean():.4f}  max={st['sigma_VM'].max():.4f}")
    print(f"  κ_Ricci: {kappa.mean():.4f}  max={kappa.max():.4f}")
    print(f"Interpolazione RBF su griglia {grid_res}³ = {grid_res**3:,} punti "
          f"({grid_res**3/N:.0f}× densità)...")

    # --- Interpolazione ---
    scalar_fields = {
        'rho':      st['rho'],
        'sigma_VM': st['sigma_VM'],
        'kappa':    kappa,
        'T_tt':     st['T_tt'],
        'T_xx':     st['T_xx'],
    }
    (Xg, Yg, Zg), ifields = interpolate_to_grid(pos, scalar_fields, grid_res)

    # Slice a z mediano
    iz = grid_res // 2
    # Smooth leggero per ridurre artefatti RBF
    for k in ifields:
        ifields[k] = gaussian_filter(ifields[k], sigma=1.0)

    # Streamlines
    print("Calcolo streamlines campo torsione...")
    x1d, y1d, U, V = compute_streamline_slice(
        pos, K, st['tangent3d'], grid_res=grid_res)
    speed = np.sqrt(U**2 + V**2) + 1e-10
    U_n, V_n = U / speed, V / speed

    # --- Figura ---
    fig = plt.figure(figsize=(18, 11))
    title = (f"τ_μν Manifold Continuum — {path.stem}  "
             f"frame={fi}  t={t_val:.3f} Planck  "
             f"ρ̄={rho_mean:.4f} [{phase}]  ε_cl={eps_cl:.0f}°")
    fig.suptitle(title, fontsize=10, fontweight='bold')
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.30)

    elev, azim = 28.0, 55.0
    cmap_ricci  = 'RdBu_r'
    cmap_vm     = 'inferno'
    cmap_rho    = 'plasma'

    # ── P0: κ_Ricci in 3D ──
    ax0 = fig.add_subplot(gs[0, 0], projection='3d')
    # κ = 1 - cos(θ) ∈ [0,2]: 0=linea retta, 2=U-turn completo
    sc0 = ax0.scatter(*pos.T, c=kappa, cmap=cmap_ricci,
                      vmin=0.0, vmax=2.0,
                      s=15 + kappa * 50, alpha=0.82, linewidths=0)
    ax0.set_title('Curvatura di Ricci κ_i  [0=retta, 2=U-turn]\n(blu=bassa, rosso=alta)',
                  fontsize=8)
    ax0.set_axis_off()
    ax0.view_init(elev, azim)
    fig.colorbar(sc0, ax=ax0, shrink=0.6, pad=0.0, label='κ_i')

    # ── P1: σ_VM in 3D (cap al p99 per visualizzare struttura) ──
    ax1 = fig.add_subplot(gs[0, 1], projection='3d')
    vm_p99 = float(np.percentile(st['sigma_VM'], 99))
    vm_plot = np.clip(st['sigma_VM'], 0, vm_p99)
    sc1 = ax1.scatter(*pos.T, c=vm_plot, cmap=cmap_vm,
                      vmin=0, vmax=vm_p99,
                      s=10 + vm_plot / (vm_p99 + 1e-10) * 40, alpha=0.78, linewidths=0)
    ax1.set_title(f'von Mises σ_VM = |T_{{xx}}−T_{{tt}}|  (cap p99={vm_p99:.0f})\n'
                  f'anisotropia stress topologico', fontsize=8)
    ax1.set_axis_off()
    ax1.view_init(elev, azim)
    fig.colorbar(sc1, ax=ax1, shrink=0.6, pad=0.0, label='σ_VM')

    # ── P2: ρ_i in 3D ──
    ax2 = fig.add_subplot(gs[0, 2], projection='3d')
    sc2 = ax2.scatter(*pos.T, c=st['rho'], cmap=cmap_rho,
                      vmin=0.0, vmax=1.0,
                      s=12 + st['rho']*35, alpha=0.80, linewidths=0)
    ax2.set_title('Densità vincolo ρ_i\n[Eq. RHO-1]  (plasma=vacuum→condensed)',
                  fontsize=8)
    ax2.set_axis_off()
    ax2.view_init(elev, azim)
    fig.colorbar(sc2, ax=ax2, shrink=0.6, pad=0.0, label='ρ_i')

    # ── P3: Streamlines torsione + sfondo σ_VM interpolato ──
    ax3 = fig.add_subplot(gs[1, 0])
    sl_vm = ifields['sigma_VM'][:, :, iz].T
    im3 = ax3.imshow(sl_vm, origin='lower', cmap=cmap_vm, aspect='auto',
                     extent=[Xg.min(), Xg.max(), Yg.min(), Yg.max()])
    lw = 0.6 + 1.5 * (speed / speed.max())
    ax3.streamplot(x1d, y1d, U_n.T, V_n.T,
                   color=speed.T, cmap='cool', linewidth=lw.T,
                   density=2.0, arrowsize=0.8, arrowstyle='->')
    ax3.scatter(pos[:, 0], pos[:, 1], c='white', s=1.5, alpha=0.35, linewidths=0)
    ax3.set_xlabel('x [Planck]', fontsize=8)
    ax3.set_ylabel('y [Planck]', fontsize=8)
    ax3.set_title(f'Streamlines K·t (slice z≈mid)\nsfondo: σ_VM interpolato '
                  f'[{grid_res}³={grid_res**3/1e6:.2f}M punti]', fontsize=8)
    fig.colorbar(im3, ax=ax3, shrink=0.7, label='σ_VM')

    # ── P4: ρ interpolato + contour κ ──
    ax4 = fig.add_subplot(gs[1, 1])
    sl_rho = ifields['rho'][:, :, iz].T
    im4 = ax4.imshow(sl_rho, origin='lower', cmap=cmap_rho, aspect='auto',
                     vmin=0.0, vmax=1.0,
                     extent=[Xg.min(), Xg.max(), Yg.min(), Yg.max()])
    sl_kap = ifields['kappa'][:, :, iz].T
    ax4.contour(Xg[:, :, iz], Yg[:, :, iz], sl_kap,
                levels=10, colors='white', linewidths=0.5, alpha=0.55)
    ax4.scatter(pos[:, 0], pos[:, 1], c='yellow', s=2.0, alpha=0.4, linewidths=0)
    ax4.set_xlabel('x [Planck]', fontsize=8)
    ax4.set_ylabel('y [Planck]', fontsize=8)
    ax4.set_title('ρ continuo (RBF)  +  isocontour κ_Ricci\n'
                  '(bande bianche = curvatura costante)', fontsize=8)
    fig.colorbar(im4, ax=ax4, shrink=0.7, label='ρ interpolata')

    # ── P5: Istogrammi τ_μν ──
    ax5 = fig.add_subplot(gs[1, 2])
    bins = 40
    ax5.hist(st['T_tt'], bins=bins, alpha=0.6, color='royalblue', label='T_{tt}', density=True)
    ax5.hist(st['T_xx'], bins=bins, alpha=0.6, color='tomato',    label='T_{xx}', density=True)
    ax5.hist(np.abs(st['T_tx']), bins=bins, alpha=0.5, color='gold',
             label='|T_{tx}|', density=True)
    ax5.hist(st['sigma_VM'], bins=bins, alpha=0.5, color='mediumorchid',
             label='σ_VM', density=True)
    ax5.axvline(0, color='black', lw=0.6)
    ax5.set_xlabel('Valore componente τ_μν', fontsize=8)
    ax5.set_ylabel('Densità (norm.)', fontsize=8)
    ax5.set_title('Distribuzione componenti τ_μν\nper tutti i segmenti', fontsize=8)
    ax5.legend(fontsize=7, ncol=2)
    ax5.grid(True, alpha=0.3)

    # Annotazione HUD con metriche chiave
    S_str = f"S/N={S_val/N:.3f}" if S_val is not None else ""
    info = (f"N={N}  H/N={H_tot/N:.1f}  {S_str}\n"
            f"Tr(τ)/N={st['trace'].mean():.3f}  "
            f"Det(τ)/N={st['det'].mean():.3f}")
    fig.text(0.5, 0.005, info, ha='center', fontsize=8, color='#555555')

    output = output or f"{path.stem}_continuum_f{fi:03d}.png"
    out = Path(output)
    fig.savefig(out, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"Salvato: {out.resolve()}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Visualizzazione continua τ_μν + Ricci del manifold VQT')
    p.add_argument('hdf5',          help='File HDF5 input')
    p.add_argument('--frame', '-f', type=int,   default=50,   help='Indice frame HDF5')
    p.add_argument('--grid',  '-g', type=int,   default=80,   help='Risoluzione griglia RBF')
    p.add_argument('--output','-o', default=None)
    p.add_argument('--dpi',         type=int,   default=140)
    return p.parse_args()


def main():
    args = parse_args()
    plot_continuum(args.hdf5, frame_idx=args.frame,
                   grid_res=args.grid, output=args.output, dpi=args.dpi)
    return 0


if __name__ == '__main__':
    sys.exit(main())
