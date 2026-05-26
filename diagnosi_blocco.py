#!/usr/bin/env python3
"""
Analisi DETTAGLIATA per capire perché il sistema è bloccato
"""
import h5py
import numpy as np

db_path = 'geometrodinamica_matrix.h5'

with h5py.File(db_path, 'r', libver='latest', swmr=True) as f:
    tel = f['telemetria_scalare'][:]
    
    valid = tel['rm'] > 0
    tel_valid = tel[valid]
    
    n = len(tel_valid)
    print(f"Frame totali validi: {n}\n")
    
    if n == 0:
        print("Nessun dato!")
        exit()
    
    # Prendi campioni distribuiti
    if n >= 50:
        indices = np.linspace(0, n-1, 50, dtype=int)
        campioni = tel_valid[indices]
    else:
        campioni = tel_valid
    
    print("="*80)
    print("ANALISI EVOLUZIONE TEMPORALE")
    print("="*80)
    
    if 'chi_vettore' in campioni.dtype.names:
        print("\nModalità: 24 CAMPI LOCALI\n")
        
        # Estrai serie temporali
        chi_medie = []
        chi_std = []
        vel_medie = []
        vel_std = []
        frames = []
        
        for i, frame in enumerate(campioni):
            chi_vec = frame['chi_vettore']
            vel_vec = frame['vel_vettore']
            
            chi_medie.append(np.mean(chi_vec))
            chi_std.append(np.std(chi_vec))
            vel_medie.append(np.mean(vel_vec))
            vel_std.append(np.std(vel_vec))
            frames.append(frame['frame_id'])
        
        chi_medie = np.array(chi_medie)
        vel_medie = np.array(vel_medie)
        
        print(f"Frame range: {frames[0]} → {frames[-1]}")
        print(f"\nChi medio:")
        print(f"  Iniziale:  {chi_medie[0]:.10f}")
        print(f"  Finale:    {chi_medie[-1]:.10f}")
        print(f"  Variazione TOTALE: {chi_medie[-1] - chi_medie[0]:.12f}")
        
        # Calcola deriva (trend lineare)
        if len(chi_medie) > 2:
            coeffs = np.polyfit(np.arange(len(chi_medie)), chi_medie, 1)
            deriva_per_frame = coeffs[0]
            print(f"  Deriva lineare: {deriva_per_frame:.3e} per campione")
            
            if abs(deriva_per_frame) < 1e-10:
                print(f"  ⚠️  DERIVA PRATICAMENTE ZERO!")
        
        print(f"\nVelocità media:")
        print(f"  Iniziale:  {vel_medie[0]:.3e}")
        print(f"  Finale:    {vel_medie[-1]:.3e}")
        print(f"  Range:     [{np.min(vel_medie):.3e}, {np.max(vel_medie):.3e}]")
        
        # ANALISI CRUCIALE: Distribuzioni dei 24 segmenti
        print("\n" + "="*80)
        print("DISTRIBUZIONE 24 SEGMENTI (frame finale)")
        print("="*80)
        
        ultimo = tel_valid[-1]
        chi_vec = ultimo['chi_vettore']
        vel_vec = ultimo['vel_vettore']
        
        # Arrotonda per trovare gruppi
        chi_arrotondato = np.round(chi_vec, decimals=6)
        valori_unici = np.unique(chi_arrotondato)
        
        print(f"\nNumero di valori χ distinti: {len(valori_unici)}")
        
        if len(valori_unici) <= 5:
            print("\n⚠️ ⚠️ ⚠️  PROBLEMA RILEVATO: SEGREGAZIONE IN GRUPPI ⚠️ ⚠️ ⚠️\n")
            print("Distribuzione dei segmenti:")
            for val in valori_unici:
                mask = np.abs(chi_vec - val) < 1e-5
                count = np.sum(mask)
                vel_gruppo = vel_vec[mask]
                print(f"\n  Gruppo χ ≈ {val:+.6f}:")
                print(f"    Segmenti:    {count}/24")
                print(f"    Velocità:    media={np.mean(vel_gruppo):.3e}, std={np.std(vel_gruppo):.3e}")
        
        # Controlla se tutti i segmenti sono bloccati in ±4.5
        in_minimo_negativo = np.sum(np.abs(chi_vec - (-4.5)) < 0.5)
        in_minimo_positivo = np.sum(np.abs(chi_vec - (+4.5)) < 0.5)
        
        print(f"\n" + "="*80)
        print("VERIFICA INTRAPPOLAMENTO NEI MINIMI DEL POTENZIALE")
        print("="*80)
        print(f"\nSegmenti vicino a χ = -4.5: {in_minimo_negativo}/24")
        print(f"Segmenti vicino a χ = +4.5: {in_minimo_positivo}/24")
        print(f"Totale nei minimi:          {in_minimo_negativo + in_minimo_positivo}/24")
        
        if (in_minimo_negativo + in_minimo_positivo) >= 20:
            print("\n⚠️ ⚠️ ⚠️  SISTEMA INTRAPPOLATO NEI MINIMI DEL POTENZIALE! ⚠️ ⚠️ ⚠️")
            print("\nFISICA:")
            print("  Il potenziale V(χ) = -χ² + 0.02χ⁴ ha minimi a χ ≈ ±5")
            print("  I segmenti sono inizializzati a χ = ±4.5 (vicino ai minimi)")
            print("  La barriera di potenziale tra i minimi impedisce il passaggio")
            print("  Risultato: oscillazioni locali ma NO espansione globale")
            print("\nSOLUZIONE:")
            print("  1. Aumentare l'energia iniziale (velocità più alte)")
            print("  2. Ridurre la barriera di potenziale")
            print("  3. Aumentare le perturbazioni stocastiche")
        
        # Verifica contorsione
        if 'contorsione_locale' in ultimo.dtype.names:
            K_loc = ultimo['contorsione_locale']
            K_critico = 4.0 * np.pi
            
            print(f"\n" + "="*80)
            print("CONTORSIONE TOPOLOGICA")
            print("="*80)
            print(f"\nK² medio:         {np.mean(K_loc):.6f}")
            print(f"K² soglia (720°): {K_critico:.6f}")
            print(f"Segmenti sopra soglia: {np.sum(K_loc > K_critico)}/24")
            
            if np.all(K_loc < K_critico):
                print("\n✓ Tutti i segmenti sotto soglia → NO attivazione bounce")
    
    else:
        print("Modalità SCALARE")
        chi_vals = [f['chi_lineare'] for f in campioni]
        print(f"\nChi iniziale: {chi_vals[0]:.6f}")
        print(f"Chi finale:   {chi_vals[-1]:.6f}")
        print(f"Variazione:   {chi_vals[-1] - chi_vals[0]:.6f}")
