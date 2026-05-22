import h5py
import os

file_path = 'geometrodinamica_matrix.h5'

if not os.path.exists(file_path):
    print(f"File non trovato: {file_path}")
else:
    try:
        with h5py.File(file_path, 'r') as f:
            if 'telemetria_scalare' in f:
                frames = f['telemetria_scalare'].shape[0]
                print(f"✓ File HDF5: {file_path}")
                print(f"✓ Frames totali: {frames}")
                
                # Verifica quanti sono validi (rm > 0)
                import numpy as np
                scalari = f['telemetria_scalare'][:]
                validi = np.sum(scalari['rm'] > 0)
                print(f"✓ Frames validi: {validi}")
            else:
                print("⚠️ Dataset 'telemetria_scalare' non trovato")
                print(f"Datasets disponibili: {list(f.keys())}")
    except Exception as e:
        print(f"Errore apertura file: {e}")
