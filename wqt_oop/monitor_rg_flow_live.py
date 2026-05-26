"""
================================================================================
MONITOR RG FLOW LIVE - Tracking K(t) durante simulazione
================================================================================

Questo script monitora in tempo reale l'evoluzione della torsione K durante
una simulazione cosmologica attiva (SWMR mode).

Obiettivo: Verificare se K_L3 converge verso 0.185 * K_L2 man mano che
           il sistema raggiunge equilibrio termodinamico.

Author: Luca Peano
Date: 2026-05-26
================================================================================
"""

import h5py
import numpy as np
import time
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Tuple


def monitor_k_evolution(filepath: Path, 
                        interval: int = 30,
                        max_checks: int = 100) -> List[Tuple[float, float, float]]:
    """
    Monitora evoluzione di K durante simulazione attiva.
    
    Parameters:
    -----------
    filepath : Path
        Path al file HDF5 in SWMR mode
    
    interval : int
        Secondi tra controlli
    
    max_checks : int
        Numero massimo controlli
    
    Returns:
    --------
    history : list of (time, K_mean, K_std)
        Storico evoluzione K
    """
    history = []
    
    print("="*80)
    print("MONITORING RG FLOW LIVE")
    print("="*80)
    print(f"File: {filepath.name}")
    print(f"Check interval: {interval}s")
    print(f"Max checks: {max_checks}")
    print("\nWaiting for simulation to start...")
    
    # Aspetta che file esista
    while not filepath.exists():
        time.sleep(1)
    
    print(f"OK File detected: {filepath}")
    print("\nStarting monitoring...\n")
    print(f"{'Check':<8} {'Time':<10} {'Frames':<8} {'K_mean':<12} {'K_std':<12} {'Trend':<10}")
    print("-"*80)
    
    last_frame_count = 0
    
    for check in range(max_checks):
        try:
            with h5py.File(filepath, 'r', swmr=True) as f:
                if 'frames' not in f:
                    print(f"{check:<8} {'--':<10} {'--':<8} {'Initializing...':<50}")
                    time.sleep(interval)
                    continue
                
                frames_group = f['frames']
                frames = sorted([k for k in frames_group.keys() if k.startswith('frame_')])
                
                if len(frames) == 0:
                    print(f"{check:<8} {'--':<10} {0:<8} {'No frames yet':<50}")
                    time.sleep(interval)
                    continue
                
                # Nuovo frame disponibile?
                if len(frames) == last_frame_count:
                    print(f"{check:<8} {'--':<10} {len(frames):<8} {'Waiting for new frame...':<50}")
                    time.sleep(interval)
                    continue
                
                last_frame_count = len(frames)
                
                # Leggi ultimo frame
                last_frame = frames_group[frames[-1]]
                K = last_frame['contorsione_locale'][:]
                K_clean = K[np.isfinite(K)]
                
                t = last_frame.attrs['time']
                K_mean = np.mean(K_clean)
                K_std = np.std(K_clean)
                
                history.append((t, K_mean, K_std))
                
                # Calcola trend (se abbastanza dati)
                if len(history) >= 3:
                    recent_K = [h[1] for h in history[-3:]]
                    trend = "↓ Decreasing" if recent_K[-1] < recent_K[0] else "↑ Increasing"
                else:
                    trend = "--"
                
                print(f"{check:<8} {t:<10.2f} {len(frames):<8} {K_mean:<12.3f} {K_std:<12.3f} {trend:<10}")
                
        except (OSError, KeyError) as e:
            print(f"{check:<8} ERROR: {str(e)[:60]}")
        
        time.sleep(interval)
    
    print("\n" + "="*80)
    print(f"Monitoring complete: {len(history)} data points collected")
    print("="*80)
    
    return history


def plot_k_evolution(history: List[Tuple[float, float, float]], 
                     target_K: float = None,
                     output_file: str = 'k_evolution_live.png') -> None:
    """
    Plotta evoluzione K nel tempo con banda target.
    
    Parameters:
    -----------
    history : list
        Storico (time, K_mean, K_std)
    
    target_K : float, optional
        Valore K atteso da RG flow (es. 0.185 * K_L2)
    
    output_file : str
        Nome file output
    """
    if len(history) == 0:
        print("WARNING: No data to plot")
        return
    
    times = np.array([h[0] for h in history])
    K_means = np.array([h[1] for h in history])
    K_stds = np.array([h[2] for h in history])
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle('K Evolution - Live Monitoring', fontsize=16, fontweight='bold')
    
    # --- PLOT 1: K(t) con errorbars ---
    ax = axes[0]
    ax.errorbar(times, K_means, yerr=K_stds, fmt='o-', markersize=6, 
                linewidth=2, capsize=4, label='K_mean(t)')
    
    if target_K is not None:
        ax.axhline(target_K, color='red', linestyle='--', linewidth=2, 
                   label=f'Target RG Flow: {target_K:.3f}')
        ax.fill_between([times[0], times[-1]], target_K*0.95, target_K*1.05, 
                        alpha=0.2, color='red', label='Target ±5%')
    
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('K_mean (torsione)', fontsize=12)
    ax.set_title('Convergenza verso Equilibrio', fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # --- PLOT 2: Rate di cambiamento ---
    ax = axes[1]
    if len(times) > 1:
        dK_dt = np.diff(K_means) / np.diff(times)
        times_mid = (times[:-1] + times[1:]) / 2
        ax.plot(times_mid, dK_dt, 'o-', markersize=6, linewidth=2, color='green')
        ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('dK/dt', fontsize=12)
    ax.set_title('Rate di Screening Topologico', fontsize=13)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved: {output_file}")
    plt.show()


def main():
    """Main monitoring pipeline."""
    # File da monitorare
    filepath = Path('cosmology_L3_equilibrio.h5')
    
    # Target RG flow (K_L3 atteso = 0.185 * K_L2)
    K_L2 = 10.122  # Dal dataset precedente
    target_K = 0.185 * K_L2  # = 1.873
    
    print(f"\nTarget K_L3 (RG flow prediction): {target_K:.3f}")
    print(f"   (currently K_L3 = 3.117, transient state)")
    
    # Monitora evoluzione
    history = monitor_k_evolution(
        filepath=filepath,
        interval=60,  # Check ogni minuto
        max_checks=300  # Max 5 ore
    )
    
    # Plot risultati
    if len(history) > 0:
        plot_k_evolution(history, target_K=target_K)
        
        # Analisi convergenza
        if len(history) >= 3:
            K_initial = history[0][1]
            K_final = history[-1][1]
            convergence = (K_initial - K_final) / K_initial * 100
            
            print(f"\nCONVERGENCE ANALYSIS")
            print(f"   K_initial: {K_initial:.3f}")
            print(f"   K_final:   {K_final:.3f}")
            print(f"   Delta %:   {convergence:.1f}%")
            print(f"   Target:    {target_K:.3f}")
            
            if abs(K_final - target_K) / target_K < 0.1:
                print(f"\nSUCCESS: K converges to RG flow prediction!")
            else:
                print(f"\nWARNING: K still far from target (distance: {abs(K_final - target_K):.3f})")


if __name__ == '__main__':
    main()
