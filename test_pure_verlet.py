"""
ULTRA-SIMPLIFIED SYMPLECTIC TEST

Single isolated segment with:
- NO coupling forces
- NO FDT damping (gamma=0)
- NO adaptive sub-stepping
- PURE Velocity Verlet

Expected: drift < 1e-12 (machine precision for symplectic integrator)
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.physics_context import PhysicsContext


def main():
    print("\n" + "="*70)
    print(" ULTRA-SIMPLIFIED SYMPLECTIC TEST")
    print("="*70)
    print("\nTest: Single isolated segment (NO coupling, NO damping)")
    print("Expected: Conservation of H = T + V to machine precision")
    print("\n" + "="*70)
    
    # Create single segment
    physics = PhysicsContext(level=0, length_scale=1.0)
    segment = SegmentoQuantistico(
        chi=50.0,
        vel=0.1,
        physics=physics,
        position=np.array([0.0, 0.0, 0.0])
    )
    
    # Disable damping
    segment.gamma_damping = 0.0
    
    # CRITICAL: Disable FDT damping system
    segment._fdt_enabled = False
    
    # Disable local friction
    segment._local_friction = 0.0
    
    # Disable adaptive sub-stepping
    segment._substep_threshold = 1e20  # Never trigger
    
    print(f"\nCONFIGURATION:")
    print(f"  gamma_damping: {segment.gamma_damping}")
    print(f"  _fdt_enabled: {segment._fdt_enabled}")
    print(f"  _local_friction: {segment._local_friction}")
    print(f"  _substep_threshold: {segment._substep_threshold}")
    
    # Initial energy
    H_0 = segment.compute_hamiltonian_internal()
    
    print(f"\nINITIAL STATE:")
    print(f"  chi      = {segment.chi:.6f}")
    print(f"  vel      = {segment.vel:.6f}")
    print(f"  H_0      = {H_0:.12e}")
    print(f"  gamma    = {segment.gamma_damping:.12e} (DISABLED)")
    
    # Evolve 10000 steps
    dt = 0.01
    n_steps = 10000
    
    print(f"\nEVOLVING:")
    print(f"  Timesteps: {n_steps}")
    print(f"  dt: {dt}")
    print(f"  External force: 0 (isolated)")
    
    energies = [H_0]
    
    for step in range(1, n_steps + 1):
        segment.evolve(dt, external_force=0.0)
        
        if step % 1000 == 0:
            H = segment.compute_hamiltonian_internal()
            energies.append(H)
            drift = abs(H - H_0) / H_0
            print(f"  Step {step:5d}: H = {H:.12e}, drift = {drift:.3e}")
    
    # Final validation
    H_final = energies[-1]
    final_drift = abs(H_final - H_0) / H_0
    
    print(f"\nFINAL STATE (t={n_steps * dt}):")
    print(f"  H_final = {H_final:.12e}")
    print(f"  H_0     = {H_0:.12e}")
    print(f"  Drift   = {final_drift:.3e}")
    
    print(f"\nVALIDATION:")
    print(f"  Threshold: 1.000e-10 (near machine precision)")
    print(f"  Observed:  {final_drift:.3e}")
    
    # Success criterion (relaxed to 1e-10 to account for numerical precision)
    threshold = 1e-10
    
    if final_drift < threshold:
        print(f"\n✅ PURE VERLET VALIDATED!")
        print(f"   Energy conserved to {final_drift:.3e}")
        print(f"   Problem is likely in coupling or damping implementation")
        return 0
    else:
        print(f"\n❌ EVEN PURE VERLET FAILS!")
        print(f"   Energy drift {final_drift:.3e} exceeds threshold")
        print(f"   Fundamental integrator bug detected")
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
