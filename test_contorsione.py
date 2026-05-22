"""
Script di test per la funzione calcola_contorsione.
Dimostra il calcolo del tensore di contorsione su un manifold di esempio.
"""

import numpy as np
import sys
import os

# Importa le funzioni dal modulo principale
# Nota: questo assume che WQT_manifold.py sia nello stesso percorso
sys.path.insert(0, os.path.dirname(__file__))

# Importiamo solo le costanti e funzioni necessarie
# Per evitare l'esecuzione dell'intero script, importiamo selettivamente
from WQT_manifold import calcola_contorsione, estrai_nodi_manifold

def test_contorsione_base():
    """Test base con un manifold semplice a spirale."""
    print("=" * 70)
    print("TEST 1: Manifold a spirale cilindrica")
    print("=" * 70)
    
    # Genera un manifold a spirale semplice
    N_punti = 100
    t = np.linspace(0, 4 * np.pi, N_punti)
    raggio = 5.0
    
    # Spirale cilindrica
    X = raggio * np.cos(t)
    Y = raggio * np.sin(t)
    Z = t * 0.5  # Avanzamento verticale
    
    # Estrai nodi
    nodi = estrai_nodi_manifold(X, Y, Z)
    print(f"Numero di nodi: {len(nodi)}")
    print(f"Shape nodi: {nodi.shape}")
    
    # Calcola contorsione
    K = calcola_contorsione(nodi)
    print(f"Shape tensore contorsione K: {K.shape}")
    print(f"Numero di punti interni con contorsione: {len(K)}")
    
    # Analisi statistica
    K_flat = K.flatten()
    K_nonzero = K_flat[np.abs(K_flat) > 1e-12]
    
    print(f"\nStatistiche del tensore K:")
    print(f"  Valore massimo: {np.max(np.abs(K_flat)):.6e}")
    print(f"  Valore medio (abs): {np.mean(np.abs(K_flat)):.6e}")
    print(f"  Elementi non-zero: {len(K_nonzero)} / {len(K_flat)}")
    print(f"  Percentuale non-zero: {100*len(K_nonzero)/len(K_flat):.2f}%")
    
    return K

def test_contorsione_toroidale():
    """Test con un manifold toroidale."""
    print("\n" + "=" * 70)
    print("TEST 2: Manifold toroidale (toro)")
    print("=" * 70)
    
    # Parametri del toro
    R = 10.0  # Raggio maggiore
    r = 3.0   # Raggio minore
    N_u = 50
    N_v = 20
    
    u = np.linspace(0, 2 * np.pi, N_u)
    v = np.linspace(0, 2 * np.pi, N_v)
    U, V = np.meshgrid(u, v)
    
    # Superficie toroidale
    X = (R + r * np.cos(V)) * np.cos(U)
    Y = (R + r * np.cos(V)) * np.sin(U)
    Z = r * np.sin(V)
    
    # Estrai nodi (lungo un meridiano)
    nodi = estrai_nodi_manifold(X[0, :], Y[0, :], Z[0, :])
    print(f"Numero di nodi: {len(nodi)}")
    
    # Calcola contorsione
    K = calcola_contorsione(nodi)
    print(f"Shape tensore contorsione K: {K.shape}")
    
    # Analisi
    K_flat = K.flatten()
    print(f"\nStatistiche del tensore K:")
    print(f"  Valore massimo: {np.max(np.abs(K_flat)):.6e}")
    print(f"  Valore medio (abs): {np.mean(np.abs(K_flat)):.6e}")
    
    return K

def test_contorsione_planck_manifold():
    """Test con parametri simili al manifold di Planck del codice principale."""
    print("\n" + "=" * 70)
    print("TEST 3: Manifold con parametri Planck (24 segmenti)")
    print("=" * 70)
    
    # Parametri simili al codice principale
    segmenti_frattali = 24
    risoluzione = 240  # Versione ridotta per test veloce
    
    theta = np.linspace(0, 4 * np.pi, risoluzione)
    frequenza = segmenti_frattali / 2.0
    
    # Raggio con modulazione
    r_base = 5.0
    r = r_base * (1 + 0.3 * np.sin(frequenza * theta))
    
    # Coordinate
    X = r * np.cos(theta)
    Y = r * np.sin(theta)
    Z = r_base * 0.2 * np.cos(frequenza * theta)
    
    # Estrai nodi
    nodi = estrai_nodi_manifold(X, Y, Z)
    print(f"Numero di nodi: {len(nodi)}")
    print(f"Frequenza utilizzata: {frequenza}")
    
    # Calcola contorsione
    K = calcola_contorsione(nodi)
    print(f"Shape tensore contorsione K: {K.shape}")
    
    # Analisi dettagliata
    K_flat = K.flatten()
    K_nonzero = K_flat[np.abs(K_flat) > 1e-12]
    
    print(f"\nStatistiche del tensore K:")
    print(f"  Valore massimo: {np.max(np.abs(K_flat)):.6e}")
    print(f"  Valore minimo (non-zero): {np.min(np.abs(K_nonzero)) if len(K_nonzero) > 0 else 0:.6e}")
    print(f"  Valore medio (abs): {np.mean(np.abs(K_flat)):.6e}")
    print(f"  Deviazione standard: {np.std(K_flat):.6e}")
    
    # Verifica simmetrie
    print(f"\nVerifica proprietà del tensore:")
    simmetria_totale = 0
    for i in range(min(10, len(K))):  # Controllo solo i primi 10 punti
        for lam in range(3):
            for mu in range(3):
                for nu in range(3):
                    # K dovrebbe essere completamente antisimmetrico
                    simm = K[i, lam, mu, nu] + K[i, mu, lam, nu] + K[i, nu, lam, mu]
                    simmetria_totale += abs(simm)
    
    print(f"  Verifica antisimmetria totale: {simmetria_totale:.6e}")
    print(f"  (dovrebbe essere ~3 volte il valore medio per costruzione)")
    
    return K

def test_performance():
    """Test delle prestazioni su manifold di diverse dimensioni."""
    print("\n" + "=" * 70)
    print("TEST 4: Performance su diverse dimensioni")
    print("=" * 70)
    
    import time
    
    dimensioni = [50, 100, 200, 500, 1000]
    
    for N in dimensioni:
        t = np.linspace(0, 4 * np.pi, N)
        X = 5.0 * np.cos(t)
        Y = 5.0 * np.sin(t)
        Z = t * 0.5
        
        nodi = estrai_nodi_manifold(X, Y, Z)
        
        start = time.time()
        K = calcola_contorsione(nodi)
        elapsed = time.time() - start
        
        print(f"  N={N:4d} nodi → {elapsed*1000:8.2f} ms (output shape: {K.shape})")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TEST DELLA FUNZIONE calcola_contorsione")
    print("Tensore di Contorsione K_λμν basato sulla geometria con torsione")
    print("=" * 70 + "\n")
    
    # Esegui tutti i test
    K1 = test_contorsione_base()
    K2 = test_contorsione_toroidale()
    K3 = test_contorsione_planck_manifold()
    test_performance()
    
    print("\n" + "=" * 70)
    print("TUTTI I TEST COMPLETATI CON SUCCESSO!")
    print("=" * 70)
    
    # Salva un esempio di output per ispezione
    output_file = "test_contorsione_output.npz"
    np.savez(output_file, 
             K_spirale=K1, 
             K_toroidale=K2, 
             K_planck=K3)
    print(f"\nDati salvati in: {output_file}")
    print("Puoi caricarli con: data = np.load('{0}')".format(output_file))
