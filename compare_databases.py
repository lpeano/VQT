import h5py
import numpy as np

print('='*70)
print('CONFRONTO: test_aging_dinamico.h5 (torsion) vs test_aging_velocity.h5')
print('='*70)

# Database 1: Torsion-based aging
f1 = h5py.File('test_aging_dinamico.h5', 'r')
tel1 = f1['telemetria_scalare']
vel1 = tel1['vel_vettore']
tau1 = tel1['tau_locale']
chi1 = tel1['chi_vettore']

print('\n### DATABASE 1: test_aging_dinamico.h5 (TORSION-BASED)')
print(f'Frames: {len(tel1)}')
print('\nVelocità:')
for frame in [0, 100, 300, 500, 719]:
    v = vel1[frame]
    print(f'  Frame {frame:3d}: mean|v|={np.mean(np.abs(v)):7.4f}, std(v)={np.std(v):9.6f}, Range=[{np.min(v):8.3f}, {np.max(v):8.3f}]')

v_f = vel1[719]
tau_f = tau1[719]
chi_f = chi1[719]
print(f'\nFRAME FINALE:')
print(f'  std(v)   = {np.std(v_f):.6f}')
print(f'  std(τ)   = {np.std(tau_f):.6f}')
print(f'  Var(χ)   = {np.var(chi_f):.4f}')
print(f'  H        = {tel1["h_fisica"][719]:.6e}')

f1.close()

# Database 2: Velocity-based aging
f2 = h5py.File('test_aging_velocity.h5', 'r')
tel2 = f2['telemetria_scalare']
vel2 = tel2['vel_vettore']
tau2 = tel2['tau_locale']
chi2 = tel2['chi_vettore']

print('\n### DATABASE 2: test_aging_velocity.h5 (VELOCITY-BASED)')
print(f'Frames: {len(tel2)}')
print('\nVelocità:')
for frame in [0, 100, 300, 500, 719]:
    v = vel2[frame]
    print(f'  Frame {frame:3d}: mean|v|={np.mean(np.abs(v)):7.4f}, std(v)={np.std(v):9.6f}, Range=[{np.min(v):8.3f}, {np.max(v):8.3f}]')

v_f = vel2[719]
tau_f = tau2[719]
chi_f = chi2[719]
print(f'\nFRAME FINALE:')
print(f'  std(v)   = {np.std(v_f):.6f}')
print(f'  std(τ)   = {np.std(tau_f):.6f}')
print(f'  Var(χ)   = {np.var(chi_f):.4f}')
print(f'  H        = {tel2["h_fisica"][719]:.6e}')

f2.close()

print('\n' + '='*70)
print('DIAGNOSI:')
print('='*70)
print('Se DB2 mostra v=-1000 → BUG nel codice velocity-based')
print('Se DB1 mostra std(v) >> 0 → Velocità esistono, ma aging torsion fallisce')
print('='*70)
