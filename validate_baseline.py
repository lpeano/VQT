"""
BASELINE SYMPLECTIC VALIDATION - Post-Rollback Verification

Tests that the system has returned to symplectic stability after
rolling back CP-2026-05-26-003 (failed relativistic timestep).

Expected: Phase-space volume drift < 1e-8 with global timestep dt=0.01
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.fractal_universe_factory import FractalUniverseFactory, UniverseConfig
from scipy.spatial import ConvexHull


def extract_all_segments(soliton):
    """Recursively extract all level-0 segments."""
    if isinstance(soliton, SegmentoQuantistico):
        return [soliton]
    elif isinstance(soliton, SolitoneComposito):
        segments = []
        for child in soliton.children:
            segments.extend(extract_all_segments(child))
        return segments
    else:
        raise TypeError(f"Unknown soliton type: {type(soliton)}")


def compute_phase_space_volume(segments):
    """Compute 2D convex hull volume in (chi, vel) space."""
    chi_values = np.array([s.chi for s in segments])
    vel_values = np.array([s.vel for s in segments])
    points = np.column_stack([chi_values, vel_values])
    hull = ConvexHull(points)
    return hull.volume


def main():
    print("\n" + "="*70)
    print(" BASELINE SYMPLECTIC VALIDATION (Post-Rollback)")
    print("="*70)
    print("\nPurpose: Verify phase-space volume conservation with global dt")
    print("Expected: drift < 1e-8 (Velocity Verlet is exactly symplectic)")
    print("\n" + "="*70)
    
    # Create L1 universe (24 segments)
    print("\nCREATING L1 UNIVERSE...")
    physics = PhysicsContext(level=0, length_scale=1.0)
    factory = FractalUniverseFactory(base_physics=physics)
    
    config = UniverseConfig(
        target_level=1,
        chi_mean=50.0,
        chi_std=5.0,
        spatial_extent=100.0,
        seed=42,
        enable_fermi_screening=True,
        enable_spatial_cache=True
    )
    universe = factory.create_universe(config)
    segments = extract_all_segments(universe)
    
    print(f"  Total segments: {len(segments)}")
    print(f"  Physics: Velocity Verlet (O(dt²), symplectic)")
    print(f"  Timestep: dt = 0.01 (GLOBAL, uniform across all segments)")
    
    # Initial volume
    V_0 = compute_phase_space_volume(segments)
    print(f"\nINITIAL STATE (t=0):")
    print(f"  Phase-space volume V_0 = {V_0:.6e}")
    
    # Evolve 1000 steps
    dt_global = 0.01
    n_steps = 1000
    
    print(f"\nEVOLVING SYSTEM:")
    print(f"  Timesteps: {n_steps}")
    print(f"  dt_global: {dt_global}")
    print(f"  Mode: BASELINE (global timestep, no relativistic adaptation)")
    
    volumes = [V_0]
    
    for step in range(1, n_steps + 1):
        universe.evolve(dt_global)
        
        if step % 100 == 0:
            V_current = compute_phase_space_volume(segments)
            volumes.append(V_current)
            drift = abs(V_current - V_0) / V_0
            print(f"  Step {step:4d}: V = {V_current:.6e}, drift = {drift:.3e}")
    
    # Final validation
    V_final = volumes[-1]
    final_drift = abs(V_final - V_0) / V_0
    
    print(f"\nFINAL STATE (t={n_steps * dt_global}):")
    print(f"  Phase-space volume V_final = {V_final:.6e}")
    print(f"  Initial volume V_0         = {V_0:.6e}")
    print(f"  Relative drift |dV/V|      = {final_drift:.3e}")
    
    print(f"\nVALIDATION:")
    print(f"  Threshold: 1.000e-08")
    print(f"  Observed:  {final_drift:.3e}")
    
    # Success criterion
    threshold = 1e-8
    
    if final_drift < threshold:
        print(f"\n✅ BASELINE VALIDATION PASSED!")
        print(f"   Symplectic property restored (drift = {final_drift:.3e} < {threshold:.3e})")
        print(f"   System ready for Yoshida integration research")
        return 0
    else:
        print(f"\n❌ BASELINE VALIDATION FAILED!")
        print(f"   Phase-space volume drift {final_drift:.3e} exceeds threshold {threshold:.3e}")
        print(f"   Rollback incomplete or underlying integration issue")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
