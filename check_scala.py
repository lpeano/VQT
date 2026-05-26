#!/usr/bin/env python3
"""
Script rapido per verificare l'evoluzione della scala nella simulazione
"""
import h5py
import numpy as np

db_path = 'geometrodinamica_matrix.h5'

try:
    with h5py.File(db_path, 'r', libver='latest', swmr=True) as f:
        # Leggi telemetria
        tel = f['telemetria_scalare'][:]
        
        # Trova frame validi (rm > 0)
        valid = tel['rm'] > 0
        tel_valid = tel[valid]
        
        if len(tel_valid) == 0:
            print("Nessun frame valido trovato!")
        else:
            n_frames = len(tel_valid)
            print(f"Frame validi: {n_frames}")
            print(f"\n{'='*70}")
            print(f"STATO ATTUALE (Frame {n_frames-1}):")
            print(f"{'='*70}")
            
            ultimo = tel_valid[-1]
            
            # Leggi chi medio
            if 'chi_medio' in ultimo.dtype.names:
                chi = ultimo['chi_medio']
            else:
                chi = ultimo['chi_lineare']
            
            # Calcola esponente
            if np.abs(chi) < 15.0:
                esponente = chi - 35.0
            else:
                esponente = np.sign(chi) * (15.0 + np.log(np.abs(chi) - 13.5) * 5.0) - 35.0
            
            scala_metri = 10**esponente
            
            print(f"Chi (χ):           {chi:.6f}")
            print(f"Esponente:         {esponente:.2f}")
            print(f"Scala fisica:      10^{esponente:.2f} m = {scala_metri:.3e} m")
            print(f"Raggio conforme:   {ultimo['rm']:.6e} m")
            
            # Velocità chi
            if 'v_chi_medio' in ultimo.dtype.names:
                v_chi = ultimo['v_chi_medio']
            else:
                v_chi = ultimo['v_chi']
            
            print(f"Velocità χ (v_chi): {v_chi:.3e}")
            
            # Stima tempo per raggiungere scale successive
            print(f"\n{'='*70}")
            print(f"PREVISIONI CAMBIO SCALA:")
            print(f"{'='*70}")
            
            # Scala di Planck: 10^-35 m (chi = 0)
            if v_chi != 0:
                delta_chi_planck = 0 - chi
                frames_to_planck = delta_chi_planck / v_chi
                
                print(f"\nScala di Planck (10^-35 m, chi=0):")
                print(f"  Δχ necessario:   {delta_chi_planck:.3f}")
                print(f"  Frames stimati:  {frames_to_planck:.0f}")
                
                # Altre scale interessanti
                target_scales = [
                    (-30, "10^-30 m (nucleo atomico)"),
                    (-25, "10^-25 m (scala nucleare)"),
                    (-15, "10^-15 m (protone)"),
                    (-10, "10^-10 m (atomo)"),
                    (0, "1 metro (scala umana)"),
                ]
                
                for chi_target, desc in target_scales:
                    if np.abs(chi_target) < 15.0:
                        esp_target = chi_target - 35.0
                    else:
                        esp_target = np.sign(chi_target) * (15.0 + np.log(np.abs(chi_target) - 13.5) * 5.0) - 35.0
                    
                    delta_chi = chi_target - chi
                    frames_needed = delta_chi / v_chi if v_chi != 0 else float('inf')
                    
                    if frames_needed > 0 and frames_needed < 1e9:
                        print(f"\n{desc}:")
                        print(f"  χ target:        {chi_target:.1f}")
                        print(f"  Δχ necessario:   {delta_chi:.3f}")
                        print(f"  Frames stimati:  {frames_needed:.0f}")
            else:
                print("\nVelocità χ = 0: sistema in equilibrio stazionario")
                print("Non ci sarà cambio di scala senza perturbazioni esterne")
            
            # Mostra trend ultimi 10 frame
            if n_frames >= 10:
                print(f"\n{'='*70}")
                print(f"TREND ULTIMI 10 FRAMES:")
                print(f"{'='*70}")
                ultimi_10 = tel_valid[-10:]
                
                if 'chi_medio' in ultimi_10.dtype.names:
                    chi_vals = ultimi_10['chi_medio']
                else:
                    chi_vals = ultimi_10['chi_lineare']
                
                print(f"Chi iniziale: {chi_vals[0]:.6f}")
                print(f"Chi finale:   {chi_vals[-1]:.6f}")
                print(f"Variazione:   {chi_vals[-1] - chi_vals[0]:.6f}")
                print(f"Variazione/frame: {(chi_vals[-1] - chi_vals[0])/10:.3e}")
                
except FileNotFoundError:
    print(f"File {db_path} non trovato!")
except Exception as e:
    print(f"Errore: {e}")
    import traceback
    traceback.print_exc()
