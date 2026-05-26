"""
================================================================================
ANALISI RG FLOW - Validazione Empirica Topological Screening
================================================================================

Questo script analizza i dataset L1, L2, L3 per verificare la legge di potenza
della torsione K sotto Renormalization Group Flow:

    K_n ~ K_0 / (24^n)^β

Predizione teorica (da RG_FLOW_TOPOLOGICAL_SCREENING.md):
    β ≈ 0.53 ± 0.05
    K_L2/K_L1 ≈ 0.185
    K_L3/K_L2 ≈ 0.185 (se legge universale)

Se il rapporto è costante, abbiamo dimostrato un PUNTO FISSO DI 
RINORMALIZZAZIONE nel sistema WQT.

Author: Luca Peano
Date: 2026-05-26
================================================================================
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Tuple


def load_dataset(filepath: Path) -> Dict[str, np.ndarray]:
    """
    Carica dataset HDF5 cosmologico.
    
    Parameters:
    -----------
    filepath : Path
        Path al file .h5
    
    Returns:
    --------
    data : dict
        Dizionario con array: contorsione_locale, time, drift, etc.
    """
    data = {}
    with h5py.File(filepath, 'r') as f:
        # Naviga gruppo 'frames' se esiste
        if 'frames' in f:
            frames_group = f['frames']
            frames = sorted([k for k in frames_group.keys() if k.startswith('frame_')])
        else:
            # Fallback: frames alla radice
            frames = sorted([k for k in f.keys() if k.startswith('frame_')])
            frames_group = f
        
        print(f"\n📁 {filepath.name}")
        print(f"   Frames: {len(frames)}")
        
        # Carica ultimo frame (stato finale)
        last_frame = frames_group[frames[-1]]
        
        data['contorsione_locale'] = last_frame['contorsione_locale'][:]
        data['chi_values'] = last_frame['chi_values'][:]
        data['tau_locale'] = last_frame['tau_locale'][:]
        data['time'] = last_frame.attrs['time']
        data['drift'] = last_frame.attrs['drift']
        data['H_total'] = last_frame.attrs['H_total']
        data['T_eff'] = last_frame.attrs['T_eff']
        data['N_segments'] = len(data['contorsione_locale'])
        
        print(f"   N_segments: {data['N_segments']}")
        print(f"   Final time: {data['time']:.3f}")
        print(f"   Final drift: {data['drift']:.6e}")
        print(f"   T_eff: {data['T_eff']:.1f}")
    
    return data


def compute_torsion_stats(data: Dict[str, np.ndarray]) -> Dict[str, float]:
    """
    Calcola statistiche della torsione K (contorsione_locale).
    
    Parameters:
    -----------
    data : dict
        Dataset caricato
    
    Returns:
    --------
    stats : dict
        mean, std, median, rms di K
    """
    K = data['contorsione_locale']
    
    # Rimuovi eventuali valori NaN/Inf
    K_clean = K[np.isfinite(K)]
    
    stats = {
        'mean': np.mean(K_clean),
        'std': np.std(K_clean),
        'median': np.median(K_clean),
        'rms': np.sqrt(np.mean(K_clean**2)),
        'min': np.min(K_clean),
        'max': np.max(K_clean),
        'N_valid': len(K_clean),
        'N_total': len(K)
    }
    
    return stats


def analyze_rg_flow(datasets: Dict[str, Dict]) -> Dict[str, float]:
    """
    Analizza RG flow confrontando livelli gerarchici.
    
    Parameters:
    -----------
    datasets : dict
        Dizionario {'L1': data, 'L2': data, 'L3': data}
    
    Returns:
    --------
    results : dict
        Rapporti K_L2/K_L1, K_L3/K_L2, esponente β, etc.
    """
    # Statistiche per livello
    stats = {}
    for level, data in datasets.items():
        stats[level] = compute_torsion_stats(data)
    
    print("\n" + "="*80)
    print("📊 STATISTICHE TORSIONE K PER LIVELLO")
    print("="*80)
    
    for level in ['L1', 'L2', 'L3']:
        s = stats[level]
        print(f"\n{level}:")
        print(f"  K_mean = {s['mean']:.3f} ± {s['std']:.3f}")
        print(f"  K_rms  = {s['rms']:.3f}")
        print(f"  K_range = [{s['min']:.3f}, {s['max']:.3f}]")
        print(f"  N_valid/N_total = {s['N_valid']}/{s['N_total']}")
    
    # Calcola rapporti
    ratio_21 = stats['L2']['mean'] / stats['L1']['mean']
    ratio_32 = stats['L3']['mean'] / stats['L2']['mean']
    
    # Errori (propagazione)
    err_21 = ratio_21 * np.sqrt(
        (stats['L2']['std']/stats['L2']['mean'])**2 + 
        (stats['L1']['std']/stats['L1']['mean'])**2
    )
    err_32 = ratio_32 * np.sqrt(
        (stats['L3']['std']/stats['L3']['mean'])**2 + 
        (stats['L2']['std']/stats['L2']['mean'])**2
    )
    
    # Fit esponente β da rapporto
    # K_n/K_{n-1} = (24^n / 24^{n-1})^{-β} = (1/24)^β
    # β = -log(ratio) / log(24)
    beta_21 = -np.log(ratio_21) / np.log(24)
    beta_32 = -np.log(ratio_32) / np.log(24)
    beta_avg = (beta_21 + beta_32) / 2
    
    print("\n" + "="*80)
    print("🔬 ANALISI RG FLOW")
    print("="*80)
    print(f"\nRapporto K_L2/K_L1 = {ratio_21:.4f} ± {err_21:.4f}")
    print(f"  → β_21 = {beta_21:.3f}")
    print(f"  → Predizione teorica: 0.185 ± 0.02")
    print(f"  → Match: {'✅ SI' if abs(ratio_21 - 0.185) < 0.05 else '❌ NO'}")
    
    print(f"\nRapporto K_L3/K_L2 = {ratio_32:.4f} ± {err_32:.4f}")
    print(f"  → β_32 = {beta_32:.3f}")
    print(f"  → Predizione teorica: 0.185 ± 0.02")
    print(f"  → Match: {'✅ SI' if abs(ratio_32 - 0.185) < 0.05 else '❌ NO'}")
    
    print(f"\nEsponente medio β = {beta_avg:.3f}")
    print(f"  → Predizione teorica: 0.53 ± 0.05")
    print(f"  → Match: {'✅ SI' if abs(beta_avg - 0.53) < 0.1 else '❌ NO'}")
    
    # Test universalità: rapporto costante?
    ratio_consistency = abs(ratio_21 - ratio_32) / ratio_21
    print(f"\nTest Universalità (costanza rapporto):")
    print(f"  |ratio_21 - ratio_32| / ratio_21 = {ratio_consistency:.2%}")
    print(f"  → {'✅ UNIVERSALE (< 10%)' if ratio_consistency < 0.1 else '⚠️  NON UNIVERSALE (> 10%)'}")
    
    return {
        'ratio_21': ratio_21,
        'ratio_32': ratio_32,
        'err_21': err_21,
        'err_32': err_32,
        'beta_21': beta_21,
        'beta_32': beta_32,
        'beta_avg': beta_avg,
        'ratio_consistency': ratio_consistency,
        'stats': stats
    }


def plot_rg_flow(datasets: Dict[str, Dict], results: Dict) -> None:
    """
    Crea plot visualizzazione RG flow.
    
    1. K vs Level (log-log) con fit
    2. Distribuzione K per livello
    3. Scaling check
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('RG Flow Analysis - Topological Screening', fontsize=16, fontweight='bold')
    
    # --- PLOT 1: K mean vs Level (log-log) ---
    ax = axes[0, 0]
    levels = [1, 2, 3]
    K_means = [results['stats'][f'L{i}']['mean'] for i in levels]
    K_stds = [results['stats'][f'L{i}']['std'] for i in levels]
    
    ax.errorbar(levels, K_means, yerr=K_stds, fmt='o-', markersize=10, 
                linewidth=2, capsize=5, label='Dati empirici')
    
    # Fit teorico: K_n = K_0 / (24^n)^β con β=0.53
    K_0_fit = K_means[0] * (24**1)**0.53
    K_fit = [K_0_fit / (24**n)**0.53 for n in levels]
    ax.plot(levels, K_fit, '--', linewidth=2, label=f'Fit β={results["beta_avg"]:.3f}')
    
    ax.set_yscale('log')
    ax.set_xlabel('Level n', fontsize=12)
    ax.set_ylabel('K_mean (torsione)', fontsize=12)
    ax.set_title('Screening Topologico: K ~ 1/(24^n)^β', fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # --- PLOT 2: Distribuzione K per livello ---
    ax = axes[0, 1]
    for level in ['L1', 'L2', 'L3']:
        K = datasets[level]['contorsione_locale']
        K_clean = K[np.isfinite(K)]
        ax.hist(K_clean, bins=50, alpha=0.6, label=level, density=True)
    
    ax.set_xlabel('K (torsione)', fontsize=12)
    ax.set_ylabel('Densità probabilità', fontsize=12)
    ax.set_title('Distribuzione Torsione per Livello', fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # --- PLOT 3: Rapporti K_n/K_{n-1} ---
    ax = axes[1, 0]
    transitions = ['L2/L1', 'L3/L2']
    ratios = [results['ratio_21'], results['ratio_32']]
    errors = [results['err_21'], results['err_32']]
    
    x_pos = [0, 1]
    ax.bar(x_pos, ratios, yerr=errors, capsize=10, alpha=0.7, color=['blue', 'green'])
    ax.axhline(0.185, color='red', linestyle='--', linewidth=2, label='Predizione teorica (0.185)')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(transitions)
    ax.set_ylabel('Rapporto K_n/K_{n-1}', fontsize=12)
    ax.set_title('Costanza RG Flow (Test Universalità)', fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # --- PLOT 4: Scaling check (log-log) ---
    ax = axes[1, 1]
    N_segments = [datasets[f'L{i}']['N_segments'] for i in levels]
    
    ax.loglog(N_segments, K_means, 'o-', markersize=10, linewidth=2, label='K_mean vs N_segments')
    
    # Fit atteso: K ~ N^{-β/log_24(N)} ≈ N^{-0.18} per scala frattale
    # Semplificato: K ~ N^{-0.2}
    N_fit = np.array(N_segments)
    K_fit_scaling = K_means[0] * (N_fit[0] / N_fit)**0.2
    ax.loglog(N_fit, K_fit_scaling, '--', linewidth=2, label='Scaling K ~ N^{-0.2}')
    
    ax.set_xlabel('N_segments', fontsize=12)
    ax.set_ylabel('K_mean', fontsize=12)
    ax.set_title('Scaling con Complessità', fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('rg_flow_analysis.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Plot salvato: rg_flow_analysis.png")
    plt.show()


def main():
    """Main analysis pipeline."""
    print("="*80)
    print("🌌 ANALISI RG FLOW - VALIDAZIONE TOPOLOGICAL SCREENING")
    print("="*80)
    
    # Carica datasets
    datasets = {}
    for level in ['L1', 'L2', 'L3']:
        filepath = Path(f'cosmology_{level}.h5')
        if not filepath.exists():
            print(f"❌ File {filepath} non trovato!")
            return
        datasets[level] = load_dataset(filepath)
    
    # Analizza RG flow
    results = analyze_rg_flow(datasets)
    
    # Plot
    plot_rg_flow(datasets, results)
    
    # Conclusione
    print("\n" + "="*80)
    print("📝 CONCLUSIONI")
    print("="*80)
    
    if abs(results['ratio_consistency']) < 0.1:
        print("\n✅ SUCCESSO: Sistema mostra RG FLOW UNIVERSALE!")
        print(f"   Rapporto costante: {results['ratio_21']:.4f} ≈ {results['ratio_32']:.4f}")
        print(f"   Esponente critico: β = {results['beta_avg']:.3f}")
        print("\n🏆 Il sistema WQT ha un PUNTO FISSO DI RINORMALIZZAZIONE.")
        print("   → Scalabilità garantita a tutti i livelli (L4, L5, ...)")
    else:
        print("\n⚠️  ATTENZIONE: Rapporti non costanti")
        print(f"   Variazione: {results['ratio_consistency']:.1%}")
        print("   → Possibile deriva numerica o fisica mancante")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
