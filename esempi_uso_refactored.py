"""
================================================================================
ESEMPI D'USO - ARCHITETTURA REFACTORATA WQT_MANIFOLD
================================================================================

Questo script fornisce esempi pratici per:
1. Simulazione cosmologica (espansione frattale)
2. Studio della separazione di fase materia/spazio
3. Analisi della crescita esponenziale per fissione
4. Visualizzazione della distribuzione spaziale

Ogni esempio è commentato linea per linea.

================================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import h5py
from WQT_manifold_refactored import (
    ManifoldBase,
    simula_universo_frattale,
    evolvi_sistema_parallelo,
    gestisci_congiunzioni,
    gestisci_fissioni,
    LUNGHEZZA_PLANCK,
    TORSIONE_CRITICA,
    N_SEGMENTI
)


# ============================================================================
# ESEMPIO 1: SIMULAZIONE COSMOLOGICA BASE
# ============================================================================

def esempio_simulazione_cosmologica():
    """
    Simula l'espansione di un universo frattale da condizioni iniziali.
    
    FISICA:
    -------
    - Partenza: 50 solitoni primordiali (gen 0)
    - Evoluzione: 1000 timestep con dt = 0.01 t_Planck
    - Osservabili: N(t), <τ>(t), E_tot(t)
    """
    print("="*70)
    print("ESEMPIO 1: SIMULAZIONE COSMOLOGICA")
    print("="*70)
    
    # Esegui simulazione (salva in HDF5)
    # Questa funzione gestisce tutto: evoluzione + collision detection + telemetria
    simula_universo_frattale(
        n_manifold_iniziali=50,      # Numero di solitoni primordiali
        n_timesteps=1000,              # Durata simulazione
        dt=0.01,                       # Timestep [unità di Planck]
        raggio_congiunzione=10.0 * LUNGHEZZA_PLANCK,  # Soglia distanza per fusione
        n_cores=None,                  # Usa tutti i core CPU disponibili
        file_output="esempio_cosmologia.h5"
    )
    
    # Analizza risultati
    print("\nANALISI RISULTATI:")
    print("-" * 70)
    
    # Leggi dati HDF5
    # Il file contiene: n_manifold(t), torsione_media(t), energia_totale(t)
    with h5py.File("esempio_cosmologia.h5", 'r') as f:
        # Array temporali delle osservabili
        n_manifold = f['n_manifold'][:]          # Numero di solitoni ad ogni step
        torsione_media = f['torsione_media'][:]  # <τ> = (1/N) Σᵢ τᵢ
        energia_totale = f['energia_totale'][:]  # E_tot = Σᵢ (E_cin,i + E_pot,i)
        
        # Leggi metadata
        n_init = f.attrs['n_manifold_iniziali']
        n_steps = f.attrs['n_timesteps']
        dt = f.attrs['dt']
    
    # Calcola statistiche
    n_finale = n_manifold[-1]
    fattore_crescita = n_finale / n_init
    
    print(f"Manifold iniziali: {n_init}")
    print(f"Manifold finali:   {n_finale}")
    print(f"Fattore crescita:  {fattore_crescita:.2f}x")
    print(f"Torsione media finale: {torsione_media[-1]:.4f} (soglia: {TORSIONE_CRITICA:.4f})")
    print(f"Energia finale:    {energia_totale[-1]:.6e}")
    
    # Visualizza grafici
    # Plot 3 pannelli: N(t), <τ>(t), E_tot(t)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    # Asse temporale in unità di Planck
    t_array = np.arange(n_steps) * dt
    
    # PANNELLO 1: Crescita popolazione (N vs t)
    axes[0].plot(t_array, n_manifold, color='blue', linewidth=2)
    axes[0].set_xlabel('Tempo [t_Planck]', fontsize=12)
    axes[0].set_ylabel('N(t)', fontsize=12)
    axes[0].set_title('Crescita Frattale', fontsize=14, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    
    # PANNELLO 2: Torsione media (<τ> vs t)
    axes[1].plot(t_array, torsione_media, color='green', linewidth=2)
    # Linea rossa tratteggiata: soglia critica 4π
    axes[1].axhline(TORSIONE_CRITICA, color='red', linestyle='--', 
                    linewidth=2, label='Soglia Critica (4π)')
    axes[1].set_xlabel('Tempo [t_Planck]', fontsize=12)
    axes[1].set_ylabel('<τ>', fontsize=12)
    axes[1].set_title('Torsione Media', fontsize=14, fontweight='bold')
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3)
    
    # PANNELLO 3: Energia totale (E vs t)
    axes[2].plot(t_array, energia_totale, color='purple', linewidth=2)
    axes[2].set_xlabel('Tempo [t_Planck]', fontsize=12)
    axes[2].set_ylabel('E_tot', fontsize=12)
    axes[2].set_title('Energia Totale', fontsize=14, fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("esempio_cosmologia.png", dpi=150)
    print("\n✓ Grafico salvato in: esempio_cosmologia.png")
    plt.show()


# ============================================================================
# ESEMPIO 2: STUDIO DELLA FISSIONE
# ============================================================================

def esempio_studio_fissione():
    """
    Analizza la dinamica di fissione di un singolo manifold saturo.
    
    FISICA:
    -------
    - Partenza: 1 manifold con τ ≈ 4π (quasi saturo)
    - Evoluzione: fino a fissione
    - Osservabili: τ(t), distribuzione χᵢ, posizioni figli
    """
    print("\n" + "="*70)
    print("ESEMPIO 2: STUDIO DELLA FISSIONE")
    print("="*70)
    
    # Crea manifold con torsione elevata (vicino a saturazione)
    # Configurazione: ampiezza grande con alternanza chiralità
    m = ManifoldBase(id_manifold=1, generazione=0)
    m.chi = np.array([(-1)**i * 5.0 for i in range(N_SEGMENTI)])
    m.vel = np.zeros(N_SEGMENTI)
    m.posizione = np.array([0.0, 0.0, 0.0])
    
    # Calcola torsione iniziale
    m.calcola_torsione_totale()
    
    print(f"\nConfigurazioni iniziale:")
    print(f"  Torsione: {m.torsione:.4f}")
    print(f"  Soglia:   {TORSIONE_CRITICA:.4f}")
    print(f"  Saturato: {m.check_saturazione()}")
    
    # Se non è saturo, aumenta ampiezza fino a saturazione
    # Questo modella l'accumulo di torsione da interazioni esterne
    iterazioni = 0
    while not m.check_saturazione() and iterazioni < 100:
        # Aumenta ampiezza del 10%
        m.chi *= 1.1
        m.calcola_torsione_totale()
        iterazioni += 1
    
    print(f"\nDopo amplificazione (×{1.1**iterazioni:.2f}):")
    print(f"  Torsione: {m.torsione:.4f}")
    print(f"  Saturato: {m.check_saturazione()}")
    
    # ESEGUI FISSIONE
    # Il manifold si divide in due figli A e B
    print("\n" + "-"*70)
    print("ESECUZIONE FISSIONE...")
    print("-"*70)
    
    m_A, m_B = m.fissione()
    
    # Analizza figli
    print(f"\nFiglio A:")
    print(f"  ID:         {m_A.id_manifold}")
    print(f"  Generazione: {m_A.generazione}")
    print(f"  Torsione:   {m_A.torsione:.4f}")
    print(f"  Posizione:  [{m_A.posizione[0]:.2e}, {m_A.posizione[1]:.2e}, {m_A.posizione[2]:.2e}]")
    
    print(f"\nFiglio B:")
    print(f"  ID:         {m_B.id_manifold}")
    print(f"  Generazione: {m_B.generazione}")
    print(f"  Torsione:   {m_B.torsione:.4f}")
    print(f"  Posizione:  [{m_B.posizione[0]:.2e}, {m_B.posizione[1]:.2e}, {m_B.posizione[2]:.2e}]")
    
    # VISUALIZZAZIONE
    # Plot distribuzione χᵢ per parent e figli
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    # Indici segmenti (0-23)
    idx_segmenti = np.arange(N_SEGMENTI)
    
    # PANNELLO 1: Parent
    axes[0].bar(idx_segmenti, m.chi, color='blue', alpha=0.7, edgecolor='black')
    axes[0].axhline(0, color='black', linewidth=1)
    axes[0].set_xlabel('Segmento i', fontsize=12)
    axes[0].set_ylabel('χᵢ', fontsize=12)
    axes[0].set_title(f'Parent (τ={m.torsione:.2f})', fontsize=14, fontweight='bold')
    axes[0].grid(True, alpha=0.3, axis='y')
    
    # PANNELLO 2: Figlio A
    axes[1].bar(idx_segmenti, m_A.chi, color='green', alpha=0.7, edgecolor='black')
    axes[1].axhline(0, color='black', linewidth=1)
    axes[1].set_xlabel('Segmento i', fontsize=12)
    axes[1].set_ylabel('χᵢ', fontsize=12)
    axes[1].set_title(f'Figlio A (τ={m_A.torsione:.2f})', fontsize=14, fontweight='bold')
    axes[1].grid(True, alpha=0.3, axis='y')
    
    # PANNELLO 3: Figlio B
    axes[2].bar(idx_segmenti, m_B.chi, color='red', alpha=0.7, edgecolor='black')
    axes[2].axhline(0, color='black', linewidth=1)
    axes[2].set_xlabel('Segmento i', fontsize=12)
    axes[2].set_ylabel('χᵢ', fontsize=12)
    axes[2].set_title(f'Figlio B (τ={m_B.torsione:.2f})', fontsize=14, fontweight='bold')
    axes[2].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig("esempio_fissione.png", dpi=150)
    print("\n✓ Grafico salvato in: esempio_fissione.png")
    plt.show()


# ============================================================================
# ESEMPIO 3: STUDIO DELLA CONGIUNZIONE
# ============================================================================

def esempio_studio_congiunzione():
    """
    Analizza la fusione di due manifold con chiralità opposte.
    
    FISICA:
    -------
    - Partenza: 2 manifold con χ_A ≈ -χ_B (chiralità opposte)
    - Distanza: piccola (~ 5 L_Planck)
    - Osservabili: accoppiamento emergente, stato post-fusione
    """
    print("\n" + "="*70)
    print("ESEMPIO 3: STUDIO DELLA CONGIUNZIONE")
    print("="*70)
    
    # Crea primo manifold (chiralità positiva dominante)
    # χᵢ = +1 per i pari, -1 per i dispari → alternanza con bias positivo
    m1 = ManifoldBase(id_manifold=1, generazione=0)
    m1.chi = np.array([2.0 if i % 2 == 0 else -1.0 for i in range(N_SEGMENTI)])
    m1.vel = np.zeros(N_SEGMENTI)
    m1.posizione = np.array([0.0, 0.0, 0.0])
    
    # Crea secondo manifold (chiralità opposta al primo)
    # χᵢ = -χ_1,i → chiralità perfettamente opposta
    m2 = ManifoldBase(id_manifold=2, generazione=0)
    m2.chi = -m1.chi
    m2.vel = np.zeros(N_SEGMENTI)
    # Posizione vicina (5 lunghezze di Planck lungo asse X)
    m2.posizione = np.array([5.0 * LUNGHEZZA_PLANCK, 0.0, 0.0])
    
    print(f"\nManifold 1:")
    print(f"  <χ>:      {np.mean(m1.chi):.4f}")
    print(f"  σ(χ):     {np.std(m1.chi):.4f}")
    print(f"  Posizione: [{m1.posizione[0]:.2e}, {m1.posizione[1]:.2e}, {m1.posizione[2]:.2e}]")
    
    print(f"\nManifold 2:")
    print(f"  <χ>:      {np.mean(m2.chi):.4f}")
    print(f"  σ(χ):     {np.std(m2.chi):.4f}")
    print(f"  Posizione: [{m2.posizione[0]:.2e}, {m2.posizione[1]:.2e}, {m2.posizione[2]:.2e}]")
    
    # CALCOLO ACCOPPIAMENTO EMERGENTE
    # A_12 = correlazione(χ_1, χ_2) × exp(-d_12 / λ)
    accoppiamento = m1.calcola_accoppiamento(m2)
    
    print(f"\nAccoppiamento emergente:")
    print(f"  A_12 = {accoppiamento:.6f}")
    print(f"  Segno: {'ATTRAZIONE (chiralità opposte)' if accoppiamento < 0 else 'REPULSIONE (chiralità allineate)'}")
    
    # Verifica simmetria A_12 = A_21
    accoppiamento_inv = m2.calcola_accoppiamento(m1)
    print(f"  A_21 = {accoppiamento_inv:.6f}")
    print(f"  Simmetria: {'✓ OK' if np.isclose(accoppiamento, accoppiamento_inv) else '✗ VIOLATA'}")
    
    # ESEGUI CONGIUNZIONE
    # Solo se accoppiamento supera soglia
    from WQT_manifold_refactored import RISONANZA_MINIMA
    
    if abs(accoppiamento) > RISONANZA_MINIMA:
        print(f"\n✓ Risonanza sufficiente (|A| = {abs(accoppiamento):.4f} > {RISONANZA_MINIMA})")
        print("-"*70)
        print("ESECUZIONE CONGIUNZIONE...")
        print("-"*70)
        
        # Fusione
        m_fuso = m1.congiungi(m2)
        
        print(f"\nManifold fuso:")
        print(f"  ID:         {m_fuso.id_manifold} (somma: {m1.id_manifold} + {m2.id_manifold})")
        print(f"  Generazione: {m_fuso.generazione}")
        print(f"  <χ>:        {np.mean(m_fuso.chi):.4f}")
        print(f"  σ(χ):       {np.std(m_fuso.chi):.4f}")
        print(f"  Torsione:   {m_fuso.torsione:.4f}")
        
        # VISUALIZZAZIONE
        # Plot χᵢ per i tre manifold
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        
        idx = np.arange(N_SEGMENTI)
        
        # Manifold 1
        axes[0].bar(idx, m1.chi, color='blue', alpha=0.7, edgecolor='black')
        axes[0].axhline(0, color='black', linewidth=1)
        axes[0].set_xlabel('Segmento i')
        axes[0].set_ylabel('χᵢ')
        axes[0].set_title('Manifold 1', fontweight='bold')
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # Manifold 2
        axes[1].bar(idx, m2.chi, color='red', alpha=0.7, edgecolor='black')
        axes[1].axhline(0, color='black', linewidth=1)
        axes[1].set_xlabel('Segmento i')
        axes[1].set_ylabel('χᵢ')
        axes[1].set_title('Manifold 2 (opposto)', fontweight='bold')
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Manifold fuso
        axes[2].bar(idx, m_fuso.chi, color='purple', alpha=0.7, edgecolor='black')
        axes[2].axhline(0, color='black', linewidth=1)
        axes[2].set_xlabel('Segmento i')
        axes[2].set_ylabel('χᵢ')
        axes[2].set_title('Manifold Fuso (annichilazione)', fontweight='bold')
        axes[2].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig("esempio_congiunzione.png", dpi=150)
        print("\n✓ Grafico salvato in: esempio_congiunzione.png")
        plt.show()
        
    else:
        print(f"\n✗ Risonanza insufficiente (|A| = {abs(accoppiamento):.4f} < {RISONANZA_MINIMA})")
        print("  Congiunzione NON avviene.")


# ============================================================================
# ESEMPIO 4: BENCHMARK PARALLELIZZAZIONE
# ============================================================================

def esempio_benchmark_parallelizzazione():
    """
    Misura lo speedup della parallelizzazione su multi-core.
    
    ARCHITETTURA:
    -------------
    - Confronta tempo seriale (1 core) vs parallelo (N cores)
    - Calcola speedup = T_seriale / T_parallelo
    - Identifica numero ottimale di core
    """
    import time
    import multiprocessing as mp
    
    print("\n" + "="*70)
    print("ESEMPIO 4: BENCHMARK PARALLELIZZAZIONE")
    print("="*70)
    
    # Numero di core disponibili
    n_cores_max = mp.cpu_count()
    print(f"\nCore CPU disponibili: {n_cores_max}")
    
    # Crea lista di manifold per test
    n_manifold = 100
    print(f"Manifold da evolvere: {n_manifold}")
    
    np.random.seed(42)  # Riproducibilità
    lista_manifold = []
    for i in range(n_manifold):
        m = ManifoldBase(id_manifold=i, generazione=0)
        m.chi = np.random.randn(N_SEGMENTI)
        m.vel = np.random.randn(N_SEGMENTI) * 0.1
        lista_manifold.append(m)
    
    dt = 0.01
    
    # TEST SERIALE (1 core)
    print("\n" + "-"*70)
    print("TEST SERIALE (1 core)...")
    print("-"*70)
    
    lista_test = [ManifoldBase(chi=m.chi.copy(), vel=m.vel.copy(), 
                                id_manifold=m.id_manifold) 
                  for m in lista_manifold]
    
    t_start = time.time()
    lista_test = evolvi_sistema_parallelo(lista_test, dt, n_cores=1)
    t_seriale = time.time() - t_start
    
    print(f"Tempo: {t_seriale:.4f} s")
    
    # TEST PARALLELO (tutti i core)
    print("\n" + "-"*70)
    print(f"TEST PARALLELO ({n_cores_max} cores)...")
    print("-"*70)
    
    lista_test = [ManifoldBase(chi=m.chi.copy(), vel=m.vel.copy(), 
                                id_manifold=m.id_manifold) 
                  for m in lista_manifold]
    
    t_start = time.time()
    lista_test = evolvi_sistema_parallelo(lista_test, dt, n_cores=n_cores_max)
    t_parallelo = time.time() - t_start
    
    print(f"Tempo: {t_parallelo:.4f} s")
    
    # ANALISI SPEEDUP
    speedup = t_seriale / t_parallelo
    efficienza = speedup / n_cores_max
    
    print("\n" + "="*70)
    print("RISULTATI BENCHMARK")
    print("="*70)
    print(f"Tempo seriale:    {t_seriale:.4f} s")
    print(f"Tempo parallelo:  {t_parallelo:.4f} s")
    print(f"Speedup:          {speedup:.2f}x")
    print(f"Efficienza:       {efficienza*100:.1f}%")
    print(f"Speedup ideale:   {n_cores_max}x")
    print(f"Overhead:         {(1 - efficienza)*100:.1f}%")
    
    if efficienza > 0.8:
        print("\n✓ Eccellente scalabilità (efficienza > 80%)")
    elif efficienza > 0.6:
        print("\n✓ Buona scalabilità (efficienza > 60%)")
    else:
        print("\n⚠  Scalabilità limitata (overhead significativo)")
        print("  → Aumentare n_manifold per ammortizzare overhead comunicazione")


# ============================================================================
# MENU PRINCIPALE
# ============================================================================

def menu_principale():
    """Menu interattivo per scegliere quale esempio eseguire."""
    print("\n" + "="*70)
    print("ESEMPI D'USO - WQT_MANIFOLD REFACTORED")
    print("="*70)
    print("\nScegli un esempio da eseguire:")
    print("  1. Simulazione cosmologica (crescita frattale)")
    print("  2. Studio della fissione (mitosi topologica)")
    print("  3. Studio della congiunzione (fusione solitoni)")
    print("  4. Benchmark parallelizzazione (speedup multi-core)")
    print("  5. Esegui TUTTI gli esempi")
    print("  0. Esci")
    
    while True:
        try:
            scelta = input("\nInserisci numero (0-5): ").strip()
            
            if scelta == '1':
                esempio_simulazione_cosmologica()
                break
            elif scelta == '2':
                esempio_studio_fissione()
                break
            elif scelta == '3':
                esempio_studio_congiunzione()
                break
            elif scelta == '4':
                esempio_benchmark_parallelizzazione()
                break
            elif scelta == '5':
                print("\nESECUZIONE DI TUTTI GLI ESEMPI...\n")
                esempio_simulazione_cosmologica()
                esempio_studio_fissione()
                esempio_studio_congiunzione()
                esempio_benchmark_parallelizzazione()
                print("\n" + "="*70)
                print("TUTTI GLI ESEMPI COMPLETATI")
                print("="*70)
                break
            elif scelta == '0':
                print("\nUscita.")
                break
            else:
                print("Scelta non valida. Riprova.")
        except KeyboardInterrupt:
            print("\n\nInterrotto dall'utente.")
            break


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Esegui menu interattivo
    menu_principale()
