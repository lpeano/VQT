#!/usr/bin/env python3
"""
================================================================================
SYSTEM AUDIT - L3 Simulation Diagnostics
================================================================================

Analizza drift energetico, force clipping e consistenza dati per
cosmology_L3_NEW.h5.
"""

import h5py
import numpy as np
from pathlib import Path

def main():
    h5_path = Path("cosmology_L3_NEW.h5")
    
    if not h5_path.exists():
        print(f"❌ File not found: {h5_path}")
        return
    
    print("="*80)
    print(" SYSTEM AUDIT - L3 SIMULATION DIAGNOSTICS")
    print("="*80)
    
    with h5py.File(h5_path, 'r') as f:
        # === METADATA ===
        print("\n=== 1. METADATA ===")
        for key, value in f.attrs.items():
            print(f"  {key}: {value}")
        
        # === FRAMES ===
        frames = sorted([k for k in f['frames'].keys()])
        print(f"\n=== 2. FRAMES INFO ===")
        print(f"  Total frames: {len(frames)}")
        print(f"  First: {frames[0]}")
        print(f"  Last: {frames[-1]}")
        
        # === FRAME 0 ===
        frame0 = f[f'frames/{frames[0]}']
        n_segments_0 = len(frame0['positions'])
        dof_0 = n_segments_0 * 2  # chi + v
        print(f"\n=== 3. FRAME 0 DATA ===")
        print(f"  N segments: {n_segments_0}")
        print(f"  Total DOF: {dof_0}")
        
        # === FRAME N ===
        frameN = f[f'frames/{frames[-1]}']
        n_segments_N = len(frameN['positions'])
        dof_N = n_segments_N * 2
        print(f"\n=== 4. FRAME {frames[-1]} DATA ===")
        print(f"  N segments: {n_segments_N}")
        print(f"  Total DOF: {dof_N}")
        
        # Consistency check
        if n_segments_0 != n_segments_N:
            print(f"\n⚠️  WARNING: DOF mismatch! Frame 0: {dof_0}, Frame {frames[-1]}: {dof_N}")
        else:
            print(f"\n✓ Consistency check PASSED: DOF constant = {dof_0}")
        
        # === DRIFT ANALYSIS ===
        print(f"\n=== 5. ENERGY & DRIFT ANALYSIS (Last 10 Frames) ===")
        drift_history = []
        energy_history = []
        
        # Compute initial energy (frame 0)
        frame0 = f['frames/frame_000000']
        chi0 = frame0['chi_values'][:]
        vel0 = frame0['velocities'][:]
        
        # H = T + V = 0.5*m*v^2 + beta*(chi^2 - chi0^2)^2
        # From physics: beta ≈ 1e-5, chi0 = 4.5
        mass = 1.0
        beta = 1e-5
        chi_stable = 4.5
        
        T0 = 0.5 * mass * np.sum(vel0**2)
        V0 = beta * np.sum((chi0**2 - chi_stable**2)**2)
        H_initial = T0 + V0
        
        print(f"  Frame 0: H_initial = {H_initial:.6e} J (T={T0:.6e}, V={V0:.6e})")
        
        for i, frame_key in enumerate(frames[-10:], start=len(frames)-10):
            frame = f[f'frames/{frame_key}']
            chi = frame['chi_values'][:]
            vel = frame['velocities'][:]
            
            # Compute energy
            T = 0.5 * mass * np.sum(vel**2)
            V = beta * np.sum((chi**2 - chi_stable**2)**2)
            H_total = T + V
            
            # Drift
            drift = abs(H_total - H_initial) / (abs(H_initial) + 1e-30)
            
            print(f"  Frame {i:2d}: H={H_total:.6e} J, drift={drift:.6e} ({drift*100:.3f}%)")
            drift_history.append(drift)
            energy_history.append(H_total)
        
        # Slope calculation (linear regression)
        if len(drift_history) >= 2:
            x = np.arange(len(drift_history))
            y = np.array(drift_history)
            slope = np.polyfit(x, y, 1)[0]
            
            print(f"\n=== 6. DRIFT SLOPE ANALYSIS ===")
            print(f"  Drift slope (last 10 frames): {slope:.6e}")
            
            if slope > 1e-4:
                print(f"  ⚠️  ALERT: Positive slope > 1e-4 detected!")
                print(f"  → Energy drift is INCREASING (potential instability)")
                print(f"  → Suspect: Insufficient damping or force clipping overflow")
            elif slope > 0:
                print(f"  ℹ️  INFO: Positive slope < 1e-4 (stable growth)")
            else:
                print(f"  ✓ Negative slope (drift decreasing, system stabilizing)")
        
        # === FORCE MAGNITUDE ANALYSIS ===
        print(f"\n=== 7. FORCE MAGNITUDE ANALYSIS ===")
        print(f"  (Estimating from chi and velocity changes)")
        
        # Compute force from acceleration: F = m * dv/dt
        # dv ≈ v[i+1] - v[i]
        if len(frames) >= 2:
            frame_prev = f[f'frames/{frames[-2]}']
            frame_curr = f[f'frames/{frames[-1]}']
            
            vel_prev = frame_prev['velocities'][:]
            vel_curr = frame_curr['velocities'][:]
            
            # Estimate dt from metadata
            dt = f.attrs.get('dt', 0.01)
            mass = 1.0  # Assume unit mass
            
            dv = vel_curr - vel_prev
            force_estimate = mass * dv / dt
            
            force_magnitude = np.abs(force_estimate)
            force_max = np.max(force_magnitude)
            force_mean = np.mean(force_magnitude)
            force_clipped = np.sum(force_magnitude > 999.0)  # Near clipping threshold
            
            print(f"  Estimated force magnitude:")
            print(f"    Mean: {force_mean:.2f} N")
            print(f"    Max: {force_max:.2f} N")
            print(f"    Near clipping (>999 N): {force_clipped} segments")
            
            if force_clipped > 0:
                print(f"\n  ⚠️  ALERT: {force_clipped} segments experiencing force clipping!")
                print(f"  → SAFETY VALVE #2 likely active")
                print(f"  → Consider increasing gamma_damping or reducing dt")
        
        # === TOPOLOGICAL CHARGE ANALYSIS ===
        print(f"\n=== 8. TOPOLOGICAL CHARGE DISTRIBUTION ===")
        frameN = f[f'frames/{frames[-1]}']
        chi_values = frameN['chi_values'][:]
        
        print(f"  Chi statistics:")
        print(f"    Min: {np.min(chi_values):.3f}")
        print(f"    Max: {np.max(chi_values):.3f}")
        print(f"    Mean: {np.mean(chi_values):.3f}")
        print(f"    Std: {np.std(chi_values):.3f}")
        
        # Check for anomalies (chi should be ~50 ± 5)
        chi_anomalies = np.sum((chi_values < 40) | (chi_values > 60))
        if chi_anomalies > 0:
            print(f"\n  ⚠️  {chi_anomalies} segments with anomalous chi (< 40 or > 60)")
    
    print("\n" + "="*80)
    print(" AUDIT COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
