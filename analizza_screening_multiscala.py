#!/usr/bin/env python
"""
Analizza l'efficacia dello Screening Multi-Scala con Aging
Estrae metriche di:
- Crescita tau_locale (deve essere lineare)
- Divergenza campi (screening attivo?)
- Memoria non-Markoviana (correlazione temporale)
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
import os

os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'

DB_PATH = "test_screening_multiscala.h5"

print(f"\n{'='*80}")
print(f"  ANALISI SCREENING MULTI-SCALA CON AGING")
print(f"{'='*80}\n")

# Apri database
with h5py.File(DB_PATH, 'r') as f:
    tel = f['telemetria_scalare'][:]
    
# Filtra frame validi
valid = tel[tel['rm'] > 0]
n_frames = len(valid)
print(f"[INFO] Frame validi: {n_frames}")

# Estrai campi vettoriali
chi_matrix = np.array([frame['chi_vettore'] for frame in valid])  # (n_frames, 24)
vel_matrix = np.array([frame['vel_vettore'] for frame in valid])
tau_matrix = np.array([frame['tau_locale'] for frame in valid])

print(f"\n{'='*80}")
print(f"  1. ANALISI CRESCITA TAU_LOCALE (Aging)")
print(f"{'='*80}\n")

# Tau deve crescere linearmente
tau_mean = tau_matrix.mean(axis=1)  # Media tra i 24 campi per ogni frame
tau_std = tau_matrix.std(axis=1)    # Divergenza tra campi

print(f"Tau iniziale (frame 0):    {tau_mean[0]:.6f} +/- {tau_std[0]:.6f}")
print(f"Tau finale (frame {n_frames-1}):  {tau_mean[-1]:.6f} +/- {tau_std[-1]:.6f}")
print(f"Crescita totale:           {tau_mean[-1] - tau_mean[0]:.6f}")
print(f"Crescita attesa (dt*N):    {0.1 * n_frames:.6f}")

# Divergenza tau (quanto i campi invecchiano a velocità diverse)
divergenza_tau = tau_std / (tau_mean + 1e-10)  # Coefficiente di variazione
print(f"\nDivergenza relativa tau:")
print(f"  Iniziale: {divergenza_tau[0]:.6e}")
print(f"  Finale:   {divergenza_tau[-1]:.6e}")
print(f"  Crescita divergenza: {divergenza_tau[-1]/max(divergenza_tau[0], 1e-10):.2f}x")

# Verifica crescita lineare
from scipy.stats import linregress
frames = np.arange(n_frames)
slope, intercept, r_value, p_value, std_err = linregress(frames, tau_mean)
print(f"\nRegressione lineare tau_mean vs frame:")
print(f"  Pendenza: {slope:.6f} (atteso: ~0.1)")
print(f"  R²: {r_value**2:.6f} (linearità)")

if r_value**2 > 0.99:
    print(f"  ✅ CRESCITA LINEARE (R²={r_value**2:.4f})")
else:
    print(f"  ⚠️ CRESCITA NON-LINEARE (R²={r_value**2:.4f})")

print(f"\n{'='*80}")
print(f"  2. ANALISI DIVERGENZA CAMPI (Screening Attivo?)")
print(f"{'='*80}\n")

# Varianza tra i 24 campi
var_chi = chi_matrix.var(axis=1)
range_chi = chi_matrix.max(axis=1) - chi_matrix.min(axis=1)

print(f"Varianza χ:")
print(f"  Iniziale (frame 0):    {var_chi[0]:.6e}")
print(f"  Finale (frame {n_frames-1}):  {var_chi[-1]:.6e}")
print(f"  Crescita: {var_chi[-1]/max(var_chi[0], 1e-10):.2f}x")

print(f"\nRange χ:")
print(f"  Iniziale: {range_chi[0]:.6f}")
print(f"  Finale:   {range_chi[-1]:.6f}")
print(f"  Variazione: {(range_chi[-1]-range_chi[0])/range_chi[0]*100:.2f}%")

# Verifica plateau vs crescita
if var_chi[-1] / max(var_chi[0], 1e-10) < 1.1:
    print(f"  ⚠️ VARIANZA STAZIONARIA (crescita < 10%)")
else:
    print(f"  ✅ VARIANZA CRESCENTE ({var_chi[-1]/max(var_chi[0], 1e-10):.2f}x)")

print(f"\n{'='*80}")
print(f"  3. ANALISI MEMORIA NON-MARKOVIANA")
print(f"{'='*80}\n")

# Correlazione tra stato N e N-100
if n_frames >= 200:
    lag = 100
    # Prendi ultimi 500 frame per l'analisi
    chi_recent = chi_matrix[-500:]
    
    # Calcola correlazione chi(t) con chi(t-lag)
    chi_t = chi_recent[lag:].flatten()
    chi_t_lag = chi_recent[:-lag].flatten()
    
    corr = np.corrcoef(chi_t, chi_t_lag)[0, 1]
    
    print(f"Correlazione χ(t) vs χ(t-{lag}):")
    print(f"  Coefficiente: {corr:.6f}")
    
    if corr > 0.9:
        print(f"  ✅ FORTE MEMORIA (corr > 0.9)")
    elif corr > 0.5:
        print(f"  ⚠️ MEMORIA MODERATA (0.5 < corr < 0.9)")
    else:
        print(f"  ❌ MEMORIA DEBOLE (corr < 0.5) - Sistema quasi Markoviano")
else:
    print(f"  ⚠️ Frame insufficienti per analisi memoria (serve > 200)")

print(f"\n{'='*80}")
print(f"  4. CONFRONTO CON SISTEMA PRECEDENTE")
print(f"{'='*80}\n")

# Cerca geometrodinamica_esplosiva_playback.h5 per confronto
COMPARE_DB = "geometrodinamica_esplosiva_playback.h5"
if os.path.exists(COMPARE_DB):
    with h5py.File(COMPARE_DB, 'r') as f_old:
        tel_old = f_old['telemetria_scalare'][:]
    
    valid_old = tel_old[tel_old['rm'] > 0]
    chi_old = np.array([frame['chi_vettore'] for frame in valid_old[:n_frames]])
    
    var_chi_old = chi_old.var(axis=1)
    
    print(f"Varianza χ confronto (ultimi 100 frame):")
    print(f"  Sistema VECCHIO (no aging): {var_chi_old[-100:].mean():.6e}")
    print(f"  Sistema NUOVO (con aging):  {var_chi[-100:].mean():.6e}")
    print(f"  Rapporto: {var_chi[-100:].mean() / max(var_chi_old[-100:].mean(), 1e-10):.2f}x")
    
    if var_chi[-100:].mean() > var_chi_old[-100:].mean() * 1.5:
        print(f"  ✅ SCREENING EFFICACE (+50% varianza)")
    else:
        print(f"  ⚠️ SCREENING INEFFICACE (< 50% miglioramento)")
else:
    print(f"  ⚠️ File confronto non trovato: {COMPARE_DB}")

print(f"\n{'='*80}")
print(f"  5. VISUALIZZAZIONE")
print(f"{'='*80}\n")

# Crea visualizzazione
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Crescita tau_locale
ax1 = axes[0, 0]
ax1.plot(frames, tau_mean, 'b-', linewidth=2, label='τ medio')
ax1.fill_between(frames, tau_mean - tau_std, tau_mean + tau_std, alpha=0.3, color='blue', label='±σ')
ax1.plot(frames, slope * frames + intercept, 'r--', label=f'Fit lineare (R²={r_value**2:.4f})')
ax1.set_xlabel('Frame', fontsize=12)
ax1.set_ylabel('τ_locale', fontsize=12)
ax1.set_title('Crescita Tempo Proprio (Aging)', fontsize=14, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Varianza campi
ax2 = axes[0, 1]
ax2.semilogy(frames, var_chi, 'g-', linewidth=2, label='Var(χ)')
ax2.set_xlabel('Frame', fontsize=12)
ax2.set_ylabel('Varianza χ', fontsize=12)
ax2.set_title('Divergenza Campi (Screening)', fontsize=14, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. Range χ
ax3 = axes[1, 0]
ax3.plot(frames, range_chi, 'm-', linewidth=2)
ax3.set_xlabel('Frame', fontsize=12)
ax3.set_ylabel('Range(χ) = max - min', fontsize=12)
ax3.set_title('Separazione Max-Min Campi', fontsize=14, fontweight='bold')
ax3.grid(True, alpha=0.3)

# 4. Divergenza tau relativa
ax4 = axes[1, 1]
ax4.semilogy(frames, divergenza_tau, 'orange', linewidth=2)
ax4.set_xlabel('Frame', fontsize=12)
ax4.set_ylabel('CV(τ) = σ(τ)/μ(τ)', fontsize=12)
ax4.set_title('Divergenza Relativa Aging', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('screening_multiscala_analisi.png', dpi=150, bbox_inches='tight')
print(f"[PLOT] Salvato: screening_multiscala_analisi.png")

print(f"\n{'='*80}")
print(f"  CONCLUSIONI")
print(f"{'='*80}\n")

# Valutazione finale
score = 0
if r_value**2 > 0.99:
    score += 1
    print(f"✅ Tau cresce linearmente (R²={r_value**2:.4f})")
else:
    print(f"❌ Tau non lineare (R²={r_value**2:.4f})")

if var_chi[-1] / max(var_chi[0], 1e-10) > 1.5:
    score += 1
    print(f"✅ Varianza campi crescente ({var_chi[-1]/max(var_chi[0], 1e-10):.2f}x)")
else:
    print(f"❌ Varianza stazionaria ({var_chi[-1]/max(var_chi[0], 1e-10):.2f}x)")

if divergenza_tau[-1] > divergenza_tau[0] * 2:
    score += 1
    print(f"✅ Aging divergente ({divergenza_tau[-1]/max(divergenza_tau[0], 1e-10):.2f}x)")
else:
    print(f"❌ Aging non divergente ({divergenza_tau[-1]/max(divergenza_tau[0], 1e-10):.2f}x)")

print(f"\n[VALUTAZIONE FINALE] {score}/3 criteri soddisfatti")

if score == 3:
    print(f"\n🎉 SCREENING MULTI-SCALA EFFICACE!")
    print(f"   Il sistema mostra aging, divergenza e memoria.")
elif score >= 1:
    print(f"\n⚠️ SCREENING PARZIALMENTE EFFICACE")
    print(f"   Alcuni criteri soddisfatti, ma non tutti.")
else:
    print(f"\n❌ SCREENING INEFFICACE")
    print(f"   Il sistema rimane stazionario/Markoviano.")
    print(f"\n💡 SUGGERIMENTI:")
    print(f"   - Aumenta SIGMA_TAU (attualmente 5.0)")
    print(f"   - Riduci SIGMA_VEL per screening cinematico più forte")
    print(f"   - Aumenta durata simulazione (serve più tempo per divergenza)")

print(f"\n{'='*80}\n")
