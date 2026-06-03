"""
================================================================================
TEST TRANSIZIONE DINAMICA — E_Psi_anchored attraverso la soglia sqrt(2)
================================================================================

L'esperimento della "nascita di materia" con la metrica geometrica corretta.

Idea: la soglia sqrt(2)*chi_stable = 70.7 e' un PICCO DINAMICO, non uno stato
statico (verificato 2026-06-01: gli stati rilassati non la raggiungono). Quindi
costruiamo un L1 che PARTE sopra la soglia (chi_max > 70.7) e lo lasciamo
evolvere: chi_max attraversa 70.7 scendendo. Registriamo E_psi_anchored e
E_psi_geom lungo la traiettoria e cerchiamo un GINOCCHIO/SALTO a sqrt(2).

Se E_psi_anchored ha un cambio di pendenza netto a chi_max/chi_stable = sqrt(2),
quella e' la firma della transizione di fase Cubottaedro->Icosaedro (Jitterbug):
la materia che si "congela" quando il campo supera la soglia geometrica.

chi_stable = 50 (fisso), chi iniziale alto (chi_mean=68, chi_std=8 -> chi_max~82).
FDT ON: il sistema decade e chi_max attraversa 70.7.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_transizione_dinamica.py
================================================================================
"""

import sys, os
import numpy as np
import warnings, logging
from dataclasses import replace as dc_replace

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.energy_metrics import PeanoVQTAnalyzer, compute_geometric_E_psi

SQRT2 = np.sqrt(2)
CHI_STABLE = 50.0
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)


def make_l1(chi_mean=68.0, chi_std=8.0, seed=3, fdt=True):
    rng = np.random.default_rng(seed)
    base0 = dc_replace(PhysicsContext.for_level(0), zero_point_amplitude=0.0)
    p1 = dc_replace(PhysicsContext.for_level(1, base_context=base0),
                    zero_point_amplitude=0.0)
    segs = []
    for i in range(24):
        s = SegmentoQuantistico(chi=chi_mean + chi_std * rng.standard_normal(),
                                vel=0.3 * rng.standard_normal(), physics=base0)
        s._fdt_enabled = fdt
        if not fdt:
            s.gamma_damping = 0.0
        segs.append(s)
    sol = SolitoneComposito(segs, p1, screening_enabled=False)
    # Drain disattivato: misuriamo SOLO la metrica geometrica istantanea
    sol._peano_analyzer = PeanoVQTAnalyzer(chi_saturation_threshold=1e12, drain_rate=0.0)
    return sol


def run_trajectory(n_steps=400, dt=0.01):
    sol = make_l1()
    rec_ratio, rec_anch, rec_geom, rec_dq = [], [], [], []
    for _ in range(n_steps):
        sol.compute_hamiltonian()
        sol.evolve(dt)
        r = compute_geometric_E_psi(sol)
        rec_ratio.append(r["chi_max_over_stable"])
        rec_anch.append(r["E_psi_anchored"])
        rec_geom.append(r["E_psi_geom"])
        rec_dq.append(r["detorsion_quality"])
    return (np.array(rec_ratio), np.array(rec_anch),
            np.array(rec_geom), np.array(rec_dq))


def analyze_knee(ratio, anch):
    """Cerca un cambio di pendenza di E_psi_anchored attorno a sqrt(2).
    Confronta la pendenza (dE/dratio) sopra e sotto la soglia."""
    # ordina per ratio
    idx = np.argsort(ratio)
    r = ratio[idx]; a = anch[idx]
    above = r >= SQRT2
    below = r < SQRT2
    if np.sum(above) < 5 or np.sum(below) < 5:
        return None
    # pendenza media sopra e sotto
    slope_below = np.polyfit(r[below], a[below], 1)[0]
    slope_above = np.polyfit(r[above], a[above], 1)[0]
    return slope_below, slope_above


def main():
    print("=" * 70)
    print("  TEST TRANSIZIONE DINAMICA — E_Psi_anchored attraverso sqrt(2)")
    print("=" * 70)
    ratio, anch, geom, dq = run_trajectory()
    print(f"  chi_max/chi_stable: range [{ratio.min():.3f}, {ratio.max():.3f}]  "
          f"(soglia sqrt2={SQRT2:.3f})")
    crosses = ratio.max() >= SQRT2 >= ratio.min()
    print(f"  Attraversa sqrt(2): {'SI' if crosses else 'NO'}")

    if crosses:
        knee = analyze_knee(ratio, anch)
        if knee:
            sb, sa = knee
            print(f"  Pendenza E_anchored sotto sqrt2: {sb:.3e}")
            print(f"  Pendenza E_anchored sopra sqrt2: {sa:.3e}")
            ratio_slope = abs(sa) / (abs(sb) + 1e-30)
            print(f"  Rapporto pendenze (sopra/sotto): {ratio_slope:.2f}")
            if ratio_slope > 2 or ratio_slope < 0.5:
                print("  -> GINOCCHIO rilevato a sqrt(2): cambio di regime (segnale di transizione).")
            else:
                print("  -> Nessun ginocchio netto: E_anchored varia con continuita'.")

    # Grafico: E_psi vs chi_max/chi_stable, con linea sqrt(2)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    ax1.scatter(ratio, anch, s=12, c=np.arange(len(ratio)), cmap="viridis", label="E_anchored")
    ax1.axvline(SQRT2, color="red", ls="--", lw=2, label=f"sqrt(2)={SQRT2:.3f}")
    ax1.axvline(1.0, color="gray", ls=":", label="1.0 (VE)")
    ax1.set_xlabel("chi_max / chi_stable"); ax1.set_ylabel("E_psi_anchored")
    ax1.set_title("E_Psi ancorata vs saturazione (colore=tempo)")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    t = np.arange(len(ratio))
    ax2.plot(t, ratio, color="#1f77b4", label="chi_max/chi_stable")
    ax2.axhline(SQRT2, color="red", ls="--", label="sqrt(2)")
    ax2b = ax2.twinx()
    ax2b.plot(t, anch, color="#2ca02c", alpha=0.7, label="E_anchored")
    ax2.set_xlabel("step"); ax2.set_ylabel("chi_max/chi_stable", color="#1f77b4")
    ax2b.set_ylabel("E_psi_anchored", color="#2ca02c")
    ax2.set_title("Traiettoria temporale")
    ax2.legend(loc="upper right", fontsize=8); ax2.grid(alpha=0.3)

    fig.suptitle("Transizione dinamica E_Psi attraverso la soglia Jitterbug sqrt(2)",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, "transizione_dinamica.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
