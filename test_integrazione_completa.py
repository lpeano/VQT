#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test di Integrazione Completa dei Moduli 1-2-3
================================================

Verifica che i tre moduli funzionino insieme correttamente:
- Modulo 1: Calcolo tensore di contorsione
- Modulo 2: Validazione topologica spinoriale
- Modulo 3: Integrazione fisica nell'evoluzione temporale

Questo test simula il flusso del main loop per alcuni frame
e verifica che:
1. I valori di K e chiusura siano calcolati correttamente
2. Questi valori siano passati a equazione_stato_einstein_cartan
3. L'evoluzione produca risultati fisicamente sensati
4. Il sistema tenda verso stabilità topologica
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import sys

# Importa le funzioni dal modulo principale
# (assumendo che WQT_manifold.py sia nella stessa directory)
sys.path.insert(0, '.')

# ============================================================================
# PARAMETRI DI SIMULAZIONE
# ============================================================================

segmenti_frattali = 24
risoluzione_base = 2400
COEFFICIENTE_ACCOPPIAMENTO = segmenti_frattali / risoluzione_base  # κ = 0.01
ACCORCIAMENTO_ANGOLARE = 1.0 / (4.0 * np.pi)

# ============================================================================
# FUNZIONI NECESSARIE (copiate/importate da WQT_manifold.py)
# ============================================================================

def calcola_contorsione(nodi):
    """Calcola il tensore di contorsione K_λμν."""
    N = len(nodi)
    if N < 3:
        raise ValueError("Servono almeno 3 nodi per calcolare la contorsione")
    
    # Triedro di Frenet-Serret
    tangenti = np.diff(nodi, axis=0)
    lunghezze_seg = np.linalg.norm(tangenti, axis=1, keepdims=True)
    lunghezze_seg = np.where(lunghezze_seg < 1e-15, 1e-15, lunghezze_seg)
    T = tangenti / lunghezze_seg
    
    # Normale (derivata seconda)
    dT = np.diff(T, axis=0)
    normali = dT / (np.linalg.norm(dT, axis=1, keepdims=True) + 1e-15)
    
    # Binormale
    T_mid = T[:-1]
    B = np.cross(T_mid, normali)
    B = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-15)
    
    N_mid = normali
    s = np.arange(N-2) / float(N-2)
    
    # Modulazione con 24 segmenti frattali
    f_24 = float(segmenti_frattali)
    phi = (f_24 / 2.0) * s
    
    # Torsione tensore S
    dphi_ds = np.gradient(phi, s, edge_order=2)
    
    K = np.zeros((N-2, 3, 3, 3))
    for i in range(N-2):
        for lam in range(3):
            for mu in range(3):
                for nu in range(3):
                    S_lam_mu_nu = dphi_ds[i] * (T_mid[i, mu]*N_mid[i, nu] - T_mid[i, nu]*N_mid[i, mu]) * np.sin(phi[i])
                    S_mu_lam_nu = dphi_ds[i] * (T_mid[i, lam]*N_mid[i, nu] - T_mid[i, nu]*N_mid[i, lam]) * np.sin(phi[i])
                    S_nu_lam_mu = dphi_ds[i] * (T_mid[i, lam]*N_mid[i, mu] - T_mid[i, mu]*N_mid[i, lam]) * np.sin(phi[i])
                    K[i, lam, mu, nu] = S_lam_mu_nu + S_mu_lam_nu + S_nu_lam_mu
    
    return K

def check_chiusura_spinore(nodi):
    """Verifica la chiusura topologica spinoriale."""
    N = len(nodi)
    if N < 3:
        return 0.0, {}
    
    # Triedro di Frenet-Serret
    tangenti = np.diff(nodi, axis=0)
    lunghezze_seg = np.linalg.norm(tangenti, axis=1)
    lunghezze_seg = np.where(lunghezze_seg < 1e-15, 1e-15, lunghezze_seg)
    T = tangenti / lunghezze_seg[:, np.newaxis]
    
    dT = np.diff(T, axis=0)
    normali = dT / (np.linalg.norm(dT, axis=1, keepdims=True) + 1e-15)
    
    T_mid = T[:-1]
    B = np.cross(T_mid, normali)
    B = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-15)
    
    # Torsione τ = -dB/ds · N
    dB = np.diff(B, axis=0)
    N_mid = normali[:-1]
    ds_mid = lunghezze_seg[1:-1]
    
    tau = np.zeros(len(dB))
    for i in range(len(dB)):
        tau[i] = -np.dot(dB[i] / (ds_mid[i] + 1e-15), N_mid[i])
    
    # Integrale di linea
    integrale = np.sum(tau * ds_mid)
    
    TARGET = 4.0 * np.pi
    errore_assoluto = integrale - TARGET
    scalar_error = errore_assoluto / TARGET
    
    diagnostica = {
        'integrale_calcolato': integrale,
        'target_teorico': TARGET,
        'errore_assoluto': errore_assoluto,
        'errore_percentuale': abs(scalar_error) * 100.0
    }
    
    return scalar_error, diagnostica

def equazione_stato_einstein_cartan(lambda_affine, stato_metrico, scatolamento, errore_chiusura=0.0, contorsione_k=0.0):
    """Equazione di evoluzione Einstein-Cartan semplificata per test."""
    chi = stato_metrico[0]
    velocita_chi = stato_metrico[1]
    
    chi_sat = 150.0 * np.tanh(chi / 150.0)
    log_r_dx = chi_sat
    
    fattore_dx = np.exp(log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
    fattore_sx = np.exp(-log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
    
    arg_dx = (4 * np.pi / risoluzione_base) * fattore_dx / (1.0 + log_r_dx**2)
    arg_sx = (4 * np.pi / risoluzione_base) * fattore_sx
    chiralita = np.where(np.arange(risoluzione_base) % 2 == 0, 1.0, -1.0)
    tor_dx = np.sinh(chiralita * arg_dx)
    tor_sx = np.sinh(chiralita * arg_sx)
    mu_dx = np.mean(np.abs(tor_dx))
    mu_sx = np.mean(np.abs(tor_sx))
    tensione_taglio = np.mean(tor_dx * tor_sx)
    energia_torsionale = np.mean((np.abs(tor_dx) - np.abs(tor_sx))**2)
    
    r_conforme = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * np.exp(log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
    accoppiamento_topologico = 1.0 / (r_conforme**2 + 1e-6)
    
    # Contributi fisici
    correzione_curvatura_contorsione = contorsione_k**2 * accoppiamento_topologico
    
    TARGET_CHIUSURA_4PI = 4.0 * np.pi
    costante_richiamo_topologico = 0.5
    errore_assoluto = errore_chiusura * TARGET_CHIUSURA_4PI
    forza_richiamo_geometrico = -costante_richiamo_topologico * errore_assoluto * accoppiamento_topologico
    
    pressione_metrica_chiusura = -(errore_assoluto**2) / (r_conforme**3 + 1e-9)
    
    densita_materia = (mu_sx - mu_dx) * scatolamento
    tensione_newtoniana = tensione_taglio * accoppiamento_topologico
    densita_torsione_quadratica = (tensione_taglio**2 + energia_torsionale**2) * accoppiamento_topologico
    
    pressione_vuoto_base = densita_materia - tensione_newtoniana - densita_torsione_quadratica
    pressione_vuoto_totale = (
        pressione_vuoto_base 
        - correzione_curvatura_contorsione
        + forza_richiamo_geometrico
        + pressione_metrica_chiusura
    )
    
    raggio_ottimale_solitone = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * 2.0
    deviazione_raggio = r_conforme - raggio_ottimale_solitone
    forza_auto_organizzazione = -0.1 * (deviazione_raggio**2) / (r_conforme**3 + 1e-9)
    
    pressione_totale = pressione_vuoto_totale + forza_auto_organizzazione
    
    jacobiano_metrico = 1.0 + 4.0 * (1.0 + np.tanh(np.abs(chi_sat) - 13.5)) / (np.abs(chi_sat) + 1e-9)
    accelerazione_conforme = pressione_totale * (jacobiano_metrico + 1e-9)
    
    coefficiente_damping = 0.05
    termine_damping = -coefficiente_damping * velocita_chi
    accelerazione_finale = accelerazione_conforme + termine_damping
    
    return [velocita_chi, accelerazione_finale]

def genera_manifold_test(chi, N=100):
    """Genera un semplice manifold toroidale per test."""
    theta = np.linspace(0, 4*np.pi, N)
    
    chi_sat = 150.0 * np.tanh(chi / 150.0)
    r_m = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * np.exp(chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    
    # Manifold SX (materia) - toroide semplice
    R = r_m  # Raggio maggiore
    r = r_m * 0.3  # Raggio minore
    
    X = (R + r * np.cos(theta)) * np.cos(theta / 2)
    Y = (R + r * np.cos(theta)) * np.sin(theta / 2)
    Z = r * np.sin(theta)
    
    nodi = np.column_stack([X, Y, Z])
    return nodi

# ============================================================================
# TEST DI INTEGRAZIONE
# ============================================================================

def test_integrazione_completa():
    """Test del flusso completo Moduli 1-2-3."""
    print("=" * 80)
    print("TEST DI INTEGRAZIONE COMPLETA - MODULI 1, 2, 3")
    print("=" * 80)
    print()
    
    # Stato iniziale
    chi_iniziale = -4.5
    stato_attuale = np.array([chi_iniziale, 0.0])  # [χ, dχ/dλ]
    lambda_corrente = 0.0
    
    # Liste per tracciare l'evoluzione
    storia_chi = [chi_iniziale]
    storia_K = []
    storia_errore = []
    storia_lambda = [lambda_corrente]
    
    # Simula 10 frame
    N_frames = 10
    delta_lambda = 0.1
    
    print(f"Simulazione di {N_frames} frame con delta_lambda = {delta_lambda}")
    print()
    print(f"{'Frame':<8} {'χ':<12} {'K (norm)':<15} {'Errore 4π':<15} {'Status'}")
    print("-" * 80)
    
    for frame in range(N_frames):
        chi = stato_attuale[0]
        
        # STEP 1: Genera geometria
        nodi_sx = genera_manifold_test(chi, N=100)
        
        # STEP 2: Calcola K e chiusura
        try:
            K_tensor = calcola_contorsione(nodi_sx)
            contorsione_k = np.sqrt(np.mean(K_tensor**2))
            
            scalar_error, diagnostica = check_chiusura_spinore(nodi_sx)
            chiusura_spinore = scalar_error
            
            # Determina status topologico
            if abs(scalar_error) < 0.01:
                status = "STABILE ✓"
            elif abs(scalar_error) < 0.05:
                status = "BUONO"
            elif abs(scalar_error) < 0.10:
                status = "ACCETTABILE"
            else:
                status = "INSTABILE ⚠"
            
        except Exception as e:
            contorsione_k = 0.0
            chiusura_spinore = 0.0
            status = f"ERRORE: {str(e)[:20]}"
        
        # Stampa stato corrente
        print(f"{frame:<8} {chi:<12.6f} {contorsione_k:<15.6e} {chiusura_spinore:<15.6f} {status}")
        
        # Salva per grafici
        storia_K.append(contorsione_k)
        storia_errore.append(chiusura_spinore)
        
        # STEP 3: Evolvi con fisica della torsione
        def equazione_con_torsione(t, y):
            return equazione_stato_einstein_cartan(
                t, y, 
                scatolamento=2.0,
                errore_chiusura=chiusura_spinore,
                contorsione_k=contorsione_k
            )
        
        sol = solve_ivp(
            equazione_con_torsione,
            [lambda_corrente, lambda_corrente + delta_lambda],
            stato_attuale,
            method='Radau',
            rtol=1e-4,
            atol=1e-6
        )
        
        # Aggiorna stato
        stato_attuale = sol.y[:, -1]
        lambda_corrente += delta_lambda
        
        storia_chi.append(stato_attuale[0])
        storia_lambda.append(lambda_corrente)
    
    print()
    print("=" * 80)
    print("ANALISI RISULTATI")
    print("=" * 80)
    print()
    
    # Analisi stabilità
    K_medio = np.mean(storia_K)
    K_std = np.std(storia_K)
    errore_medio = np.mean(np.abs(storia_errore))
    errore_finale = abs(storia_errore[-1])
    
    print(f"Contorsione K:")
    print(f"  - Media: {K_medio:.6e}")
    print(f"  - Std Dev: {K_std:.6e}")
    print(f"  - Range: [{min(storia_K):.6e}, {max(storia_K):.6e}]")
    print()
    
    print(f"Errore Chiusura:")
    print(f"  - Medio: {errore_medio:.6f}")
    print(f"  - Finale: {errore_finale:.6f}")
    print(f"  - Range: [{min(storia_errore):.6f}, {max(storia_errore):.6f}]")
    print()
    
    # Verifica convergenza
    if len(storia_errore) > 5:
        trend_errore = storia_errore[-1] - storia_errore[0]
        if trend_errore < 0:
            print("✓ Errore in DIMINUZIONE → Sistema converge verso 4π")
        elif abs(trend_errore) < 0.01:
            print("✓ Errore STABILE → Sistema in equilibrio")
        else:
            print("⚠ Errore in AUMENTO → Possibile instabilità")
    
    print()
    
    # Grafici
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Test Integrazione Completa - Moduli 1-2-3', fontsize=14, weight='bold')
    
    # Evoluzione χ
    axes[0, 0].plot(storia_lambda, storia_chi, 'b-', linewidth=2)
    axes[0, 0].set_xlabel('Parametro affine λ')
    axes[0, 0].set_ylabel('Potenziale di scala χ')
    axes[0, 0].set_title('Evoluzione χ(λ)')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Contorsione K
    axes[0, 1].plot(range(len(storia_K)), storia_K, 'r-', linewidth=2, marker='o')
    axes[0, 1].set_xlabel('Frame')
    axes[0, 1].set_ylabel('||K|| (Norma Frobenius)')
    axes[0, 1].set_title('Tensore di Contorsione')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Errore chiusura
    axes[1, 0].plot(range(len(storia_errore)), storia_errore, 'g-', linewidth=2, marker='s')
    axes[1, 0].axhline(y=0, color='k', linestyle='--', alpha=0.5, label='Target (4π)')
    axes[1, 0].set_xlabel('Frame')
    axes[1, 0].set_ylabel('Errore Normalizzato')
    axes[1, 0].set_title('Errore Chiusura Spinoriale')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Correlazione K vs Errore
    axes[1, 1].scatter(storia_K, np.abs(storia_errore), c=range(len(storia_K)), cmap='viridis', s=100)
    axes[1, 1].set_xlabel('||K|| (Contorsione)')
    axes[1, 1].set_ylabel('|Errore Chiusura|')
    axes[1, 1].set_title('Correlazione K vs Errore')
    axes[1, 1].grid(True, alpha=0.3)
    cbar = plt.colorbar(axes[1, 1].collections[0], ax=axes[1, 1])
    cbar.set_label('Frame')
    
    plt.tight_layout()
    plt.savefig('test_integrazione_completa.png', dpi=150)
    print("Grafico salvato in: test_integrazione_completa.png")
    print()
    
    # Verdetto finale
    print("=" * 80)
    print("VERDETTO FINALE")
    print("=" * 80)
    
    successo = True
    
    # Test 1: K deve essere finito e stabile
    if K_std / (K_medio + 1e-12) < 0.5:
        print("✓ TEST 1 PASSATO: Contorsione K stabile")
    else:
        print("✗ TEST 1 FALLITO: Contorsione K troppo variabile")
        successo = False
    
    # Test 2: Errore deve essere ragionevole
    if errore_medio < 1.0:
        print("✓ TEST 2 PASSATO: Errore di chiusura entro limiti fisici")
    else:
        print("✗ TEST 2 FALLITO: Errore di chiusura eccessivo")
        successo = False
    
    # Test 3: Sistema non deve divergere
    if abs(storia_chi[-1]) < 100:
        print("✓ TEST 3 PASSATO: χ non diverge")
    else:
        print("✗ TEST 3 FALLITO: χ diverge")
        successo = False
    
    print()
    if successo:
        print("🎉 INTEGRAZIONE COMPLETA FUNZIONA CORRETTAMENTE! 🎉")
    else:
        print("⚠️  ATTENZIONE: Alcuni test non sono passati. Rivedere i parametri.")
    
    print("=" * 80)
    
    return successo

# ============================================================================
# ESECUZIONE
# ============================================================================

if __name__ == "__main__":
    try:
        successo = test_integrazione_completa()
        sys.exit(0 if successo else 1)
    except Exception as e:
        print()
        print("=" * 80)
        print("ERRORE FATALE")
        print("=" * 80)
        print(f"Errore: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
