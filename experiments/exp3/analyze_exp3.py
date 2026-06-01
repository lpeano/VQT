"""
================================================================================
ANALISI exp3 — Statistiche e grafici dei run L1/L2/L3 (--fast-evolver)
================================================================================

Legge cosmo_L{1,2,3}_fast.h5 e produce:
  - Statistiche testuali (triade energetica, drift, Jitterbug ratio, vincoli topologici)
  - Grafici PNG in experiments/exp3/figures/

GRAFICI:
  1. triade_energetica.png   — E_chi, E_RX, E_Psi vs step (per livello)
  2. conservazione_H.png     — H_total e drift vs step
  3. campo_chi.png           — chi_mean/std/max vs step + istogramma finale
  4. vincoli_topologici.png  — constraint_density, closure_error vs step
  5. jitterbug_scaling.png   — chi_max/chi_stable vs livello (soglia sqrt(2))

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/analyze_exp3.py
================================================================================
"""

import os
import sys
import numpy as np
import h5py

import matplotlib
matplotlib.use("Agg")  # no display, salva su file
import matplotlib.pyplot as plt

EXP3 = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(EXP3, "figures")
os.makedirs(FIGDIR, exist_ok=True)

CHI_STABLE = 50.0
SQRT2 = np.sqrt(2)
LEVELS = [1, 2, 3]
COLORS = {1: "#1f77b4", 2: "#ff7f0e", 3: "#2ca02c"}


def load_series(level):
    """Estrae le serie temporali da un file HDF5."""
    fp = os.path.join(EXP3, f"cosmo_L{level}_fast.h5")
    if not os.path.exists(fp):
        return None
    data = {"step": [], "time": [], "H_total": [], "drift": [],
            "E_chi": [], "E_RX": [], "E_Psi": [],
            "chi_mean": [], "chi_std": [], "chi_max": []}
    topo = {}
    with h5py.File(fp, "r") as f:
        frames = sorted(f["frames"].keys(), key=lambda x: int(x.split("_")[1]))
        for fn in frames:
            g = f["frames/" + fn]
            a = g.attrs
            data["step"].append(int(a.get("step", 0)))
            data["time"].append(float(a.get("time", 0.0)))
            data["H_total"].append(float(a.get("H_total", np.nan)))
            data["drift"].append(float(a.get("drift", np.nan)))
            data["E_chi"].append(float(a.get("E_chi", np.nan)))
            data["E_RX"].append(float(a.get("E_RX", np.nan)))
            data["E_Psi"].append(float(a.get("E_Psi", np.nan)))
            chi = np.abs(g["chi_values"][:])
            data["chi_mean"].append(float(np.mean(chi)))
            data["chi_std"].append(float(np.std(g["chi_values"][:])))
            data["chi_max"].append(float(np.max(chi)))
        # ultimo frame chi per istogramma
        data["chi_final"] = f["frames/" + frames[-1]]["chi_values"][:]
        # topological validation
        if "topological_validation" in f:
            tv = f["topological_validation"]
            for k in ["constraint_density_std", "mean_constraint_density",
                      "closure_error_deg", "detorsion_quality"]:
                if k in tv:
                    topo[k] = tv[k][:]
    for k in data:
        if k != "chi_final":
            data[k] = np.array(data[k])
    data["topo"] = topo
    data["level"] = level
    data["n_frames"] = len(data["step"])
    return data


def print_stats(series):
    print("=" * 70)
    print("  STATISTICHE exp3 (run --fast-evolver)")
    print("=" * 70)
    print(f"  {'Livello':>8} {'frame':>6} {'N_seg':>7} {'H_total':>12} {'drift_max':>10} "
          f"{'chi_max/chi0':>12} {'fase':>14}")
    print("  " + "-" * 72)
    for s in series:
        if s is None:
            continue
        nseg = 24 ** s["level"]
        ratio = s["chi_max"][-1] / CHI_STABLE
        phase = ("Icosaedrica" if ratio >= SQRT2 else
                 "Cubottaedrica" if ratio >= 1.0 else "Ottaedrica")
        drift_max = np.nanmax(np.abs(s["drift"]))
        print(f"  {'L'+str(s['level']):>8} {s['n_frames']:>6} {nseg:>7} "
              f"{s['H_total'][-1]:>12.4e} {drift_max:>10.2e} {ratio:>12.4f} {phase:>14}")
    print("\n  Triade energetica (ultimo frame):")
    for s in series:
        if s is None:
            continue
        print(f"    L{s['level']}: E_chi={s['E_chi'][-1]:.4e}  E_RX={s['E_RX'][-1]:.4e}  "
              f"E_Psi={s['E_Psi'][-1]:.4e}")
    print("=" * 70)


def plot_triade(series):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, s in zip(axes, series):
        if s is None:
            continue
        st = s["step"]
        ax.plot(st, s["E_chi"], "o-", label="E_chi", color="#1f77b4")
        ax.plot(st, s["E_RX"], "s-", label="E_RX", color="#ff7f0e")
        ax.plot(st, s["E_Psi"], "^-", label="E_Psi (drain)", color="#2ca02c")
        ax.set_title(f"L{s['level']} — Triade Peano-VQT")
        ax.set_xlabel("step"); ax.set_ylabel("Energia")
        ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.suptitle("Triade energetica E_chi / E_RX / E_Psi", fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "triade_energetica.png"), dpi=120)
    plt.close(fig)


def plot_conservazione(series):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    for s in series:
        if s is None:
            continue
        c = COLORS[s["level"]]
        # H normalizzato al valore iniziale
        H = s["H_total"]
        ax1.plot(s["step"], H / H[0], "o-", color=c, label=f"L{s['level']}")
        ax2.semilogy(s["step"], np.abs(s["drift"]) + 1e-12, "o-", color=c, label=f"L{s['level']}")
    ax1.set_title("H_total normalizzato (H/H_0)"); ax1.set_xlabel("step")
    ax1.set_ylabel("H/H_0"); ax1.legend(); ax1.grid(alpha=0.3)
    ax2.set_title("Drift energetico |dH/H|"); ax2.set_xlabel("step")
    ax2.set_ylabel("drift (log)"); ax2.legend(); ax2.grid(alpha=0.3)
    fig.suptitle("Conservazione energia (--fast-evolver)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "conservazione_H.png"), dpi=120)
    plt.close(fig)


def plot_campo_chi(series):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    for s in series:
        if s is None:
            continue
        c = COLORS[s["level"]]
        ax1.plot(s["step"], s["chi_max"], "o-", color=c, label=f"L{s['level']} max")
        ax1.plot(s["step"], s["chi_mean"], "--", color=c, alpha=0.6, label=f"L{s['level']} mean")
    ax1.axhline(SQRT2 * CHI_STABLE, color="red", ls=":", label="soglia Jitterbug √2·χ₀")
    ax1.set_title("chi_max e chi_mean vs step"); ax1.set_xlabel("step")
    ax1.set_ylabel("|chi|"); ax1.legend(fontsize=8); ax1.grid(alpha=0.3)
    for s in series:
        if s is None:
            continue
        ax2.hist(s["chi_final"], bins=40, alpha=0.5, color=COLORS[s["level"]],
                 label=f"L{s['level']}", density=True)
    ax2.axvline(CHI_STABLE, color="k", ls=":", alpha=0.5, label="χ₀=50")
    ax2.set_title("Distribuzione chi (ultimo frame)"); ax2.set_xlabel("chi")
    ax2.set_ylabel("densità"); ax2.legend(fontsize=8); ax2.grid(alpha=0.3)
    fig.suptitle("Campo chi", fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "campo_chi.png"), dpi=120)
    plt.close(fig)


def plot_vincoli(series):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    plotted = False
    for s in series:
        if s is None or not s["topo"]:
            continue
        c = COLORS[s["level"]]
        topo = s["topo"]
        if "constraint_density_std" in topo:
            y = topo["constraint_density_std"]
            ax1.plot(np.arange(len(y)), y, "o-", color=c, label=f"L{s['level']}")
            plotted = True
        if "closure_error_deg" in topo:
            y = topo["closure_error_deg"]
            ax2.plot(np.arange(len(y)), y, "o-", color=c, label=f"L{s['level']}")
    ax1.set_title("σ(ρ) constraint_density_std (= sigma_inf)")
    ax1.set_xlabel("step"); ax1.set_ylabel("σ(ρ)"); ax1.legend(); ax1.grid(alpha=0.3)
    ax2.set_title("Errore di chiusura topologica [°]")
    ax2.set_xlabel("step"); ax2.set_ylabel("closure_err [°]"); ax2.legend(); ax2.grid(alpha=0.3)
    fig.suptitle("Vincoli topologici", fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "vincoli_topologici.png"), dpi=120)
    plt.close(fig)
    return plotted


def plot_jitterbug_scaling(series):
    fig, ax = plt.subplots(figsize=(7, 5))
    levels, ratios = [], []
    for s in series:
        if s is None:
            continue
        levels.append(s["level"])
        ratios.append(s["chi_max"][-1] / CHI_STABLE)
    ax.plot(levels, ratios, "o-", markersize=10, color="#2ca02c", label="chi_max/χ₀ (exp3)")
    ax.axhline(SQRT2, color="red", ls="--", lw=2, label=f"√2 = {SQRT2:.4f} (soglia Jitterbug)")
    ax.axhline(1.0, color="gray", ls=":", label="1.0 (Cubottaedro/VE)")
    ax.set_title("Costante Jitterbug per livello", fontweight="bold")
    ax.set_xlabel("Livello L"); ax.set_ylabel("chi_max / chi_stable")
    ax.set_xticks(levels); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "jitterbug_scaling.png"), dpi=120)
    plt.close(fig)


def main():
    series = [load_series(l) for l in LEVELS]
    if all(s is None for s in series):
        print("Nessun file cosmo_L*_fast.h5 trovato in exp3.")
        sys.exit(1)

    print_stats(series)

    plot_triade(series)
    plot_conservazione(series)
    plot_campo_chi(series)
    has_topo = plot_vincoli(series)
    plot_jitterbug_scaling(series)

    print("\n  Grafici salvati in:", FIGDIR)
    for f in sorted(os.listdir(FIGDIR)):
        if f.endswith(".png"):
            print("   -", f)
    if not has_topo:
        print("  (nota: vincoli_topologici puo' essere vuoto se topological_validation assente)")


if __name__ == "__main__":
    main()
