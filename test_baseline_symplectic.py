"""
BASELINE SYMPLECTIC VALIDATION (Post-Rollback)

Verifica che il Velocity Verlet con dt globale uniforme preservi
la proprietà simplettica (conservazione volume spazio delle fasi).

Questo test conferma il ripristino della stabilità dopo il rollback
dell'implementazione multi-rate (CP-2026-05-26-003).

Expected: drift < 1e-8
"""

import sys
import numpy as np
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
    """
    Compute phase-space volume using 2D convex hull (chi vs vel projection).
    
    Physics: V_Γ measures occupied region in (χ, v) space
             Liouville's theorem: dV_Γ/dt = 0 for Hamiltonian systems
    """
    chi_values = np.array([s.chi for s in segments])
    vel_values = np.array([s.vel for s in segments])
    
    points = np.column_stack([chi_values, vel_values])
    hull = ConvexHull(points)
    
    return hull.volume


def test_baseline_symplectic():
    """
    Test baseline symplectic property with uniform global timestep.
    
    Expected: drift < 1e-8 (validates Velocity Verlet is working correctly)
    """
    print("\n" + "="*70)
    print(" BASELINE SYMPLECTIC VALIDATION (Post-Rollback)")
    print("="*70)
    print("\nObjective: Verify phase-space volume conservation with uniform dt")
    print("Integrator: Velocity Verlet (2nd-order symplectic)")
    print("Threshold: |dV/V| < 1e-8\n")
    
    # Create L1 universe (24 segments)
    physics = PhysicsContext(level=0, length_scale=1.0)
    factory = FractalUniverseFactory(base_physics=physics)
    
    print("Creating L1 universe (24 segments)...")
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
    N_segments = len(segments)
    print(f"  Total segments: {N_segments}")
    
    # Initial phase-space volume
    V_0 = compute_phase_space_volume(segments)
    print(f"\nINITIAL STATE (t=0):")
    print(f"  Phase-space volume V_0 = {V_0:.6e}")
    
    # Evolve 1000 steps with UNIFORM global timestep (NO multi-rate)
    dt_global = 0.01
    n_steps = 1000
    
    print(f"\nEVOLVING SYSTEM:")
    print(f"  Timesteps: {n_steps}")
    print(f"  dt_global: {dt_global} (UNIFORM - no local adaptation)")
    print(f"  Mode: Baseline Velocity Verlet")
    
    volumes = [V_0]
    
    for step in range(1, n_steps + 1):
        # Evolve with UNIFORM dt (no use_local_timestep parameter anymore)
        universe.evolve(dt_global)
        
        # Track phase-space volume every 100 steps
        if step % 100 == 0:
            V_current = compute_phase_space_volume(segments)
            drift = abs(V_current - V_0) / V_0
            volumes.append(V_current)
            print(f"  Step {step:4d}: V = {V_current:.6e}, drift = {drift:.3e}")
    
    # Final validation
    V_final = volumes[-1]
    final_drift = abs(V_final - V_0) / V_0
    
    print(f"\nFINAL STATE (t={n_steps * dt_global}):")
    print(f"  Phase-space volume V_final = {V_final:.6e}")
    print(f"  Initial volume V_0         = {V_0:.6e}")
    print(f"  Relative drift |dV/V|      = {final_drift:.6e}")
    
    print(f"\nVALIDATION:")
    print(f"  Threshold: {1e-8:.6e}")
    print(f"  Observed:  {final_drift:.6e}")
    
    if final_drift < 1e-8:
        print(f"\n✅ BASELINE SYMPLECTIC PROPERTY RESTORED!")
        print(f"   Phase-space volume conserved to machine precision")
        print(f"   Drift = {final_drift:.3e} << 1e-8")
        print(f"\n🎯 ROLLBACK SUCCESSFUL: System stable with uniform dt")
        return True
    else:
        print(f"\n❌ BASELINE VALIDATION FAILED!")
        print(f"   Drift {final_drift:.3e} exceeds threshold {1e-8:.3e}")
        print(f"   This suggests a deeper issue beyond multi-rate integration")
        return False


def main():
    try:
        result = test_baseline_symplectic()
        return 0 if result else 1
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
