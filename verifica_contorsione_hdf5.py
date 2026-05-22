"""
Script di verifica dei dati di contorsione e chiusura spinoriale salvati nel file HDF5.
"""

import h5py
import numpy as np

file_path = 'geometrodinamica_matrix.h5'

print("=" * 70)
print("VERIFICA DATI GEOMETRIA CON TORSIONE NEL FILE HDF5")
print("=" * 70)

try:
    with h5py.File(file_path, 'r') as f:
        print(f"\nFile: {file_path}")
        print(f"Attributi del file:")
        for key, value in f.attrs.items():
            print(f"  {key}: {value}")
        
        if 'telemetria_scalare' in f:
            data = f['telemetria_scalare'][:]
            print(f"\nDataset 'telemetria_scalare':")
            print(f"  Shape: {data.shape}")
            print(f"  Dtype: {data.dtype}")
            print(f"\nCampi disponibili:")
            for name in data.dtype.names:
                print(f"  - {name}")
            
            # Verifica che il campo contorsione_k esista
            if 'contorsione_k' in data.dtype.names:
                print(f"\n✓ Campo 'contorsione_k' presente!")
                
                # Trova i frame validi (con rm > 0)
                valid_frames = data['rm'] > 0
                num_valid = np.sum(valid_frames)
                
                print(f"\nFrame validi: {num_valid}/{len(data)}")
                
                if num_valid > 0:
                    contorsione_values = data['contorsione_k'][valid_frames]
                    
                    print(f"\nStatistiche della contorsione K:")
                    print(f"  Valore minimo: {np.min(contorsione_values):.6e}")
                    print(f"  Valore massimo: {np.max(contorsione_values):.6e}")
                    print(f"  Valore medio: {np.mean(contorsione_values):.6e}")
                    print(f"  Deviazione std: {np.std(contorsione_values):.6e}")
                    
                    # Mostra i primi 10 valori
                    print(f"\nPrimi 10 valori di contorsione:")
                    for i in range(min(10, num_valid)):
                        frame_id = data['frame_id'][valid_frames][i]
                        k_val = contorsione_values[i]
                        rm_val = data['rm'][valid_frames][i]
                        print(f"  Frame {int(frame_id):3d}: K = {k_val:.6e}, r_m = {rm_val:.6e}")
                    
                    # Verifica che i valori non siano tutti zero
                    nonzero_count = np.sum(np.abs(contorsione_values) > 1e-15)
                    print(f"\nValori non-zero: {nonzero_count}/{num_valid} ({100*nonzero_count/num_valid:.1f}%)")
                    
                    if nonzero_count > 0:
                        print("\n✓ Calcolo della contorsione funzionante!")
                    else:
                        print("\n⚠ Tutti i valori sono zero - possibile problema nel calcolo")
                else:
                    print("\n⚠ Nessun frame valido trovato")
            else:
                print(f"\n✗ Campo 'contorsione_k' NON presente")
                print("  Il file potrebbe essere stato generato con una versione precedente")
            
            # Verifica campo chiusura_spinore
            print("\n" + "-" * 70)
            if 'chiusura_spinore' in data.dtype.names:
                print(f"\n✓ Campo 'chiusura_spinore' presente!")
                
                if num_valid > 0:
                    chiusura_values = data['chiusura_spinore'][valid_frames]
                    
                    print(f"\nStatistiche della chiusura spinoriale:")
                    print(f"  Valore minimo: {np.min(chiusura_values):.6e}")
                    print(f"  Valore massimo: {np.max(chiusura_values):.6e}")
                    print(f"  Valore medio: {np.mean(chiusura_values):.6e}")
                    print(f"  Deviazione std: {np.std(chiusura_values):.6e}")
                    
                    # Mostra i primi 10 valori
                    print(f"\nPrimi 10 valori di chiusura spinore:")
                    for i in range(min(10, num_valid)):
                        frame_id = data['frame_id'][valid_frames][i]
                        chi_val = chiusura_values[i]
                        k_val = data['contorsione_k'][valid_frames][i] if 'contorsione_k' in data.dtype.names else 0
                        print(f"  Frame {int(frame_id):3d}: Chiusura = {chi_val:+.6e}, K = {k_val:.6e}")
                    
                    # Interpretazione
                    print(f"\n  Interpretazione fisica:")
                    err_medio = np.mean(np.abs(chiusura_values))
                    if err_medio < 0.01:
                        print(f"    ✓ ECCELLENTE: Chiusura topologica quasi perfetta!")
                        print(f"    Il solitone è topologicamente stabile (fermionico).")
                    elif err_medio < 0.05:
                        print(f"    ✓ BUONO: Chiusura entro tolleranza fisica.")
                        print(f"    Il solitone mantiene carattere fermionico.")
                    elif err_medio < 0.1:
                        print(f"    ⚠ ACCETTABILE: Deviazione moderata.")
                        print(f"    Il solitone è parzialmente stabile.")
                    else:
                        print(f"    ✗ CRITICO: Violazione del vincolo topologico!")
                        print(f"    Errore medio: {err_medio:.2%}")
                        print(f"    Il solitone potrebbe non essere fermionicamente stabile.")
                    
                    # Verifica che i valori non siano tutti zero
                    nonzero_count = np.sum(np.abs(chiusura_values) > 1e-15)
                    print(f"\n  Valori non-zero: {nonzero_count}/{num_valid} ({100*nonzero_count/num_valid:.1f}%)")
                    
                    if nonzero_count > 0:
                        print("\n  ✓ Calcolo della chiusura spinoriale funzionante!")
                    else:
                        print("\n  ⚠ Tutti i valori sono zero - possibile problema nel calcolo")
            else:
                print(f"\n✗ Campo 'chiusura_spinore' NON presente")
                print("  Il file potrebbe essere stato generato con una versione precedente")
        else:
            print("\n✗ Dataset 'telemetria_scalare' non trovato")
            
except Exception as e:
    print(f"\n✗ Errore durante la lettura del file: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
