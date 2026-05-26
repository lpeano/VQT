"""
CONVERGENCE TEST - Strang Splitting Accuracy

Test symplectic property with decreasing timesteps.
Expected: drift ~ O(dt²) for Velocity Verlet
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.physics_context import PhysicsContext


def test_convergence(dt, n_steps):
    """Run convergence test with given timestep."""
    
    # Create segment
    physics = PhysicsContext(level=0, length_scale=1.0)
    segment = SegmentoQuantistico(
        chi=50.0,
        vel=0.1,
        physics=physics,
        position=np.array([0.0, 0.0, 0.0])
    )
    
    # Disable all damping
    segment.gamma_damping = 0.0
    segment._fdt_enabled = False
    segment._local_friction = 0.0
    segment._substep_threshold = 1e20
    
    # Initial energy
    H_0 = segment.compute_hamiltonian_internal()
    
    # Evolve
    for _ in range(n_steps):
        segment.evolve(dt, external_force=0.0)
    
    # Final energy
    H_final = segment.compute_hamiltonian_internal()
    drift = abs(H_final - H_0) / H_0
    
    return H_0, H_final, drift


def main():
    print("\n" + "="*80)
    print(" CONVERGENCE TEST - Strang Splitting O(dt²) Accuracy")
    print("="*80)
    print("\nTest: Energy conservation with decreasing timesteps")
    print("Expected: drift ~ C·dt² (2nd order Verlet)")
    print("\n" + "="*80)
    
    # Test different timesteps (same total time T=10.0)
    T_total = 10.0
    timesteps = [0.1, 0.01, 0.001, 0.0001]
    
    results = []
    
    print(f"\n{'dt':>10} | {'n_steps':>8} | {'H_0':>12} | {'H_final':>12} | {'drift':>12} | drift/dt²")
    print("-" * 80)
    
    for dt in timesteps:
        n_steps = int(T_total / dt)
        H_0, H_final, drift = test_convergence(dt, n_steps)
        drift_over_dt2 = drift / (dt**2)
        
        results.append((dt, drift, drift_over_dt2))
        
        print(f"{dt:10.4f} | {n_steps:8d} | {H_0:12.6e} | {H_final:12.6e} | {drift:12.3e} | {drift_over_dt2:8.2f}")
    
    print("\n" + "="*80)
    print("ANALYSIS:")
    print("="*80)
    
    # Check if drift scales as O(dt²)
    print("\nIf drift ~ C·dt², then drift/dt² should be approximately constant:")
    for i, (dt, drift, ratio) in enumerate(results):
        print(f"  dt={dt:7.4f}: drift/dt² = {ratio:8.2f}")
    
    # Compare ratios
    ratios = [r[2] for r in results]
    ratio_std = np.std(ratios)
    ratio_mean = np.mean(ratios)
    
    print(f"\nMean drift/dt²: {ratio_mean:.2f}")
    print(f"Std drift/dt²:  {ratio_std:.2f}")
    print(f"Coefficient of variation: {ratio_std/ratio_mean*100:.1f}%")
    
    # Final assessment
    print("\n" + "="*80)
    print("VERDICT:")
    print("="*80)
    
    # Check smallest timestep
    smallest_dt_drift = results[-1][1]
    
    if smallest_dt_drift < 1e-8:
        print(f"✅ SYMPLECTIC PROPERTY VALIDATED!")
        print(f"   With dt=0.0001: drift = {smallest_dt_drift:.3e} < 1e-8")
        print(f"   Strang Splitting successfully restores symplecticity")
        return 0
    elif ratio_std / ratio_mean < 0.3:  # Consistent O(dt²) scaling
        print(f"✅ O(dt²) CONVERGENCE CONFIRMED!")
        print(f"   drift/dt² varies by only {ratio_std/ratio_mean*100:.1f}%")
        print(f"   Verlet algorithm working correctly")
        if smallest_dt_drift < 1e-6:
            print(f"   With dt=0.0001: drift = {smallest_dt_drift:.3e}")
            print(f"   → Acceptable for production (use smaller dt if needed)")
            return 0
        else:
            print(f"   ⚠️  But drift={smallest_dt_drift:.3e} at dt=0.0001 is high")
            print(f"   → May need investigation")
            return 1
    else:
        print(f"❌ NON-CONVERGENT BEHAVIOR!")
        print(f"   drift/dt² varies by {ratio_std/ratio_mean*100:.1f}%")
        print(f"   Expected < 30% for O(dt²) method")
        print(f"   → Algorithm may not be 2nd order")
        return 1


if __name__ == "__main__":
    exit(main())
