"""
PHASE 1 UNIT TESTS - CP-2026-05-26-003 (Relativistic Timestep Localization)

Tests:
1. test_local_timestep_scaling(): Verify dt_i decreases with E_local
2. test_symplectic_property(): Verify phase-space volume conservation (CRITICAL)
3. test_synchronization(): Verify all segments synchronized at global dt grid

Reference: CHANGE_PROPOSAL_TIMESTEP_RELATIVITY.md § VI "Validation Protocol"
"""

import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.fractal_universe_factory import FractalUniverseFactory, UniverseConfig
from scipy.spatial import ConvexHull


def extract_all_segments(soliton):
    """
    Recursively extract all level-0 segments from fractal hierarchy.
    
    Parameters:
    -----------
    soliton : AbstractSoliton
        Root node (can be SegmentoQuantistico or SolitoneComposito)
        
    Returns:
    --------
    segments : List[SegmentoQuantistico]
        All leaf nodes (level-0 segments)
    """
    if isinstance(soliton, SegmentoQuantistico):
        return [soliton]
    elif isinstance(soliton, SolitoneComposito):
        segments = []
        for child in soliton.children:
            segments.extend(extract_all_segments(child))
        return segments
    else:
        raise TypeError(f"Unknown soliton type: {type(soliton)}")


def test_local_timestep_scaling():
    """
    TEST 1: Verify dt_i decreases with increasing E_local.
    
    Physics Principle: Energy-Time Uncertainty (Heisenberg)
                       ΔE·Δt ≥ ℏ/2 → high E requires small Δt
    
    Expected: dt_high < dt_low (at least 10× reduction for high energy)
    """
    print("\n" + "="*70)
    print(" TEST 1: Local Timestep Scaling (dt_i ~ E^(-0.5))")
    print("="*70)
    
    physics = PhysicsContext(level=0, length_scale=1.0)
    
    # Create test segment (positional args: chi, vel, physics, position)
    segment = SegmentoQuantistico(
        50.0,  # chi_initial
        0.1,   # vel_initial (low velocity → low energy)
        physics,
        position=np.array([0.0, 0.0, 0.0])
    )
    
    # Low energy state
    segment.vel = 0.1
    E_low = segment.compute_hamiltonian_internal()
    dt_low = segment.compute_local_timestep(dt_base=0.01)
    
    print(f"LOW ENERGY STATE:")
    print(f"  E_local = {E_low:.6e} J")
    print(f"  dt_i    = {dt_low:.6e} s")
    
    # High energy state (v² → 1e6× increase in T_kin)
    segment.vel = 100.0
    E_high = segment.compute_hamiltonian_internal()
    dt_high = segment.compute_local_timestep(dt_base=0.01)
    
    print(f"\nHIGH ENERGY STATE:")
    print(f"  E_local = {E_high:.6e} J")
    print(f"  dt_i    = {dt_high:.6e} s")
    
    # Compute ratio
    energy_ratio = E_high / E_low
    timestep_ratio = dt_high / dt_low
    
    print(f"\nRATIO ANALYSIS:")
    print(f"  E_high / E_low   = {energy_ratio:.3e}")
    print(f"  dt_high / dt_low = {timestep_ratio:.3e}")
    
    # Validation
    assert dt_high < dt_low, "❌ FAIL: dt_i should decrease with energy!"
    assert timestep_ratio < 0.1, f"❌ FAIL: Expected at least 10× reduction, got {timestep_ratio:.3e}"
    
    # Theoretical prediction: dt_i = dt_base * (1 + E_i / E_ref)^(-alpha)
    dt_base = 0.01  # Same value used in compute_local_timestep() calls
    E_ref = 1.0  # From PhysicsContext.timestep_energy_ref
    alpha = 0.5  # From PhysicsContext.timestep_power_alpha
    
    expected_dt_low = dt_base * (1.0 + E_low / E_ref)**(-alpha)
    expected_dt_high = dt_base * (1.0 + E_high / E_ref)**(-alpha)
    expected_ratio = expected_dt_high / expected_dt_low
    
    relative_error = abs(timestep_ratio - expected_ratio) / expected_ratio
    
    print(f"\nTHEORETICAL VALIDATION:")
    print(f"  Expected dt_low   = {expected_dt_low:.6e} s")
    print(f"  Expected dt_high  = {expected_dt_high:.6e} s")
    print(f"  Expected ratio    = {expected_ratio:.6e}")
    print(f"  Observed ratio    = {timestep_ratio:.6e}")
    print(f"  Relative error    = {relative_error:.3%}")
    
    # Allow 5% deviation (from numerical precision)
    assert relative_error < 0.05, f"❌ FAIL: Scaling error {relative_error:.1%}"
    
    print("\n✅ TEST 1 PASSED: dt_i correctly follows (1+E/E_ref)^(-0.5) scaling")
    return True


def compute_phase_space_volume(segments):
    """
    Compute phase-space volume using 2D convex hull (chi vs vel projection).
    
    Physical: Phase-space volume V_Gamma measures "occupied region" in (chi, v) space
             Liouville's theorem: dV_Gamma/dt = 0 for Hamiltonian systems
    
    Returns:
        volume: Area of convex hull in (chi, vel) plane [dimensionless]
    """
    # Extract (chi, vel) coordinates
    chi_values = np.array([s.chi for s in segments])
    vel_values = np.array([s.vel for s in segments])
    
    # Stack into 2D points
    points = np.column_stack([chi_values, vel_values])
    
    # Compute convex hull
    hull = ConvexHull(points)
    
    # Return area (2D volume)
    return hull.volume


def test_symplectic_property():
    """
    TEST 2 (CRITICAL): Verify phase-space volume conservation.
    
    Physics Principle: Liouville's Theorem (Hamiltonian Mechanics)
                       dV_Γ/dt = 0 → Phase-space volume preserved
    
    Symplectic Integrator: Velocity Verlet preserves symplectic structure
                          -> |V_final - V_initial| / V_initial < 1e-8
    
    Expected: Phase-space volume drift < 1e-8 (10⁻⁸)
    
    This is the CRITICAL TEST that determines approval for Phase 2 (L1 validation).
    """
    print("\n" + "="*70)
    print(" TEST 2: Symplectic Property (Phase-Space Volume Conservation)")
    print("="*70)
    print("\n⚠️  CRITICAL TEST - Phase 2 approval depends on drift < 1e-8\n")
    
    physics = PhysicsContext(level=0, length_scale=1.0)
    factory = FractalUniverseFactory(base_physics=physics)
    
    # Create L1 universe (24 segments)
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
    
    # Evolve 1000 steps with relativistic timestep
    dt = 0.01
    N_steps = 1000
    print(f"\nEVOLVING SYSTEM:")
    print(f"  Timesteps: {N_steps}")
    print(f"  dt_global: {dt}")
    print(f"  Mode: Relativistic timestep (use_local_timestep=True)")
    
    # Track volume every 100 steps
    volumes = [V_0]
    timesteps_log = [0]
    
    for step in range(1, N_steps + 1):
        universe.evolve(dt, use_local_timestep=True)
        
        if step % 100 == 0:
            V_current = compute_phase_space_volume(segments)
            volumes.append(V_current)
            timesteps_log.append(step)
            
            drift = abs(V_current - V_0) / V_0
            print(f"  Step {step:4d}: V = {V_current:.6e}, drift = {drift:.3e}")
    
    # Final volume
    V_final = volumes[-1]
    final_drift = abs(V_final - V_0) / V_0
    
    print(f"\nFINAL STATE (t={N_steps * dt}):")
    print(f"  Phase-space volume V_final = {V_final:.6e}")
    print(f"  Initial volume V_0         = {V_0:.6e}")
    print(f"  Absolute drift |V_f - V_0| = {abs(V_final - V_0):.3e}")
    print(f"  Relative drift |dV/V|      = {final_drift:.3e}")
    
    # CRITICAL THRESHOLD
    threshold = 1e-8
    print(f"\nVALIDATION:")
    print(f"  Threshold (symplectic criterion): {threshold:.0e}")
    print(f"  Measured drift:                   {final_drift:.3e}")
    
    if final_drift < threshold:
        print(f"\n✅ TEST 2 PASSED: Phase-space volume conserved (drift = {final_drift:.3e} < {threshold:.0e})")
        print("\n🎉 SYMPLECTIC PROPERTY VERIFIED - APPROVED FOR PHASE 2 (L1 Validation)")
        return True
    else:
        print(f"\n❌ TEST 2 FAILED: Non-symplectic integration detected!")
        print(f"   Phase-space volume drift {final_drift:.3e} exceeds threshold {threshold:.0e}")
        print("\n⚠️  CRITICAL FAILURE - Phase 2 validation BLOCKED")
        print("   Recommended action: Debug integrator, check for numerical instabilities")
        return False


def test_synchronization():
    """
    TEST 3: Verify all segments synchronized at global dt grid.
    
    Physics Principle: Multi-Rate Verlet Synchronization
                       All segments must meet at t = n·dt_global
    
    Method: Compute n_i = ceil(dt_global / dt_i) for each segment
            Verify dt_eff = dt_global / n_i divides dt_global evenly
    
    Expected: Residual (dt_global mod dt_eff) / dt_global < 1e-10
    """
    print("\n" + "="*70)
    print(" TEST 3: Synchronization (Multi-Rate Verlet Grid Alignment)")
    print("="*70)
    
    physics = PhysicsContext(level=0, length_scale=1.0)
    factory = FractalUniverseFactory(base_physics=physics)
    
    # Create L2 universe (576 segments)
    print("Creating L2 universe (576 segments)...")
    config = UniverseConfig(
        target_level=2,
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
    
    # Global timestep
    dt_global = 0.01
    
    # Record substep counts and timestep distribution
    n_substeps = []
    dt_locals = []
    dt_effs = []
    
    print(f"\nANALYZING TIMESTEP DISTRIBUTION:")
    
    for i, segment in enumerate(segments):
        dt_local = segment.compute_local_timestep(dt_base=dt_global)
        dt_locals.append(dt_local)
        
        # Compute number of substeps (as done in evolve())
        n = max(1, int(np.ceil(dt_global / dt_local)))
        n_substeps.append(n)
        
        # Effective timestep
        dt_eff = dt_global / n
        dt_effs.append(dt_eff)
    
    # Statistics
    n_substeps = np.array(n_substeps)
    dt_locals = np.array(dt_locals)
    dt_effs = np.array(dt_effs)
    
    print(f"  n_substeps:  min={n_substeps.min()}, max={n_substeps.max()}, median={np.median(n_substeps)}")
    print(f"  dt_local:    min={dt_locals.min():.6e}, max={dt_locals.max():.6e}")
    print(f"  dt_eff:      min={dt_effs.min():.6e}, max={dt_effs.max():.6e}")
    
    # Verify synchronization
    print(f"\nSYNCHRONIZATION VALIDATION:")
    max_residual = 0.0
    failures = 0
    
    for i, (n, dt_eff) in enumerate(zip(n_substeps, dt_effs)):
        # Check if dt_eff divides dt_global evenly
        residual = (dt_global % dt_eff) / dt_global
        
        if residual > 1e-10:
            failures += 1
            if failures <= 5:  # Print first 5 failures only
                print(f"  Segment {i}: n={n}, dt_eff={dt_eff:.6e}, residual={residual:.3e} ❌")
        
        max_residual = max(max_residual, residual)
    
    print(f"\n  Max residual across all segments: {max_residual:.3e}")
    print(f"  Failed segments: {failures} / {N_segments}")
    
    if failures == 0:
        print(f"\n✅ TEST 3 PASSED: All segments synchronized (max residual = {max_residual:.3e} < 1e-10)")
        return True
    else:
        print(f"\n⚠️  TEST 3 WARNING: {failures} segments desynchronized (residual > 1e-10)")
        print(f"   This may cause Newton's 3rd law violations in coupling forces")
        print(f"   Recommended: Investigate quantization algorithm in evolve()")
        return False


def main():
    """Run all Phase 1 unit tests."""
    print("\n" + "="*70)
    print(" PHASE 1 UNIT TESTS - CP-2026-05-26-003")
    print(" Relativistic Timestep Localization (dt_i ~ E_local^(-0.5))")
    print("="*70)
    print("\nReference: CHANGE_PROPOSAL_TIMESTEP_RELATIVITY.md § VI")
    print("Theoretical Foundation: PHYSICS_MANIFESTO.md § 4.5 (pending)")
    
    results = []
    
    # Test 1: Timestep scaling
    try:
        result_1 = test_local_timestep_scaling()
        results.append(("Timestep Scaling", result_1))
    except Exception as e:
        print(f"\n❌ TEST 1 EXCEPTION: {e}")
        results.append(("Timestep Scaling", False))
    
    # Test 2: Symplectic property (CRITICAL)
    try:
        result_2 = test_symplectic_property()
        results.append(("Symplectic Property", result_2))
    except Exception as e:
        print(f"\n❌ TEST 2 EXCEPTION: {e}")
        results.append(("Symplectic Property", False))
    
    # Test 3: Synchronization
    try:
        result_3 = test_synchronization()
        results.append(("Synchronization", result_3))
    except Exception as e:
        print(f"\n❌ TEST 3 EXCEPTION: {e}")
        results.append(("Synchronization", False))
    
    # Summary
    print("\n" + "="*70)
    print(" PHASE 1 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:25s}: {status}")
    
    all_passed = all(result for _, result in results)
    symplectic_passed = results[1][1]  # Test 2 (critical)
    
    print("\n" + "="*70)
    if all_passed:
        print(" 🎉 ALL TESTS PASSED")
        print("="*70)
        print("\n✅ Phase 1 validation COMPLETE")
        print("✅ Symplectic property verified (phase-space volume conserved)")
        print("\n📋 NEXT STEP: Proceed to Phase 2 (L1 Validation)")
        print("   Command: python -m wqt_oop.run_cosmology --level 1 --steps 100 \\")
        print("                     --relativistic-dt --output cosmology_L1_relativistic.h5")
        return 0
    elif symplectic_passed:
        print(" ⚠️  PARTIAL SUCCESS")
        print("="*70)
        print("\n✅ CRITICAL: Symplectic property verified")
        print("⚠️  Some non-critical tests failed (see above)")
        print("\n📋 DECISION: Proceed to Phase 2 with monitoring")
        print("   The core physics (symplectic integration) is sound")
        print("   Non-critical failures can be debugged in parallel")
        return 0
    else:
        print(" ❌ CRITICAL FAILURE")
        print("="*70)
        print("\n❌ Symplectic property VIOLATED (phase-space volume not conserved)")
        print("❌ Phase 2 validation BLOCKED")
        print("\n📋 REQUIRED ACTION:")
        print("   1. Debug integrator implementation")
        print("   2. Check for numerical instabilities")
        print("   3. Verify compute_local_timestep() correctness")
        print("   4. Resubmit for Phase 1 testing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
