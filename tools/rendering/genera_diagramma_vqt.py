"""
Genera lo schema delle interazioni del sistema VQT (motore Einstein-Cartan integrato).
Mostra elementi e relazioni: voxel/spinore -> torsione dallo spin (K2_spin) -> le quattro
facce tipo-GR (saturazione, espansione/gravita', tempo proprio, direzione del tempo).

ESECUZIONE:  python tools/rendering/genera_diagramma_vqt.py
OUTPUT:      docs/figures/vqt_sistema.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   "docs", "figures", "vqt_sistema.png")

# palette per categoria
COL = {
    "found": "#dbe9f6",   # fondamenta (statica)
    "voxel": "#fff2cc",    # voxel
    "spin":  "#ffe0b3",    # spinore
    "hub":   "#f8b26a",    # torsione (cuore)
    "chir":  "#e8d5f0",    # chiralita'
    "thr":   "#f4cccc",    # soglia rho*
    "expg":  "#d5e8d4",    # espansione/gravita'
    "time":  "#d0e0f0",    # tempo
    "sat":   "#f4cccc",    # saturazione
}

# box: id -> (x, y, w, h, testo, colore)
B = {
    "leech": (1.3, 9.2, 3.0, 0.9, "Reticolo di Leech\nN=24, accoppiamento W", "found"),
    "rgeo":  (1.3, 7.9, 3.0, 0.9, "R_geo = 4·24/23 = 4.174\nrigidezza topologica", "found"),
    "planck":(10.6, 9.2, 3.2, 0.9, "Scala di Planck\nℓ_voxel=ℓ_P, Θ=E_P", "found"),
    "voxel": (5.4, 9.25, 3.6, 0.85, "VOXEL\ncampo (χ, v)  +  spinore (θ, φ)", "voxel"),
    "spin":  (3.7, 6.7, 3.6, 1.15, "Spinore (θ, φ)\nβ/α = tan(θ/2)e^{iφ} = pendenza\n180° alternato · 720 esatto", "spin"),
    "chir":  (0.6, 5.0, 3.0, 1.1, "Chiralità (da θ)\nρ_SX=sin²(θ/2) materia\nρ_DX=cos²(θ/2) spazio", "chir"),
    "hub":   (7.7, 6.6, 4.3, 1.15, "K²_spin = χ₀² Σ Wᵢⱼ|nᵢ−nⱼ|²\nTORSIONE SORGENTATA DALLO SPIN\n(n = vettore di Bloch)", "hub"),
    "rho":   (8.8, 5.05, 2.6, 0.7, "ρ* = 2χ₀² = (√2χ₀)²\nsoglia derivata", "thr"),
    "sat":   (0.7, 2.7, 3.1, 1.2, "Saturazione / BOUNCE\nK²>ρ* → allinea gli spin\ntetto densità, no singolarità", "sat"),
    "exp":   (4.1, 3.0, 3.0, 1.0, "Espansione metrica  a\nH = bounce + emissione", "expg"),
    "grav":  (4.1, 1.3, 3.0, 1.0, "GRAVITÀ / clumping\nvuoti espandono > materia\nspinta = attrazione", "expg"),
    "gG":    (4.25, 5.0, 2.7, 0.7, "G emergente\nβ = Θ/R_phys", "expg"),
    "time":  (7.7, 3.0, 3.1, 1.0, "Tempo proprio ATTIVO\nf = 1 − K²_spin/ρ*\nmateria ~31% più lenta", "time"),
    "tdir":  (11.0, 2.6, 3.0, 1.5, "DIREZIONE DEL TEMPO\nτ_net = τ_DX − τ_SX\nspazio avanti, materia indietro\n→ netto avanti (spazio domina)", "time"),
}

# archi: (da, a, etichetta, stile)  stile: 'solid' relazione, 'dash' feedback
E = [
    ("leech", "rgeo", "", "solid"),
    ("rgeo", "gG", "β=Θ/R", "solid"),
    ("planck", "voxel", "scala", "solid"),
    ("voxel", "spin", "", "solid"),
    ("voxel", "spin", "β/α=pendenza", "solid"),
    ("spin", "hub", "spin→torsione", "solid"),
    ("spin", "chir", "", "solid"),
    ("hub", "sat", "", "solid"),
    ("hub", "exp", "", "solid"),
    ("hub", "time", "", "solid"),
    ("hub", "gG", "rigidezza", "solid"),
    ("rho", "hub", "", "dash"),
    ("sat", "spin", "feedback (allinea)", "dash"),
    ("exp", "hub", "a diluisce K²/a²", "dash"),
    ("exp", "grav", "", "solid"),
    ("gG", "exp", "modula", "solid"),
    ("time", "tdir", "", "solid"),
    ("chir", "tdir", "ρ_SX,ρ_DX", "solid"),
    ("time", "exp", "", "dash"),
]


def center(b):
    x, y, w, h, *_ = B[b]
    return (x + w / 2, y + h / 2)


def edge_point(b, toward):
    """punto sul bordo del box b verso 'toward' (centro->centro, clip al rettangolo)."""
    x, y, w, h, *_ = B[b]
    cx, cy = x + w / 2, y + h / 2
    tx, ty = toward
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2) / abs(dx) if dx != 0 else 1e9
    sy = (h / 2) / abs(dy) if dy != 0 else 1e9
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


fig, ax = plt.subplots(figsize=(14.5, 10.2))
ax.set_xlim(0, 14.5); ax.set_ylim(0.5, 10.6); ax.axis("off")

# archi prima (sotto i box)
for a, b, lab, st in E:
    pa = edge_point(a, center(b)); pb = edge_point(b, center(a))
    dashed = (st == "dash")
    arr = FancyArrowPatch(pa, pb, arrowstyle="-|>", mutation_scale=14,
                          lw=1.4, color="#888" if dashed else "#444",
                          linestyle=":" if dashed else "-",
                          connectionstyle="arc3,rad=0.04", zorder=1)
    ax.add_patch(arr)
    if lab:
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        ax.text(mx, my, lab, fontsize=7.0, ha="center", va="center",
                color="#555", style="italic",
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85), zorder=2)

# box
for bid, (x, y, w, h, txt, col) in B.items():
    fb = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                        fc=COL[col], ec="#333", lw=1.3, zorder=3)
    ax.add_patch(fb)
    weight = "bold" if bid in ("hub", "tdir", "grav") else "normal"
    ax.text(x + w / 2, y + h / 2, txt, fontsize=8.0, ha="center", va="center",
            weight=weight, zorder=4)

ax.text(7.25, 10.35, "VQT — Sistema Einstein-Cartan integrato: elementi e relazioni",
        fontsize=13, weight="bold", ha="center")
# legenda
ax.plot([0.8, 1.6], [0.85, 0.85], "-", color="#444", lw=1.4)
ax.text(1.75, 0.85, "relazione (genera / guida)", fontsize=7.5, va="center")
ax.plot([5.0, 5.8], [0.85, 0.85], ":", color="#888", lw=1.4)
ax.text(5.95, 0.85, "feedback (auto-regolazione)", fontsize=7.5, va="center")

plt.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"salvato: {OUT}")
