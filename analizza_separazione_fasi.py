#!/usr/bin/env python3
"""
ANALISI SEPARAZIONE FASI - Mappatura Topologica 24 Segmenti
============================================================
Analizza la configurazione dei 24 campi locali per identificare
la geometria della separazione materia/spazio dopo inizializzazione bimodale.

Obiettivi:
- Identificare quali segmenti sono MATERIA (χ > 0) vs SPAZIO (χ < 0)
- Verificare stabilità temporale della configurazione
- Calcolare statistiche dei cluster
- Visualizzare evoluzione temporale
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# ==============================================================================
# CARICAMENTO DATI
# ==============================================================================

print("=" * 80)
print("ANALISI SEPARAZIONE FASI - Test Rottura Simmetria Forzata")
print("=" * 80)

# Apri file HDF5 con dati simulazione
db_file = "test_rottura_simmetria_forzata.h5"

try:
    with h5py.File(db_file, 'r') as f:
        # Verifica presenza dataset
        if 'telemetria_scalare' not in f:
            print(f"❌ Dataset 'telemetria_scalare' non trovato in {db_file}")
            exit(1)
        
        telemetria = f['telemetria_scalare']
        n_frames = len(telemetria)
        
        print(f"\n📁 File: {db_file}")
        print(f"📊 Frame disponibili: {n_frames}")
        
        # Estrai configurazione χ per tutti i 24 segmenti
        # Il campo 'chi_vettore' contiene array (24,) con valori per ogni segmento
        
        # Prima frame per verificare
        frame0 = telemetria[0]
        print(f"\n🔍 Struttura Dataset:")
        print(f"   Campi disponibili: {list(frame0.dtype.names)}")
        print(f"   Shape chi_vettore: {frame0['chi_vettore'].shape}")
        
        # Estrai tutti i vettori χ (shape: n_frames × 24)
        chi_array_24 = np.array([telemetria[i]['chi_vettore'] for i in range(n_frames)])
        chi_medio = np.array([telemetria[i]['chi_medio'] for i in range(n_frames)])
        
        print(f"\n✅ Dati estratti:")
        print(f"   chi_array_24: {chi_array_24.shape} (frame × segmenti)")
        print(f"   chi_medio: {len(chi_medio)} valori")
        print(f"   Range chi_medio: [{chi_medio.min():.3f}, {chi_medio.max():.3f}]")
        
        # Salva per uso successivo
        chi_24_data = chi_array_24
        
        # Analizza configurazione iniziale e finale
        frame_iniziale = 0
        frame_finale = min(n_frames - 1, 89)
        
        chi_init = chi_24_data[frame_iniziale]
        chi_final = chi_24_data[frame_finale]
        
        # Identifica segmenti stabili
        stable_materia = np.where((chi_init > 0) & (chi_final > 0))[0]
        stable_spazio = np.where((chi_init < 0) & (chi_final < 0))[0]
        flipped = np.where(np.sign(chi_init) != np.sign(chi_final))[0]
        
        # Varianza temporale per segmento
        var_per_segment = np.var(chi_24_data, axis=0)
            
except FileNotFoundError:
    print(f"❌ File {db_file} non trovato!")
    print("\n💡 Suggerimento: Verifica che la simulazione abbia completato almeno alcuni frame.")
    exit(1)

# ==============================================================================
# ANALISI CONFIGURAZIONE INIZIALE VS FINALE
# ==============================================================================

print("\n" + "=" * 80)
print("MAPPATURA SEGMENTI - CONFIGURAZIONE MATERIA/SPAZIO")
print("=" * 80)

# Analizza configurazione iniziale (frame 0) e finale
frame_iniziale = 0
frame_finale = min(n_frames - 1, 89)  # Usa ultimo frame disponibile

chi_init = chi_24_data[frame_iniziale]
chi_final = chi_24_data[frame_finale]

print(f"\n📍 Frame Iniziale (λ≈0):")
print(f"   Segmenti MATERIA (χ > 0): {np.sum(chi_init > 0)}")
print(f"   Segmenti SPAZIO (χ < 0): {np.sum(chi_init < 0)}")
print(f"   χ range: [{chi_init.min():.3f}, {chi_init.max():.3f}]")
print(f"   χ medio: {chi_init.mean():.3f} ± {chi_init.std():.3f}")

print(f"\n📍 Frame Finale (λ≈{frame_finale/10:.1f}):")
print(f"   Segmenti MATERIA (χ > 0): {np.sum(chi_final > 0)}")
print(f"   Segmenti SPAZIO (χ < 0): {np.sum(chi_final < 0)}")
print(f"   χ range: [{chi_final.min():.3f}, {chi_final.max():.3f}]")
print(f"   χ medio: {chi_final.mean():.3f} ± {chi_final.std():.3f}")

# Calcola persistenza: quanti segmenti mantengono lo stesso segno?
same_sign = np.sum(np.sign(chi_init) == np.sign(chi_final))
print(f"\n🔒 Persistenza topologica:")
print(f"   Segmenti con stesso segno (init→final): {same_sign}/24 ({100*same_sign/24:.1f}%)")

# Identifica segmenti stabili
stable_materia = np.where((chi_init > 0) & (chi_final > 0))[0]
stable_spazio = np.where((chi_init < 0) & (chi_final < 0))[0]
flipped = np.where(np.sign(chi_init) != np.sign(chi_final))[0]

print(f"   Sempre MATERIA: {len(stable_materia)} segmenti → {list(stable_materia)}")
print(f"   Sempre SPAZIO:  {len(stable_spazio)} segmenti → {list(stable_spazio)}")
if len(flipped) > 0:
    print(f"   FLIPPED (cambio segno): {len(flipped)} segmenti → {list(flipped)}")

# Calcola varianza temporale per ogni segmento
print(f"\n📊 Varianza temporale per segmento:")
var_per_segment = np.var(chi_24_data, axis=0)  # Varianza lungo tempo
most_stable_idx = np.argmin(var_per_segment)
most_dynamic_idx = np.argmax(var_per_segment)

print(f"   Segmento più stabile:  #{most_stable_idx} (var={var_per_segment[most_stable_idx]:.2f})")
print(f"   Segmento più dinamico: #{most_dynamic_idx} (var={var_per_segment[most_dynamic_idx]:.2f})")

# ==============================================================================
# ANALISI CONFIGURAZIONE INIZIALE VS FINALE (vecchia sezione rimossa)
# ==============================================================================

# Leggi log flussi per dati aggiuntivi
try:
    with open("flussi_24campi.log", 'r') as log:
        lines = log.readlines()
        
        # Estrai varianze da log
        varianze = []
        lambdas = []
        max_flussi = []
        
        for line in lines:
            if line.startswith(('Frame', '====', 'LOG', 'LEGENDA')):
                continue
            if 'Var(chi)' in line:
                parts = line.split()
                # Formato: "Frame lambda=X.X Var(chi)=Y.YYe+ZZ ..."
                try:
                    # Trova indice di Var(chi)=
                    for i, part in enumerate(parts):
                        if 'Var(chi)=' in part:
                            var_str = part.split('=')[1]
                            varianze.append(float(var_str))
                        if 'lambda=' in part:
                            lam_str = part.split('=')[1]
                            lambdas.append(float(lam_str))
                        if 'Max|flux|=' in part:
                            flux_str = part.split('=')[1]
                            max_flussi.append(float(flux_str))
                except (ValueError, IndexError):
                    continue
        
        n_log_frames = len(varianze)
        print(f"\n📈 Dati da log flussi:")
        print(f"   Frame analizzati: {n_log_frames}")
        print(f"   Varianza χ:")
        print(f"      - Media: {np.mean(varianze):.1f}")
        print(f"      - Min: {np.min(varianze):.1f} (frame {np.argmin(varianze)})")
        print(f"      - Max: {np.max(varianze):.1f} (frame {np.argmax(varianze)})")
        print(f"   Max|Flusso|:")
        print(f"      - Media: {np.mean(max_flussi):.2f}")
        print(f"      - Min: {np.min(max_flussi):.2f}")
        print(f"      - Max: {np.max(max_flussi):.2f}")
        
except FileNotFoundError:
    print("⚠️ flussi_24campi.log non trovato, salto analisi varianze")
    varianze = []
    lambdas = []
    max_flussi = []

# ==============================================================================
# STATISTICHE SEPARAZIONE
# ==============================================================================

if len(varianze) > 0:
    print("\n" + "=" * 80)
    print("STATISTICHE SEPARAZIONE FASI")
    print("=" * 80)
    
    # Conta frame con separazione
    sep_threshold = 100  # Var(χ) > 100 considerato SEP_FASI
    n_sep = np.sum(np.array(varianze) > sep_threshold)
    
    print(f"\n🎯 Separazione di fase:")
    print(f"   Frame con Var(χ) > {sep_threshold}: {n_sep}/{n_log_frames} ({100*n_sep/n_log_frames:.1f}%)")
    
    # Stabilità della separazione
    var_array = np.array(varianze)
    if len(var_array) > 10:
        # Calcola deriva temporale
        trend = np.polyfit(range(len(var_array)), var_array, 1)[0]
        print(f"   Trend varianza: {trend:+.2f} per frame")
        if abs(trend) < 10:
            print(f"   → ✅ STABILE (deriva < 10)")
        else:
            print(f"   → ⚠️ INSTABILE (deriva ≥ 10)")

# ==============================================================================
# VISUALIZZAZIONE
# ==============================================================================

if len(varianze) > 0 and len(max_flussi) > 0:
    print("\n" + "=" * 80)
    print("GENERAZIONE GRAFICI")
    print("=" * 80)
    
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(4, 2, figure=fig, hspace=0.35, wspace=0.3)
    
    # 1. Evoluzione temporale di TUTTI i 24 campi χᵢ(t)
    ax1 = fig.add_subplot(gs[0, :])
    time_axis = np.arange(len(chi_24_data)) * 0.1  # λ = frame * 0.1
    for i in range(24):
        color = 'red' if chi_24_data[0, i] > 0 else 'blue'
        alpha = 0.6 if i in stable_materia or i in stable_spazio else 0.3
        linewidth = 1.5 if i in stable_materia or i in stable_spazio else 0.8
        ax1.plot(time_axis, chi_24_data[:, i], color=color, alpha=alpha, linewidth=linewidth)
    
    ax1.axhline(y=0, color='black', linestyle='--', linewidth=2, alpha=0.5)
    ax1.set_xlabel('λ (tempo affine)', fontsize=12)
    ax1.set_ylabel('χᵢ (chiralità locale)', fontsize=12)
    ax1.set_title('Evoluzione 24 Campi Locali - ROSSO=Materia(+), BLU=Spazio(-)', 
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 2. Varianza χ nel tempo
    ax2 = fig.add_subplot(gs[1, :])
    ax2.plot(lambdas, varianze, 'b-', linewidth=2, label='Var(χ)')
    ax2.axhline(y=100, color='r', linestyle='--', alpha=0.5, label='Soglia SEP_FASI')
    ax2.set_xlabel('λ (tempo affine)', fontsize=12)
    ax2.set_ylabel('Var(χ)', fontsize=12)
    ax2.set_title('Evoluzione Varianza Chiralità - Indicatore Separazione', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_yscale('log')
    
    # 3. Heatmap configurazione segmenti nel tempo
    ax3 = fig.add_subplot(gs[2, 0])
    im = ax3.imshow(chi_24_data.T, aspect='auto', cmap='RdBu_r', 
                    extent=[0, time_axis[-1], 0, 24], 
                    vmin=-6, vmax=6, interpolation='nearest')
    ax3.set_xlabel('λ (tempo affine)', fontsize=12)
    ax3.set_ylabel('Segmento ID', fontsize=12)
    ax3.set_title('Heatmap χᵢ(t) - 24 Segmenti', fontsize=12, fontweight='bold')
    cbar3 = plt.colorbar(im, ax=ax3)
    cbar3.set_label('χᵢ', fontsize=10)
    
    # 4. Distribuzione valori χ (frame finale)
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.hist(chi_final, bins=20, color='green', alpha=0.7, edgecolor='black')
    ax4.axvline(x=0, color='black', linestyle='--', linewidth=2, label='χ=0 (separazione)')
    ax4.set_xlabel('χ (frame finale)', fontsize=12)
    ax4.set_ylabel('N. segmenti', fontsize=12)
    ax4.set_title(f'Distribuzione χ al Frame {frame_finale}', fontsize=12, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    # 5. Scatter Varianza vs Flusso
    ax5 = fig.add_subplot(gs[3, 0])
    scatter = ax5.scatter(varianze, max_flussi, c=lambdas, cmap='viridis', alpha=0.6, s=50)
    ax5.set_xlabel('Var(χ)', fontsize=12)
    ax5.set_ylabel('Max|Flusso|', fontsize=12)
    ax5.set_title('Correlazione Varianza-Flusso', fontsize=12, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    cbar = plt.colorbar(scatter, ax=ax5)
    cbar.set_label('λ (tempo)', fontsize=10)
    
    # 6. Varianza per segmento (bar chart)
    ax6 = fig.add_subplot(gs[3, 1])
    colors_bar = ['red' if i in stable_materia else 'blue' if i in stable_spazio else 'gray' 
                  for i in range(24)]
    ax6.bar(range(24), var_per_segment, color=colors_bar, alpha=0.7, edgecolor='black')
    ax6.set_xlabel('Segmento ID', fontsize=12)
    ax6.set_ylabel('Var(χᵢ) temporale', fontsize=12)
    ax6.set_title('Stabilità per Segmento - Rosso=Materia, Blu=Spazio', fontsize=12, fontweight='bold')
    ax6.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle('ANALISI SEPARAZIONE FASI - Inizializzazione Bimodale ±4.5', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    output_file = "analisi_separazione_fasi.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✅ Grafici salvati in: {output_file}")
    plt.close()

# ==============================================================================
# CONCLUSIONI
# ==============================================================================

print("\n" + "=" * 80)
print("CONCLUSIONI")
print("=" * 80)

if len(varianze) > 0:
    if np.mean(varianze) > 1000:
        print("\n🎉 SEPARAZIONE DI FASE CONFERMATA!")
        print(f"   Varianza media: {np.mean(varianze):.1f} >> 100 (soglia)")
        print(f"   Persistenza: {n_sep}/{n_log_frames} frame ({100*n_sep/n_log_frames:.1f}%)")
        print("\n✅ Il sistema mantiene configurazione separata (materia vs spazio)")
        print("✅ Nessuna regressione verso omogeneità (Big Freeze evitato)")
    else:
        print("\n⚠️ Separazione debole o instabile")
        print(f"   Varianza media: {np.mean(varianze):.1f}")

print("\n" + "=" * 80)
print("PROSSIMI PASSI SUGGERITI:")
print("=" * 80)
print("1. Estrarre configurazione χᵢ per ogni segmento (richiede modifica salvataggio HDF5)")
print("2. Mappare correlazioni topologiche su reticolo di Leech")
print("3. Identificare cluster persistenti (quali segmenti restano 'materia'?)")
print("4. Stress test: perturbazione esterna per testare robustezza")
print("=" * 80)
