#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualizza l'evoluzione di χ, ρ e rapporto bounce dal log di stabilità.
Permette di vedere se il sistema sta oscillando o collassando.
"""

import numpy as np
import matplotlib.pyplot as plt
import re

# Leggi il log
log_file = 'stabilita.log'
data = {
    'frame': [],
    'lambda': [],
    'chi': [],
    'K': [],
    'errore': [],
    'rho': [],
    'rapporto': []
}

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        # Salta header e separatori
        if line.startswith('=') or line.startswith('-') or 'Frame' in line or 'LOG' in line or 'Fine' in line:
            continue
        
        # Parse dei dati
        parts = line.strip().split()
        if len(parts) >= 7:
            try:
                data['frame'].append(int(parts[0]))
                data['lambda'].append(float(parts[1]))
                data['chi'].append(float(parts[2]))
                data['K'].append(float(parts[3]))
                data['errore'].append(float(parts[4]))
                data['rho'].append(float(parts[5]))
                data['rapporto'].append(float(parts[6]))
            except ValueError:
                continue

# Converti in array numpy
for key in data:
    data[key] = np.array(data[key])

# Crea il grafico
fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
fig.suptitle('Evoluzione del Manifold - Bounce Quantistico', fontsize=14, fontweight='bold')

# 1. Evoluzione di χ (potenziale di scala)
ax1 = axes[0]
ax1.plot(data['lambda'], data['chi'], 'b-', linewidth=2, label='χ (potenziale)')
ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5, label='Equilibrio (χ=0)')
ax1.set_ylabel('χ (potenziale di scala)', fontsize=11, fontweight='bold')
ax1.legend(loc='best')
ax1.grid(True, alpha=0.3)
ax1.set_title('Collasso o Oscillazione?', fontsize=10)

# 2. Densità di energia
ax2 = axes[1]
ax2.plot(data['lambda'], data['rho'], 'r-', linewidth=2, label='ρ_total')
ax2.set_ylabel('ρ (densità energia)', fontsize=11, fontweight='bold')
ax2.set_yscale('log')
ax2.legend(loc='best')
ax2.grid(True, alpha=0.3, which='both')
ax2.set_title('Densità (deve divergere durante collasso)', fontsize=10)

# 3. Rapporto Bounce (P_rep / |P_grav|)
ax3 = axes[2]
ax3.plot(data['lambda'], data['rapporto'], 'g-', linewidth=2, label='P_rep / |P_grav|')
ax3.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Soglia Bounce (=1)')
ax3.fill_between(data['lambda'], 1.0, data['rapporto'], where=(data['rapporto']>=1), alpha=0.3, color='green', label='ZONA BOUNCE')
ax3.set_ylabel('Rapporto Bounce', fontsize=11, fontweight='bold')
ax3.set_xlabel('λ (parametro affine)', fontsize=11, fontweight='bold')
ax3.set_yscale('log')
ax3.legend(loc='best')
ax3.grid(True, alpha=0.3, which='both')
ax3.set_title('Repulsione vs Gravità (>1 = BOUNCE!)', fontsize=10)

plt.tight_layout()
plt.savefig('evoluzione_bounce.png', dpi=150, bbox_inches='tight')
print(f"✓ Grafico salvato: evoluzione_bounce.png")

# Statistiche
print(f"\n{'='*60}")
print(f"ANALISI BOUNCE QUANTISTICO")
print(f"{'='*60}")
print(f"Frames totali: {len(data['frame'])}")
print(f"Range λ: {data['lambda'][0]:.2f} → {data['lambda'][-1]:.2f}")
print(f"\nEVOLUZIONE χ:")
print(f"  Iniziale: {data['chi'][0]:.2f}")
print(f"  Finale:   {data['chi'][-1]:.2f}")
print(f"  Δχ:       {data['chi'][-1] - data['chi'][0]:.2f}")
print(f"  Velocità: {(data['chi'][-1] - data['chi'][0]) / len(data['frame']):.2f} Δχ/frame")
print(f"\nDENSITÀ ρ:")
print(f"  Iniziale: {data['rho'][0]:.6e}")
print(f"  Finale:   {data['rho'][-1]:.6e}")
print(f"  Fattore:  {data['rho'][-1] / data['rho'][0]:.1f}×")
print(f"\nRAPPORTO BOUNCE:")
print(f"  Iniziale: {data['rapporto'][0]:.2f}")
print(f"  Massimo:  {np.max(data['rapporto']):.2f}")
print(f"  Finale:   {data['rapporto'][-1]:.2f}")
print(f"  Frames con rapporto > 1: {np.sum(data['rapporto'] > 1.0)} / {len(data['rapporto'])} ({100*np.sum(data['rapporto'] > 1.0)/len(data['rapporto']):.1f}%)")

# Verifica bounce
if np.sum(data['rapporto'] > 1.0) > len(data['rapporto']) * 0.9:
    print(f"\n✅ BOUNCE QUANTISTICO ATTIVO! (Repulsione domina per {100*np.sum(data['rapporto'] > 1.0)/len(data['rapporto']):.0f}% del tempo)")
else:
    print(f"\n⚠️  Bounce parziale ({100*np.sum(data['rapporto'] > 1.0)/len(data['rapporto']):.0f}% con rapporto > 1)")

# Verifica oscillazione
delta_chi = np.diff(data['chi'])
segno_changes = np.sum(np.diff(np.sign(delta_chi)) != 0)
if segno_changes > 2:
    print(f"✅ Sistema OSCILLA! ({segno_changes} inversioni di velocità rilevate)")
elif data['chi'][-1] > data['chi'][0]:
    print(f"⚠️  Sistema in ESPANSIONE (χ aumenta)")
else:
    print(f"⚠️  Sistema in COLLASSO (χ diminuisce)")
    
print(f"{'='*60}\n")

plt.show()
