import h5py
import numpy as np

# Apriamo il file HDF5 che contiene la cronologia della torsione
with h5py.File('geometrodinamica_matrix.h5', 'r') as f:
    # Estraiamo i dati di torsione e scala metrica
    telemetria = f['telemetria_scalare'][:]
    torsione = telemetria['torsione']
    rm = telemetria['rm']
    
    # Cerchiamo gli indici dove rm < 1e-35 (la zona di Planck)
    indici_critici = np.where(rm < 1e-35)[0]
    
    if len(indici_critici) > 0:
        print(f"Trovati {len(indici_critici)} step nella zona sub-planckiana.")
        print(f"Valore medio torsione in zona critica: {np.mean(torsione[indici_critici]):.4e}")
        print(f"Valore max torsione: {np.max(torsione[indici_critici]):.4e}")
    else:
        print("Il manifold non è mai entrato sotto la scala di Planck.")