#!/usr/bin/env python3
"""
Genera le figure geometriche fondamentali per TOPOLOGICAL_DYNAMICS.md §0.

Figure prodotte:
  fig0_chirality.png      -- Chiralità alternata ai punti di flesso
  fig0_closure_720.png    -- Chiusura spinoriale 720° (condizione spinore)
  fig0_dim_genesis.png    -- Genesi dimensionale L0→L1→L2→L3→4D

Eseguire da VQT_repo/:
  python docs/figures/generate_vqt_geometry_figures.py
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.proj3d import proj_transform
from pathlib import Path

OUT = Path(__file__).parent
STYLE = {
    "axes.facecolor":  "#0d1117",
    "figure.facecolor": "#0d1117",
    "text.color":       "#e6edf3",
    "axes.labelcolor":  "#e6edf3",
    "xtick.color":      "#8b949e",
    "ytick.color":      "#8b949e",
    "axes.edgecolor":   "#30363d",
    "grid.color":       "#21262d",
    "grid.linestyle":   "--",
    "grid.alpha":       0.4,
}
plt.rcParams.update(STYLE)

RED   = "#f85149"
BLUE  = "#58a6ff"
GREEN = "#3fb950"
GOLD  = "#e3b341"
WHITE = "#e6edf3"
DIM   = "#8b949e"


# ============================================================================
# FIG 1 — Chiralità Alternata ai Punti di Flesso
# ============================================================================

def make_chirality_figure():
    fig = plt.figure(figsize=(14, 5), facecolor="#0d1117")
    ax = fig.add_subplot(111, projection="3d", facecolor="#0d1117")

    # Parametrizzazione: curva planare sinusoidale come base
    t = np.linspace(0, 4 * np.pi, 2000)
    x = t / (4 * np.pi)        # x: arco normalizzato [0,1]
    y = np.sin(t)               # y: campo chi (sinusoide)
    z = np.zeros_like(t)        # z: direzione di torsione

    # Punti di flesso: dove sin(t) = 0, t = k*pi
    inflection_t = [np.pi, 2 * np.pi, 3 * np.pi]
    inflection_idx = [np.argmin(np.abs(t - ti)) for ti in inflection_t]

    # Aggiungi torsione alternata intorno a ogni flesso
    # In ogni flesso il manifold "gira" di ±180° fuori dal piano
    for k, ti in enumerate(inflection_t):
        chirality = (-1) ** k
        width = 0.6
        mask = np.abs(t - ti) < width
        # Torsione smussata: ribbon che ruota fuori dal piano y-z
        phi = chirality * np.pi * np.exp(-((t[mask] - ti) ** 2) / (2 * 0.08))
        z[mask] += np.sin(phi) * 0.35

    # Plot curva principale — colora per chiralità (segno di dz/dt)
    dzdt = np.gradient(z, t)
    norm_dz = dzdt / (np.abs(dzdt).max() + 1e-9)
    cmap = plt.cm.RdBu
    for i in range(len(t) - 1):
        c = cmap(0.5 + 0.5 * np.tanh(norm_dz[i] * 6))
        ax.plot(x[i:i+2], y[i:i+2], z[i:i+2], color=c, linewidth=2.5, alpha=0.9)

    # Marker ai punti di flesso con label chiralità
    colors_chiral = [RED, BLUE, RED]
    labels_chiral = ["+180°", "−180°", "+180°"]
    for k, idx in enumerate(inflection_idx):
        ax.scatter(x[idx], y[idx], z[idx], s=160, c=colors_chiral[k],
                   zorder=10, edgecolors=WHITE, linewidths=1)
        ax.text(x[idx], y[idx] + 0.15, z[idx] + 0.1,
                f"  {labels_chiral[k]}", color=colors_chiral[k],
                fontsize=11, fontweight="bold")

    # Piano di riferimento (y-x)
    xx, yy = np.meshgrid([0, 1], [-1, 1])
    ax.plot_surface(xx, yy, np.zeros_like(xx), alpha=0.06, color=BLUE)

    # Frecce per indicare direzione torsione
    for k, idx in enumerate(inflection_idx):
        sign = (-1) ** k
        ax.quiver(x[idx], y[idx], z[idx],
                  0, 0, sign * 0.4,
                  color=colors_chiral[k], arrow_length_ratio=0.4,
                  linewidth=2, alpha=0.8)

    ax.set_xlabel("Arco s / N", color=DIM, labelpad=8)
    ax.set_ylabel("χ(s,t)", color=DIM, labelpad=8)
    ax.set_zlabel("Torsione locale", color=DIM, labelpad=8)
    ax.set_title("Chiralità Alternata ai Punti di Flesso  |  VQT §0.3",
                 color=WHITE, fontsize=13, pad=14)

    # Legenda
    red_p  = mpatches.Patch(color=RED,  label="Chiralità + (torsione +180°)")
    blue_p = mpatches.Patch(color=BLUE, label="Chiralità − (torsione −180°)")
    ax.legend(handles=[red_p, blue_p], loc="upper left",
              framealpha=0.3, labelcolor=WHITE, fontsize=10)

    ax.view_init(elev=22, azim=-50)
    ax.set_box_aspect([2.5, 1, 0.6])
    plt.tight_layout()

    out = OUT / "fig0_chirality.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    print(f"  [OK] {out}")


# ============================================================================
# FIG 2 — Chiusura Spinoriale 720°
# ============================================================================

def make_spinorial_closure_figure():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor="#0d1117")

    # ---- LEFT: confronto 360° vs 720° ----
    ax1 = axes[0]
    ax1.set_facecolor("#0d1117")
    theta_360 = np.linspace(0, 2 * np.pi, 500)
    theta_720 = np.linspace(0, 4 * np.pi, 500)

    # Curva ordinaria — chiusura 360°: cerchio
    r_360 = 1.0
    ax1.plot(r_360 * np.cos(theta_360), r_360 * np.sin(theta_360),
             color=BLUE, linewidth=2.5, label=r"Chiusura 360° (bosone)", alpha=0.7)
    ax1.scatter([r_360], [0], s=120, c=BLUE, zorder=10)

    # Curva spinoriale — chiusura 720°: spirale che raddoppia
    r_720 = 0.55 + 0.45 * theta_720 / (4 * np.pi)   # raggio cresce: andata+ritorno
    x_720 = r_720 * np.cos(theta_720 / 2)            # frequenza dimezzata
    y_720 = r_720 * np.sin(theta_720 / 2)

    # Colora per fase: 0→2π (primo giro), 2π→4π (secondo giro)
    n = len(theta_720)
    ax1.plot(x_720[:n//2], y_720[:n//2], color=RED, linewidth=2.5,
             linestyle="--", label=r"Primo giro (0→2π)", alpha=0.9)
    ax1.plot(x_720[n//2:], y_720[n//2:], color=GOLD, linewidth=2.5,
             label=r"Secondo giro (2π→4π)", alpha=0.9)
    ax1.scatter([x_720[-1]], [y_720[-1]], s=120, c=GOLD,
                zorder=10, marker="*")
    ax1.annotate("CHIUSURA\n720°", xy=(x_720[-1], y_720[-1]),
                 xytext=(0.1, -0.9), color=GOLD, fontsize=10, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5))

    ax1.set_xlim(-1.3, 1.3)
    ax1.set_ylim(-1.1, 1.1)
    ax1.set_aspect("equal")
    ax1.set_title("Bosone vs Spinore: Tipo di Chiusura", color=WHITE, fontsize=12)
    ax1.legend(framealpha=0.2, labelcolor=WHITE, fontsize=9)
    ax1.grid(True, alpha=0.2)
    ax1.axhline(0, color=DIM, linewidth=0.5)
    ax1.axvline(0, color=DIM, linewidth=0.5)

    # ---- RIGHT: torsione globale ∮ dθ = 4π ----
    ax2 = axes[1]
    ax2.set_facecolor("#0d1117")

    s = np.linspace(0, 1, 500)            # arco normalizzato [0,1]
    torsion_cum = 4 * np.pi * s           # torsione cumulata lineare

    # Evidenzia π, 2π, 4π
    ax2.plot(s, torsion_cum, color=GREEN, linewidth=2.5)
    ax2.fill_between(s, 0, torsion_cum, alpha=0.12, color=GREEN)

    milestones = [(0.25, np.pi, "π"),
                  (0.5,  2*np.pi, "2π"),
                  (0.75, 3*np.pi, "3π"),
                  (1.0,  4*np.pi, "4π  ←  CHIUSURA")]
    for sx, ty, lab in milestones:
        ax2.axhline(ty, color=DIM, linewidth=0.7, linestyle=":")
        ax2.scatter([sx], [ty], s=80, c=GOLD if "CHIUSURA" in lab else WHITE,
                    zorder=10)
        ax2.text(sx + 0.02, ty + 0.15, lab,
                 color=GOLD if "CHIUSURA" in lab else WHITE, fontsize=10)

    ax2.set_xlabel("Arco s (fraz. del manifold)", color=DIM)
    ax2.set_ylabel(r"$\oint d\theta_{\mathrm{tors}}$ [rad]", color=DIM)
    ax2.set_title(r"Torsione Globale Cumulata: $\oint d\theta = 4\pi$",
                  color=WHITE, fontsize=12)
    ax2.set_yticks([0, np.pi, 2*np.pi, 3*np.pi, 4*np.pi])
    ax2.set_yticklabels(["0", "π", "2π", "3π", "4π"], color=WHITE)
    ax2.set_xlim(0, 1.05)
    ax2.grid(True, alpha=0.2)

    fig.suptitle("Chiusura Spinoriale 720°  |  VQT §0.4",
                 color=WHITE, fontsize=13, y=1.01)
    plt.tight_layout()

    out = OUT / "fig0_closure_720.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    print(f"  [OK] {out}")


# ============================================================================
# FIG 3 — Genesi Dimensionale L0→L1→L2→L3
# ============================================================================

def make_dimensional_genesis_figure():
    fig = plt.figure(figsize=(16, 7), facecolor="#0d1117")

    levels = [
        ("L0",  1,    "Segmento\ndi Planck", "0D → punto",   "#8b949e"),
        ("L1", 24,    "Anello\nspinoriale",  "1D → curva",   BLUE),
        ("L2", 576,   "Foglio\ndi anelli",   "2D → piano",   GREEN),
        ("L3", 13824, "Volume\ndi fogli",    "3D → spazio",  GOLD),
    ]

    n = len(levels)
    axes_list = []
    for i, (label, N, name, dim_str, color) in enumerate(levels):
        ax = fig.add_subplot(1, n, i + 1, facecolor="#0d1117")
        axes_list.append(ax)

        if i == 0:
            # L0: singolo punto
            ax.scatter([0.5], [0.5], s=300, c=color, zorder=10)
            ax.text(0.5, 0.62, r"$\ell_P$", ha="center", color=color,
                    fontsize=13, fontweight="bold")
            ax.plot([0.3, 0.7], [0.5, 0.5], color=color, linewidth=4)

        elif i == 1:
            # L1: cerchio (anello chiuso)
            theta = np.linspace(0, 2 * np.pi, 200)
            x_c = 0.5 + 0.35 * np.cos(theta)
            y_c = 0.5 + 0.35 * np.sin(theta)
            # Colora alternando chirality
            for j in range(0, len(theta) - 1, 2):
                col = RED if (j // (len(theta) // 12)) % 2 == 0 else BLUE
                ax.plot(x_c[j:j+2], y_c[j:j+2], color=col, linewidth=3)
            # Nodi (flessi)
            for k in range(12):
                tk = 2 * np.pi * k / 12
                ax.scatter([0.5 + 0.35 * np.cos(tk)],
                           [0.5 + 0.35 * np.sin(tk)],
                           s=30, c=WHITE, zorder=10)
            ax.text(0.5, 0.04, "24 segmenti", ha="center", color=DIM, fontsize=9)

        elif i == 2:
            # L2: griglia di piccoli cerchi
            cols_per_row = 5
            rows = 5
            r_small = 0.07
            xs = np.linspace(0.15, 0.85, cols_per_row)
            ys = np.linspace(0.15, 0.85, rows)
            theta_s = np.linspace(0, 2 * np.pi, 40)
            for ri, y0 in enumerate(ys):
                for ci, x0 in enumerate(xs):
                    alt = (ri + ci) % 2
                    c1, c2 = (RED, BLUE) if alt == 0 else (BLUE, RED)
                    half = len(theta_s) // 2
                    ax.plot(x0 + r_small * np.cos(theta_s[:half]),
                            y0 + r_small * np.sin(theta_s[:half]),
                            color=c1, linewidth=1.5)
                    ax.plot(x0 + r_small * np.cos(theta_s[half:]),
                            y0 + r_small * np.sin(theta_s[half:]),
                            color=c2, linewidth=1.5)
            # Connessioni tra anelli
            for ri in range(rows - 1):
                for ci in range(cols_per_row - 1):
                    ax.plot([xs[ci], xs[ci+1]], [ys[ri], ys[ri]],
                            color=DIM, linewidth=0.5, alpha=0.4)
            ax.text(0.5, 0.01, "576 segmenti (24 anelli)", ha="center",
                    color=DIM, fontsize=9)

        else:
            # L3: cubo prospettico + asse τ (quarta dimensione)
            # Vista prospettica 3D semplice
            # Cubo wireframe
            def cube_edges():
                v = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],
                               [0,0,1],[1,0,1],[1,1,1],[0,1,1]], dtype=float)
                edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
                         (0,4),(1,5),(2,6),(3,7)]
                return v, edges

            # Proiezione isometrica semplice
            def iso(p):
                a, b = np.radians(30), np.radians(30)
                M = np.array([
                    [np.cos(b), -np.cos(a)*np.sin(b)],
                    [np.sin(b),  np.cos(a)*np.cos(b)]
                ])
                return M @ p[:2] + np.array([0, p[2]*0.5])

            v, edges = cube_edges()
            v = v * 0.5   # scala
            off = np.array([0.25, 0.22])
            for e0, e1 in edges:
                p0 = iso(v[e0]) + off
                p1 = iso(v[e1]) + off
                ax.plot([p0[0], p1[0]], [p0[1], p1[1]],
                        color=GOLD, linewidth=1.8, alpha=0.7)

            # Asse τ (quarta dimensione) — freccia colore separato
            ax.annotate("", xy=(0.92, 0.85), xytext=(0.78, 0.35),
                        arrowprops=dict(arrowstyle="->", color=GREEN,
                                        lw=2.5, mutation_scale=15))
            ax.text(0.93, 0.85, r"$\tau_i$", color=GREEN,
                    fontsize=14, fontweight="bold")
            ax.text(0.74, 0.12, "13824 segmenti\n(576 fogli)", ha="center",
                    color=DIM, fontsize=9)

        # Stile comune
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.axis("off")

        # Titolo del pannello
        ax.set_title(f"{label}  ·  N={N:,}\n{name}\n{dim_str}",
                     color=color, fontsize=11, fontweight="bold", pad=10)

    # Frecce di connessione tra pannelli
    for i in range(n - 1):
        fig.text(0.21 + i * 0.195, 0.5, "→",
                 ha="center", va="center", color=WHITE, fontsize=22,
                 fontweight="bold", transform=fig.transFigure)

    # Asse τ come annotazione globale
    fig.text(0.5, 0.02,
             r"La quarta dimensione $t_{\rm macro} = \sum_i \tau_i / N$"
             r"  emerge dall'evoluzione del manifold — non è un'assunzione",
             ha="center", color=GREEN, fontsize=11, style="italic")

    fig.suptitle("Genesi delle 4 Dimensioni per Avvolgimento Frattale  |  VQT §0.5",
                 color=WHITE, fontsize=13, y=1.01)

    plt.tight_layout(rect=[0, 0.06, 1, 1])

    out = OUT / "fig0_dim_genesis.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    print(f"  [OK] {out}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Generazione figure VQT §0 — Fondazione Geometrica")
    print(f"Output: {OUT}")
    print()
    make_chirality_figure()
    make_spinorial_closure_figure()
    make_dimensional_genesis_figure()
    print("\nDone. 3 figure generate.")
