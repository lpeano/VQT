"""
Genera lo schema delle interazioni del sistema VQT (motore Einstein-Cartan integrato),
con pannello di TUTTE le costanti (stato: derivato/postulato/topologico/eliminato) e di
TUTTE le formule di derivazione.

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

COL = {
    "found": "#dbe9f6", "voxel": "#fff2cc", "spin": "#ffe0b3", "hub": "#f8b26a",
    "chir": "#e8d5f0", "thr": "#f4cccc", "expg": "#d5e8d4", "time": "#d0e0f0",
    "sat": "#f4cccc", "panel": "#fbfbf6",
}
# colori per stato delle costanti
STAT = {"der": "#1b7837", "fis": "#2166ac", "top": "#762a83",
        "post": "#b35806", "elim": "#b2182b"}

# box del diagramma: id -> (x, y, w, h, testo, colore)
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
E = [
    ("leech", "rgeo", "", "solid"), ("rgeo", "gG", "β=Θ/R", "solid"),
    ("planck", "voxel", "scala", "solid"), ("voxel", "spin", "", "solid"),
    ("voxel", "spin", "β/α=pendenza", "solid"), ("spin", "hub", "spin→torsione", "solid"),
    ("spin", "chir", "", "solid"), ("hub", "sat", "", "solid"), ("hub", "exp", "", "solid"),
    ("hub", "time", "", "solid"), ("hub", "gG", "rigidezza", "solid"),
    ("rho", "hub", "", "dash"), ("sat", "spin", "feedback (allinea)", "dash"),
    ("exp", "hub", "a diluisce K²/a²", "dash"), ("exp", "grav", "", "solid"),
    ("gG", "exp", "modula", "solid"), ("time", "tdir", "", "solid"),
    ("chir", "tdir", "ρ_SX,ρ_DX", "solid"), ("time", "exp", "", "dash"),
]

# costanti: (formula mathtext, stato, descrizione)
COSTANTI = [
    (r"$N=24$", "der", "reticolo di Leech (numero di contatto)"),
    (r"$R_{geo}=4N/(N-1)=4\cdot24/23=4.174$", "der", "rigidezza topologica (spettro Laplaciano)"),
    (r"$\rho^*=2\chi_0^2=(\sqrt{2}\,\chi_0)^2$", "der", "soglia (scala parete; √2 Jitterbug)"),
    (r"$180^\circ=\pi,\ \ 720^\circ=4\pi$", "top", "twist / chiusura spin-1/2"),
    (r"$\chi_0$ (VEV)", "fis", "minimo del doppio pozzo (chi_stable)"),
    (r"$\Theta=E_{Planck},\ \ \ell_{vox}=\ell_{Planck}$", "post", "ancoraggio: fondo gerarchia = Planck"),
    (r"$coeff\ (\sim T_{eff})$", "post", "tasso di emissione di fondo (da calibrare)"),
    (r"$\alpha_K,\ \kappa,\ \lambda{\sim}24^{2L},\ \gamma$", "elim", "leggi di scala postulate: DISSOLTE"),
]
# formule di derivazione (mathtext)
FORMULE = [
    r"$\psi=\cos\frac{\theta}{2}|0\rangle+\sin\frac{\theta}{2}\,e^{i\phi}|1\rangle$",
    r"$\beta/\alpha=\tan(\theta/2)\,e^{i\phi}=$ pendenza del kink",
    r"$\rho_{SX}=\sin^2\frac{\theta}{2},\ \ \rho_{DX}=\cos^2\frac{\theta}{2}$",
    r"$\tau_i=\frac{4\pi}{N}+\pi(-1)^i,\ \ \sum_i\tau_i=4\pi$ (720 esatto)",
    r"$\mathbf{n}=(\sin\theta\cos\phi,\ \sin\theta\sin\phi,\ \cos\theta)$",
    r"$K^2_{spin}=\chi_0^2\sum_j W_{ij}\,|\mathbf{n}_i-\mathbf{n}_j|^2$",
    r"$R_{phys}=R_{geo}/a^2,\ \ R_{loc}=R_{geo}(1+K^2/\rho^*)$",
    r"$\beta_{sat}=\Theta/R_{phys}$  (G emergente)",
    r"$H=\beta_{sat}\langle(\frac{K^2}{a^2}-\rho^*)_+\rangle+\frac{coeff}{1+K^2/\rho^*}$",
    r"$a^*=\sqrt{K^2_{max}/\rho^*}$  (punto fisso espansione)",
    r"$f=1-\langle K^2_{spin}\rangle/\rho^*,\ \ dt_{loc}=f\,dt$",
    r"$\tau_{SX}=\int f\,\rho_{SX},\ \ \tau_{DX}=\int f\,\rho_{DX}$",
    r"$\tau_{net}=\tau_{DX}-\tau_{SX}=\int f\cos\theta\,dt$",
    r"$\ell_L=24^{L/d}\,\ell_{Planck}$  (d=3: protone $\sim$L43)",
]


def center(b):
    x, y, w, h, *_ = B[b]; return (x + w / 2, y + h / 2)


def edge_point(b, toward):
    x, y, w, h, *_ = B[b]; cx, cy = x + w / 2, y + h / 2
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    s = min((w / 2) / abs(dx) if dx else 1e9, (h / 2) / abs(dy) if dy else 1e9)
    return cx + dx * s, cy + dy * s


fig, ax = plt.subplots(figsize=(21, 10.6))
ax.set_xlim(0, 21); ax.set_ylim(0.4, 10.7); ax.axis("off")

# --- diagramma (sinistra) ---
for a, b, lab, st in E:
    pa = edge_point(a, center(b)); pb = edge_point(b, center(a))
    dashed = (st == "dash")
    ax.add_patch(FancyArrowPatch(pa, pb, arrowstyle="-|>", mutation_scale=14, lw=1.4,
                 color="#888" if dashed else "#444", linestyle=":" if dashed else "-",
                 connectionstyle="arc3,rad=0.04", zorder=1))
    if lab:
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        ax.text(mx, my, lab, fontsize=7.0, ha="center", va="center", color="#555",
                style="italic", bbox=dict(boxstyle="round,pad=0.12", fc="white",
                ec="none", alpha=0.85), zorder=2)
for bid, (x, y, w, h, txt, col) in B.items():
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                 fc=COL[col], ec="#333", lw=1.3, zorder=3))
    weight = "bold" if bid in ("hub", "tdir", "grav") else "normal"
    ax.text(x + w / 2, y + h / 2, txt, fontsize=8.0, ha="center", va="center",
            weight=weight, zorder=4)

ax.text(7.25, 10.45, "VQT — Sistema Einstein-Cartan integrato: elementi, relazioni, costanti, formule",
        fontsize=13.5, weight="bold", ha="center")
# legenda frecce
ax.plot([0.8, 1.6], [0.75, 0.75], "-", color="#444", lw=1.4)
ax.text(1.72, 0.75, "relazione (genera/guida)", fontsize=7.5, va="center")
ax.plot([5.0, 5.8], [0.75, 0.75], ":", color="#888", lw=1.4)
ax.text(5.95, 0.75, "feedback (auto-regolazione)", fontsize=7.5, va="center")

# --- pannello COSTANTI (destra alto) ---
px = 14.5
ax.add_patch(FancyBboxPatch((px, 5.65), 6.2, 4.55, boxstyle="round,pad=0.06,rounding_size=0.1",
             fc=COL["panel"], ec="#333", lw=1.4, zorder=3))
ax.text(px + 3.1, 9.95, "COSTANTI", fontsize=11, weight="bold", ha="center")
# legenda stato
sx = px + 0.25
for i, (k, lbl) in enumerate([("der", "derivata"), ("top", "topologica"),
                              ("fis", "fisica"), ("post", "postulata"), ("elim", "eliminata")]):
    ax.text(sx + i * 1.18, 9.55, "● " + lbl, fontsize=6.6, color=STAT[k], va="center")
yy = 9.15
for f, st, desc in COSTANTI:
    ax.text(px + 0.25, yy, f, fontsize=8.4, va="center", color=STAT[st])
    ax.text(px + 0.45, yy - 0.21, desc, fontsize=6.4, va="center", color="#555", style="italic")
    yy -= 0.43

# --- pannello FORMULE (destra basso) ---
ax.add_patch(FancyBboxPatch((px, 0.55), 6.2, 4.9, boxstyle="round,pad=0.06,rounding_size=0.1",
             fc=COL["panel"], ec="#333", lw=1.4, zorder=3))
ax.text(px + 3.1, 5.2, "FORMULE DI DERIVAZIONE", fontsize=11, weight="bold", ha="center")
yy = 4.78
for f in FORMULE:
    ax.text(px + 0.25, yy, f, fontsize=8.2, va="center")
    yy -= 0.325

plt.tight_layout()
fig.savefig(OUT, dpi=160, bbox_inches="tight")
print(f"salvato: {OUT}")
