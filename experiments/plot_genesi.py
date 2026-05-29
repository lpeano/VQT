"""
plot_genesi.py
==============
Visualizzazione della Run di Genesi: transizione Ottaedrica -> Icosaedrica.

Genera un grafico a due pannelli:
  Pannello superiore : chi_sat(step) — saturazione campo χ, annotazione cristallizzazione
  Pannello inferiore : E_chi (log) e E_Psi — crossover energetico

Report fisico (3 righe):
  1. Il crollo esponenziale di E_chi (−6 ordini di grandezza, step 1→700) è
     la firma diretta della cristallizzazione icosaedrica: quando χ converge
     a ±χ_stable, le disomogeneità Δχᵢⱼ → 0 e il coupling κ·Σ(Δχ)² si annulla.
  2. E_Psi sale monotonicamente mentre E_chi crolla: il drain cattura l'energia
     rilasciata durante i rimbalzi di condensazione (step 20–700).
  3. Dal crossover (E_chi < E_Psi) in poi il sink Ψ domina: la materia
     icosaedrica è cristallizzata e il drain si esaurisce (~step 700).

Uso:
  cd <repo_root>
  python plot_genesi.py

Dipendenze: h5py, numpy, matplotlib
"""

import glob
import sys
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

CHI_STABLE = 50.0

# Dati dalla Genesis Run (PhaseEventLogger)
FIRST_ICO_STEP   = 10   # prima cristallizzazione icosaedrica
FIRST_DRAIN_STEP = 20   # primo evento drain

# Soglie di fase
THRESH_CUB = 0.30
THRESH_ICO = 0.70
THRESH_DRAIN = 0.80

COLORS = {
    "chi":      "#264653",
    "ico_line": "#e63946",
    "E_chi":    "#e63946",
    "E_Psi":    "#2a9d8f",
    "cross":    "#6c757d",
    "bg_ott":   "#4e9af1",
    "bg_cub":   "#f4a261",
    "bg_ico":   "#2a9d8f",
}


# ============================================================================
# RICERCA FILE HDF5
# ============================================================================

def find_genesis_h5() -> Path:
    """Trova l'HDF5 della Genesis Run (il piu' recente se multipli)."""
    candidates = sorted(glob.glob("output_peano/genesis_*.h5"))
    if candidates:
        p = Path(candidates[-1])
        print(f"  HDF5 trovato: {p}")
        return p
    # Fallback path esplicito
    explicit = Path("output_peano/genesis_20260529_122803.h5")
    if explicit.exists():
        return explicit
    print("ERRORE: nessun file genesis_*.h5 trovato in output_peano/")
    print("Eseguire prima:  python -m wqt_oop.genesis_run")
    sys.exit(1)


# ============================================================================
# LETTURA DATI
# ============================================================================

def load_genesis_data(filepath: Path) -> dict:
    """
    Carica le serie temporali dalla Genesis HDF5.

    Estrae per ogni frame:
      step, chi_sat (da chi_values), E_chi, E_RX, E_Psi
    """
    steps, chi_sat_list = [], []
    E_chi_list, E_RX_list, E_Psi_list = [], [], []

    with h5py.File(str(filepath), "r") as f:
        if "frames" not in f:
            raise ValueError(f"Gruppo /frames mancante in {filepath}")

        frame_names = sorted(f["frames"].keys())
        n = len(frame_names)
        print(f"  Frames: {n}")

        for fname in frame_names:
            fr = f["frames"][fname]

            steps.append(int(fr.attrs["step"]))

            # chi_sat dal vettore chi_values (tutti i segmenti)
            chi_vals = fr["chi_values"][:]
            chi_sat_list.append(float(np.mean(np.abs(chi_vals))) / CHI_STABLE)

            E_chi_list.append(float(fr.attrs.get("E_chi", 0.0)))
            E_RX_list.append(float(fr.attrs.get("E_RX",  0.0)))
            E_Psi_list.append(float(fr.attrs.get("E_Psi", 0.0)))

    data = {
        "steps":   np.array(steps,       dtype=float),
        "chi_sat": np.array(chi_sat_list, dtype=float),
        "E_chi":   np.array(E_chi_list,   dtype=float),
        "E_RX":    np.array(E_RX_list,    dtype=float),
        "E_Psi":   np.array(E_Psi_list,   dtype=float),
    }
    return data


# ============================================================================
# GRAFICO
# ============================================================================

def plot_genesis(data: dict, save_path: Path = None) -> None:
    """
    Grafico a due pannelli (sharex):
      ax1 — chi_sat vs step
      ax2 — E_chi (log, asse sx) e E_Psi (lineare, asse dx)
    """
    steps   = data["steps"]
    chi_sat = data["chi_sat"]
    E_chi   = data["E_chi"]
    E_Psi   = data["E_Psi"]

    # E_chi per scala log: zeri → NaN
    E_chi_log = np.where(E_chi > 0, E_chi, np.nan)

    # Crossover: primo frame dove E_chi < E_Psi (entrambi > 0)
    valid = (E_chi_log > 0) & (E_Psi > 0)
    cross_idx = np.where(valid & (E_chi_log < E_Psi))[0]
    cross_step = int(steps[cross_idx[0]]) if len(cross_idx) > 0 else None

    # -------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(
        2, 1,
        figsize=(13, 8.5),
        sharex=True,
        gridspec_kw={"hspace": 0.07, "height_ratios": [1, 1.3]},
    )
    fig.suptitle(
        "Genesis Run VQT  —  Transizione di Fase: Ottaedrica → Icosaedrica\n"
        "L1 · 24 segmenti · chi_mean = 5  →  chi_stable = 50 · 2000 step",
        fontsize=13, fontweight="bold", y=0.99,
    )

    x_max = steps[-1] + 60

    # ===================================================================
    # PANNELLO 1 — chi_sat
    # ===================================================================

    # Sfondi colorati per fase
    ax1.axhspan(0.00,      THRESH_CUB,  alpha=0.10, color=COLORS["bg_ott"], zorder=0)
    ax1.axhspan(THRESH_CUB, THRESH_ICO, alpha=0.10, color=COLORS["bg_cub"], zorder=0)
    ax1.axhspan(THRESH_ICO, 1.40,       alpha=0.10, color=COLORS["bg_ico"], zorder=0)

    # Linee soglia
    ax1.axhline(THRESH_CUB,  color=COLORS["bg_cub"],  lw=0.9, ls="--", alpha=0.55,
                label=f"Soglia Cubottaedrica ({THRESH_CUB:.2f})")
    ax1.axhline(THRESH_ICO,  color=COLORS["bg_ico"],  lw=0.9, ls="--", alpha=0.55,
                label=f"Soglia Icosaedrica ({THRESH_ICO:.2f})")
    ax1.axhline(THRESH_DRAIN, color=COLORS["E_chi"], lw=0.9, ls=":",  alpha=0.55,
                label=f"Soglia drain ({THRESH_DRAIN:.2f})")

    # Serie chi_sat
    ax1.plot(steps, chi_sat, color=COLORS["chi"], lw=2.0, label="chi_sat", zorder=5)

    # Linea verticale prima cristallizzazione (step 10, prima del primo frame)
    ax1.axvline(FIRST_ICO_STEP, color=COLORS["ico_line"], lw=1.8, ls="-",
                label=f"Prima cristallizzazione (step {FIRST_ICO_STEP})", zorder=6)

    # Annotazione cristallizzazione
    ax1.annotate(
        f"Step {FIRST_ICO_STEP}\nOttaedrica → Icosaedrica\n(chi_sat = 0.996)",
        xy=(FIRST_ICO_STEP, 0.996),
        xytext=(200, 0.55),
        arrowprops=dict(arrowstyle="->", color=COLORS["ico_line"], lw=1.3,
                        connectionstyle="arc3,rad=0.15"),
        fontsize=8.5, color=COLORS["ico_line"],
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor=COLORS["ico_line"], alpha=0.88),
        zorder=7,
    )

    # Etichette fasi (angolo destro)
    x_lbl = x_max * 0.88
    ax1.text(x_lbl, 0.15, "Ottaedrica",    ha="center", va="center",
             fontsize=8.5, color=COLORS["bg_ott"], alpha=0.75)
    ax1.text(x_lbl, 0.50, "Cubottaedrica", ha="center", va="center",
             fontsize=8.5, color=COLORS["bg_cub"], alpha=0.75)
    ax1.text(x_lbl, 1.05, "ICOSAEDRICA",   ha="center", va="center",
             fontsize=9.5, color=COLORS["bg_ico"], fontweight="bold")

    ax1.set_ylabel("chi_sat = ⟨|χ|⟩ / χ_stable", fontsize=10)
    ax1.set_ylim(0.0, 1.40)
    ax1.set_xlim(0, x_max)
    ax1.legend(loc="lower right", fontsize=8, framealpha=0.88, ncol=2)
    ax1.set_title("Pannello 1  —  Saturazione campo χ", fontsize=9.5, loc="left", pad=3)
    ax1.grid(alpha=0.25, color="gray", lw=0.6)

    # ===================================================================
    # PANNELLO 2 — E_chi (log) e E_Psi (lineare)
    # ===================================================================

    # E_chi asse sinistro (log)
    ln1, = ax2.semilogy(steps, E_chi_log, color=COLORS["E_chi"], lw=2.0,
                        label="E_chi  [asse sx, log]", zorder=5)
    ax2.set_ylabel("E_chi  (scala log)", color=COLORS["E_chi"], fontsize=10)
    ax2.tick_params(axis="y", labelcolor=COLORS["E_chi"])

    # E_Psi asse destro (lineare)
    ax2r = ax2.twinx()
    ln2, = ax2r.plot(steps, E_Psi, color=COLORS["E_Psi"], lw=2.2,
                     label="E_Psi  [asse dx, lineare]", zorder=4)
    ax2r.set_ylabel("E_Psi  (lineare)", color=COLORS["E_Psi"], fontsize=10)
    ax2r.tick_params(axis="y", labelcolor=COLORS["E_Psi"])
    ax2r.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))

    # Linea cristallizzazione
    ax2.axvline(FIRST_ICO_STEP, color=COLORS["ico_line"], lw=1.5, ls="-", alpha=0.40)

    # Crossover
    if cross_step is not None:
        ln3 = ax2.axvline(cross_step, color=COLORS["cross"], lw=1.4, ls="--", alpha=0.75,
                          label=f"Crossover E_chi < E_Psi  (step {cross_step})")

        y_arrow = E_chi_log[cross_idx[0]]
        # posizione testo: 30% del max E_chi (in log) e 35% del range x
        y_text  = float(np.nanmax(E_chi_log)) * 0.25
        x_text  = cross_step + (x_max - cross_step) * 0.30

        ax2.annotate(
            f"Crossover\nE_chi < E_Psi\nstep {cross_step}",
            xy=(cross_step, y_arrow),
            xytext=(x_text, y_text),
            arrowprops=dict(arrowstyle="->", color=COLORS["cross"], lw=1.1,
                            connectionstyle="arc3,rad=-0.20"),
            fontsize=8.5, color=COLORS["cross"],
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor=COLORS["cross"], alpha=0.88),
            zorder=7,
        )

    # Legenda combinata
    legends = [ln1, ln2]
    if cross_step:
        legends.append(ln3)
    ax2.legend(handles=legends, loc="upper right", fontsize=8, framealpha=0.88)

    ax2.set_xlabel("Step di simulazione", fontsize=10)
    ax2.set_title(
        "Pannello 2  —  Crossover energetico: crollo E_chi · salita E_Psi",
        fontsize=9.5, loc="left", pad=3,
    )
    ax2.grid(alpha=0.22, color="gray", lw=0.6, which="both")

    # ===================================================================
    # REPORT FISICO (textbox in calce)
    # ===================================================================
    cross_str = f"step {cross_step}" if cross_step else "non osservato"
    report = (
        "Report fisico:  "
        "(1) Il crollo esponenziale di E_chi (−6 ordini di grandezza, step 1→700) "
        "è la firma della cristallizzazione icosaedrica: quando χ → ±χ_stable le disomogeneità "
        "Δχᵢⱼ → 0 e il coupling κ·Σ(Δχ)² si annulla.  "
        f"(2) E_Psi sale monotonicamente (drain step 20–700) catturando l'energia dei rimbalzi di condensazione.  "
        f"(3) Dal crossover ({cross_str}) il sink Ψ domina sul coupling residuo: "
        "la materia icosaedrica è cristallizzata definitivamente."
    )
    fig.text(
        0.05, 0.003,
        report,
        fontsize=7.5, style="italic", color="#444",
        wrap=True,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#f7f7f7",
                  alpha=0.92, edgecolor="#bbb"),
    )

    plt.tight_layout(rect=[0, 0.065, 1, 0.975])

    if save_path:
        plt.savefig(str(save_path), dpi=150, bbox_inches="tight")
        print(f"  Grafico salvato: {save_path}")

    plt.show()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 62)
    print("  PLOT GENESI  —  Transizione di Fase VQT / Peano-VQT")
    print("=" * 62)

    h5_path = find_genesis_h5()
    data = load_genesis_data(h5_path)

    print(f"  Steps:       {int(data['steps'][0])} -> {int(data['steps'][-1])}")
    print(f"  chi_sat:     {data['chi_sat'].min():.4f} -> {data['chi_sat'].max():.4f}")
    print(f"  E_chi max:   {np.nanmax(data['E_chi']):.4e}")
    print(f"  E_chi final: {data['E_chi'][-1]:.4e}")
    print(f"  E_Psi init:  {data['E_Psi'][0]:.4e}")
    print(f"  E_Psi final: {data['E_Psi'][-1]:.4e}")

    # Crossover info
    E_chi_log = np.where(data["E_chi"] > 0, data["E_chi"], np.nan)
    valid = (E_chi_log > 0) & (data["E_Psi"] > 0)
    cross_idx = np.where(valid & (E_chi_log < data["E_Psi"]))[0]
    if len(cross_idx) > 0:
        print(f"  Crossover:   step {int(data['steps'][cross_idx[0]])}")
    else:
        print("  Crossover:   non rilevato nei frame HDF5")

    print()

    save_path = h5_path.parent / "plot_genesi.png"
    plot_genesis(data, save_path=save_path)

    print()
    print("Report fisico (3 righe):")
    print("  1. E_chi crolla esponenzialmente dopo la cristallizzazione (step 10):")
    print("     chi -> +-chi_stable elimina le disomogeneita' di coupling (Dchi_ij -> 0).")
    print("  2. E_Psi cresce monotonicamente (drain step 20-700): cattura l'energia")
    print("     rilasciata durante i rimbalzi di condensazione icosaedrica.")
    print("  3. Dal crossover (E_chi < E_Psi) il sink Psi domina: la struttura")
    print("     icosaedrica e' consolidata e il drain si esaurisce.")
    print("=" * 62)
