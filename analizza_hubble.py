import h5py
import numpy as np

with h5py.File('geometrodinamica_matrix.h5', 'r') as f:
    tel = f['telemetria_scalare'][:]
    
print('\n=== ANALISI TELEMETRIA (120 frames) ===')
print(f'Range Hubble: {tel["h_fisica"].min():.6e} → {tel["h_fisica"].max():.6e} s⁻¹')
print(f'Hubble medio: {tel["h_fisica"].mean():.6e} s⁻¹')
print(f'Frames con H>0 (espansione): {np.sum(tel["h_fisica"] > 0)}')
print(f'Frames con H<0 (contrazione): {np.sum(tel["h_fisica"] < 0)}')
print(f'Frames con |H|<1e-43 (vuoto quantistico): {np.sum(np.abs(tel["h_fisica"]) < 1e-43)}')
print(f'Frames con |H|<1e-50 (stasi): {np.sum(np.abs(tel["h_fisica"]) < 1e-50)}')

# Campioni di valori
print(f'\nPrimi 5 valori H:')
for i in range(min(5, len(tel))):
    print(f"  Frame {i}: H = {tel['h_fisica'][i]:.6e} s⁻¹")
