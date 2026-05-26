import h5py
import numpy as np
import os

# Disabilita file locking
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

try:
    with h5py.File(r'C:\Users\lpeano\plank\VQT\geometrodinamica_matrix.h5', 'r') as f:
        print("=== CONTENUTO FILE HDF5 ===")
        print(f"\nDataset disponibili: {list(f.keys())}")
        
        if 'telemetria_scalare' in f:
            tel = f['telemetria_scalare']
            print(f"\nTelemetria shape: {tel.shape}")
            print(f"Telemetria dtype: {tel.dtype}")
            
            if tel.shape[0] > 0:
                # Conta quanti frame hanno rm > 0 (validi)
                scalari = tel[:]
                valid_indices = np.where(scalari['rm'] > 0)[0]
                print(f"\n✓ Frame TOTALI nel dataset: {tel.shape[0]}")
                print(f"✓ Frame VALIDI (rm > 0): {len(valid_indices)}")
                
                if len(valid_indices) > 0:
                    print(f"✓ Ultimo frame valido: {valid_indices[-1]}")
                    print(f"\nPrimo frame valido [0]:")
                    print(tel[0])
                    print(f"\nUltimo frame valido [{valid_indices[-1]}]:")
                    print(tel[valid_indices[-1]])
                else:
                    print("\n❌ PROBLEMA: Tutti i frame hanno rm = 0 (INVALIDI)")
                    print(f"\nEsempio primo frame:")
                    print(tel[0])
            else:
                print("\n❌ TELEMETRIA VUOTA - Nessun frame salvato!")
        
        print(f"\nAttributi file: {dict(f.attrs)}")
        
except Exception as e:
    print(f"❌ ERRORE lettura file: {e}")
    import traceback
    traceback.print_exc()
