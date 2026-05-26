"""Verifica rapida dati chi_vettore nel database HDF5"""
import h5py
import numpy as np
import sys

with h5py.File(sys.argv[1], 'r') as f:
    tel = f['telemetria_scalare'][:]
    
    # Ultimo frame valido
    valid = tel['rm'] > 0
    tel_valid = tel[valid]
    
    if len(tel_valid) == 0:
        print("ERRORE: Nessun frame valido!")
        sys.exit(1)
    
    ultimo = tel_valid[-1]
    chi_vec = ultimo['chi_vettore']
    
    print(f"\nFrame: {ultimo['frame_id']}")
    print(f"Chi vettore (24 valori):")
    print(chi_vec)
    print(f"\nStatistiche:")
    print(f"  Min:     {np.min(chi_vec):.4f}")
    print(f"  Max:     {np.max(chi_vec):.4f}")
    print(f"  Range:   {np.ptp(chi_vec):.4f}")
    print(f"  Media:   {np.mean(chi_vec):.4f}")
    print(f"  Var(χ):  {np.var(chi_vec):.6e}")
    print(f"  Std Dev: {np.std(chi_vec):.4f}")
