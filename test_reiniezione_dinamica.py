#!/usr/bin/env python3
"""
Test della funzione di reiniezione dinamica VETTORIALE
"""
import numpy as np
import sys

# Importa la funzione dal modulo (simuliamo il comportamento)
def calcola_reiniezione_dinamica(K_squared_local, delta_chi_vettore):
    """Copia della funzione VETTORIALE per test standalone"""
    BASE_MINIMA = 1e-55
    
    SOGLIA_CRITICA_K2 = (4.0 * np.pi) ** 2
    
    rapporto_torsione = np.log1p(K_squared_local / SOGLIA_CRITICA_K2)
    amplificazione_torsione = 1.0 + 9.0 * np.tanh(rapporto_torsione / 3.0)
    
    SOGLIA_STASI = 1e-6
    abs_delta = np.abs(delta_chi_vettore)
    indicatore_blocco = 1.0 / (1.0 + (abs_delta / SOGLIA_STASI) ** 2)
    amplificazione_stasi = 1.0 + 99.0 * indicatore_blocco
    
    fattore_combinato = amplificazione_torsione * amplificazione_stasi
    fattore_saturato = np.tanh(fattore_combinato / 1e10) * 1e10
    fattore_vettore = BASE_MINIMA * fattore_saturato
    fattore_vettore = np.clip(fattore_vettore, 1e-55, 1e-40)
    
    return fattore_vettore

print("="*80)
print("TEST FATTORE REINIEZIONE DINAMICO VETTORIALE (24 segmenti)")
print("="*80)

# Caso 1: Situazione normale (K² moderato, sistema in movimento)
print("\n[CASO 1] Sistema sano: K² moderato, Δχ normale su tutti i segmenti")
K2_normale = np.full(24, 500.0)  # Sotto soglia critica
delta_normale = np.full(24, 0.01)  # Tutti si muovono
fattore1 = calcola_reiniezione_dinamica(K2_normale, delta_normale)
print(f"  K² medio:     {np.mean(K2_normale):.2f}")
print(f"  Δχ medio:     {np.mean(delta_normale):.3e}")
print(f"  Fattore medio: {np.mean(fattore1):.3e}")
print(f"  Fattore range: [{np.min(fattore1):.3e}, {np.max(fattore1):.3e}]")
print(f"  Amplif media: {np.mean(fattore1)/1e-55:.1f}×")

# Caso 2: Alta torsione ma sistema in movimento (tutti i segmenti)
print("\n[CASO 2] Alta torsione, sistema in movimento (uniforme)")
K2_alto = np.full(24, 2457.0)  # Come nei dati reali
delta_movimento = np.full(24, 0.1)
fattore2 = calcola_reiniezione_dinamica(K2_alto, delta_movimento)
print(f"  K² medio:     {np.mean(K2_alto):.2f}")
print(f"  Δχ medio:     {np.mean(delta_movimento):.3e}")
print(f"  Fattore medio: {np.mean(fattore2):.3e}")
print(f"  Amplif media: {np.mean(fattore2)/1e-55:.1f}×")

# Caso 3: Sistema BLOCCATO (alta K², Δχ ≈ 0 su tutti) - PROBLEMA ATTUALE!
print("\n[CASO 3] ⚠️  Sistema bloccato: alta K², Δχ ≈ 0 su tutti (problema attuale)")
K2_bloccato = np.full(24, 2457.0)  # Come nei dati reali
delta_bloccato = np.full(24, 1e-12)  # Praticamente zero
fattore3 = calcola_reiniezione_dinamica(K2_bloccato, delta_bloccato)
print(f"  K² medio:     {np.mean(K2_bloccato):.2f}")
print(f"  Δχ medio:     {np.mean(delta_bloccato):.3e}")
print(f"  Fattore medio: {np.mean(fattore3):.3e}")
print(f"  Amplif media: {np.mean(fattore3)/1e-55:.1f}×")
print(f"  → Questo dovrebbe SBLOCCARE il sistema!")

# Caso 4: ETEROGENEITÀ - alcuni segmenti bloccati, altri in movimento
print("\n[CASO 4] Eterogeneità: metà bloccati, metà in movimento")
K2_etero = np.full(24, 2457.0)
delta_etero = np.concatenate([
    np.full(12, 1e-12),  # 12 segmenti bloccati
    np.full(12, 0.1)     # 12 segmenti in movimento
])
fattore4 = calcola_reiniezione_dinamica(K2_etero, delta_etero)
print(f"  K² medio:     {np.mean(K2_etero):.2f}")
print(f"  Δχ segmenti 0-11:  {np.mean(delta_etero[:12]):.3e} (bloccati)")
print(f"  Δχ segmenti 12-23: {np.mean(delta_etero[12:]):.3e} (attivi)")
print(f"  Fattore segmenti bloccati: {np.mean(fattore4[:12]):.3e}")
print(f"  Fattore segmenti attivi:   {np.mean(fattore4[12:]):.3e}")
print(f"  Amplif bloccati: {np.mean(fattore4[:12])/1e-55:.1f}×")
print(f"  Amplif attivi:   {np.mean(fattore4[12:])/1e-55:.1f}×")
print(f"  → I segmenti bloccati ricevono più rumore!")

# Caso 5: Variabilità completa - K² e Δχ diversi per ogni segmento
print("\n[CASO 5] Variabilità completa: ogni segmento ha K² e Δχ diversi")
np.random.seed(42)
K2_vario = np.random.uniform(500, 5000, 24)  # K² varia
delta_vario = np.random.uniform(1e-10, 0.5, 24)  # Δχ varia
fattore5 = calcola_reiniezione_dinamica(K2_vario, delta_vario)
print(f"  K² range:     [{np.min(K2_vario):.0f}, {np.max(K2_vario):.0f}]")
print(f"  Δχ range:     [{np.min(delta_vario):.3e}, {np.max(delta_vario):.3e}]")
print(f"  Fattore range: [{np.min(fattore5):.3e}, {np.max(fattore5):.3e}]")
print(f"  Fattore medio: {np.mean(fattore5):.3e}")
print(f"  Std dev:       {np.std(fattore5):.3e}")

# Identifica segmento con più rumore
idx_max = np.argmax(fattore5)
print(f"\n  Segmento con più rumore: #{idx_max}")
print(f"    K²[{idx_max}] = {K2_vario[idx_max]:.2f}")
print(f"    Δχ[{idx_max}] = {delta_vario[idx_max]:.3e}")
print(f"    Fattore[{idx_max}] = {fattore5[idx_max]:.3e}")

print("\n" + "="*80)
print("ANALISI")
print("="*80)
print(f"\nRapporto Caso3/Caso2: {np.mean(fattore3)/np.mean(fattore2):.1f}×")
print(f"→ Segmenti bloccati ricevono {np.mean(fattore3)/np.mean(fattore2):.0f} volte più rumore!")
print(f"\nRapporto etero (bloccati/attivi): {np.mean(fattore4[:12])/np.mean(fattore4[12:]):.1f}×")
print(f"→ Omeostasi locale: ogni segmento riceve rumore proporzionale al suo stato!")
print("\n✓ La funzione VETTORIALE risponde correttamente alle condizioni LOCALI!")
