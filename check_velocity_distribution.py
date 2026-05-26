import h5py
import numpy as np

# Apri database
f = h5py.File('test_aging_velocity.h5', 'r')
tel = f['telemetria_scalare']

print('=== DATABASE test_aging_velocity.h5 ===')
print(f'Frames salvati: {len(tel)}')
print(f'Campi HDF5: {list(tel.dtype.names)}')
print('')

# Estrai dati
vel = tel['vel_vettore']
tau = tel['tau_locale']
chi = tel['chi_vettore']
last_frame = len(tel) - 1

print('=== DISTRIBUZIONE VELOCITÀ (DIAGNOSI TOPOLOGICA) ===')
for frame in [0, 100, 200, 300, last_frame]:
    if frame <= last_frame:
        v = vel[frame]
        print(f'Frame {frame:3d}: v_mean={np.mean(np.abs(v)):7.4f}, std(v)={np.std(v):9.6f}, Range=[{np.min(v):8.3f}, {np.max(v):8.3f}]')

print('')

# Analizza frame finale
v_final = vel[last_frame]
var_v = np.std(v_final)

print('=== VERDETTO TOPOLOGICO ===')
if var_v > 0.1:
    print(f'✅ SUCCESSO: std(v) = {var_v:.4f} >> 0')
    print('   → Velocità DIFFERENZIATE tra i 24 campi')
    print('   → Aging relativistico FUNZIONERÀ')
    print('   → Sistema ha variabilità cinematica sufficiente')
else:
    print(f'❌ LIMITE TOPOLOGICO: std(v) = {var_v:.6f} ≈ 0')
    print('   → Velocità UNIFORMI (sincronizzazione forzata)')
    print('   → Reticolo 24 nodi troppo simmetrico')
    print('   → SOLUZIONE: Passare a 96 campi (Leech ×4)')

print('')
print('=== ANALISI AGING RELATIVISTICO ===')
tau_0 = tau[0]
tau_final = tau[last_frame]
print(f'τ frame 0:        mean={np.mean(tau_0):.6f}, std={np.std(tau_0):.6f}')
print(f'τ frame {last_frame:3d}:      mean={np.mean(tau_final):.6f}, std={np.std(tau_final):.6f}')
print(f'Divergenza τ:     Δstd = {np.std(tau_final) - np.std(tau_0):.6f}')

if np.std(tau_final) > 10 * np.std(tau_0):
    print('✅ AGING FUNZIONA: τ diverge nel tempo!')
else:
    print('⚠️  AGING DEBOLE: τ cresce uniformemente')

print('')
print('=== ANALISI Var(χ) ===')
var_chi_0 = np.var(chi[0])
var_chi_final = np.var(chi[last_frame])
print(f'Var(χ) @ frame 0:   {var_chi_0:.4f}')
print(f'Var(χ) @ frame {last_frame:3d}: {var_chi_final:.4f}')
print(f'Crescita Var(χ):    {var_chi_final / var_chi_0:.2f}×')

f.close()
