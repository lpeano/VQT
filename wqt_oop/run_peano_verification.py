"""
================================================================================
VERIFICA PEANO-VQT  (VQT_repo)
================================================================================

Confronto diretto:
  BASELINE (drain OFF, soglia 0.8 bug):  simulazione L2
  PEANO-VQT (drain ON, soglia sqrt(2)):  stessa simulazione con fix applicati

Stesse condizioni iniziali di produzione:
  chi_mean=50, chi_std=5, chi_stable=50, seed=42, target_level=2, dt=0.01

Usa la nomenclatura del repo ufficiale:
  get_energy_triad(), _peano_analyzer.E_psi_total, classify_geometric_phase()

UTILIZZO:
    cd VQT_repo
    python -m wqt_oop.run_peano_verification
================================================================================
"""

import numpy as np
import time
import sys
import warnings
import logging
from dataclasses import replace as dc_replace
from pathlib import Path

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.ERROR)

sys.path.insert(0, str(Path(__file__).parent.parent))

from wqt_oop.fractal_universe_factory import FractalUniverseFactory, UniverseConfig
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.energy_metrics import classify_geometric_phase

# ---------------------------------------------------------------------------
# CONFIGURAZIONE
# ---------------------------------------------------------------------------

SIM_CONFIG = UniverseConfig(
    target_level=2,    # L2 = 576 segmenti
    chi_mean=50.0,
    chi_std=5.0,
    vel_std=1.0,
    spatial_extent=50.0,
    seed=42,
    enable_fermi_screening=False,
    enable_spatial_cache=True,
)

N_FRAMES        = 80
STEPS_PER_FRAME = 10
DT              = 0.01


# ---------------------------------------------------------------------------
# RUNNER
# ---------------------------------------------------------------------------

def run_simulation(with_drain: bool, label: str):
    np.random.seed(SIM_CONFIG.seed)
    factory = FractalUniverseFactory()
    universe = factory.create_universe(SIM_CONFIG)

    if not with_drain:
        # Disabilita drain: imposta soglia irraggiungibile
        universe._peano_analyzer.chi_saturation_threshold = 1e9

    print(f"\n  [{label}]  drain={'ON (sqrt2)' if with_drain else 'OFF (disabilitato)'}"
          f"  threshold={universe._peano_analyzer.chi_saturation_threshold:.4f}")
    print(f"  {'frame':>5}  {'H_total':>12}  {'E_chi':>10}  {'E_RX':>10}  "
          f"{'E_Psi':>10}  {'chi_max/cs':>10}  {'fase':>14}")
    print("  " + "-" * 80)

    history = []
    t0 = time.time()

    for frame in range(N_FRAMES):
        for _ in range(STEPS_PER_FRAME):
            universe.evolve(DT)

        H = universe.compute_hamiltonian()
        triad = universe.get_energy_triad()

        E_chi = triad.E_chi if triad else 0.0
        E_RX  = triad.E_RX  if triad else 0.0
        E_Psi = triad.E_Psi if triad else 0.0

        chi_values = np.array([
            universe._get_child_chi(c) for c in universe.children
        ])
        chi_max = float(np.max(np.abs(chi_values)))
        chi_stable = universe.physics.chi_stable
        chi_sat = chi_max / max(chi_stable, 1e-30)
        phase = classify_geometric_phase(chi_sat)

        history.append((frame, H, E_chi, E_RX, E_Psi, chi_sat, phase))

        if frame % 10 == 0 or E_Psi > 0:
            print(f"  {frame:>5}  {H:>12.4e}  {E_chi:>10.4e}  {E_RX:>10.4e}  "
                  f"{E_Psi:>10.4e}  {chi_sat:>10.4f}  {phase:>14s}")

    elapsed = time.time() - t0
    print(f"\n  [{label}] completato in {elapsed:.1f}s")
    return history


# ---------------------------------------------------------------------------
# CONFRONTO
# ---------------------------------------------------------------------------

def compare(hist_on, hist_off):
    print("\n" + "=" * 70)
    print("  CONFRONTO: Drain ON (sqrt2) vs Drain OFF (baseline)")
    print("=" * 70)

    def anomalies(history):
        H_arr = np.array([r[1] for r in history])
        if len(H_arr) < 4:
            return []
        H_diff = np.diff(H_arr)
        med = np.median(H_diff)
        mad = np.median(np.abs(H_diff - med)) + 1e-30
        z = np.abs(H_diff - med) / mad
        return list(np.where(z > 5.0)[0])

    anom_on  = anomalies(hist_on)
    anom_off = anomalies(hist_off)

    print(f"\n  Anomalie H_total (eventi 'truncation'):")
    print(f"    Drain ON  : frame {anom_on  if anom_on  else 'nessuno'}")
    print(f"    Drain OFF : frame {anom_off if anom_off else 'nessuno'}")

    E_Psi_on  = hist_on[-1][4]
    E_Psi_off = hist_off[-1][4]
    print(f"\n  E_Psi accumulata (frame {N_FRAMES - 1}):")
    print(f"    Drain ON  : {E_Psi_on:.4e}")
    print(f"    Drain OFF : {E_Psi_off:.4e}")

    phase_on  = hist_on[-1][6]
    phase_off = hist_off[-1][6]
    print(f"\n  Fase geometrica finale:")
    print(f"    Drain ON  : {phase_on}")
    print(f"    Drain OFF : {phase_off}")

    chi_sat_max_on  = max(r[5] for r in hist_on)
    chi_sat_max_off = max(r[5] for r in hist_off)
    print(f"\n  chi_max/chi_stable massimo:")
    print(f"    Drain ON  : {chi_sat_max_on:.4f}  (soglia sqrt(2)={np.sqrt(2):.4f})")
    print(f"    Drain OFF : {chi_sat_max_off:.4f}")

    print("\n" + "=" * 70)
    verdict_ok = (E_Psi_on > 0 or len(anom_on) < len(anom_off))
    if E_Psi_on > 0:
        print(f"  VERDETTO: Drain ON -> E_Psi = {E_Psi_on:.4e}")
        print(f"  Il motore si TRASFORMA invece di BLOCCARSI.")
        print(f"  La Transizione di Fase Jitterbug (chi_sat = sqrt(2)) e' attiva.")
    elif len(anom_on) < len(anom_off):
        print(f"  VERDETTO: Drain ON riduce le anomalie H da {len(anom_off)} a {len(anom_on)}.")
    else:
        print(f"  NOTA: Chi_max/chi_stable_max = {chi_sat_max_on:.4f}")
        if chi_sat_max_on < np.sqrt(2):
            print(f"  La soglia Jitterbug sqrt(2) non e' stata raggiunta in questo run.")
            print(f"  Usa L3 completo o incrementa chi_std per attivare la transizione.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("  VERIFICA PEANO-VQT  (VQT_repo)")
    print(f"  Livello: L{SIM_CONFIG.target_level}  N={24**SIM_CONFIG.target_level} segmenti")
    print(f"  chi_mean={SIM_CONFIG.chi_mean}  chi_stable={SIM_CONFIG.chi_mean}")
    print(f"  Soglia Jitterbug: sqrt(2) = {np.sqrt(2):.6f}")
    print(f"  dt={DT}  frames={N_FRAMES}  steps_per_frame={STEPS_PER_FRAME}")
    print("=" * 70)

    hist_off = run_simulation(with_drain=False, label="BASELINE (drain OFF)")
    hist_on  = run_simulation(with_drain=True,  label="PEANO-VQT (drain ON)")

    compare(hist_on, hist_off)
