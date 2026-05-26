"""
ANALISI CLUSTERING: Rivela struttura nascosta in produzione_history.npz

Questo script analizza l'evoluzione temporale della configurazione materia/spazio
per identificare pattern di clustering che l'indice spaziale globale non cattura.
"""

import numpy as np
import matplotlib.pyplot as plt

# Carica storia
data = np.load('produzione_history.npz')

steps = data['steps']
n_matter = data['n_matter']
n_space = data['n_space']
H_total = data['H_total']
H_conserved = data['H_conserved']
E_radiated = data['E_radiated']
boundary_flux = data['boundary_flux']
separation_index = data['separation_index']
gamma = data['gamma']

print("=" * 80)
print(" ANALISI CLUSTERING: Struttura Nascosta")
print("=" * 80)
print(f"N_steps totali = {len(steps)}")
print()

# === 1. EVOLUZIONE MATERIA/SPAZIO ===
print("1. EVOLUZIONE CONFIGURAZIONE M/S:")
print(f"   Iniziale: {n_matter[0]}/{n_space[0]} (materia/spazio)")
print(f"   Finale:   {n_matter[-1]}/{n_space[-1]}")
print(f"   Media:    {np.mean(n_matter):.1f} ± {np.std(n_matter):.1f}")
print()

# Verifica convergenza
last_100 = n_matter[-100:]
print(f"   Ultimi 100 step:")
print(f"     M media = {np.mean(last_100):.1f} ± {np.std(last_100):.1f}")
print(f"     Varianza = {np.var(last_100):.3f}")
if np.std(last_100) < 0.5:
    print(f"     ✓ CONFIGURAZIONE STABILE (std < 0.5)")
else:
    print(f"     ○ Configurazione oscillante")
print()

# === 2. TRANSIZIONI TOPOLOGICHE ===
print("2. DINAMICA TRANSIZIONI:")
total_flux = np.sum(boundary_flux)
print(f"   Transizioni totali = {total_flux}")

# Identifica quando avvengono
transition_steps = np.where(boundary_flux > 0)[0]
if len(transition_steps) > 0:
    print(f"   Numero eventi = {len(transition_steps)}")
    print(f"   Step con transizioni:")
    for i, step_idx in enumerate(transition_steps[:10]):  # Prime 10
        step_num = steps[step_idx]
        flux = boundary_flux[step_idx]
        m_before = n_matter[step_idx-1] if step_idx > 0 else n_matter[0]
        m_after = n_matter[step_idx]
        print(f"     Step {step_num:4d}: {m_before:2d}→{m_after:2d} ({flux} flip)")
    if len(transition_steps) > 10:
        print(f"     ... ({len(transition_steps)-10} eventi omessi)")
print()

# === 3. CORRELAZIONE ENERGIA-CONFIGURAZIONE ===
print("3. STATI ENERGETICI PREFERITI:")
# Raggruppa per configurazione M/S
configs = {}
for i, m in enumerate(n_matter):
    key = f"{m}/{24-m}"
    if key not in configs:
        configs[key] = []
    configs[key].append(H_total[i])

print(f"   Configurazioni osservate: {len(configs)}")
for config, energies in sorted(configs.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
    E_mean = np.mean(energies)
    E_std = np.std(energies)
    count = len(energies)
    print(f"     {config:>6} M/S: {count:4d} step, H = {E_mean:.2e} ± {E_std:.2e}")
print()

# === 4. CONSERVAZIONE ENERGETICA ===
print("4. CONSERVAZIONE TERMODINAMICA:")
H_init = H_conserved[0]
H_final = H_conserved[-1]
drift_abs = abs(H_final - H_init)
drift_rel = drift_abs / H_init * 100
print(f"   H_conserved_init  = {H_init:.6e}")
print(f"   H_conserved_final = {H_final:.6e}")
print(f"   Drift assoluto    = {drift_abs:.6e}")
print(f"   Drift relativo    = {drift_rel:.6f}%")
if drift_rel < 0.01:
    print(f"   ✓ CONSERVAZIONE PERFETTA (drift < 0.01%)")
elif drift_rel < 1.0:
    print(f"   ✓ Conservazione buona (drift < 1%)")
else:
    print(f"   ✗ Drift eccessivo")
print()

# === 5. OSCILLAZIONE ENERGIA TOTALE ===
print("5. DINAMICA ENERGIA TOTALE:")
H_min = np.min(H_total)
H_max = np.max(H_total)
H_mean = np.mean(H_total)
amplitude = (H_max - H_min) / H_mean * 100
print(f"   H_min  = {H_min:.2e}")
print(f"   H_max  = {H_max:.2e}")
print(f"   H_mean = {H_mean:.2e}")
print(f"   Ampiezza oscillazione = {amplitude:.1f}%")
print()

# === 6. PLOT EVOLUZIONE ===
fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

# Plot 1: Configurazione M/S
axes[0].plot(steps, n_matter, 'b-', label='Materia', linewidth=1)
axes[0].plot(steps, n_space, 'r-', label='Spazio', linewidth=1)
axes[0].axhline(12, color='gray', linestyle='--', alpha=0.5, label='Equilibrio 12/12')
axes[0].set_ylabel('Numero nodi')
axes[0].legend()
axes[0].grid(True, alpha=0.3)
axes[0].set_title('Evoluzione Configurazione Materia/Spazio')

# Plot 2: Transizioni
axes[1].plot(steps, boundary_flux, 'g-', linewidth=1)
axes[1].set_ylabel('Boundary Flux')
axes[1].grid(True, alpha=0.3)
axes[1].set_title('Transizioni Materia ↔ Spazio')

# Plot 3: Energie
ax3 = axes[2]
ax3.plot(steps, H_total, 'purple', label='H_total', linewidth=1)
ax3.set_ylabel('H_total', color='purple')
ax3.tick_params(axis='y', labelcolor='purple')
ax3.grid(True, alpha=0.3)

ax3_twin = ax3.twinx()
ax3_twin.plot(steps, E_radiated, 'orange', label='E_radiated', linewidth=1)
ax3_twin.set_ylabel('E_radiated', color='orange')
ax3_twin.tick_params(axis='y', labelcolor='orange')
ax3.set_title('Bilancio Energetico')

# Plot 4: Gamma (cooling)
axes[3].plot(steps, gamma, 'k-', linewidth=1)
axes[3].set_ylabel('γ (damping)')
axes[3].set_xlabel('Step')
axes[3].grid(True, alpha=0.3)
axes[3].set_title('Coefficiente Smorzamento')
axes[3].axvline(200, color='red', linestyle='--', alpha=0.5, label='Cooling OFF')
axes[3].legend()

plt.tight_layout()
plt.savefig('clustering_analysis.png', dpi=150)
print("Plot salvato in: clustering_analysis.png")
print()

print("=" * 80)
