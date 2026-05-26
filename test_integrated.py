"""
================================================================================
TEST SUITE - WQT MANIFOLD INTEGRATO
================================================================================

Verifica completa di tutte le funzionalità dell'applicazione integrata.

Test Coverage:
1. Inizializzazione sistema
2. Evoluzione parallela
3. Visualizzazione 3D
4. Telemetria HDF5
5. Modalità headless
6. Generazione geometria
7. Fissione/congiunzione
================================================================================
"""

import sys
import os
import tempfile
import numpy as np
import h5py
from pathlib import Path

# Importa modulo da testare
sys.path.insert(0, str(Path(__file__).parent))

# Mock argparse per test
class MockArgs:
    film = False
    playback = False
    headless = True  # Default per test
    output = None
    fps = 24
    duration = 1  # 1 secondo = 24 frame
    db = None
    speed = 1
    n_manifold = 5
    cores = 2

# Patch sys.argv per evitare parsing
original_argv = sys.argv
sys.argv = ['test']

# Importa dopo mock
from WQT_manifold_integrated import (
    ManifoldBase, 
    evolvi_sistema_parallelo,
    gestisci_congiunzioni,
    gestisci_fissioni,
    genera_mappatura_da_manifold,
    inizializza_hdf5,
    salva_frame_hdf5,
    LUNGHEZZA_PLANCK,
    N_SEGMENTI,
    TORSIONE_CRITICA
)

# Colori ANSI
VERDE = '\033[92m'
ROSSO = '\033[91m'
GIALLO = '\033[93m'
RESET = '\033[0m'

def print_test(nome_test):
    """Header test."""
    print(f"\n{'='*70}")
    print(f"TEST: {nome_test}")
    print(f"{'='*70}")

def assert_true(condizione, messaggio):
    """Asserzione custom con output colorato."""
    if condizione:
        print(f"{VERDE}✓{RESET} {messaggio}")
        return True
    else:
        print(f"{ROSSO}✗{RESET} {messaggio}")
        raise AssertionError(f"Fallito: {messaggio}")

def assert_quasi_uguale(a, b, tolleranza, messaggio):
    """Confronto float con tolleranza."""
    if abs(a - b) < tolleranza:
        print(f"{VERDE}✓{RESET} {messaggio} (diff: {abs(a-b):.2e})")
        return True
    else:
        print(f"{ROSSO}✗{RESET} {messaggio} (diff: {abs(a-b):.2e} > {tolleranza:.2e})")
        raise AssertionError(f"Fallito: {messaggio}")


# ============================================================================
# TEST 1: Inizializzazione ManifoldBase
# ============================================================================

def test_inizializzazione():
    print_test("Inizializzazione ManifoldBase")
    
    # Crea manifold con parametri default
    m = ManifoldBase()
    
    assert_true(len(m.chi) == N_SEGMENTI, f"chi ha {N_SEGMENTI} componenti")
    assert_true(len(m.vel) == N_SEGMENTI, f"vel ha {N_SEGMENTI} componenti")
    assert_true(len(m.posizione) == 3, "posizione è 3D")
    assert_true(m.generazione == 0, "generazione iniziale = 0")
    
    # Verifica chiralità alternata
    chiralita_attesa = np.array([(-1)**i for i in range(N_SEGMENTI)])
    segni_chi = np.sign(m.chi)
    correlazione = np.mean(segni_chi * chiralita_attesa)
    
    assert_true(correlazione > 0.5, f"Chiralità alternata rispettata (corr={correlazione:.2f})")
    
    # Calcola torsione
    tau = m.calcola_torsione_totale()
    assert_true(tau >= 0, f"Torsione positiva: τ={tau:.3f}")
    assert_true(tau < TORSIONE_CRITICA, f"Torsione sotto soglia: τ={tau:.3f} < {TORSIONE_CRITICA:.3f}")
    
    print(f"{VERDE}✓ Test inizializzazione PASSATO{RESET}")


# ============================================================================
# TEST 2: Evoluzione Locale
# ============================================================================

def test_evoluzione_locale():
    print_test("Evoluzione Locale (Velocity Verlet)")
    
    m = ManifoldBase()
    
    # Stato iniziale
    chi_0 = m.chi.copy()
    vel_0 = m.vel.copy()
    
    # Calcola energia iniziale
    E_cin_0 = 0.5 * np.sum(vel_0**2)
    E_pot_0 = np.sum(-0.5 * 0.5 * chi_0**2 + 0.25 * chi_0**4)
    E_tot_0 = E_cin_0 + E_pot_0
    
    # Evolvi per 100 step
    dt = 0.01
    n_step = 100
    
    for _ in range(n_step):
        m.evolvi_locale(dt)
    
    # Stato finale
    chi_f = m.chi
    vel_f = m.vel
    
    E_cin_f = 0.5 * np.sum(vel_f**2)
    E_pot_f = np.sum(-0.5 * 0.5 * chi_f**2 + 0.25 * chi_f**4)
    E_tot_f = E_cin_f + E_pot_f
    
    # Verifica conservazione energia
    drift = abs(E_tot_f - E_tot_0) / (abs(E_tot_0) + 1e-12)
    
    assert_true(drift < 0.1, f"Conservazione energia: drift={drift:.2%} < 10%")
    
    # Verifica cambiamento stato
    delta_chi = np.linalg.norm(chi_f - chi_0)
    assert_true(delta_chi > 1e-6, f"χ è evoluto: Δχ={delta_chi:.2e}")
    
    print(f"{VERDE}✓ Test evoluzione locale PASSATO{RESET}")


# ============================================================================
# TEST 3: Fissione
# ============================================================================

def test_fissione():
    print_test("Fissione Topologica")
    
    # Crea manifold saturo artificialmente
    m = ManifoldBase()
    m.chi = 10.0 * np.ones(N_SEGMENTI)  # Saturazione forzata
    m.calcola_torsione_totale()
    
    assert_true(m.check_saturazione(), f"Manifold saturo: τ={m.torsione:.3f} > {TORSIONE_CRITICA:.3f}")
    
    # Esegui fissione
    m_A, m_B = m.fissione()
    
    # Verifica creazione due figli
    assert_true(isinstance(m_A, ManifoldBase), "m_A è ManifoldBase")
    assert_true(isinstance(m_B, ManifoldBase), "m_B è ManifoldBase")
    
    # Verifica generazione incrementata
    assert_true(m_A.generazione == m.generazione + 1, f"Generazione A: {m_A.generazione}")
    assert_true(m_B.generazione == m.generazione + 1, f"Generazione B: {m_B.generazione}")
    
    # Verifica torsione ridotta
    tau_A = m_A.calcola_torsione_totale()
    tau_B = m_B.calcola_torsione_totale()
    
    assert_true(tau_A < m.torsione, f"τ_A ridotta: {tau_A:.3f} < {m.torsione:.3f}")
    assert_true(tau_B < m.torsione, f"τ_B ridotta: {tau_B:.3f} < {m.torsione:.3f}")
    
    # Verifica separazione spaziale
    distanza = np.linalg.norm(m_A.posizione - m_B.posizione)
    assert_true(distanza > 0, f"Separazione spaziale: d={distanza:.2e} m")
    
    print(f"{VERDE}✓ Test fissione PASSATO{RESET}")


# ============================================================================
# TEST 4: Congiunzione
# ============================================================================

def test_congiunzione():
    print_test("Congiunzione (Fusione)")
    
    # Crea due manifold vicini con chiralità opposta
    m1 = ManifoldBase(posizione=np.array([0, 0, 0]))
    m1.chi = +1.0 * np.ones(N_SEGMENTI)
    
    m2 = ManifoldBase(posizione=np.array([1e-34, 0, 0]))  # Vicinissimi
    m2.chi = -1.0 * np.ones(N_SEGMENTI)  # Chiralità opposta
    
    # Verifica accoppiamento
    acopp = m1.calcola_accoppiamento(m2)
    assert_true(abs(acopp) > 0, f"Accoppiamento presente: g={acopp:.3f}")
    
    # Fusione
    m_fuso = m1.congiungi(m2)
    
    # Verifica chiralità media
    chi_fuso_medio = np.mean(m_fuso.chi)
    assert_quasi_uguale(chi_fuso_medio, 0.0, 0.1, "Chiralità fusa ≈ 0 (annichilazione)")
    
    # Verifica generazione incrementata
    assert_true(m_fuso.generazione > max(m1.generazione, m2.generazione), 
               f"Generazione fusa: {m_fuso.generazione}")
    
    print(f"{VERDE}✓ Test congiunzione PASSATO{RESET}")


# ============================================================================
# TEST 5: Evoluzione Parallela
# ============================================================================

def test_evoluzione_parallela():
    print_test("Evoluzione Parallela (HPC)")
    
    # Crea lista di manifold
    N_manifold = 10
    lista = [ManifoldBase(posizione=(np.random.rand(3) - 0.5) * 1e-34) for _ in range(N_manifold)]
    
    # Energia iniziale
    E_tot_0 = sum([
        0.5 * np.sum(m.vel**2) + np.sum(-0.5 * 0.5 * m.chi**2 + 0.25 * m.chi**4)
        for m in lista
    ])
    
    # Evolvi parallelo
    dt = 0.01
    lista_evoluti = evolvi_sistema_parallelo(lista, dt, n_cores=2)
    
    # Verifica numero manifold invariato
    assert_true(len(lista_evoluti) == N_manifold, f"N_manifold invariato: {len(lista_evoluti)}")
    
    # Energia finale
    E_tot_f = sum([
        0.5 * np.sum(m.vel**2) + np.sum(-0.5 * 0.5 * m.chi**2 + 0.25 * m.chi**4)
        for m in lista_evoluti
    ])
    
    drift = abs(E_tot_f - E_tot_0) / (abs(E_tot_0) + 1e-12)
    assert_true(drift < 0.2, f"Conservazione energia parallela: drift={drift:.2%}")
    
    print(f"{VERDE}✓ Test evoluzione parallela PASSATO{RESET}")


# ============================================================================
# TEST 6: Generazione Geometria 3D
# ============================================================================

def test_generazione_geometria():
    print_test("Generazione Geometria 3D")
    
    m = ManifoldBase()
    
    # Genera mappatura
    Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, rm, th, tor_dx, tor_sx = genera_mappatura_da_manifold(m, frame=0)
    
    # Verifica dimensioni
    from WQT_manifold_integrated import RISOLUZIONE_RENDERING
    assert_true(len(Xdx) == RISOLUZIONE_RENDERING, f"Xdx ha {RISOLUZIONE_RENDERING} punti")
    assert_true(len(Ydx) == RISOLUZIONE_RENDERING, f"Ydx ha {RISOLUZIONE_RENDERING} punti")
    assert_true(len(Zdx) == RISOLUZIONE_RENDERING, f"Zdx ha {RISOLUZIONE_RENDERING} punti")
    
    # Verifica valori finiti
    assert_true(np.all(np.isfinite(Xdx)), "Xdx tutti finiti")
    assert_true(np.all(np.isfinite(Ydx)), "Ydx tutti finiti")
    assert_true(np.all(np.isfinite(Zdx)), "Zdx tutti finiti")
    
    # Verifica rm > 0
    assert_true(rm > 0, f"Raggio conforme positivo: rm={rm:.2e}")
    
    print(f"{VERDE}✓ Test generazione geometria PASSATO{RESET}")


# ============================================================================
# TEST 7: Telemetria HDF5
# ============================================================================

def test_telemetria_hdf5():
    print_test("Telemetria HDF5")
    
    # File temporaneo
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, 'test_telemetria.h5')
    
    # Rimuovi se esiste
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Inizializza
    n_frames = 10
    inizializza_hdf5(db_path, n_frames)
    
    assert_true(os.path.exists(db_path), f"File HDF5 creato: {db_path}")
    
    # Apri e salva frame
    lista_test = [ManifoldBase() for _ in range(3)]
    
    with h5py.File(db_path, 'a') as f:
        for frame_id in range(n_frames):
            salva_frame_hdf5(f, frame_id, lista_test)
    
    # Verifica lettura
    with h5py.File(db_path, 'r') as f:
        assert_true('telemetria_scalare' in f, "Dataset telemetria_scalare presente")
        
        telemetria = f['telemetria_scalare'][:]
        assert_true(len(telemetria) == n_frames, f"Salvati {n_frames} frame")
        
        # Verifica campi
        assert_true('n_manifold' in telemetria.dtype.names, "Campo n_manifold presente")
        assert_true('torsione_media' in telemetria.dtype.names, "Campo torsione_media presente")
        assert_true('energia_totale' in telemetria.dtype.names, "Campo energia_totale presente")
        
        # Verifica valori
        assert_true(telemetria[0]['n_manifold'] == 3, f"N_manifold corretto: {telemetria[0]['n_manifold']}")
    
    # Cleanup
    os.remove(db_path)
    
    print(f"{VERDE}✓ Test telemetria HDF5 PASSATO{RESET}")


# ============================================================================
# TEST 8: Gestione Fissioni Multiple
# ============================================================================

def test_gestione_fissioni():
    print_test("Gestione Fissioni Multiple")
    
    # Crea lista con manifold saturi
    lista = []
    for i in range(5):
        m = ManifoldBase()
        m.chi = 10.0 * np.ones(N_SEGMENTI)  # Forza saturazione
        m.calcola_torsione_totale()
        lista.append(m)
    
    N_iniziale = len(lista)
    tau_medio_iniziale = np.mean([m.torsione for m in lista])
    
    # Gestisci fissioni
    lista_post = gestisci_fissioni(lista)
    
    N_finale = len(lista_post)
    
    # Ogni manifold saturo dovrebbe generare 2 figli
    assert_true(N_finale == 2 * N_iniziale, 
               f"Fissioni multiple: {N_iniziale} → {N_finale} (atteso {2*N_iniziale})")
    
    # Verifica che la torsione media dei figli sia RIDOTTA rispetto ai genitori
    tau_medio_finale = np.mean([m.torsione for m in lista_post])
    riduzione = (tau_medio_iniziale - tau_medio_finale) / tau_medio_iniziale
    
    assert_true(riduzione > 0.1, 
               f"Torsione media ridotta: {tau_medio_iniziale:.2f} → {tau_medio_finale:.2f} (-{riduzione:.1%})")
    
    print(f"{VERDE}✓ Test gestione fissioni PASSATO{RESET}")


# ============================================================================
# TEST 9: Gestione Congiunzioni Multiple
# ============================================================================

def test_gestione_congiunzioni():
    print_test("Gestione Congiunzioni Multiple")
    
    # Crea coppie vicine
    lista = []
    for i in range(4):
        pos = np.array([i * 5e-35, 0, 0])  # Separati ma alcuni vicini
        m = ManifoldBase(posizione=pos)
        m.chi = ((-1)**i) * 1.0 * np.ones(N_SEGMENTI)  # Chiralità alternata
        lista.append(m)
    
    N_iniziale = len(lista)
    
    # Gestisci congiunzioni (raggio grande per forzare fusioni)
    raggio = 20.0 * LUNGHEZZA_PLANCK
    lista_post = gestisci_congiunzioni(lista, raggio)
    
    N_finale = len(lista_post)
    
    # Dovrebbe esserci almeno una fusione
    assert_true(N_finale < N_iniziale, 
               f"Congiunzioni avvenute: {N_iniziale} → {N_finale}")
    
    print(f"{VERDE}✓ Test gestione congiunzioni PASSATO{RESET}")


# ============================================================================
# ESECUZIONE SUITE COMPLETA
# ============================================================================

def run_all_tests():
    """Esegue tutti i test."""
    print("\n" + "="*70)
    print(" SUITE TEST WQT_MANIFOLD_INTEGRATED ")
    print("="*70)
    
    test_functions = [
        test_inizializzazione,
        test_evoluzione_locale,
        test_fissione,
        test_congiunzione,
        test_evoluzione_parallela,
        test_generazione_geometria,
        test_telemetria_hdf5,
        test_gestione_fissioni,
        test_gestione_congiunzioni
    ]
    
    n_passati = 0
    n_falliti = 0
    
    for test_func in test_functions:
        try:
            test_func()
            n_passati += 1
        except Exception as e:
            n_falliti += 1
            print(f"{ROSSO}ERRORE: {e}{RESET}")
    
    # Riepilogo
    print("\n" + "="*70)
    print(f" RIEPILOGO ")
    print("="*70)
    print(f"{VERDE}✓ Passati: {n_passati}/{len(test_functions)}{RESET}")
    
    if n_falliti > 0:
        print(f"{ROSSO}✗ Falliti: {n_falliti}/{len(test_functions)}{RESET}")
    else:
        print(f"{VERDE}✓ TUTTI I TEST PASSATI!{RESET}")
    
    print("="*70 + "\n")
    
    # Ripristina argv
    sys.argv = original_argv
    
    return n_falliti == 0


if __name__ == "__main__":
    successo = run_all_tests()
    sys.exit(0 if successo else 1)
