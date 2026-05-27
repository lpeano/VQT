"""
================================================================================
VISUALIZZAZIONE FRATTALE L2 - Playback Auto-Organizzazione Gerarchica
================================================================================

Legge fractal_l2_history.npz e mostra:
1. Evoluzione configurazione Materia/Spazio (24 compositi)
2. Conservazione H_conserved
3. Dinamica chi_barycenter (transizione di fase)
4. Oscillazioni collettive

Compatibile con vecchi software di plotting.
================================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def load_history(filename="fractal_l2_history.npz"):
    """Carica storia simulazione."""
    if not Path(filename).exists():
        raise FileNotFoundError(f"File {filename} non trovato!")
    
    data = np.load(filename)
    print(f"[OK] Caricato {filename}")
    print(f"     Chiavi disponibili: {list(data.keys())}")
    
    return data


def analyze_phase_transition(data):
    """Analizza transizione di fase macroscopica."""
    steps = data['steps']
    n_matter = data['n_composites_matter']
    n_space = data['n_composites_space']
    chi_bar = data['chi_barycenter']
    
    N_total = n_matter[0] + n_space[0]
    
    print("\n" + "="*80)
    print(" ANALISI TRANSIZIONE DI FASE")
    print("="*80)
    
    print(f"\nN_compositi totali = {N_total}")
    print(f"N_steps            = {len(steps)}")
    
    print(f"\nSTATO INIZIALE:")
    print(f"  Materia/Spazio = {n_matter[0]}/{n_space[0]}")
    print(f"  chi_barycenter = {chi_bar[0]:.3f}")
    
    print(f"\nSTATO FINALE:")
    print(f"  Materia/Spazio = {n_matter[-1]}/{n_space[-1]}")
    print(f"  chi_barycenter = {chi_bar[-1]:.3f}")
    
    # Configurazioni osservate
    configs = [(n_matter[i], n_space[i]) for i in range(len(steps))]
    unique_configs = list(set(configs))
    
    print(f"\nCONFIGURAZIONI OSSERVATE: {len(unique_configs)}")
    for config in sorted(unique_configs, key=lambda x: x[0], reverse=True):
        count = configs.count(config)
        fraction = count / len(steps) * 100
        print(f"  {config[0]:2d}/{config[1]:2d} M/S: {count:3d} step ({fraction:5.1f}%)")
    
    # Polarizzazione massima
    max_polarization = max(abs(n_matter[i] - N_total/2) for i in range(len(steps)))
    print(f"\nPOLARIZZAZIONE MASSIMA: {max_polarization:.0f} (da equilibrio {N_total/2:.0f})")
    
    # Oscillazioni
    transitions = sum(1 for i in range(1, len(n_matter)) if n_matter[i] != n_matter[i-1])
    print(f"TRANSIZIONI TOTALI: {transitions}")
    
    return unique_configs


def plot_evolution(data):
    """Plot evoluzione completa."""
    steps = data['steps']
    H_total = data['H_total']
    H_cons = data['H_conserved']
    E_rad = data['E_radiated']
    n_matter = data['n_composites_matter']
    n_space = data['n_composites_space']
    chi_bar = data['chi_barycenter']
    
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('SIMULAZIONE FRATTALE L2: Auto-Organizzazione Gerarchica (576 segmenti)', 
                 fontsize=14, fontweight='bold')
    
    # --- SUBPLOT 1: Configurazione M/S ---
    ax = axs[0, 0]
    ax.plot(steps, n_matter, 'ro-', label='Materia', linewidth=2, markersize=4)
    ax.plot(steps, n_space, 'bs-', label='Spazio', linewidth=2, markersize=4)
    ax.axhline(12, color='gray', linestyle='--', alpha=0.5, label='Equilibrio (12/12)')
    ax.set_xlabel('Step', fontsize=11)
    ax.set_ylabel('N compositi', fontsize=11)
    ax.set_title('Configurazione Materia/Spazio (24 compositi)', fontsize=12, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(alpha=0.3)
    
    # --- SUBPLOT 2: Conservazione Energia ---
    ax = axs[0, 1]
    ax.plot(steps, H_cons, 'g-', linewidth=2, label='H_conserved')
    ax.set_xlabel('Step', fontsize=11)
    ax.set_ylabel('H_conserved [unita naturali]', fontsize=11)
    ax.set_title('Conservazione Hamiltoniana', fontsize=12, fontweight='bold')
    ax.ticklabel_format(style='scientific', axis='y', scilimits=(-2,2))
    ax.grid(alpha=0.3)
    
    # Drift percentuale
    H_init = H_cons[0]
    drift_pct = abs(H_cons - H_init) / abs(H_init) * 100
    ax_twin = ax.twinx()
    ax_twin.plot(steps, drift_pct, 'r--', alpha=0.7, linewidth=1.5, label='Drift %')
    ax_twin.set_ylabel('Drift %', fontsize=11, color='red')
    ax_twin.tick_params(axis='y', labelcolor='red')
    ax_twin.set_ylim([0, max(0.01, drift_pct.max() * 1.1)])
    
    ax.legend(loc='upper left')
    ax_twin.legend(loc='upper right')
    
    # --- SUBPLOT 3: chi_barycenter (transizione di fase) ---
    ax = axs[1, 0]
    ax.plot(steps, chi_bar, 'purple', linewidth=2)
    ax.axhline(0, color='black', linestyle='-', alpha=0.3)
    ax.set_xlabel('Step', fontsize=11)
    ax.set_ylabel('chi_barycenter', fontsize=11)
    ax.set_title('Baricentro Topologico (transizione di fase)', fontsize=12, fontweight='bold')
    ax.grid(alpha=0.3)
    
    # Regioni
    ax.fill_between(steps, 0, chi_bar, where=(chi_bar > 0), 
                     color='red', alpha=0.2, label='Fase Materia')
    ax.fill_between(steps, chi_bar, 0, where=(chi_bar <= 0), 
                     color='blue', alpha=0.2, label='Fase Spazio')
    ax.legend(loc='best')
    
    # --- SUBPLOT 4: Energia Totale + Radiazione ---
    ax = axs[1, 1]
    ax.plot(steps, H_total, 'b-', linewidth=2, label='H_total')
    ax.plot(steps, E_rad, 'orange', linewidth=1.5, alpha=0.8, label='E_radiation')
    ax.set_xlabel('Step', fontsize=11)
    ax.set_ylabel('Energia [unita naturali]', fontsize=11)
    ax.set_title('Dinamica Energetica', fontsize=12, fontweight='bold')
    ax.ticklabel_format(style='scientific', axis='y', scilimits=(-2,2))
    ax.legend(loc='best')
    ax.grid(alpha=0.3)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Salva
    outfile = "fractal_l2_evolution.png"
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    print(f"\n[OK] Plot salvato: {outfile}")
    
    plt.show()


def plot_phase_space(data):
    """Plot spazio delle fasi (chi_bar vs n_matter)."""
    n_matter = data['n_composites_matter']
    chi_bar = data['chi_barycenter']
    steps = data['steps']
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Traiettoria colorata per tempo
    scatter = ax.scatter(chi_bar, n_matter, c=steps, cmap='viridis', 
                         s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
    
    # Punto iniziale/finale
    ax.plot(chi_bar[0], n_matter[0], 'go', markersize=15, label='Iniziale', 
            markeredgecolor='black', markeredgewidth=2)
    ax.plot(chi_bar[-1], n_matter[-1], 'r*', markersize=20, label='Finale', 
            markeredgecolor='black', markeredgewidth=2)
    
    ax.set_xlabel('chi_barycenter (carica topologica)', fontsize=12)
    ax.set_ylabel('N compositi Materia', fontsize=12)
    ax.set_title('Spazio delle Fasi: Auto-Organizzazione Gerarchica', 
                 fontsize=14, fontweight='bold')
    ax.axhline(12, color='gray', linestyle='--', alpha=0.5, label='Equilibrio')
    ax.axvline(0, color='gray', linestyle='--', alpha=0.5)
    ax.grid(alpha=0.3)
    ax.legend(loc='best', fontsize=11)
    
    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Step', fontsize=11)
    
    plt.tight_layout()
    
    outfile = "fractal_l2_phase_space.png"
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    print(f"[OK] Plot salvato: {outfile}")
    
    plt.show()


def print_conservation_report(data):
    """Report conservazione termodinamica."""
    H_cons = data['H_conserved']
    
    H_init = H_cons[0]
    H_final = H_cons[-1]
    drift_abs = abs(H_final - H_init)
    drift_pct = drift_abs / abs(H_init) * 100
    
    print("\n" + "="*80)
    print(" CONSERVAZIONE TERMODINAMICA")
    print("="*80)
    print(f"\nH_conserved_init  = {H_init:.6e}")
    print(f"H_conserved_final = {H_final:.6e}")
    print(f"Drift assoluto    = {drift_abs:.6e}")
    print(f"Drift relativo    = {drift_pct:.9f}%")
    
    if drift_pct < 1e-6:
        status = "PERFETTO (< 1e-6%)"
    elif drift_pct < 0.01:
        status = "ECCELLENTE (< 0.01%)"
    elif drift_pct < 0.1:
        status = "BUONO (< 0.1%)"
    else:
        status = "ACCETTABILE"
    
    print(f"Stato             = {status}")
    print("="*80)


def main():
    """Playback completo simulazione frattale L2."""
    print("="*80)
    print(" PLAYBACK SIMULAZIONE FRATTALE L2")
    print("="*80)
    
    # Carica dati
    data = load_history("fractal_l2_history.npz")
    
    # Analisi
    print_conservation_report(data)
    analyze_phase_transition(data)
    
    # Visualizzazione
    print("\n[...] Generazione plot...")
    plot_evolution(data)
    plot_phase_space(data)
    
    print("\n" + "="*80)
    print(" PLAYBACK COMPLETATO")
    print("="*80)


if __name__ == "__main__":
    main()
