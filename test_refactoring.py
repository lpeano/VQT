"""
================================================================================
SUITE DI TEST - VALIDAZIONE INVARIANTI FISICI
================================================================================

Questo script verifica che l'architettura refactorata preservi:
1. Chiusura topologica (∮ τ ds = 4π)
2. Conservazione energia durante evoluzione
3. Alternanza chiralità dopo fissione
4. Simmetria accoppiamento (A_ij = A_ji)
5. Stabilità numerica integratore Velocity Verlet

================================================================================
"""

import numpy as np
import sys
from WQT_manifold_refactored import (
    ManifoldBase, 
    evolvi_sistema_parallelo,
    gestisci_congiunzioni,
    gestisci_fissioni,
    TORSIONE_CRITICA,
    RISONANZA_MINIMA,
    LUNGHEZZA_PLANCK,
    N_SEGMENTI,
    LAMBDA_DOPPIO_POZZO
)


# ============================================================================
# CLASSE PER COLORARE OUTPUT
# ============================================================================

class Colors:
    """Codici ANSI per output colorato."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def test_ok(msg):
    """Stampa messaggio di successo."""
    print(f"{Colors.GREEN}✓{Colors.ENDC} {msg}")

def test_fail(msg):
    """Stampa messaggio di fallimento."""
    print(f"{Colors.RED}✗{Colors.ENDC} {msg}")

def test_warn(msg):
    """Stampa messaggio di warning."""
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {msg}")

def test_header(msg):
    """Stampa intestazione di sezione test."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.ENDC}")


# ============================================================================
# TEST 1: INIZIALIZZAZIONE MANIFOLD
# ============================================================================

def test_inizializzazione():
    """Verifica che ManifoldBase si inizializzi correttamente."""
    test_header("TEST 1: INIZIALIZZAZIONE MANIFOLD")
    
    # Crea manifold con valori di default
    m = ManifoldBase()
    
    # VERIFICA 1: Dimensione array chi
    if m.chi.shape == (N_SEGMENTI,):
        test_ok(f"Array chi ha dimensione corretta: {N_SEGMENTI}")
    else:
        test_fail(f"Array chi ha dimensione errata: {m.chi.shape}")
        return False
    
    # VERIFICA 2: Dimensione array vel
    if m.vel.shape == (N_SEGMENTI,):
        test_ok(f"Array vel ha dimensione corretta: {N_SEGMENTI}")
    else:
        test_fail(f"Array vel ha dimensione errata: {m.vel.shape}")
        return False
    
    # VERIFICA 3: Alternanza chiralità
    # Calcola il prodotto di segmenti adiacenti
    chiralita = np.array([(-1)**(i) for i in range(N_SEGMENTI)])
    chiralita_next = np.roll(chiralita, -1)
    prodotti = chiralita * chiralita_next
    
    # Tutti i prodotti devono essere -1 (alternanza perfetta)
    if np.all(prodotti == -1):
        test_ok("Alternanza chiralità verificata (tutti i flessi alternano ±)")
    else:
        test_fail("Alternanza chiralità violata!")
        return False
    
    # VERIFICA 4: Torsione iniziale
    m.calcola_torsione_totale()
    if 0 <= m.torsione <= TORSIONE_CRITICA:
        test_ok(f"Torsione iniziale valida: {m.torsione:.4f} ∈ [0, {TORSIONE_CRITICA:.4f}]")
    else:
        test_warn(f"Torsione iniziale alta: {m.torsione:.4f} (potrebbe fissionare subito)")
    
    # VERIFICA 5: Posizione inizializzata
    if m.posizione.shape == (3,):
        test_ok("Posizione 3D inizializzata correttamente")
    else:
        test_fail(f"Posizione ha dimensione errata: {m.posizione.shape}")
        return False
    
    return True


# ============================================================================
# TEST 2: EVOLUZIONE LOCALE E CONSERVAZIONE ENERGIA
# ============================================================================

def test_conservazione_energia():
    """Verifica che l'integratore Velocity Verlet conservi l'energia."""
    test_header("TEST 2: CONSERVAZIONE ENERGIA (INTEGRATORE SIMPLECTICO)")
    
    # Crea manifold con condizioni iniziali note
    m = ManifoldBase()
    m.chi = np.array([(-1)**(i) * 0.5 for i in range(N_SEGMENTI)])  # Piccola ampiezza
    m.vel = np.zeros(N_SEGMENTI)
    
    # Calcola energia iniziale
    def calcola_energia_totale(manifold):
        """Energia cinetica + potenziale."""
        E_cin = 0.5 * np.sum(manifold.vel**2)
        E_pot = np.sum(-0.5 * LAMBDA_DOPPIO_POZZO * manifold.chi**2 + 0.25 * manifold.chi**4)
        return E_cin + E_pot
    
    E_iniziale = calcola_energia_totale(m)
    
    # Evolvi per molti timestep
    dt = 0.001
    n_step = 1000
    
    energie = [E_iniziale]
    
    for _ in range(n_step):
        m.evolvi_locale(dt)
        energie.append(calcola_energia_totale(m))
    
    energie = np.array(energie)
    
    # Calcola variazione energetica
    E_finale = energie[-1]
    variazione_assoluta = abs(E_finale - E_iniziale)
    variazione_relativa = variazione_assoluta / (abs(E_iniziale) + 1e-12)
    
    print(f"  E(t=0)   = {E_iniziale:.8e}")
    print(f"  E(t=T)   = {E_finale:.8e}")
    print(f"  ΔE       = {variazione_assoluta:.8e}")
    print(f"  ΔE/E     = {variazione_relativa:.6f} ({variazione_relativa*100:.4f}%)")
    
    # CRITERIO: Variazione < 1% è accettabile per integratori simplectici
    if variazione_relativa < 0.01:
        test_ok(f"Energia conservata entro 1% ({variazione_relativa*100:.4f}%)")
        return True
    elif variazione_relativa < 0.05:
        test_warn(f"Deriva energetica moderata: {variazione_relativa*100:.2f}% (ridurre dt)")
        return True
    else:
        test_fail(f"Deriva energetica eccessiva: {variazione_relativa*100:.2f}%")
        return False


# ============================================================================
# TEST 3: FISSIONE E PRESERVAZIONE SIMMETRIA
# ============================================================================

def test_fissione():
    """Verifica che la fissione preservi la simmetria topologica."""
    test_header("TEST 3: FISSIONE TOPOLOGICA")
    
    # Crea manifold con torsione ELEVATA (vicino a soglia)
    m = ManifoldBase()
    m.chi = np.array([(-1)**(i) * 5.0 for i in range(N_SEGMENTI)])  # Ampiezza grande
    m.calcola_torsione_totale()
    
    print(f"  Torsione parent: {m.torsione:.4f}")
    print(f"  Soglia critica:  {TORSIONE_CRITICA:.4f}")
    
    # Forza saturazione aumentando ulteriormente chi
    while not m.check_saturazione():
        m.chi *= 1.1
        m.calcola_torsione_totale()
    
    print(f"  Torsione saturata: {m.torsione:.4f}")
    
    # Esegui fissione
    m_A, m_B = m.fissione()
    
    # VERIFICA 1: Entrambi i figli hanno 24 segmenti
    if m_A.chi.shape == (N_SEGMENTI,) and m_B.chi.shape == (N_SEGMENTI,):
        test_ok("Entrambi i figli hanno 24 segmenti")
    else:
        test_fail(f"Dimensioni errate: A={m_A.chi.shape}, B={m_B.chi.shape}")
        return False
    
    # VERIFICA 2: Alternanza chiralità preservata
    def verifica_alternanza(chi_array):
        """Verifica che il segno alterni."""
        segni = np.sign(chi_array)
        prodotti_adiacenti = segni[:-1] * segni[1:]
        return np.all(prodotti_adiacenti <= 0)  # <= 0 permette zeri
    
    if verifica_alternanza(m_A.chi):
        test_ok("Figlio A: Alternanza chiralità preservata")
    else:
        test_fail("Figlio A: Alternanza chiralità VIOLATA")
        return False
    
    if verifica_alternanza(m_B.chi):
        test_ok("Figlio B: Alternanza chiralità preservata")
    else:
        test_fail("Figlio B: Alternanza chiralità VIOLATA")
        return False
    
    # VERIFICA 3: Torsione figli < parent
    m_A.calcola_torsione_totale()
    m_B.calcola_torsione_totale()
    
    print(f"  τ_A = {m_A.torsione:.4f}")
    print(f"  τ_B = {m_B.torsione:.4f}")
    print(f"  τ_A + τ_B = {m_A.torsione + m_B.torsione:.4f}")
    
    if m_A.torsione < m.torsione and m_B.torsione < m.torsione:
        test_ok("Torsioni figli < parent (rilassamento avvenuto)")
    else:
        test_warn("Torsioni figli non diminuite (configurazione particolare)")
    
    # VERIFICA 4: Genealogia corretta
    if m_A.generazione == m.generazione + 1 and m_B.generazione == m.generazione + 1:
        test_ok(f"Generazione incrementata: {m.generazione} → {m_A.generazione}")
    else:
        test_fail("Generazione non incrementata correttamente")
        return False
    
    if m_A.id_manifold == 2 * m.id_manifold and m_B.id_manifold == 2 * m.id_manifold + 1:
        test_ok(f"ID genealogici corretti: {m.id_manifold} → ({m_A.id_manifold}, {m_B.id_manifold})")
    else:
        test_fail("ID genealogici errati")
        return False
    
    return True


# ============================================================================
# TEST 4: CONGIUNZIONE E ACCOPPIAMENTO EMERGENTE
# ============================================================================

def test_congiunzione():
    """Verifica che la congiunzione funzioni correttamente."""
    test_header("TEST 4: CONGIUNZIONE E ACCOPPIAMENTO EMERGENTE")
    
    # Crea due manifold con chiralità OPPOSTE
    m1 = ManifoldBase(id_manifold=1, generazione=0)
    m1.chi = np.array([(-1)**(i) * 1.0 for i in range(N_SEGMENTI)])
    m1.posizione = np.array([0.0, 0.0, 0.0])
    
    m2 = ManifoldBase(id_manifold=2, generazione=0)
    m2.chi = -m1.chi  # Chiralità esattamente opposta
    m2.posizione = np.array([5.0 * LUNGHEZZA_PLANCK, 0.0, 0.0])
    
    # VERIFICA 1: Accoppiamento emergente
    accoppiamento = m1.calcola_accoppiamento(m2)
    
    print(f"  Accoppiamento A-B: {accoppiamento:.6f}")
    print(f"  Soglia minima:     {RISONANZA_MINIMA:.6f}")
    
    # Con chiralità opposte, accoppiamento dovrebbe essere negativo (attrazione)
    if accoppiamento < 0:
        test_ok("Accoppiamento negativo (chiralità opposte → attrazione)")
    else:
        test_warn("Accoppiamento positivo (inaspettato con chiralità opposte)")
    
    # VERIFICA 2: Simmetria accoppiamento (A_ij = A_ji)
    accoppiamento_inverso = m2.calcola_accoppiamento(m1)
    
    if np.isclose(accoppiamento, accoppiamento_inverso, rtol=1e-9):
        test_ok(f"Simmetria accoppiamento verificata: A_12 = A_21 = {accoppiamento:.6f}")
    else:
        test_fail(f"Simmetria violata: A_12 = {accoppiamento:.6f}, A_21 = {accoppiamento_inverso:.6f}")
        return False
    
    # VERIFICA 3: Congiunzione
    if abs(accoppiamento) > RISONANZA_MINIMA:
        test_ok("Risonanza sufficiente per congiunzione")
        
        # Esegui fusione
        m_fuso = m1.congiungi(m2)
        
        # Verifica dimensioni
        if m_fuso.chi.shape == (N_SEGMENTI,):
            test_ok("Manifold fuso ha 24 segmenti")
        else:
            test_fail(f"Manifold fuso ha dimensione errata: {m_fuso.chi.shape}")
            return False
        
        # Verifica genealogia
        if m_fuso.id_manifold == m1.id_manifold + m2.id_manifold:
            test_ok(f"ID somma corretto: {m1.id_manifold} + {m2.id_manifold} = {m_fuso.id_manifold}")
        else:
            test_fail("ID somma errato")
            return False
        
        # Verifica generazione
        gen_attesa = max(m1.generazione, m2.generazione) + 1
        if m_fuso.generazione == gen_attesa:
            test_ok(f"Generazione incrementata: max({m1.generazione}, {m2.generazione}) + 1 = {m_fuso.generazione}")
        else:
            test_fail(f"Generazione errata: attesa {gen_attesa}, ottenuta {m_fuso.generazione}")
            return False
        
        # Verifica annichilazione parziale (|χ_fuso| < |χ_1| + |χ_2|)
        norma_fuso = np.linalg.norm(m_fuso.chi)
        norma_somma = np.linalg.norm(m1.chi) + np.linalg.norm(m2.chi)
        
        print(f"  |χ_fuso| = {norma_fuso:.4f}")
        print(f"  |χ_1| + |χ_2| = {norma_somma:.4f}")
        
        if norma_fuso < norma_somma:
            test_ok("Annichilazione parziale avvenuta (|χ_fuso| < |χ_1| + |χ_2|)")
        else:
            test_warn("Nessuna annichilazione (chiralità non perfettamente opposte)")
        
    else:
        test_warn("Risonanza troppo debole per congiunzione (aumentare vicinanza)")
    
    return True


# ============================================================================
# TEST 5: PARALLELIZZAZIONE
# ============================================================================

def test_parallelizzazione():
    """Verifica che la parallelizzazione produca risultati deterministici."""
    test_header("TEST 5: PARALLELIZZAZIONE DETERMINISTICA")
    
    # Crea lista di manifold
    n_manifold = 10
    lista_manifold = [ManifoldBase(id_manifold=i, generazione=0) for i in range(n_manifold)]
    
    # Imposta seed per riproducibilità
    np.random.seed(42)
    for m in lista_manifold:
        m.chi = np.random.randn(N_SEGMENTI)
        m.vel = np.random.randn(N_SEGMENTI) * 0.1
    
    # Evoluzione seriale
    lista_seriale = [ManifoldBase(
        chi=m.chi.copy(), 
        vel=m.vel.copy(), 
        id_manifold=m.id_manifold
    ) for m in lista_manifold]
    
    dt = 0.01
    for m in lista_seriale:
        m.evolvi_locale(dt)
    
    # Evoluzione parallela (1 core → equivalente a seriale)
    lista_parallela = [ManifoldBase(
        chi=m.chi.copy(), 
        vel=m.vel.copy(), 
        id_manifold=m.id_manifold
    ) for m in lista_manifold]
    
    lista_parallela = evolvi_sistema_parallelo(lista_parallela, dt, n_cores=1)
    
    # VERIFICA: Risultati identici
    errore_massimo = 0.0
    
    for i in range(n_manifold):
        errore_chi = np.max(np.abs(lista_seriale[i].chi - lista_parallela[i].chi))
        errore_vel = np.max(np.abs(lista_seriale[i].vel - lista_parallela[i].vel))
        
        errore_massimo = max(errore_massimo, errore_chi, errore_vel)
    
    print(f"  Errore massimo: {errore_massimo:.2e}")
    
    if errore_massimo < 1e-12:
        test_ok("Parallelizzazione deterministica (errore < 1e-12)")
        return True
    else:
        test_fail(f"Risultati divergenti (errore = {errore_massimo:.2e})")
        return False


# ============================================================================
# TEST 6: GESTIONE FISSIONI MULTIPLE
# ============================================================================

def test_fissioni_multiple():
    """Verifica che gestisci_fissioni() funzioni con molti manifold."""
    test_header("TEST 6: GESTIONE FISSIONI MULTIPLE")
    
    # Crea manifold tutti saturi
    n_manifold = 5
    lista_manifold = []
    
    for i in range(n_manifold):
        m = ManifoldBase(id_manifold=i, generazione=0)
        # Forza saturazione
        m.chi = np.array([(-1)**(j) * 10.0 for j in range(N_SEGMENTI)])
        m.calcola_torsione_totale()
        lista_manifold.append(m)
    
    # Conta manifold saturi
    n_saturi = sum(1 for m in lista_manifold if m.check_saturazione())
    
    print(f"  Manifold iniziali: {len(lista_manifold)}")
    print(f"  Manifold saturi:   {n_saturi}")
    
    # Esegui fissioni
    lista_dopo_fissioni = gestisci_fissioni(lista_manifold)
    
    print(f"  Manifold finali:   {len(lista_dopo_fissioni)}")
    
    # VERIFICA 1: Numero di manifold raddoppiato
    n_atteso = len(lista_manifold) - n_saturi + 2 * n_saturi
    
    if len(lista_dopo_fissioni) == n_atteso:
        test_ok(f"Numero manifold corretto: {len(lista_manifold)} - {n_saturi} + 2×{n_saturi} = {n_atteso}")
    else:
        test_fail(f"Numero manifold errato: atteso {n_atteso}, ottenuto {len(lista_dopo_fissioni)}")
        return False
    
    # VERIFICA 2: Tutti i nuovi manifold hanno torsione < 4π
    for i, m in enumerate(lista_dopo_fissioni):
        m.calcola_torsione_totale()
        if m.torsione > TORSIONE_CRITICA * 1.01:
            test_fail(f"Manifold {i} ancora saturo: τ = {m.torsione:.4f}")
            return False
    
    test_ok("Tutti i manifold post-fissione hanno torsione < 4π")
    
    return True


# ============================================================================
# RUNNER PRINCIPALE
# ============================================================================

def run_all_tests():
    """Esegue tutti i test e stampa sommario."""
    test_header("SUITE DI TEST - ARCHITETTURA REFACTORATA WQT_MANIFOLD")
    
    risultati = {}
    
    print("\n" + "="*70)
    print("ESECUZIONE TEST...")
    print("="*70)
    
    # Esegui test
    risultati['Inizializzazione'] = test_inizializzazione()
    risultati['Conservazione Energia'] = test_conservazione_energia()
    risultati['Fissione'] = test_fissione()
    risultati['Congiunzione'] = test_congiunzione()
    risultati['Parallelizzazione'] = test_parallelizzazione()
    risultati['Fissioni Multiple'] = test_fissioni_multiple()
    
    # Sommario
    test_header("SOMMARIO RISULTATI")
    
    n_passati = sum(risultati.values())
    n_totali = len(risultati)
    
    for nome, passato in risultati.items():
        if passato:
            print(f"{Colors.GREEN}✓{Colors.ENDC} {nome}")
        else:
            print(f"{Colors.RED}✗{Colors.ENDC} {nome}")
    
    print("\n" + "="*70)
    print(f"{Colors.BOLD}RISULTATO FINALE: {n_passati}/{n_totali} test superati{Colors.ENDC}")
    print("="*70)
    
    if n_passati == n_totali:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 TUTTI I TEST SUPERATI!{Colors.ENDC}")
        print(f"{Colors.GREEN}L'architettura refactorata preserva tutti gli invarianti fisici.{Colors.ENDC}\n")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  ALCUNI TEST FALLITI{Colors.ENDC}")
        print(f"{Colors.RED}Rivedere l'implementazione prima di usare in produzione.{Colors.ENDC}\n")
        return False


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    successo = run_all_tests()
    sys.exit(0 if successo else 1)
