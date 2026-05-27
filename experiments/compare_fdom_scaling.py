#!/usr/bin/env python3
"""
================================================================================
COMPARE FDOM SCALING  —  Spettroscopia del Manifold VQT per Livello
================================================================================

Analizza la firma dinamica di σ(ρ) = constraint_density_std per ogni livello
frattale disponibile in experiments/exp1/, estraendo:

  • f_dom  — frequenza di risonanza dominante [1/Planck]
  • T_dom  — periodo fondamentale [Planck]
  • Potenza dominante / Entropia spettrale  (ordine vs. rumore)
  • σ(ρ) medio, range, trend

Produce un report completo e una figura a 4 pannelli:
  [A] σ(ρ) vs tempo — serie temporali sovrapposte per livello
  [B] Spettro di potenza FFT — firma spettrale per livello
  [C] f_dom vs N_dof — legge di scala con fit a potenza
  [D] Osservabili di scala — σ_mean, entropia, potenza dom. vs. livello

USO:
  python experiments/compare_fdom_scaling.py
  python experiments/compare_fdom_scaling.py --exp-dir experiments/exp1
  python experiments/compare_fdom_scaling.py --save-json results.json
================================================================================
"""

import argparse
import json
import sys
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

try:
    from scipy.signal import spectrogram as _scipy_spectrogram
    _SCIPY_OK = True
except ImportError:
    _SCIPY_OK = False


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

LEVEL_COLORS = {1: "#4C72B0", 2: "#DD8452", 3: "#55A868", 4: "#C44E52",
                5: "#8172B2", 6: "#937860"}
LEVEL_N_DOF  = {L: 2 * 24**L for L in range(1, 7)}


# ============================================================================
# ANALISI SPETTRALE
# ============================================================================

def spectral_analysis(sigma: np.ndarray, dt: float, level: int) -> dict:
    """
    Analisi FFT + autocorrelazione di σ(ρ).

    Restituisce un dizionario con tutti gli osservabili spettrali.
    """
    N = len(sigma)
    t_total = N * dt

    # Detrend lineare (rimuove drift lento)
    trend_coeffs = np.polyfit(np.arange(N), sigma, 1)
    sigma_d = sigma - np.polyval(trend_coeffs, np.arange(N))
    sigma_trend_slope = float(trend_coeffs[0])

    # --- FFT ---
    fft_vals = np.fft.rfft(sigma_d)
    freq = np.fft.rfftfreq(N, d=dt)
    power = np.abs(fft_vals) ** 2
    power[0] = 0.0  # escludi DC
    total_power = float(power.sum())
    freq_resolution = float(freq[1]) if len(freq) > 1 else np.nan

    dom_idx = int(np.argmax(power))
    f_dom = float(freq[dom_idx])
    T_dom = 1.0 / f_dom if f_dom > 0 else np.inf
    dom_power_frac = float(power[dom_idx] / (total_power + 1e-30))

    # Top-5 frequenze
    top5_idx = np.argsort(power)[::-1][:5]
    top5 = [(float(freq[i]), float(power[i] / (total_power + 1e-30)))
             for i in top5_idx if freq[i] > 0]

    # Entropia spettrale (misura quanti modi contribuiscono significativamente)
    p_norm = power / (total_power + 1e-30)
    p_pos = p_norm[p_norm > 1e-15]
    spectral_entropy = float(-np.sum(p_pos * np.log(p_pos)))
    spectral_entropy_max = float(np.log(len(p_pos)))  # massimo teorico

    # --- Autocorrelazione ---
    sig_norm = (sigma - sigma.mean()) / (sigma.std() + 1e-30)
    ac = np.correlate(sig_norm, sig_norm, mode='full')[N - 1:]
    ac = ac / ac[0]

    # Primo zero-crossing → stima T_osc
    zc_idx = np.where(np.diff(np.sign(ac)))[0]
    T_ac_halfperiod = float(zc_idx[0] * dt) if len(zc_idx) > 0 else np.nan
    T_ac = 4.0 * T_ac_halfperiod  # AC di sinusoide = coseno → zero a T/4

    # Primo minimo locale → conferma
    grad = np.diff(ac)
    local_min_idx = np.where((grad[:-1] < 0) & (grad[1:] >= 0))[0]
    T_ac_min = float(local_min_idx[0] * dt * 2) if len(local_min_idx) > 0 else np.nan

    # Flag affidabilità FFT: serve almeno 2 periodi completi
    reliable = (T_dom < t_total / 2.0) if np.isfinite(T_dom) else False

    return {
        "level":              level,
        "N_dof":              LEVEL_N_DOF[level],
        "N_samples":          N,
        "dt":                 dt,
        "t_total_planck":     t_total,
        # FFT
        "f_dom":              f_dom,
        "T_dom_planck":       T_dom,
        "T_dom_steps":        int(T_dom / dt) if np.isfinite(T_dom) else -1,
        "dom_power_fraction": dom_power_frac,
        "spectral_entropy":   spectral_entropy,
        "spectral_entropy_max": spectral_entropy_max,
        "freq_resolution":    freq_resolution,
        "fft_reliable":       reliable,
        "top5_frequencies":   top5,
        # Autocorrelazione
        "T_ac_planck":        T_ac,
        "T_ac_min_planck":    T_ac_min,
        # σ(ρ) statistiche
        "sigma_mean":         float(sigma.mean()),
        "sigma_std":          float(sigma.std()),
        "sigma_min":          float(sigma.min()),
        "sigma_max":          float(sigma.max()),
        "sigma_range":        float(sigma.max() - sigma.min()),
        "sigma_trend_slope":  sigma_trend_slope,
        # Raw arrays per plotting
        "_freq":              freq,
        "_power":             power,
        "_ac":                ac,
        "_sigma":             sigma,
        "_sigma_d":           sigma_d,
    }


# ============================================================================
# CARICAMENTO DATI
# ============================================================================

def load_experiment(exp_dir: Path) -> dict:
    """
    Carica tutti i file HDF5 dell'esperimento e restituisce i risultati
    spettrali per livello.
    """
    results = {}

    # Cerca file HDF5 con nome cosmo_L*.h5
    candidates = sorted(exp_dir.glob("cosmo_L*.h5"))
    if not candidates:
        print(f"Nessun file cosmo_L*.h5 trovato in {exp_dir}")
        return results

    for hdf5_path in candidates:
        # Estrai il livello dal nome file (es. cosmo_L2.h5 → 2)
        stem = hdf5_path.stem  # e.g. "cosmo_L2"
        parts = stem.split("_L")
        if len(parts) < 2:
            continue
        try:
            level = int(parts[1].split("_")[0])  # gestisce "cosmo_L1_spectral" → 1
        except ValueError:
            continue

        # Salta duplicati (mantieni il file con più campioni per quel livello)
        try:
            with h5py.File(hdf5_path, "r") as f:
                if "topological_validation" not in f:
                    print(f"  [skip] {hdf5_path.name}: nessun gruppo topological_validation")
                    continue
                tv = f["topological_validation"]
                sigma = tv["constraint_density_std"][:]
                time  = tv["time"][:]
                rho   = tv["mean_constraint_density"][:]
                H     = tv["H_total_emergent"][:]
        except Exception as e:
            print(f"  [skip] {hdf5_path.name}: {e}")
            continue

        if len(sigma) < 10:
            print(f"  [skip] {hdf5_path.name}: troppo pochi campioni ({len(sigma)})")
            continue

        dt = float(time[1] - time[0]) if len(time) > 1 else 0.01

        # Se abbiamo già un risultato per questo livello, tieni quello con più campioni
        if level in results and len(sigma) <= results[level]["N_samples"]:
            print(f"  [dup]  {hdf5_path.name}: L{level} già caricato con più campioni")
            continue

        print(f"  Carico {hdf5_path.name}: L{level}  N={len(sigma)}  t=[{time[0]:.3f}..{time[-1]:.3f}]")
        res = spectral_analysis(sigma, dt, level)
        res["_rho"]  = rho
        res["_H"]    = H
        res["_time"] = time
        res["filename"] = hdf5_path.name
        results[level] = res

    return results


# ============================================================================
# LEGGE DI SCALA
# ============================================================================

def fit_scaling_law(levels_data: dict) -> dict:
    """
    Fit legge di potenza: f_dom = A × N_dof^α

    Usa solo i livelli con FFT affidabile.
    """
    reliable = {L: d for L, d in levels_data.items()
                if d["fft_reliable"] and d["f_dom"] > 0}

    if len(reliable) < 2:
        return {"fitted": False, "reason": f"Solo {len(reliable)} livelli con FFT affidabile"}

    N_dof_arr = np.array([d["N_dof"] for d in reliable.values()], dtype=float)
    f_dom_arr = np.array([d["f_dom"] for d in reliable.values()], dtype=float)

    # Fit lineare in log-log
    log_N = np.log10(N_dof_arr)
    log_f = np.log10(f_dom_arr)
    coeffs = np.polyfit(log_N, log_f, 1)
    alpha = float(coeffs[0])
    log_A = float(coeffs[1])
    A = 10 ** log_A

    # R² del fit
    log_f_pred = np.polyval(coeffs, log_N)
    ss_res = float(np.sum((log_f - log_f_pred) ** 2))
    ss_tot = float(np.sum((log_f - log_f.mean()) ** 2))
    R2 = 1.0 - ss_res / (ss_tot + 1e-30)

    return {
        "fitted":    True,
        "A":         A,
        "alpha":     alpha,
        "R2":        R2,
        "n_points":  len(reliable),
        "levels_used": sorted(reliable.keys()),
        "formula":   f"f_dom = {A:.4f} × N_dof^({alpha:+.4f})",
    }


# ============================================================================
# STFT — SPETTROGRAMMA A CASCATA
# ============================================================================

def _compute_stft(sigma: np.ndarray, dt: float, nperseg: int) -> tuple:
    """
    Ritorna (t_stft, f_stft, Sxx_db) con Sxx_db normalizzato a 0 dB al picco.
    Usa scipy.signal.spectrogram se disponibile, altrimenti implementazione numpy.
    """
    noverlap = nperseg * 3 // 4

    if _SCIPY_OK:
        f, t, Sxx = _scipy_spectrogram(
            sigma, fs=1.0 / dt, nperseg=nperseg,
            noverlap=noverlap, scaling="density", detrend="linear",
        )
    else:
        # Fallback manuale con finestra di Hann
        step = nperseg - noverlap
        n_frames = max(1, (len(sigma) - nperseg) // step + 1)
        t = np.array([(i * step + nperseg // 2) * dt for i in range(n_frames)])
        f = np.fft.rfftfreq(nperseg, d=dt)
        window = np.hanning(nperseg)
        Sxx = np.zeros((len(f), n_frames))
        for i in range(n_frames):
            chunk = sigma[i * step: i * step + nperseg]
            if len(chunk) < nperseg:
                break
            chunk = (chunk - chunk.mean()) * window
            Sxx[:, i] = np.abs(np.fft.rfft(chunk)) ** 2

    Sxx_db = 10.0 * np.log10(Sxx + 1e-30)
    Sxx_db -= Sxx_db.max()  # normalizza a 0 dB al picco globale
    return t, f, Sxx_db


def plot_stft_cascade(results: dict, out_path: Path, f_max: float = 4.0,
                      db_floor: float = -40.0, nperseg_override: int = 0):
    """
    Figura separata con spettrogrammi STFT per ogni livello.

    Mostra la cascata di energia dalle alte frequenze (turbolenza transitoria)
    verso il modo fondamentale — la prova visiva dell'auto-organizzazione.
    """
    levels = sorted(results.keys())
    n = len(levels)
    fig_h = max(4, 3.5 * n)
    fig = plt.figure(figsize=(14, fig_h), facecolor="#0d0d0d")
    fig.suptitle(
        "VQT — STFT Cascade: turbolenza → modo fondamentale",
        color="white", fontsize=13, fontweight="bold", y=1.0 - 0.01 / n,
    )

    axes = []
    for idx, L in enumerate(levels):
        ax = fig.add_subplot(n, 1, idx + 1)
        ax.set_facecolor("#0d0d0d")
        axes.append(ax)

        d = results[L]
        sigma = d["_sigma"]
        dt    = d["dt"]
        N     = len(sigma)
        color = LEVEL_COLORS.get(L, "white")

        # Scegli nperseg: almeno 3× T_turbulenza (0.13P → 13 step) e max N//4
        if nperseg_override > 0:
            nperseg = nperseg_override
        else:
            # Target: finestra = 1.0 Planck → buon compromesso per vedere entrambe le scale
            nperseg = max(30, min(N // 4, int(1.0 / dt)))

        t_stft, f_stft, Sxx_db = _compute_stft(sigma, dt, nperseg)

        # Maschera frequenze fuori range
        f_mask = f_stft <= f_max
        freq_res = float(f_stft[1]) if len(f_stft) > 1 else np.nan

        im = ax.pcolormesh(
            t_stft,
            f_stft[f_mask],
            Sxx_db[f_mask, :len(t_stft)],
            cmap="magma",
            vmin=db_floor,
            vmax=0.0,
            shading="gouraud",
        )

        # Linea orizzontale al modo fondamentale (f_dom da FFT globale)
        f_dom = d["f_dom"]
        ax.axhline(f_dom, color=color, lw=1.0, ls="--", alpha=0.8,
                   label=f"f_dom={f_dom:.3f} Hz")

        # Banda di turbolenza di transizione (f ≈ 7–8 Hz se visibile)
        if f_max >= 7.0:
            ax.axhspan(6.5, 8.5, color="cyan", alpha=0.08, label="banda turbolenza")

        # Colorbar
        cb = fig.colorbar(im, ax=ax, pad=0.01, fraction=0.025)
        cb.set_label("dB (rel. peak)", color="gray", fontsize=7)
        cb.ax.yaxis.set_tick_params(color="gray", labelsize=7)
        plt.setp(cb.ax.yaxis.get_ticklabels(), color="gray")

        ax.set_ylim(0, f_max)
        ax.set_ylabel("Frequenza [1/P]", color="gray", fontsize=9)
        ax.tick_params(colors="gray", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#444")
        ax.grid(True, color="#333", lw=0.4, alpha=0.6)
        ax.set_title(
            f"L{L}  (N_dof={d['N_dof']}  |  N={N} step  |  "
            f"Δf={freq_res:.3f} Hz  |  win={nperseg*dt:.2f}P)",
            color="white", fontsize=9, pad=4,
        )
        ax.legend(fontsize=7, facecolor="#1a1a1a", edgecolor="gray", labelcolor="white",
                  loc="upper right")

    axes[-1].set_xlabel("Tempo [Planck]", color="gray", fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 1 - 0.03 / n])
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Spettrogramma STFT salvato: {out_path}")


# ============================================================================
# VISUALIZZAZIONE
# ============================================================================

def plot_spectral_comparison(results: dict, scaling: dict, out_path: Path):
    """
    Figura a 4 pannelli per il confronto spettrale tra livelli.
    """
    levels = sorted(results.keys())
    n_levels = len(levels)

    fig = plt.figure(figsize=(16, 12), facecolor="#0d0d0d")
    fig.suptitle("VQT Manifold — Spettroscopia di σ(ρ) per Livello Frattale",
                 color="white", fontsize=14, fontweight="bold", y=0.98)

    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.32,
                           left=0.07, right=0.97, top=0.93, bottom=0.07)
    ax_ts  = fig.add_subplot(gs[0, 0])  # A: serie temporali
    ax_fft = fig.add_subplot(gs[0, 1])  # B: spettro FFT
    ax_sc  = fig.add_subplot(gs[1, 0])  # C: legge di scala f_dom
    ax_obs = fig.add_subplot(gs[1, 1])  # D: osservabili di scala

    _style_ax(ax_ts,  "A — σ(ρ) vs Tempo",    "Tempo [Planck]",   "σ(ρ)")
    _style_ax(ax_fft, "B — Spettro di Potenza", "Frequenza [1/Planck]", "Potenza (norm.)")
    _style_ax(ax_sc,  "C — Legge di Scala  f_dom(N_dof)", "N_dof", "f_dom [1/Planck]")
    _style_ax(ax_obs, "D — Osservabili di Scala", "Livello L", "")

    # ---- A: serie temporali ----
    for L in levels:
        d = results[L]
        color = LEVEL_COLORS.get(L, "white")
        t = d["_time"]
        s = d["_sigma"]
        ax_ts.plot(t, s, color=color, lw=1.2, alpha=0.85, label=f"L{L}  (N={d['N_dof']//2})")
        ax_ts.axhline(d["sigma_mean"], color=color, lw=0.5, ls="--", alpha=0.5)
    ax_ts.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="gray", labelcolor="white")

    # ---- B: spettro FFT ----
    for L in levels:
        d = results[L]
        color = LEVEL_COLORS.get(L, "white")
        freq = d["_freq"]
        power = d["_power"]
        p_norm = power / (power.max() + 1e-30)
        mask = freq > 0
        ax_fft.plot(freq[mask], p_norm[mask], color=color, lw=1.2, alpha=0.85,
                    label=f"L{L}  f*={d['f_dom']:.3f}")
        # Marcatore frequenza dominante
        ax_fft.axvline(d["f_dom"], color=color, lw=0.8, ls=":", alpha=0.7)
    ax_fft.set_xlim(0, 3.0)
    ax_fft.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="gray", labelcolor="white")

    # ---- C: legge di scala ----
    N_dof_arr = [results[L]["N_dof"] for L in levels]
    f_dom_arr = [results[L]["f_dom"] for L in levels]
    colors_arr = [LEVEL_COLORS.get(L, "white") for L in levels]
    reliable = [results[L]["fft_reliable"] for L in levels]

    for i, L in enumerate(levels):
        marker = "o" if reliable[i] else "^"
        ax_sc.scatter(N_dof_arr[i], f_dom_arr[i], color=colors_arr[i],
                      s=80, zorder=5, marker=marker,
                      label=f"L{L}" + (" *" if not reliable[i] else ""))
        ax_sc.annotate(f"L{L}", (N_dof_arr[i], f_dom_arr[i]),
                       textcoords="offset points", xytext=(6, 4),
                       fontsize=8, color=colors_arr[i])

    # Fit power law
    if scaling.get("fitted"):
        N_fit = np.logspace(np.log10(min(N_dof_arr)) * 0.9,
                            np.log10(max(N_dof_arr)) * 1.1, 200)
        f_fit = scaling["A"] * N_fit ** scaling["alpha"]
        ax_sc.plot(N_fit, f_fit, color="gray", lw=1.2, ls="--", alpha=0.7,
                   label=f"fit: A·N^α\nα={scaling['alpha']:+.3f}  R²={scaling['R2']:.3f}")
        ax_sc.set_xscale("log")
        ax_sc.set_yscale("log")

    ax_sc.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="gray", labelcolor="white")

    # ---- D: osservabili di scala ----
    ax_obs2 = ax_obs.twinx()
    _style_ax_twinx(ax_obs2)

    L_arr = levels
    sigma_means = [results[L]["sigma_mean"] for L in L_arr]
    entropies   = [results[L]["spectral_entropy"] for L in L_arr]
    dom_powers  = [results[L]["dom_power_fraction"] * 100 for L in L_arr]

    lw = 1.5
    ax_obs.plot(L_arr, sigma_means, "o-", color="#4C72B0", lw=lw, ms=7, label="σ(ρ) medio")
    ax_obs.plot(L_arr, entropies,   "s-", color="#DD8452", lw=lw, ms=7, label="Entropia spettrale")
    ax_obs2.plot(L_arr, dom_powers, "^-", color="#55A868", lw=lw, ms=7, label="Potenza dom. [%]")

    ax_obs.set_xlabel("Livello L", color="gray", fontsize=10)
    ax_obs.set_ylabel("σ(ρ) medio  /  Entropia", color="gray", fontsize=9)
    ax_obs2.set_ylabel("Potenza dominante [%]", color="#55A868", fontsize=9)
    ax_obs2.yaxis.label.set_color("#55A868")
    ax_obs2.tick_params(colors="#55A868")

    lines1, labels1 = ax_obs.get_legend_handles_labels()
    lines2, labels2 = ax_obs2.get_legend_handles_labels()
    ax_obs.legend(lines1 + lines2, labels1 + labels2, fontsize=8,
                  facecolor="#1a1a1a", edgecolor="gray", labelcolor="white")
    ax_obs.set_xticks(L_arr)

    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"\nFigura salvata: {out_path}")


def _style_ax(ax, title, xlabel, ylabel):
    ax.set_facecolor("#1a1a1a")
    ax.tick_params(colors="gray", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#444")
    ax.set_title(title, color="white", fontsize=10, pad=6)
    ax.set_xlabel(xlabel, color="gray", fontsize=9)
    ax.set_ylabel(ylabel, color="gray", fontsize=9)
    ax.grid(True, color="#333", lw=0.5, alpha=0.7)


def _style_ax_twinx(ax):
    ax.set_facecolor("#1a1a1a")
    ax.tick_params(colors="gray", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#444")


# ============================================================================
# REPORT TESTUALE
# ============================================================================

def print_report(results: dict, scaling: dict):
    print("\n" + "=" * 72)
    print("  VQT SPECTRAL SCALING REPORT")
    print("=" * 72)
    print(f"  {'L':>3}  {'N_dof':>8}  {'N_samp':>7}  {'f_dom':>8}  {'T_dom':>8}  "
          f"{'PowDom%':>8}  {'Entropy':>8}  {'s_mean':>8}  {'Reliable':>8}")
    print("  " + "-" * 68)
    for L in sorted(results.keys()):
        d = results[L]
        rel = "YES" if d["fft_reliable"] else "NO (*)"
        T_str = f"{d['T_dom_planck']:.3f}" if np.isfinite(d["T_dom_planck"]) else "  ∞  "
        print(f"  L{L}  {d['N_dof']:>8d}  {d['N_samples']:>7d}  "
              f"{d['f_dom']:>8.4f}  {T_str:>8}  "
              f"{d['dom_power_fraction']*100:>8.1f}  {d['spectral_entropy']:>8.3f}  "
              f"{d['sigma_mean']:>8.5f}  {rel:>8}")

    print()
    print("  (*) FFT bassa affidabilita': campioni insufficienti per >=2 periodi")
    print()

    if scaling.get("fitted"):
        print(f"  Legge di scala:  {scaling['formula']}")
        print(f"  Esponente alpha: {scaling['alpha']:+.4f}  (0 = invariante di scala)")
        print(f"  R2:              {scaling['R2']:.4f}")
        print(f"  Livelli usati:   {scaling['levels_used']}")
        print()
        if abs(scaling["alpha"]) < 0.05:
            print("  *** f_dom e' essenzialmente INVARIANTE di scala rispetto a N_dof.")
            print("    Interpretazione: la frequenza di risonanza e' determinata dalle")
            print("    costanti fisiche (lambda, gamma, dt), non dalla risoluzione spaziale.")
        elif scaling["alpha"] < 0:
            print(f"  f_dom diminuisce con N_dof (alpha={scaling['alpha']:.3f}).")
            print("    Il periodo fondamentale cresce con la risoluzione.")
        else:
            print(f"  f_dom aumenta con N_dof (alpha={scaling['alpha']:.3f}).")
    else:
        print(f"  Fit di scala non disponibile: {scaling.get('reason','')}")

    # --- Check super-estensivita': s_mean dovrebbe calare con L (ordine emergente) ---
    sigma_vals = {L: results[L]["sigma_mean"] for L in sorted(results.keys())}
    if len(sigma_vals) >= 2:
        print()
        print("  Omogeneizzazione progressiva (s_mean per livello):")
        lvls = sorted(sigma_vals.keys())
        for i in range(len(lvls) - 1):
            La, Lb = lvls[i], lvls[i + 1]
            sa, sb = sigma_vals[La], sigma_vals[Lb]
            arrow = "CONFERMATA (s cala)" if sb < sa else "NEGATA (s cresce)"
            ratio = sb / sa if sa > 0 else float("inf")
            print(f"    s(L{La})={sa:.5f} -> s(L{Lb})={sb:.5f}  "
                  f"(x{ratio:.2f})  {arrow}")

    print("=" * 72)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analisi spettrale f_dom(L) per i manifold VQT")
    parser.add_argument("--exp-dir", default="experiments/exp1",
                        help="Cartella dell'esperimento con i file HDF5")
    parser.add_argument("--out-fig", default=None,
                        help="Percorso figura output (default: <exp-dir>/fdom_scaling.png)")
    parser.add_argument("--save-json", default=None,
                        help="Salva risultati in JSON per analisi future")
    parser.add_argument("--stft", action="store_true",
                        help="Genera spettrogramma STFT a cascata (figura separata)")
    parser.add_argument("--stft-fmax", type=float, default=4.0,
                        help="Frequenza massima nell'asse Y dello spettrogramma [1/P] (default: 4)")
    parser.add_argument("--stft-nperseg", type=int, default=0,
                        help="Finestra STFT in campioni (0=auto, basato su 1 Planck)")
    parser.add_argument("--stft-floor", type=float, default=-40.0,
                        help="Piano rumore in dB per colormap spettrogramma (default: -40)")
    args = parser.parse_args()

    exp_dir = Path(args.exp_dir)
    if not exp_dir.exists():
        print(f"Errore: {exp_dir} non esiste.")
        sys.exit(1)

    out_fig = Path(args.out_fig) if args.out_fig else exp_dir / "fdom_scaling.png"

    print(f"Caricamento dati da {exp_dir}/")
    results = load_experiment(exp_dir)

    if not results:
        print("Nessun dato trovato.")
        sys.exit(1)

    scaling = fit_scaling_law(results)
    print_report(results, scaling)

    plot_spectral_comparison(results, scaling, out_fig)

    # Spettrogramma STFT opzionale
    if args.stft:
        stft_path = out_fig.parent / (out_fig.stem + "_stft.png")
        if not _SCIPY_OK:
            print("  (scipy non disponibile — uso implementazione numpy fallback per STFT)")
        plot_stft_cascade(
            results, stft_path,
            f_max=args.stft_fmax,
            db_floor=args.stft_floor,
            nperseg_override=args.stft_nperseg,
        )

    # Salva JSON (senza array numpy)
    if args.save_json:
        json_out = {}
        for L, d in results.items():
            row = {k: v for k, v in d.items() if not k.startswith("_")}
            # Converti tipi numpy
            for k, v in row.items():
                if isinstance(v, (np.floating, np.integer)):
                    row[k] = float(v)
                elif isinstance(v, list):
                    row[k] = [[float(x) for x in pair] for pair in v]
            json_out[str(L)] = row
        json_out["scaling"] = scaling
        with open(args.save_json, "w") as f:
            json.dump(json_out, f, indent=2, default=str)
        print(f"JSON salvato: {args.save_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
