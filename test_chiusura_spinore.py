"""
Script di test per la funzione check_chiusura_spinore.
Verifica la validazione topologica spinoriale del solitone fermionico.
"""

import numpy as np
import sys
import os

# Importa le funzioni dal modulo principale
sys.path.insert(0, os.path.dirname(__file__))

from WQT_manifold import check_chiusura_spinore, estrai_nodi_manifold

def test_chiusura_spirale_ideale():
    """Test con una spirale ideale che dovrebbe avere torsione costante."""
    print("=" * 70)
    print("TEST 1: Spirale cilindrica ideale")
    print("=" * 70)
    
    # Genera una spirale con parametri controllati
    N_punti = 500
    t = np.linspace(0, 4 * np.pi, N_punti)
    raggio = 5.0
    passo = 1.0  # Passo verticale per giro
    
    # Spirale cilindrica
    X = raggio * np.cos(t)
    Y = raggio * np.sin(t)
    Z = passo * t / (2 * np.pi)
    
    nodi = estrai_nodi_manifold(X, Y, Z)
    print(f"Numero di nodi: {len(nodi)}")
    
    # Calcola chiusura spinoriale
    scalar_error, diagnostica = check_chiusura_spinore(nodi)
    
    print(f"\nRisultati:")
    print(f"  Integrale calcolato: {diagnostica['integrale_calcolato']:.6f}")
    print(f"  Target teorico (4π): {diagnostica['target_teorico']:.6f}")
    print(f"  Errore scalare normalizzato: {scalar_error:.6e}")
    print(f"  Errore percentuale: {diagnostica['errore_percentuale']:.2f}%")
    print(f"  Errore assoluto: {diagnostica['errore_assoluto']:.6e}")
    print(f"  Torsione media: {diagnostica['torsione_media']:.6e}")
    print(f"  Lunghezza totale: {diagnostica['lunghezza_totale']:.6f} m")
    print(f"  Frequenza modulazione: {diagnostica['frequenza_modulazione']:.1f}")
    
    return scalar_error, diagnostica

def test_chiusura_toroidale():
    """Test con un toroide (curva chiusa naturalmente)."""
    print("\n" + "=" * 70)
    print("TEST 2: Toroide (curva chiusa)")
    print("=" * 70)
    
    # Parametri del toro - percorso lungo un meridiano
    R = 10.0  # Raggio maggiore
    r = 3.0   # Raggio minore
    N_punti = 300
    
    v = np.linspace(0, 2 * np.pi, N_punti)
    u_fisso = 0.0  # Meridiano fisso
    
    # Superficie toroidale - meridiano
    X = (R + r * np.cos(v)) * np.cos(u_fisso)
    Y = (R + r * np.cos(v)) * np.sin(u_fisso)
    Z = r * np.sin(v)
    
    nodi = estrai_nodi_manifold(X, Y, Z)
    print(f"Numero di nodi: {len(nodi)}")
    
    scalar_error, diagnostica = check_chiusura_spinore(nodi)
    
    print(f"\nRisultati:")
    print(f"  Integrale calcolato: {diagnostica['integrale_calcolato']:.6f}")
    print(f"  Target teorico (4π): {diagnostica['target_teorico']:.6f}")
    print(f"  Errore scalare normalizzato: {scalar_error:.6e}")
    print(f"  Errore percentuale: {diagnostica['errore_percentuale']:.2f}%")
    print(f"  Errore assoluto: {diagnostica['errore_assoluto']:.6e}")
    print(f"  Torsione media: {diagnostica['torsione_media']:.6e}")
    
    return scalar_error, diagnostica

def test_chiusura_solitone_24segmenti():
    """Test con parametri realistici del solitone a 24 segmenti."""
    print("\n" + "=" * 70)
    print("TEST 3: Solitone fermionico con 24 segmenti frattali")
    print("=" * 70)
    
    # Parametri simili al manifold WQT
    segmenti_frattali = 24
    risoluzione = 480  # Alta risoluzione per accuratezza
    
    theta = np.linspace(0, 4 * np.pi, risoluzione)
    frequenza = segmenti_frattali / 2.0
    
    # Raggio con modulazione caratteristica del solitone
    r_base = 5.0
    r = r_base * (1 + 0.3 * np.sin(frequenza * theta))
    
    # Coordinate con oscillazione in Z (caratteristica del solitone)
    X = r * np.cos(theta)
    Y = r * np.sin(theta)
    Z = r_base * 0.2 * np.cos(frequenza * theta)
    
    nodi = estrai_nodi_manifold(X, Y, Z)
    print(f"Numero di nodi: {len(nodi)}")
    print(f"Frequenza di modulazione: {frequenza}")
    
    scalar_error, diagnostica = check_chiusura_spinore(nodi)
    
    print(f"\nRisultati:")
    print(f"  Integrale calcolato: {diagnostica['integrale_calcolato']:.6f}")
    print(f"  Target teorico (4π): {diagnostica['target_teorico']:.6f} ({diagnostica['target_teorico']/np.pi:.1f}π)")
    print(f"  Errore scalare normalizzato: {scalar_error:.6e}")
    print(f"  Errore percentuale: {diagnostica['errore_percentuale']:.2f}%")
    print(f"  Errore assoluto: {diagnostica['errore_assoluto']:.6e}")
    print(f"  Errore in unità Planck: {diagnostica['errore_planck']:.6e}")
    print(f"  Torsione media: {diagnostica['torsione_media']:.6e}")
    print(f"  Lunghezza totale: {diagnostica['lunghezza_totale']:.6f} m")
    
    # Interpretazione fisica
    print(f"\n  Interpretazione:")
    if abs(scalar_error) < 0.01:
        print(f"    ✓ ECCELLENTE: Chiusura topologica quasi perfetta!")
        print(f"    Il solitone è topologicamente stabile (fermionico).")
    elif abs(scalar_error) < 0.05:
        print(f"    ✓ BUONO: Chiusura topologica entro tolleranza fisica.")
        print(f"    Il solitone mantiene carattere fermionico.")
    elif abs(scalar_error) < 0.1:
        print(f"    ⚠ ACCETTABILE: Deviazione moderata dalla chiusura ideale.")
        print(f"    Il solitone è parzialmente stabile.")
    else:
        print(f"    ✗ CRITICO: Violazione significativa del vincolo topologico!")
        print(f"    Il solitone potrebbe non essere fermionicamente stabile.")
    
    return scalar_error, diagnostica

def test_confronto_risoluzioni():
    """Test della convergenza con diverse risoluzioni."""
    print("\n" + "=" * 70)
    print("TEST 4: Convergenza al variare della risoluzione")
    print("=" * 70)
    
    segmenti = 24
    frequenza = segmenti / 2.0
    r_base = 5.0
    
    risoluzioni = [100, 200, 400, 800, 1200]
    
    print(f"{'N_punti':<10} {'Integrale':<12} {'Errore %':<12} {'Tempo (ms)':<12}")
    print("-" * 50)
    
    import time
    risultati = []
    
    for N in risoluzioni:
        theta = np.linspace(0, 4 * np.pi, N)
        r = r_base * (1 + 0.3 * np.sin(frequenza * theta))
        X = r * np.cos(theta)
        Y = r * np.sin(theta)
        Z = r_base * 0.2 * np.cos(frequenza * theta)
        
        nodi = estrai_nodi_manifold(X, Y, Z)
        
        start = time.time()
        scalar_error, diagnostica = check_chiusura_spinore(nodi)
        elapsed = (time.time() - start) * 1000
        
        risultati.append({
            'N': N,
            'integrale': diagnostica['integrale_calcolato'],
            'errore_perc': diagnostica['errore_percentuale'],
            'tempo_ms': elapsed
        })
        
        print(f"{N:<10} {diagnostica['integrale_calcolato']:<12.6f} "
              f"{diagnostica['errore_percentuale']:<12.4f} {elapsed:<12.2f}")
    
    # Verifica convergenza
    print(f"\nVerifica convergenza:")
    if len(risultati) > 1:
        variazione = abs(risultati[-1]['integrale'] - risultati[-2]['integrale'])
        print(f"  Variazione ultimi due punti: {variazione:.6e}")
        if variazione < 0.01:
            print(f"  ✓ Convergenza numerica raggiunta")
        else:
            print(f"  ⚠ Potrebbe richiedere maggiore risoluzione")
    
    return risultati

def test_interpretazione_fisica():
    """Test con interpretazione fisica dettagliata."""
    print("\n" + "=" * 70)
    print("TEST 5: Interpretazione fisica della chiusura spinoriale")
    print("=" * 70)
    
    print(f"\nBackground teorico:")
    print(f"  Gli spinori (fermioni) hanno una proprietà topologica unica:")
    print(f"  - Rotazione di 360° (2π): ψ → -ψ  (cambio di segno)")
    print(f"  - Rotazione di 720° (4π): ψ → ψ   (ritorno allo stato originale)")
    print(f"")
    print(f"  Un solitone fermionico stabile deve soddisfare:")
    print(f"    ∮ τ ds = 4π")
    print(f"  dove τ è la torsione geometrica del manifold.")
    print(f"")
    
    # Test con solitone realistico
    segmenti = 24
    risoluzione = 600
    frequenza = segmenti / 2.0
    r_base = 5.0
    
    theta = np.linspace(0, 4 * np.pi, risoluzione)
    r = r_base * (1 + 0.3 * np.sin(frequenza * theta))
    X = r * np.cos(theta)
    Y = r * np.sin(theta)
    Z = r_base * 0.2 * np.cos(frequenza * theta)
    
    nodi = estrai_nodi_manifold(X, Y, Z)
    scalar_error, diagnostica = check_chiusura_spinore(nodi)
    
    print(f"Risultati del test:")
    print(f"  Integrale misurato: {diagnostica['integrale_calcolato']:.6f}")
    print(f"  Valore teorico:     {diagnostica['target_teorico']:.6f}")
    print(f"  Differenza:         {diagnostica['errore_assoluto']:.6f}")
    print(f"")
    print(f"  In termini di angoli:")
    angolo_calcolato = diagnostica['integrale_calcolato'] * 180 / np.pi
    angolo_target = diagnostica['target_teorico'] * 180 / np.pi
    print(f"    Calcolato: {angolo_calcolato:.2f}°")
    print(f"    Target:    {angolo_target:.2f}°")
    print(f"    Δ:         {abs(angolo_calcolato - angolo_target):.2f}°")
    print(f"")
    
    # Classificazione del solitone
    print(f"  Classificazione topologica:")
    integrale = diagnostica['integrale_calcolato']
    
    if abs(integrale - 4*np.pi) < 0.1:
        tipo = "FERMIONE (spin-1/2)"
        stabilita = "TOPOLOGICAMENTE STABILE"
    elif abs(integrale - 2*np.pi) < 0.1:
        tipo = "BOSONE VETTORIALE (spin-1)"
        stabilita = "STABILE (simmetria diversa)"
    elif abs(integrale) < 0.1:
        tipo = "BOSONE SCALARE (spin-0)"
        stabilita = "INSTABILE topologicamente"
    else:
        tipo = "IBRIDO o ECCITATO"
        stabilita = "PARZIALMENTE STABILE"
    
    print(f"    Tipo:      {tipo}")
    print(f"    Stabilità: {stabilita}")
    
    return scalar_error, diagnostica

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TEST DELLA FUNZIONE check_chiusura_spinore")
    print("Validazione Topologica Spinoriale per Solitoni Fermionici")
    print("=" * 70 + "\n")
    
    # Esegui tutti i test
    e1, d1 = test_chiusura_spirale_ideale()
    e2, d2 = test_chiusura_toroidale()
    e3, d3 = test_chiusura_solitone_24segmenti()
    risultati_conv = test_confronto_risoluzioni()
    e5, d5 = test_interpretazione_fisica()
    
    print("\n" + "=" * 70)
    print("RIEPILOGO RISULTATI")
    print("=" * 70)
    
    tests = [
        ("Spirale cilindrica", e1, d1),
        ("Toroide", e2, d2),
        ("Solitone 24 segmenti", e3, d3),
        ("Interpretazione fisica", e5, d5)
    ]
    
    print(f"\n{'Test':<25} {'Errore %':<12} {'Status':<20}")
    print("-" * 60)
    
    for nome, errore, diag in tests:
        err_perc = diag['errore_percentuale']
        if abs(errore) < 0.01:
            status = "✓ ECCELLENTE"
        elif abs(errore) < 0.05:
            status = "✓ BUONO"
        elif abs(errore) < 0.1:
            status = "⚠ ACCETTABILE"
        else:
            status = "✗ CRITICO"
        
        print(f"{nome:<25} {err_perc:<12.2f} {status:<20}")
    
    print("\n" + "=" * 70)
    print("TUTTI I TEST COMPLETATI!")
    print("=" * 70)
    
    # Salva risultati
    output_file = "test_chiusura_spinore_output.npz"
    np.savez(output_file,
             errore_spirale=e1,
             errore_toroide=e2,
             errore_solitone=e3,
             convergenza=[r['integrale'] for r in risultati_conv])
    print(f"\nDati salvati in: {output_file}")
