"""
TEST E VALIDAZIONE DINAMICA HAMILTONIANA
=========================================

Questo script verifica che la nuova dinamica di trasporto chiralità:
1. Minimizzi l'energia nel tempo
2. Conservi la carica totale
3. Formi clustering spontanei
4. Sia numericamente stabile

Author: Senior Computational Physicist
Date: 2026-05-22
"""

import numpy as np
import matplotlib.pyplot as plt
from dinamica_hamiltoniana_chiralita import (
    update_dinamica_chiralita,
    calcola_energia_sistema,
    ALPHA_COUPLING,
    K2_REF_720,
    MU_TRANSPORT
)

# ============================================================================
# SETUP SISTEMA TEST
# ============================================================================

N_SEGMENTI = 24
N_STEPS = 200
DT = 0.01

print("╔══════════════════════════════════════════════════════════════╗")
print("║  TEST DINAMICA HAMILTONIANA - SEPARAZIONE FASI               ║")
print("╚══════════════════════════════════════════════════════════════╝\n")

print(f"Parametri:")
print(f"  • Segmenti: {N_SEGMENTI}")
print(f"  • Steps: {N_STEPS}")
print(f"  • dt: {DT}")
print(f"  • α (coupling): {ALPHA_COUPLING}")
print(f"  • μ (transport): {MU_TRANSPORT}")
print(f"  • K²_ref (720°): {K2_REF_720:.3f}\n")

# ============================================================================
# MATRICE ACCOPPIAMENTO LEECH (TOPOLOGIA TOROIDALE)
# ============================================================================

def costruisci_matrice_test():
    """Crea matrice di accoppiamento semplificata per test"""
    W = np.zeros((N_SEGMENTI, N_SEGMENTI))
    
    for i in range(N_SEGMENTI):
        for j in range(N_SEGMENTI):
            if i != j:
                # Distanza minima sul cerchio (toroidale)
                dist = min(abs(i - j), N_SEGMENTI - abs(i - j))
                # Peso inversamente proporzionale a distanza² + epsilon
                W[i, j] = 1.0 / (dist**2 + 0.1)
    
    # Normalizzazione per righe
    for i in range(N_SEGMENTI):
        row_sum = np.sum(W[i, :])
        if row_sum > 0:
            W[i, :] /= row_sum
    
    return W

matrice_accoppiamento = costruisci_matrice_test()

# ============================================================================
# CONDIZIONI INIZIALI: SISTEMA PERTURBATO
# ============================================================================

# Stato iniziale: χ con perturbazione gaussiana localizzata
chi_vettore = -5.0 * np.ones(N_SEGMENTI)

# Perturbazione localizzata in segmenti 5-10 (innesca dinamica)
chi_vettore[5:10] += 2.0 * np.random.randn(5)

vel_vettore = np.zeros(N_SEGMENTI)

# Stato vettoriale [χ₀, v₀, χ₁, v₁, ...]
stato = np.zeros(48)
stato[0::2] = chi_vettore
stato[1::2] = vel_vettore

# Torsione iniziale: alta in zona perturbata, bassa altrove
contorsione = np.ones(N_SEGMENTI) * 2.0  # ~2 rad (~115°)
contorsione[5:10] = 15.0  # ~900° (oltre soglia 720°)

print("Condizioni iniziali:")
print(f"  • χ medio: {np.mean(chi_vettore):.3f} ± {np.std(chi_vettore):.3f}")
print(f"  • K² medio: {np.mean(contorsione):.3f} rad")
print(f"  • K² max: {np.max(contorsione):.3f} rad (segmento {np.argmax(contorsione)})")
print(f"  • K² > 720° ({K2_REF_720:.2f}): {np.sum(contorsione > K2_REF_720)} segmenti\n")

# ============================================================================
# ARRAYS PER LOGGING EVOLUZIONE
# ============================================================================

energia_totale = []
energia_coupling = []
energia_torsion = []
carica_totale = []
varianza_densita_sx = []
max_flusso = []
tempo = []

# Densità iniziali (calcolo semplificato)
chi_sat = np.tanh(chi_vettore / 5.0)
K2_norm = contorsione / K2_REF_720
boost = 1.0 + 0.5 * K2_norm
densita_base = 1.0 + 0.1 * np.abs(chi_vettore)
densita_sx = densita_base * 0.5 * (1.0 - chi_sat) * boost
densita_dx = densita_base * 0.5 * (1.0 + chi_sat) * boost

# ============================================================================
# LOOP DI EVOLUZIONE
# ============================================================================

print("Evoluzione temporale:")
print("─" * 70)

for step in range(N_STEPS):
    # Aggiorna dinamica
    densita_sx, densita_dx, flussi = update_dinamica_chiralita(
        stato_attuale=stato,
        dt=DT,
        matrice_accoppiamento=matrice_accoppiamento,
        contorsione_locale=contorsione
    )
    
    # Calcola energia
    E_tot, E_coup, E_tors = calcola_energia_sistema(
        densita_sx, densita_dx, contorsione, matrice_accoppiamento
    )
    
    # Logging
    energia_totale.append(E_tot)
    energia_coupling.append(E_coup)
    energia_torsion.append(E_tors)
    
    carica = np.sum(densita_sx) + np.sum(densita_dx)
    carica_totale.append(carica)
    
    varianza_densita_sx.append(np.var(densita_sx))
    max_flusso.append(np.max(np.abs(flussi)))
    tempo.append(step * DT)
    
    # Aggiorna contorsione (simulazione semplificata: K² ~ ρ_SX)
    # In realtà sarebbe calcolata da solve_ivp in WQT_manifold
    contorsione = 2.0 + 10.0 * (densita_sx / np.max(densita_sx))
    
    # Print progresso ogni 20 steps
    if step % 20 == 0:
        print(f"Step {step:3d}: E_tot={E_tot:8.2f}  Carica={carica:6.2f}  "
              f"Var(ρ_SX)={np.var(densita_sx):6.3f}  Max(flux)={np.max(np.abs(flussi)):6.3f}")

print("─" * 70)
print("✓ Evoluzione completata\n")

# ============================================================================
# ANALISI RISULTATI
# ============================================================================

print("Analisi Risultati:")
print("─" * 70)

# 1. Minimizzazione energia
E_iniziale = energia_totale[0]
E_finale = energia_totale[-1]
delta_E = E_finale - E_iniziale
print(f"1. ENERGIA:")
print(f"   • E_iniziale: {E_iniziale:.2f}")
print(f"   • E_finale:   {E_finale:.2f}")
print(f"   • ΔE:         {delta_E:.2f} {'✓ MINIMIZZATA' if delta_E < 0 else '✗ NON minimizzata'}")
print(f"   • Riduzione:  {abs(delta_E)/E_iniziale*100:.1f}%\n")

# 2. Conservazione carica
Q_iniziale = carica_totale[0]
Q_finale = carica_totale[-1]
delta_Q = abs(Q_finale - Q_iniziale)
print(f"2. CONSERVAZIONE CARICA:")
print(f"   • Q_iniziale: {Q_iniziale:.6f}")
print(f"   • Q_finale:   {Q_finale:.6f}")
print(f"   • |ΔQ|:       {delta_Q:.2e} {'✓ CONSERVATA' if delta_Q < 1e-6 else '✗ NON conservata'}\n")

# 3. Formazione clustering
var_iniziale = varianza_densita_sx[0]
var_finale = varianza_densita_sx[-1]
aumento_var = (var_finale - var_iniziale) / var_iniziale * 100
print(f"3. CLUSTERING (Varianza ρ_SX):")
print(f"   • Var iniziale: {var_iniziale:.3f}")
print(f"   • Var finale:   {var_finale:.3f}")
print(f"   • Aumento:      {aumento_var:+.1f}% {'✓ CLUSTERING ATTIVO' if aumento_var > 10 else '✗ Basso clustering'}\n")

# 4. Stabilità numerica
flusso_max_globale = max(max_flusso)
print(f"4. STABILITÀ:")
print(f"   • Max flusso: {flusso_max_globale:.3f} {'✓ STABILE' if flusso_max_globale < 10 else '✗ INSTABILE'}\n")

print("─" * 70)

# ============================================================================
# PLOT RISULTATI
# ============================================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('TEST DINAMICA HAMILTONIANA - SEPARAZIONE FASI', fontsize=14, fontweight='bold')

# Plot 1: Energia totale
ax1 = axes[0, 0]
ax1.plot(tempo, energia_totale, 'b-', linewidth=2, label='E_tot')
ax1.plot(tempo, energia_coupling, 'g--', linewidth=1.5, label='E_coupling')
ax1.plot(tempo, energia_torsion, 'r--', linewidth=1.5, label='E_torsion')
ax1.set_xlabel('Tempo')
ax1.set_ylabel('Energia')
ax1.set_title('Minimizzazione Energia')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Plot 2: Conservazione carica
ax2 = axes[0, 1]
ax2.plot(tempo, carica_totale, 'purple', linewidth=2)
ax2.axhline(Q_iniziale, color='red', linestyle='--', alpha=0.5, label='Q_iniziale')
ax2.set_xlabel('Tempo')
ax2.set_ylabel('Carica Totale')
ax2.set_title('Conservazione Carica')
ax2.legend()
ax2.grid(True, alpha=0.3)

# Plot 3: Clustering (varianza densità)
ax3 = axes[1, 0]
ax3.plot(tempo, varianza_densita_sx, 'orange', linewidth=2)
ax3.set_xlabel('Tempo')
ax3.set_ylabel('Var(ρ_SX)')
ax3.set_title('Formazione Clustering')
ax3.grid(True, alpha=0.3)

# Plot 4: Flussi massimi
ax4 = axes[1, 1]
ax4.plot(tempo, max_flusso, 'cyan', linewidth=2)
ax4.set_xlabel('Tempo')
ax4.set_ylabel('Max|Flusso|')
ax4.set_title('Stabilità Flussi')
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('test_dinamica_hamiltoniana.png', dpi=150, bbox_inches='tight')
print("\n📊 Grafici salvati in: test_dinamica_hamiltoniana.png")

# ============================================================================
# DISTRIBUZIONE FINALE DENSITÀ
# ============================================================================

fig2, ax = plt.subplots(figsize=(12, 6))

segmenti = np.arange(N_SEGMENTI)
ax.bar(segmenti - 0.2, densita_sx, width=0.4, label='ρ_SX (materia)', color='blue', alpha=0.7)
ax.bar(segmenti + 0.2, densita_dx, width=0.4, label='ρ_DX (spazio)', color='red', alpha=0.7)
ax.axhline(np.mean(densita_sx), color='blue', linestyle='--', alpha=0.5, label='<ρ_SX>')
ax.axhline(np.mean(densita_dx), color='red', linestyle='--', alpha=0.5, label='<ρ_DX>')

ax.set_xlabel('Segmento i', fontsize=12)
ax.set_ylabel('Densità', fontsize=12)
ax.set_title('Distribuzione Finale Densità Chiralità (Separazione Fasi)', fontsize=13, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticks(segmenti)

plt.tight_layout()
plt.savefig('distribuzione_densita_finale.png', dpi=150, bbox_inches='tight')
print("📊 Distribuzione densità salvata in: distribuzione_densita_finale.png")

# ============================================================================
# VERIFICA SUCCESSO TEST
# ============================================================================

print("\n╔══════════════════════════════════════════════════════════════╗")
print("║  RIEPILOGO VALIDAZIONE                                       ║")
print("╚══════════════════════════════════════════════════════════════╝\n")

successi = 0
test_totali = 4

# Test 1: Energia minimizzata
if delta_E < 0:
    print("✓ TEST 1: Energia minimizzata")
    successi += 1
else:
    print("✗ TEST 1: Energia NON minimizzata")

# Test 2: Carica conservata
if delta_Q < 1e-6:
    print("✓ TEST 2: Carica conservata")
    successi += 1
else:
    print("✗ TEST 2: Carica NON conservata")

# Test 3: Clustering attivo
if aumento_var > 10:
    print("✓ TEST 3: Clustering formato")
    successi += 1
else:
    print("✗ TEST 3: Clustering debole")

# Test 4: Stabilità numerica
if flusso_max_globale < 10:
    print("✓ TEST 4: Numericamente stabile")
    successi += 1
else:
    print("✗ TEST 4: Instabilità numerica")

print(f"\nRISULTATO: {successi}/{test_totali} test superati")

if successi == test_totali:
    print("\n🎉 VALIDAZIONE COMPLETA: Sistema pronto per integrazione!")
elif successi >= test_totali - 1:
    print("\n⚠️  VALIDAZIONE PARZIALE: Verificare parametri")
else:
    print("\n❌ VALIDAZIONE FALLITA: Rivedere implementazione")

print("\n" + "="*70)
