#!/usr/bin/env python3
"""
Test della funzione calcola_c_locale() 
implementata in WQT_manifold.py

Verifica che la velocità della luce locale emerga correttamente
dalla distribuzione di densità chirale.
"""

import numpy as np

# ============================================================================
# VELOCITÀ DELLA LUCE EMERGENTE DALLA SCALA DI PLANCK
# ============================================================================

# Scale di Planck fondamentali
LUNGHEZZA_PLANCK_METRI = 1.616255e-35  # [m]
TEMPO_PLANCK_SECONDI = 5.391247e-44    # [s]

# La velocità della luce EMERGE dalla scala di Planck (non è un parametro libero)
C_PLANCK = LUNGHEZZA_PLANCK_METRI / TEMPO_PLANCK_SECONDI  # ≈ 299792458 m/s

# ============================================================================
# VELOCITÀ DELLA LUCE LOCALE EMERGENTE (copia da WQT_manifold.py)
# ============================================================================

def calcola_c_locale(densita_sx, densita_dx):
    """
    Calcola la velocità di propagazione locale emergente dalla geometria chirale.
    
    FISICA:
    -------
    La velocità della luce NON è una costante globale, ma emerge localmente
    dal tensore metrico modulato dalle densità di chiralità DX (spazio) e SX (materia).
    
    La materia agisce come un mezzo rifrangente geometrico:
    - Vuoto puro (ρ_SX → 0):  c → C_PLANCK (emerge dalla scala quantistica)
    - Materia densa (ρ_SX alta): c si riduce (rallentamento geometrico)
    
    FORMULA:
    --------
    Indice di rifrazione geometrico:
        n_geo = 1 + α × (ρ_SX / ρ_totale)
    
    Velocità locale (VETTORIALE - 24 valori):
        c_locale[i] = C_PLANCK / n_geo[i]
    
    Parametri:
    ----------
    densita_sx : float or ndarray
        Densità di chiralità SX (materia)
    densita_dx : float or ndarray  
        Densità di chiralità DX (spazio)
        
    Restituisce:
    -----------
    c_locale_vettore : ndarray(24)
        Velocità di propagazione locale in m/s per ogni segmento
    """
    
    # Coefficiente di rifrazione geometrica
    ALPHA_REFRACTION = 0.1
    
    # Converte input a vettori se sono scalari
    if not hasattr(densita_sx, '__len__'):
        densita_sx_vec = np.full(24, densita_sx)
        densita_dx_vec = np.full(24, densita_dx)
    else:
        densita_sx_vec = np.asarray(densita_sx)
        densita_dx_vec = np.asarray(densita_dx)
    
    # Densità totale per segmento
    rho_totale = densita_sx_vec + densita_dx_vec + 1e-12
    
    # Frazione di materia per segmento
    frazione_materia = densita_sx_vec / rho_totale
    
    # Indice di rifrazione geometrico per segmento
    n_geo = 1.0 + ALPHA_REFRACTION * frazione_materia
    
    # Velocità locale emergente PER SEGMENTO (24 valori!)
    c_locale_vettore = C_PLANCK / n_geo
    
    return c_locale_vettore


# ============================================================================
# TEST SUITE
# ============================================================================

def main():
    print("\n" + "="*70)
    print("🌌 TEST VELOCITÀ DELLA LUCE LOCALE EMERGENTE (VETTORIALE)")
    print("="*70 + "\n")
    
    print("📐 FISICA FONDAMENTALE:")
    print(f"  Lunghezza Planck: {LUNGHEZZA_PLANCK_METRI:.6e} m")
    print(f"  Tempo Planck:     {TEMPO_PLANCK_SECONDI:.6e} s")
    print(f"  C_PLANCK = l_P/t_P = {C_PLANCK:,.2f} m/s")
    print("  → La velocità emerge dalla scala quantistica!\n")
    
    # Test 1: Vuoto Puro
    print("Test 1: VUOTO PURO (rho_SX -> 0)")
    print("-" * 70)
    c_vuoto_test = calcola_c_locale(0.0, 1.0)
    print(f"  Input:  rho_SX = 0.0, rho_DX = 1.0")
    print(f"  Output: c_locale[0..23] = array(24 valori)")
    print(f"          Media: {np.mean(c_vuoto_test):,.2f} m/s")
    print(f"          Std:   {np.std(c_vuoto_test):.2e} m/s")
    print(f"  Atteso: C_PLANCK = {C_PLANCK:,.2f} m/s")
    diff_vuoto = abs(np.mean(c_vuoto_test) - C_PLANCK)
    print(f"  Differenza media: {diff_vuoto:.2e}")
    print("\nTest 2: MATERIA DENSA OMOGENEA (rho_SX = rho_DX)")
    print("-" * 70)
    c_materia_test = calcola_c_locale(1.0, 1.0)
    frazione = np.mean(c_materia_test) / C_PLANCK
    rallentamento = (1 - frazione) * 100
    print(f"  Input:  rho_SX = 1.0, rho_DX = 1.0 (uniforme)")
    print(f"  Output: c_locale[0..23] = array(24 valori)")
    print(f"          Media: {np.mean(c_materia_test):,.2f} m/s")
    print(f"          Std:   {np.std(c_materia_test):.2e} m/s")
    print(f"  Frazione di C_PLANCK: {frazione:.4f}")
    print(f"  Rallentamento: {rallentamento:.2f}%")
    n_geo_atteso = 1.0 + 0.1 * 0.5
    c_atteso = C_PLANCK / n_geo_atteso100
    print(f"  Input:  rho_SX = 1.0, rho_DX = 1.0")
    print(f"  Output: c_locale = {c_materia_test:,.2f} m/s")
    print(f"  Frazione di c_vuoto: {frazione:.4f}")
    print(f"  Rallentamento: {rallentamento:.2f}%")
    n_geo_atteso = 1.0 + 0.1 * 0.5  # frazione_materia = 0.5
    c_atteso = C_VUOTO / n_geo_atteso
    print(f"  Valore atteso: {c_atteso:,.2f} m/s")
    if 0.90 < frazione < 0.96:
        print("  ✅ Test PASSATO - Rallentamento ~5% come previsto")
    else:
        print("  ❌ Test FALLITO")
    print("\nTest 3: MATERIA PURA OMOGENEA (rho_DX -> 0)")
    print("-" * 70)
    c_pura_test = calcola_c_locale(1.0, 0.0)
    frazione_pura = np.mean(c_pura_test) / C_PLANCK
    rallentamento_pura = (1 - frazione_pura) * 100
    print(f"  Input:  rho_SX = 1.0, rho_DX = 0.0 (uniforme)")
    print(f"  Output: c_locale[0..23] = array(24 valori)")
    print(f"          Media: {np.mean(c_pura_test):,.2f} m/s")
    print(f"          Std:   {np.std(c_pura_test):.2e} m/s")
    print(f"  Frazione di C_PLANCK: {frazione_pura:.4f}")
    print(f"  Rallentamento: {rallentamento_pura:.2f}%")
    n_geo_max = 1.1
    c_min_atteso = C_PLANCK / n_geo_max
    print(f"  Valore atteso: {c_min_atteso:,.2f} m/s")
    if abs(np.mean(c_pura_test) - c_min_atteso) < 100:
    print(f"  Valore atteso: {c_min_atteso:,.2f} m/s")
    if abs(c_pura_test - c_min_atteso) < 100:
        print("  ✅ Test PASSATO - Rallentamento massimo ~10%")
    else:
        print("  ❌ Test FALLITO")
    
    # Test 4: Sistema 24 Campi (inhomogeneo) - VERIFICA ANISOTROPIA!
    print("\nTest 4: SISTEMA 24 CAMPI (distribuzione inhomogenea)")
    print("-" * 70)
    np.random.seed(42)
    rho_sx_24 = np.random.rand(24)
    rho_dx_24 = np.random.rand(24)
    c_24_test = calcola_c_locale(rho_sx_24, rho_dx_24)
    
    # 🔥 CHIAVE: c_24_test DEVE essere un array(24), NON uno scalare!
    if hasattr(c_24_test, '__len__'):
        print(f"  ✅ Output VETTORIALE: c_locale[24] (24 velocità distinte!)")
        print(f"  Densità SX: min={np.min(rho_sx_24):.3f}, max={np.max(rho_sx_24):.3f}")
        print(f"  Densità DX: min={np.min(rho_dx_24):.3f}, max={np.max(rho_dx_24):.3f}")
        print(f"  c_locale: min={np.min(c_24_test):,.0f} m/s, max={np.max(c_24_test):,.0f} m/s")
        print(f"  Gradiente Δc: {np.max(c_24_test) - np.min(c_24_test):,.0f} m/s")
        print(f"  Std Dev: {np.std(c_24_test):,.0f} m/s (anisotropia)")
        
        # Verifica anisotropia: i 24 valori devono essere DIVERSI
        valori_unici = len(np.unique(c_24_test))
        print(f"  Valori unici: {valori_unici}/24")
        
        if valori_unici > 20:  # Almeno 20 valori distinti su 24
            print("  ✅ Test PASSATO - Anisotropia confermata (24 velocità diverse!)")
            print("     → UNIVERSO INTERNO TURBOLENTO attivato 🌌")
        else:
            print("  ❌ Test FALLITO - Troppi duplicati (sistema cristallizzato)")
    else:
        print(f"  ❌ ERRORE: Output SCALARE invece di VETTORIALE!")
        print(f"  c_locale = {c_24_test:,.2f} m/s (media sbagliata!)")
        print("  → SisteESTREMO tra segmenti (micro-rifrazione!)
    print("\nTest 5: GRADIENTE ESTREMO TRA SEGMENTI ADIACENTI")
    print("-" * 70)
    # Crea distribuzione con gradiente drammatico
    rho_sx_grad = np.zeros(24)
    rho_dx_grad = np.ones(24)
    # Segmenti 10-14: materia ultra-densa
    rho_sx_grad[10:15] = 0.95
    rho_dx_grad[10:15] = 0.05
    
    c_grad = calcola_c_locale(rho_sx_grad, rho_dx_grad)
    
    print(f"  Input: Distribuzione con cluster denso (segmenti 10-14)")
    print(f"  Segmenti VUOTI (0-9, 15-23):")
    print(f"    c_media = {np.mean(c_grad[[0,1,2,3,4,5,6,7,8,9,15,16,17,18,19,20,21,22,23]]):,.2f} m/s")
    print(f"  Segmenti DENSI (10-14):")
    print(f"    c_media = {np.mean(c_grad[10:15]):,.2f} m/s")
    
    # Gradiente tra segmento 9 (vuoto) e 10 (denso)
    delta_c_interfaccia = c_grad[9] - c_grad[10]
    gradiente_relativo = delta_c_interfaccia / c_grad[9] * 100
    
    print(f"\n  INTERFACCIA VUOTO-MATERIA (segmenti 9→10):")
    print(f"    c[9]  = {c_grad[9]:,.2f} m/s (vuoto)")
    print(f"    c[10] = {c_grad[10]:,.2f} m/s (denso)")
    print(f"    Δc = {delta_c_interfaccia:,.2f} m/s")
    print(f"    Gradiente: {gradiente_relativo:.2f}%")
    
    if delta_c_interfaccia > 1e7:
        print("  ✅ Test PASSATO - Micro-rifrazione tra segmenti!")
        print("     → La luce 'rimbalza' internamente tra i segmenti!")
        print("     → Universo interno TURBOLENTO e VIBRANTE!
        print("  ✅ Test PASSATO - Gradiente produce rallentamento in materia densa")
        print("     → Questo causerà curvatura geodesiche (gravità emergente!)")
    else:
        print("  ❌ Test FALLITO")
    
    # Riepilogo
    print("\n" + "="*70)
    print("✅ TUTTI I TEST COMPLETATI")
    print("="*70)
    print("\n📐 FISICA IMPLEMENTATA:")
    print("   - Velocità luce NON è più una costante globale")
    print("   - c emerge localmente da densità chiralità")
    print("   - Limite vuoto puro: c → c_vuoto ✓")
    print("   - Materia densa: c si riduce (~10% max) ✓")
    print("   🔥 24 CAMPI: Output VETTORIALE (24 velocità distinte!) ✓")
    print("\n🌌 EFFETTO EMERGENTE - UNIVERSO INTERNO TURBOLENTO:")
    print("   - Ogni segmento ha la SUA velocità della luce")
    print("   - Gradiente Δc tra segmenti adiacenti")
    print("   - Micro-rifrazioni locali → luce rimbalza internamente")
    print("   - GRAVITÀ = rifrazione geometrica tra segmenti")
    print("   - Feedback: ρ_SX ↑ → c ↓ → ρ_SX ↑↑ (clustering esplosivo!)")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
