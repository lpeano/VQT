"""
================================================================================
CALIBRATORE PEANO-VQT  (VQT_repo)
================================================================================

Verifica sperimentale della costante Jitterbug:
    chi_max_peak / chi_stable = sqrt(2)

sui file HDF5 di produzione (L2/L3/L4).

Usa load_h5_and_validate() di energy_metrics.py che:
  - rilevamento del picco di chi_max  (non chi_mean)
  - calcolo del ratio Jitterbug
  - coincidenza con il troncamento H (delta <= 15 frame)

UTILIZZO:
    cd VQT_repo
    python -m wqt_oop.calibrate_peano_vqt

================================================================================
"""

import numpy as np
import sys
import time
from pathlib import Path

from wqt_oop.energy_metrics import load_h5_and_validate

CALIBRATION_FILES = {
    'L2_topo':   r'C:\Users\lpeano\plank\VQT_repo\data\cosmo_L2_topo.h5',
    'L2_var':    r'C:\Users\lpeano\plank\VQT_repo\data\cosmo_L2_variational.h5',
    'L3_full':   r'C:\Users\lpeano\plank\VQT_repo\data\cosmo_L3_full.h5',
    'L3_probe':  r'C:\Users\lpeano\plank\VQT_repo\data\cosmo_L3_probe.h5',
    'L3':        r'C:\Users\lpeano\plank\VQT_repo\experiments\exp1\cosmo_L3.h5',
    'L3_ext':    r'C:\Users\lpeano\plank\VQT_repo\experiments\exp1\cosmo_L3_ext.h5',
    'L3_ext2':   r'C:\Users\lpeano\plank\VQT_repo\experiments\exp1\cosmo_L3_ext2.h5',
    'L3_ext3':   r'C:\Users\lpeano\plank\VQT_repo\experiments\exp1\cosmo_L3_ext3.h5',
    'L4':        r'C:\Users\lpeano\plank\VQT_repo\experiments\exp1\cosmo_L4.h5',
}

CHI_STABLE = 50.0  # VEV del campo chi nelle simulazioni di produzione


def run_calibration():
    print("=" * 70)
    print("  CALIBRAZIONE JITTERBUG  (VQT_repo)")
    print(f"  Ipotesi: chi_max_peak / chi_stable = sqrt(2) = {np.sqrt(2):.6f}")
    print(f"  chi_stable = {CHI_STABLE}")
    print("=" * 70)

    results = []
    t0 = time.time()

    for name, fp in CALIBRATION_FILES.items():
        if not Path(fp).exists():
            print(f"  [SKIP] {name}: file non trovato")
            continue
        report = load_h5_and_validate(fp, chi_stable=CHI_STABLE, verbose=False)
        results.append((name, report))

    if not results:
        print("  Nessun file trovato.")
        return

    # Tabella riepilogo
    print(f"\n  {'File':12s} {'frames':>7} {'peak_frame':>11} {'chi_max_peak':>13} "
          f"{'ratio':>7} {'vs sqrt2':>9} {'trunc':>6} {'delta':>6} {'Teorema':>8}")
    print("  " + "-" * 82)

    n_confirmed = 0
    n_jitterbug = 0

    for name, r in results:
        peak_f  = r.get('chi_max_peak_frame', '--') or '--'
        peak_v  = r.get('chi_max_peak_value', 0.0)
        ratio   = r.get('jitterbug_ratio', 0.0)
        jok     = "<SQRT2" if r.get('jitterbug_confirmed') else "     "
        trunc_f = r.get('truncation_frame', '--') or '--'
        delta   = r.get('truncation_delta', '--')
        delta_s = str(delta) if delta is not None else '--'
        peano   = "YES" if r.get('peano_theorem_confirmed') else "no "
        dev_pct = (ratio - np.sqrt(2)) / np.sqrt(2) * 100

        if r.get('jitterbug_confirmed'):
            n_jitterbug += 1
        if r.get('peano_theorem_confirmed'):
            n_confirmed += 1

        print(f"  {name:12s} {r['total_frames']:>7d} {peak_f:>11s} {peak_v:>13.4f} "
              f"{ratio:>7.4f} {dev_pct:>+8.2f}%{jok} {trunc_f:>6s} {delta_s:>6s} {peano:>8s}")

    print("\n" + "=" * 70)
    print(f"  Costante Jitterbug confermata: {n_jitterbug}/{len(results)} file "
          f"(entro 10% da sqrt(2))")
    print(f"  Teorema Peano-VQT confermato : {n_confirmed}/{len(results)} file "
          f"(delta <= 15 frame)")
    print(f"  sqrt(2) = {np.sqrt(2):.6f}")
    print(f"  Tempo: {time.time()-t0:.2f}s")
    print("=" * 70)

    # Fase geometrica da load_h5_and_validate
    print("\n  Fasi geometriche osservate (per file con drain):")
    print(f"  {'File':12s}  {'Ottaedrica':>12}  {'Cubottaedrica':>14}  {'Icosaedrica':>12}  "
          f"{'E_Psi_final':>12}  {'drain_frames':>13}")
    print("  " + "-" * 80)
    for name, r in results:
        if r['total_frames'] < 2:
            continue
        counts = r['geometric_phase_counts']
        print(f"  {name:12s}  {counts['Ottaedrica']:>12d}  "
              f"{counts['Cubottaedrica']:>14d}  {counts['Icosaedrica']:>12d}  "
              f"{r['E_psi_final']:>12.4e}  {r['drain_frames']:>13d}")


if __name__ == "__main__":
    run_calibration()
