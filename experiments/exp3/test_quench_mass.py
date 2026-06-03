"""
================================================================================
COOLING-DOWN / QUENCH TEST — la massa come frustrazione congelata irriducibile
================================================================================

Ipotesi (c): la massa NON e' un evento alla soglia sqrt(2), ma una configurazione
di frustrazione geometrica STABILE che persiste dopo il congelamento (T->0).

Protocollo (freeze_and_measure_mass in energy_metrics.py):
  1. Stato a T_final (dopo storia dinamica varia).
  2. Quench: velocity-cooling esplicito -> KE -> 0 (rilassamento adiabatico).
  3. Misura E_psi_anchored RESIDUA = massa candidata; IPR = localizzazione cicatrice.

Domanda: la E_Psi residua e' irriducibile e quantizzata (massa topologica) o
rumore continuo dipendente dalla storia?

Risultato atteso/osservato (2026-06-01): BIMODALITA' -> il sistema congela in
DUE classi: E_Psi ~ 0 (nessun difetto) oppure E_Psi ~ valore finito (difetto
congelato = massa). Le storie lunghe tendono allo stato massivo.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_quench_mass.py
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
from wqt_oop.energy_metrics import PeanoVQTAnalyzer, freeze_and_measure_mass

FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)


def make(seed, chi_mean=65.0):
    rng = np.random.default_rng(seed)
    base0 = dc_replace(PhysicsContext.for_level(0), zero_point_amplitude=0.0)
    p1 = dc_replace(PhysicsContext.for_level(1, base_context=base0),
                    zero_point_amplitude=0.0)
    segs = [SegmentoQuantistico(chi=chi_mean + 8 * rng.standard_normal(),
                                vel=1.0 * rng.standard_normal(), physics=base0)
            for i in range(24)]
    for s in segs:
        s._fdt_enabled = True
    sol = SolitoneComposito(segs, p1, screening_enabled=False)
    sol._peano_analyzer = PeanoVQTAnalyzer(chi_saturation_threshold=1e12, drain_rate=0.0)
    return sol


def main():
    print("=" * 70)
    print("  QUENCH TEST — distribuzione della massa residua (frustrazione congelata)")
    print("=" * 70)

    masses, iprs, conv_count = [], [], 0
    n_states = 0
    for seed in range(1, 13):
        for pre in [40, 100, 200]:
            sol = make(seed)
            for _ in range(pre):
                sol.compute_hamiltonian(); sol.evolve(0.01)
            r = freeze_and_measure_mass(sol, max_steps=2000, dt=0.01)
            masses.append(r["E_psi_residual"])
            iprs.append(r["IPR"])
            conv_count += int(r["converged"])
            n_states += 1

    masses = np.array(masses)
    iprs = np.array(iprs)
    # Classifica: massivo se E_psi > 1% del massimo (separa lo zero dal finito)
    thr = 0.01 * masses.max()
    massive = masses > thr
    m_massive = masses[massive]

    print(f"\n  Stati totali: {n_states}  |  congelati (KE->0): {conv_count}/{n_states}")
    print(f"  Stati MASSIVI (E_psi > {thr:.2e}): {np.sum(massive)}/{n_states} "
          f"({np.mean(massive)*100:.0f}%)")
    print(f"  Stati a massa ~0:                 {np.sum(~massive)}/{n_states}")
    if len(m_massive) > 0:
        cv_massive = np.std(m_massive) / np.mean(m_massive)
        print(f"\n  Tra i massivi: massa media = {np.mean(m_massive):.4e}  "
              f"+- {np.std(m_massive):.4e}  (CV={cv_massive:.3f})")
        print(f"  range massa: [{m_massive.min():.3e}, {m_massive.max():.3e}]")
        if cv_massive < 0.3:
            print("  -> Massa QUANTIZZATA (valore preferito stretto): difetto topologico discreto.")
        else:
            print("  -> Massa a banda larga: difetti di entita' variabile.")

    # Correlazione massa con la storia (pre-steps)
    print("\n  Frazione massiva per lunghezza storia (pre-steps):")
    idx = 0
    for seed in range(1, 13):
        pass
    # ricostruisco per pre
    for pre_target, label in [(40, "corta"), (100, "media"), (200, "lunga")]:
        sub = []
        i = 0
        for seed in range(1, 13):
            for pre in [40, 100, 200]:
                if pre == pre_target:
                    sub.append(masses[i] > thr)
                i += 1
        print(f"    storia {label:5} (pre={pre_target:>3}): {np.mean(sub)*100:>3.0f}% massivi")

    # Grafico: istogramma della massa residua
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    ax1.hist(masses, bins=25, color="#2ca02c", alpha=0.75, edgecolor="k")
    ax1.axvline(thr, color="red", ls="--", label=f"soglia massa ({thr:.1e})")
    ax1.set_xlabel("E_psi_anchored residua (dopo quench)")
    ax1.set_ylabel("conteggio")
    ax1.set_title("Distribuzione della massa congelata (bimodale?)")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    ax2.scatter(masses, iprs, c=massive, cmap="coolwarm", s=40, edgecolor="k")
    ax2.axvline(thr, color="red", ls="--", alpha=0.5)
    ax2.set_xlabel("massa residua E_psi"); ax2.set_ylabel("IPR (localizzazione)")
    ax2.set_title("Massa vs localizzazione della cicatrice")
    ax2.grid(alpha=0.3)

    fig.suptitle("Quench test: la massa come frustrazione topologica congelata",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, "quench_mass.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
