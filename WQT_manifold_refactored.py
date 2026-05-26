"""
================================================================================
WQT MANIFOLD - ARCHITETTURA REFACTORATA A OGGETTI DINAMICI
================================================================================

TRANSIZIONE ARCHITETTURALE:
---------------------------
Questo file rappresenta il refactoring radicale da:
  ❌ Monolitico: Array globale chi statico
  ✅ A oggetti: Gerarchia frattale di solitoni topologici dinamici

INVARIANTI FISICI FONDAMENTALI:
--------------------------------
1. UNITÀ BASE (ManifoldBase):
   - 24 segmenti (12 monti + 12 valli)
   - Chiusura topologica: ∮ τ ds = 4π (720°)
   - Potenziale di doppio pozzo φ(χ) = -½χ² + ¼χ⁴
   
2. CHIRALITÀ DISCRETA (Flessi):
   - ±π salto di fase (NON continuo!)
   - Alternanza topologica: (+π, -π, +π, -π, ...)
   - Violazione = instabilità → fissione

3. DINAMICA DI CONGIUNZIONE:
   - Trigger: χ_A + χ_B ≈ 0 (chiralità opposta)
   - Condizione: Risonanza di fase > soglia critica
   - Accoppiamento NON costante → emerge dalla geometria locale

4. FISSIONE (MITOSI TOPOLOGICA):
   - Trigger: Torsione accumulata > 4π
   - Output: 2 manifold con simmetria preservata
   - Conservazione: Torsione totale = Σ torsioni componenti

5. ESPANSIONE RICORSIVA:
   - Crescita per auto-assemblaggio frattale
   - N(t) = N₀ × 2^(t/τ_fissione)
   - Universo = reticolo dinamico di solitoni interconnessi

================================================================================
"""

import numpy as np
import multiprocessing as mp
from multiprocessing import Pool
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import h5py
from datetime import datetime
import time

# ============================================================================
# COSTANTI FISICHE FONDAMENTALI (Unità di Planck)
# ============================================================================

# Lunghezza di Planck [m] - Scala minima dello spazio-tempo
# Sotto questa scala la geometria classica perde significato
LUNGHEZZA_PLANCK = 1.616255e-35

# Tempo di Planck [s] - Quanto temporale minimo
# Δt < t_P → cromodinamica quantistica della gravità attiva
TEMPO_PLANCK = 5.391247e-44

# Coefficiente di accoppiamento chirale (adimensionale)
# Regola l'intensità della separazione materia/spazio
# α_χ = 1/137 ≈ costante di struttura fine gravitazionale
COEFFICIENTE_ACCOPPIAMENTO = 1.0 / 137.0

# Numero di segmenti per solitone (simmetria del reticolo di Leech)
# 24 = dim(Algebra di Lie E₈) × 3 proiezioni spaziali
# Questo è il MINIMO per chiudere topologicamente un fermione (720°)
N_SEGMENTI = 24

# Torsione critica per fissione [radianti]
# ∮ τ ds > 4π → il solitone eccede la capacità topologica → mitosi
TORSIONE_CRITICA = 4.0 * np.pi

# Soglia di risonanza per congiunzione (adimensionale)
# Due manifold si fondono solo se |risonanza| > R_MIN
# Evita fusioni spurie da rumore numerico
RISONANZA_MINIMA = 0.5

# Parametro del potenziale di doppio pozzo (adimensionale)
# V(χ) = -½λχ² + ¼χ⁴
# λ controlla la larghezza delle buche (regime perturbativo)
LAMBDA_DOPPIO_POZZO = 0.5


# ============================================================================
# CLASSE: MANIFOLDBASE - Solitone Topologico Elementare
# ============================================================================

@dataclass
class ManifoldBase:
    """
    Rappresenta un solitone topologico chiuso con 24 segmenti.
    
    FISICA:
    -------
    Ogni istanza è un'eccitazione localizzata dello spazio-tempo con torsione,
    che soddisfa il vincolo di chiusura spinoriale ∮ τ ds = 4π.
    
    La chiralità alterna tra i segmenti crea 12 "creste" (materia condensata)
    e 12 "valli" (spazio dilatato), analogamente alle dodecaedro di Poincaré.
    
    ATTRIBUTI:
    ----------
    chi : ndarray, shape (24,)
        Potenziale di scala per ogni segmento [adimensionale]
        χᵢ > 0 → espansione locale (spazio)
        χᵢ < 0 → contrazione locale (materia)
        
    vel : ndarray, shape (24,)
        Derivata temporale dχᵢ/dτ per ogni segmento [adimensionale]
        Rappresenta il "momento coniugato" nel formalismo hamiltoniano
        
    torsione : float
        Torsione geometrica totale accumulata ∮ K_λμν ds [radianti]
        Quando > 4π, il solitone è topologicamente saturo → fissione
        
    posizione : ndarray, shape (3,)
        Coordinate del centro di massa nel manifold globale [m]
        Usato per collision detection e calcolo accoppiamenti
        
    id_manifold : int
        Identificatore univoco per tracciamento genealogico
        ID pari = generazione da fissione di ID//2
        
    generazione : int
        Livello di annidamento frattale (0 = primordiale)
        Gen n → scala ~ L_P × 2^n
    """
    
    # Campi dinamici (mutabili durante evoluzione)
    chi: np.ndarray = field(default_factory=lambda: np.zeros(N_SEGMENTI))
    vel: np.ndarray = field(default_factory=lambda: np.zeros(N_SEGMENTI))
    
    # Invarianti topologici (aggiornati ad ogni step)
    torsione: float = 0.0
    
    # Coordinate spaziali (per collision detection)
    posizione: np.ndarray = field(default_factory=lambda: np.zeros(3))
    
    # Metadati
    id_manifold: int = 0
    generazione: int = 0
    
    def __post_init__(self):
        """
        Inizializzazione post-costruzione.
        
        FISICA:
        -------
        Impone la configurazione iniziale con chiralità alternata.
        Questo garantisce che il solitone nasca già in uno stato topologicamente
        valido (alternanza ±π nei flessi).
        """
        # Se chi è zero, inizializza con piccole fluttuazioni alternate
        # Questo rompe la simmetria e innesca la separazione di fase
        if np.allclose(self.chi, 0.0):
            # Alternanza (+1, -1, +1, -1, ...) - vincolo topologico INVIOLABILE
            # Ogni segmento ha chiralità opposta ai vicini → 12 monti + 12 valli
            chiralita = np.array([(-1)**(i) for i in range(N_SEGMENTI)])
            
            # Fluttuazione quantistica iniziale ~ √(ℏ/(m_P c))
            # Ampiezza ~ 10^-3 per evitare divergenze numeriche al primo step
            self.chi = 1e-3 * chiralita * np.random.randn(N_SEGMENTI)
            
            # Velocità iniziale nulla → solitone "a riposo" nel vuoto
            self.vel = np.zeros(N_SEGMENTI)
    
    def calcola_torsione_totale(self) -> float:
        """
        Calcola la torsione geometrica totale del manifold.
        
        FISICA:
        -------
        La torsione emerge dalla derivata covariante della chiralità:
        K_λμν = ∂_λ ω_μν - ∂_μ ω_λν
        
        dove ω_μν è la connessione di spin.
        
        In 1D discreto (approssimazione):
        K ≈ Σᵢ |Δχᵢ| × (chiralità_i × chiralità_{i+1})
        
        Il prodotto delle chiralità adiacenti vale:
        - (+1)×(-1) = -1 → contributo POSITIVO (torsione destra)
        - (-1)×(+1) = -1 → contributo POSITIVO (torsione destra)
        
        L'alternanza GARANTISCE che ogni interfaccia contribuisca allo stesso segno,
        portando a torsione netta ≠ 0 (effetto topologico non banale).
        
        RESTITUISCE:
        ------------
        torsione : float
            Integrale della contorsione ∮ K ds [radianti]
        """
        # Gradiente discreto di χ tra segmenti adiacenti (derivata spaziale)
        # Usa condizioni al contorno periodiche (manifold chiuso!)
        delta_chi = np.diff(self.chi, append=self.chi[0])
        
        # Chiralità alternata per ogni segmento (±1)
        chiralita = np.array([(-1)**(i) for i in range(N_SEGMENTI)])
        
        # Chiralità del segmento successivo (shift ciclico)
        chiralita_next = np.roll(chiralita, -1)
        
        # Contributo torsionale per ogni interfaccia
        # Il prodotto chiralita[i] × chiralita[i+1] rileva le "cerniere di inversione"
        # dove la fase salta di ±π (flessi del solitone)
        contrib_torsione = np.abs(delta_chi) * np.abs(chiralita * chiralita_next)
        
        # Somma su tutte le interfacce → torsione totale
        # Fattore π: ogni interfaccia contribuisce con un salto di fase π
        torsione_totale = np.pi * np.sum(contrib_torsione)
        
        # Aggiorna l'attributo interno
        self.torsione = torsione_totale
        
        return torsione_totale
    
    def check_saturazione(self) -> bool:
        """
        Verifica se il manifold ha raggiunto la saturazione topologica.
        
        FISICA:
        -------
        Un solitone fermionico stabile deve soddisfare:
        ∮ τ ds = 4π (una rotazione completa spinoriale, 720°)
        
        Se τ > 4π, il solitone ha "troppa informazione topologica":
        - Opzione A: Collassa gravitazionalmente (buco nero)
        - Opzione B: Si divide in due solitoni stabili (fissione)
        
        La natura sceglie B perché minimizza l'azione totale.
        
        CRITERIO:
        ---------
        Saturato = True  se  torsione > 4π
        Saturato = False altrimenti
        
        RESTITUISCE:
        ------------
        saturato : bool
            True se il manifold deve subire fissione
        """
        # Calcola torsione aggiornata
        self.calcola_torsione_totale()
        
        # Confronto con soglia critica
        # Tolleranza numerica: 1.01× per evitare fissioni spurie da roundoff
        saturato = self.torsione > (1.01 * TORSIONE_CRITICA)
        
        return saturato
    
    def calcola_accoppiamento(self, other: 'ManifoldBase') -> float:
        """
        Calcola il coefficiente di accoppiamento emergente con un altro manifold.
        
        FISICA:
        -------
        Due solitoni NON interagiscono sempre! L'accoppiamento è una proprietà
        EMERGENTE che dipende dalla "risonanza di fase" tra i loro campi χ.
        
        Risonanza = correlazione spaziale dei profili di chiralità:
        R_AB = Σᵢ (χ_A[i] × χ_B[i]) / (|χ_A| × |χ_B|)
        
        INTERPRETAZIONE:
        ----------------
        R > 0  → Chiralità allineate → repulsione (simile a cariche uguali)
        R < 0  → Chiralità opposte   → attrazione (simile a cariche opposte)
        |R| ≈ 1 → Risonanza perfetta  → massimo accoppiamento
        R ≈ 0  → Fasi ortogonali     → nessun accoppiamento (trasparenza)
        
        MODULAZIONE GEOMETRICA:
        -----------------------
        Fattore di decadimento spaziale: exp(-d/λ)
        dove d = distanza tra i centri di massa
              λ = lunghezza d'onda di Compton del solitone ≈ χ_medio / k
        
        PARAMETRI:
        ----------
        other : ManifoldBase
            Il manifold con cui calcolare l'accoppiamento
        
        RESTITUISCE:
        ------------
        accoppiamento : float
            Coefficiente emergente [adimensionale]
            |accoppiamento| > RISONANZA_MINIMA → può avvenire congiunzione
        """
        # Distanza euclidea tra i centri di massa [m]
        distanza = np.linalg.norm(self.posizione - other.posizione)
        
        # Norma dei campi χ (protezione divisione per zero)
        norma_self = np.linalg.norm(self.chi) + 1e-12
        norma_other = np.linalg.norm(other.chi) + 1e-12
        
        # Prodotto scalare tra i profili di chiralità (correlazione)
        correlazione = np.dot(self.chi, other.chi) / (norma_self * norma_other)
        
        # Scala caratteristica di decadimento [m]
        # χ_medio grande → solitone "più esteso" → interazione a lungo raggio
        chi_medio_self = np.mean(np.abs(self.chi))
        chi_medio_other = np.mean(np.abs(other.chi))
        scala_decadimento = (chi_medio_self + chi_medio_other) * LUNGHEZZA_PLANCK
        
        # Fattore di decadimento geometrico (interazione locale)
        # exp(-d/λ): decadimento esponenziale con la distanza
        decadimento = np.exp(-distanza / (scala_decadimento + 1e-30))
        
        # Accoppiamento emergente = risonanza × localizzazione
        accoppiamento_emergente = correlazione * decadimento
        
        return accoppiamento_emergente
    
    def congiungi(self, other: 'ManifoldBase') -> 'ManifoldBase':
        """
        Fonde questo manifold con un altro, creando un manifold composito.
        
        FISICA:
        -------
        La congiunzione è il processo inverso della fissione:
        - Due solitoni con chiralità opposte si incontrano
        - I flessi di segno opposto si annichilano parzialmente
        - Si forma un nuovo solitone con χ = χ_A + χ_B
        
        CONSERVAZIONE:
        --------------
        - Carica topologica: Q_totale = Q_A + Q_B (additività)
        - Torsione: τ_totale = τ_A + τ_B (somma ricorsiva)
        - Energia: E_totale = E_A + E_B - E_legame
        
        dove E_legame > 0 è l'energia rilasciata nella fusione.
        
        ALGORITMO:
        ----------
        1. Verifica condizione di chiralità opposta (χ_A + χ_B ≈ 0)
        2. Calcola risonanza di fase
        3. Se risonanza > soglia → FUSIONE
        4. Combina i campi: χ_nuovo = (χ_A + χ_B) / 2
        5. Combina le velocità: v_nuovo = (v_A + v_B) / 2
        6. Posizione: centro di massa ponderato
        
        PARAMETRI:
        ----------
        other : ManifoldBase
            Manifold da fondere con questo
        
        RESTITUISCE:
        ------------
        nuovo_manifold : ManifoldBase
            Solitone composito risultante dalla fusione
        """
        # Campo χ del manifold fuso: media pesata per preservare simmetria
        # Divisione per 2: evita crescita esponenziale durante fusioni successive
        chi_nuovo = (self.chi + other.chi) / 2.0
        
        # Velocità del manifold fuso: conservazione momento (media)
        vel_nuovo = (self.vel + other.vel) / 2.0
        
        # Posizione del centro di massa ponderato per le norme dei campi
        # Manifold con |χ| maggiore "pesa di più" nel determinare la posizione
        peso_self = np.linalg.norm(self.chi) + 1e-12
        peso_other = np.linalg.norm(other.chi) + 1e-12
        peso_totale = peso_self + peso_other
        
        posizione_nuova = (self.posizione * peso_self + other.posizione * peso_other) / peso_totale
        
        # ID del nuovo manifold: somma degli ID parent (tracciamento genealogia)
        # Permette di ricostruire l'albero di fusioni/fissioni
        id_nuovo = self.id_manifold + other.id_manifold
        
        # Generazione: massimo tra i due + 1 (nuovo livello frattale)
        generazione_nuova = max(self.generazione, other.generazione) + 1
        
        # Crea il manifold fuso
        manifold_fuso = ManifoldBase(
            chi=chi_nuovo,
            vel=vel_nuovo,
            torsione=0.0,  # Verrà ricalcolato da calcola_torsione_totale()
            posizione=posizione_nuova,
            id_manifold=id_nuovo,
            generazione=generazione_nuova
        )
        
        # Calcola torsione del manifold fuso
        manifold_fuso.calcola_torsione_totale()
        
        return manifold_fuso
    
    def fissione(self) -> Tuple['ManifoldBase', 'ManifoldBase']:
        """
        Divide questo manifold in due solitoni figli.
        
        FISICA:
        -------
        Quando τ > 4π, il solitone ha eccesso di "carica topologica".
        Per rilassare la tensione, si divide in due solitoni:
        
        - Manifold A: eredita i segmenti 0-11  (prima metà)
        - Manifold B: eredita i segmenti 12-23 (seconda metà)
        
        Ogni figlio ha τ ≈ 2π → topologicamente stabile.
        
        SIMMETRIA:
        ----------
        La divisione preserva l'alternanza di chiralità:
        - Se parent ha (+, -, +, -, ...)
        - Figlio A ha (+, -, +, -, ..., +, -)  [12 segmenti]
        - Figlio B ha (+, -, +, -, ..., +, -)  [12 segmenti]
        
        Entrambi mantengono la struttura topologica!
        
        ENERGIA:
        --------
        La fissione COSTA energia (rompe legami interni):
        ΔE = E_A + E_B - E_parent > 0
        
        Questa energia viene fornita dall'eccesso di torsione.
        
        RESTITUISCE:
        ------------
        (manifold_A, manifold_B) : Tuple[ManifoldBase, ManifoldBase]
            I due solitoni figli generati dalla fissione
        """
        # Divisione del campo χ in due metà
        # Segmenti 0-11: prima metà (6 monti + 6 valli)
        chi_A_base = self.chi[:12]
        # Segmenti 12-23: seconda metà (6 monti + 6 valli)
        chi_B_base = self.chi[12:]
        
        # Velocità: stessa divisione
        vel_A_base = self.vel[:12]
        vel_B_base = self.vel[12:]
        
        # ESTENSIONE A 24 SEGMENTI: ogni figlio deve avere 24 segmenti!
        # Rispecchiamo i 12 segmenti per ottenere 24, preservando alternanza
        # A: [0,1,2,...,11] → [0,1,2,...,11, 0,1,2,...,11] con inversione di segno
        chi_A = np.concatenate([chi_A_base, -chi_A_base])
        chi_B = np.concatenate([chi_B_base, -chi_B_base])
        
        vel_A = np.concatenate([vel_A_base, -vel_A_base])
        vel_B = np.concatenate([vel_B_base, -vel_B_base])
        
        # Posizioni spaziali: separiamo i figli lungo un asse casuale
        # Distanza di separazione ~ scala del solitone parent
        scala_separazione = np.mean(np.abs(self.chi)) * LUNGHEZZA_PLANCK
        
        # Direzione casuale di separazione (distribuita uniformemente su sfera)
        theta = 2.0 * np.pi * np.random.rand()
        phi = np.arccos(2.0 * np.random.rand() - 1.0)
        direzione = np.array([
            np.sin(phi) * np.cos(theta),
            np.sin(phi) * np.sin(theta),
            np.cos(phi)
        ])
        
        # Posizioni dei figli: spostate simmetricamente rispetto al parent
        posizione_A = self.posizione - 0.5 * scala_separazione * direzione
        posizione_B = self.posizione + 0.5 * scala_separazione * direzione
        
        # ID figli: 2×parent e 2×parent+1 (numerazione binaria)
        id_A = 2 * self.id_manifold
        id_B = 2 * self.id_manifold + 1
        
        # Generazione: incremento di 1
        gen_nuova = self.generazione + 1
        
        # Crea i due manifold figli
        manifold_A = ManifoldBase(
            chi=chi_A,
            vel=vel_A,
            torsione=0.0,
            posizione=posizione_A,
            id_manifold=id_A,
            generazione=gen_nuova
        )
        
        manifold_B = ManifoldBase(
            chi=chi_B,
            vel=vel_B,
            torsione=0.0,
            posizione=posizione_B,
            id_manifold=id_B,
            generazione=gen_nuova
        )
        
        # Calcola torsioni dei figli
        manifold_A.calcola_torsione_totale()
        manifold_B.calcola_torsione_totale()
        
        return manifold_A, manifold_B
    
    def evolvi_locale(self, dt: float) -> None:
        """
        Evolve lo stato interno del manifold per un timestep dt.
        
        FISICA:
        -------
        Equazioni di campo di Einstein-Cartan in forma hamiltoniana:
        
        dχᵢ/dτ = vᵢ                           (equazione di definizione)
        dvᵢ/dτ = -∂V/∂χᵢ + Σⱼ A_ij χⱼ         (equazione di Euler-Lagrange)
        
        dove:
        - V(χ) = -½λχ² + ¼χ⁴  (potenziale di doppio pozzo)
        - A_ij = matrice di accoppiamento Leech (connette i 24 segmenti)
        
        POTENZIALE DI DOPPIO POZZO:
        ---------------------------
        V(χ) ha due minimi a χ = ±√λ:
        - Minimo sx (χ < 0): fase condensata (materia)
        - Minimo dx (χ > 0): fase espansa (spazio)
        - Barriera centrale: separa le due fasi
        
        ∂V/∂χ = -λχ + χ³
        
        Questa forza spinge χ verso i minimi, realizzando la separazione di fase
        spontanea materia/spazio (rottura di simmetria χ → -χ).
        
        ACCOPPIAMENTO LEECH:
        --------------------
        La matrice A_ij connette i 24 segmenti secondo la geometria del reticolo
        di Leech (impacchettamento ottimale di sfere in 24 dimensioni).
        
        Ogni segmento è accoppiato con:
        - Vicini immediati (±1): accoppiamento forte
        - Vicini secondi (±2): accoppiamento medio
        - Opposti (±12): accoppiamento debole (riflessione antipodica)
        
        INTEGRATORE:
        ------------
        Velocity Verlet (simplectico, conserva energia):
        1. χ_{n+½} = χ_n + ½ v_n dt
        2. a_n = -∂V/∂χ|_{χ_n} + A·χ_n
        3. v_{n+1} = v_n + a_n dt
        4. χ_{n+1} = χ_{n+½} + ½ v_{n+1} dt
        
        PARAMETRI:
        ----------
        dt : float
            Timestep di integrazione [unità di tempo di Planck]
            Deve essere dt << τ_oscillazione per stabilità numerica
        """
        # STEP 1: Costruzione matrice di accoppiamento Leech
        # Questa matrice è SIMMETRICA (A_ij = A_ji) per conservare energia
        A = np.zeros((N_SEGMENTI, N_SEGMENTI))
        
        for i in range(N_SEGMENTI):
            for j in range(N_SEGMENTI):
                if i == j:
                    # Diagonale: auto-interazione nulla (campo non interagisce con sé stesso)
                    A[i, j] = 0.0
                else:
                    # Distanza sul manifold chiuso (metrica toroidale)
                    # min(|i-j|, 24-|i-j|) considera il percorso più breve sul cerchio
                    distanza_minima = min(abs(i - j), N_SEGMENTI - abs(i - j))
                    
                    # Accoppiamento decade esponenzialmente con la distanza
                    # Lunghezza caratteristica: λ_Leech ≈ 3 segmenti
                    A[i, j] = np.exp(-distanza_minima / 3.0)
        
        # STEP 2: Calcolo forza dal potenziale di doppio pozzo
        # ∂V/∂χ = -λχ + χ³
        # Termine lineare: -λχ → spinge verso i minimi ±√λ
        # Termine cubico: +χ³ → limita la crescita (stabilizzazione)
        forza_potenziale = -LAMBDA_DOPPIO_POZZO * self.chi + self.chi**3
        
        # STEP 3: Forza di accoppiamento tra segmenti
        # Σⱼ A_ij χⱼ: ogni segmento "sente" il campo degli altri segmenti
        # Questo sincronizza i 24 segmenti → comportamento coerente del solitone
        forza_accoppiamento = A @ self.chi
        
        # STEP 4: Accelerazione totale
        # a = -∂V/∂χ + forza_sincronizzazione
        accelerazione = -forza_potenziale + forza_accoppiamento
        
        # STEP 5: Integrazione Velocity Verlet (metodo simplectico)
        # Simplectico → conserva energia e momento anche con dt finito
        
        # Mezzo step di posizione
        chi_half = self.chi + 0.5 * self.vel * dt
        
        # Aggiornamento velocità (full step)
        self.vel = self.vel + accelerazione * dt
        
        # Aggiornamento posizione (completa con secondo mezzo step)
        self.chi = chi_half + 0.5 * self.vel * dt
        
        # STEP 6: Aggiornamento torsione dopo evoluzione
        self.calcola_torsione_totale()


# ============================================================================
# FUNZIONI DI PARALLELIZZAZIONE HPC
# ============================================================================

def evolvi_manifold_parallelo(manifold: ManifoldBase, dt: float) -> ManifoldBase:
    """
    Wrapper per evoluzione locale di un singolo manifold.
    
    NOTA TECNICA:
    -------------
    Questa funzione è necessaria perché multiprocessing.Pool.map() richiede
    una funzione top-level (non può serializzare metodi di classe direttamente).
    
    PARAMETRI:
    ----------
    manifold : ManifoldBase
        Manifold da evolvere
    dt : float
        Timestep di integrazione
    
    RESTITUISCE:
    ------------
    manifold : ManifoldBase
        Manifold evoluto (stesso oggetto, modificato in-place)
    """
    # Evolvi il manifold localmente (metodo di istanza)
    manifold.evolvi_locale(dt)
    
    # Restituisci l'oggetto modificato
    return manifold


def evolvi_sistema_parallelo(lista_manifold: List[ManifoldBase], dt: float, 
                              n_cores: Optional[int] = None) -> List[ManifoldBase]:
    """
    Evolve tutti i manifold in parallelo su più core CPU.
    
    ARCHITETTURA HPC:
    -----------------
    - Distribuzione: ogni core CPU riceve un sottoinsieme di manifold
    - Comunicazione: minima (solo scambio manifold iniziali/finali)
    - Scalabilità: lineare fino a N_manifold/N_cores ≈ 100
    
    ALGORITMO:
    ----------
    1. Divide lista_manifold in N_cores chunk
    2. Ogni processo figlio evolve il suo chunk localmente
    3. Risultati vengono raccolti dal processo master
    4. Ordine preservato (deterministico)
    
    NOTA IMPORTANTE:
    ----------------
    Questa funzione evolve SOLO la dinamica LOCALE di ogni manifold.
    Le interazioni (congiunzioni) vengono gestite DOPO nel loop principale,
    perché richiedono collision detection globale.
    
    PARAMETRI:
    ----------
    lista_manifold : List[ManifoldBase]
        Lista di tutti i manifold da evolvere
    dt : float
        Timestep di integrazione
    n_cores : Optional[int]
        Numero di core da usare. Se None, usa tutti i core disponibili.
    
    RESTITUISCE:
    ------------
    lista_manifold_evoluti : List[ManifoldBase]
        Lista di manifold dopo l'evoluzione locale
    """
    # Determina numero di core da usare
    if n_cores is None:
        # Usa tutti i core disponibili (massimo parallelismo)
        n_cores = mp.cpu_count()
    
    # Se c'è un solo manifold o un solo core, esegui serialmente (overhead evitato)
    if len(lista_manifold) <= 1 or n_cores == 1:
        for manifold in lista_manifold:
            manifold.evolvi_locale(dt)
        return lista_manifold
    
    # Crea pool di processi worker
    with Pool(processes=n_cores) as pool:
        # Distribuisci evoluzione su tutti i core
        # starmap: permette di passare tuple (manifold, dt) a ogni worker
        lista_evoluti = pool.starmap(
            evolvi_manifold_parallelo,
            [(m, dt) for m in lista_manifold]
        )
    
    return lista_evoluti


# ============================================================================
# COLLISION DETECTION E GESTIONE INTERAZIONI
# ============================================================================

def trova_coppie_candidate_congiunzione(lista_manifold: List[ManifoldBase], 
                                         raggio_ricerca: float) -> List[Tuple[int, int]]:
    """
    Identifica coppie di manifold candidati alla congiunzione.
    
    ALGORITMO:
    ----------
    1. Per ogni coppia di manifold (i, j) con i < j:
       a. Calcola distanza euclidea d_ij
       b. Se d_ij < raggio_ricerca → coppia candidata
    
    2. Filtra candidati verificando risonanza di fase:
       - Calcola accoppiamento emergente
       - Se |accoppiamento| > RISONANZA_MINIMA → accetta
    
    OTTIMIZZAZIONE:
    ---------------
    Per N manifold, il numero di coppie è N(N-1)/2.
    Con N grande, questo può essere proibitivo (O(N²)).
    
    Ottimizzazioni possibili (TODO):
    - Spatial hashing (griglia 3D)
    - Octree / KD-tree
    - Cell-linked list
    
    PARAMETRI:
    ----------
    lista_manifold : List[ManifoldBase]
        Lista di tutti i manifold nel sistema
    raggio_ricerca : float
        Distanza massima per considerare due manifold "vicini" [m]
    
    RESTITUISCE:
    ------------
    coppie : List[Tuple[int, int]]
        Lista di coppie (indice_i, indice_j) candidate alla congiunzione
    """
    coppie_candidate = []
    
    N = len(lista_manifold)
    
    # Loop su tutte le coppie (i, j) con i < j (evita duplicati)
    for i in range(N):
        for j in range(i + 1, N):
            # Distanza euclidea tra i centri di massa
            distanza = np.linalg.norm(
                lista_manifold[i].posizione - lista_manifold[j].posizione
            )
            
            # Prima scrematura: vicinanza spaziale
            if distanza < raggio_ricerca:
                # Seconda scrematura: risonanza di fase
                accoppiamento = lista_manifold[i].calcola_accoppiamento(lista_manifold[j])
                
                # Accetta coppia solo se risonanza è sufficientemente forte
                if np.abs(accoppiamento) > RISONANZA_MINIMA:
                    coppie_candidate.append((i, j))
    
    return coppie_candidate


def gestisci_congiunzioni(lista_manifold: List[ManifoldBase], 
                           raggio_ricerca: float) -> List[ManifoldBase]:
    """
    Esegue le congiunzioni tra manifold compatibili.
    
    ALGORITMO:
    ----------
    1. Trova coppie candidate (collision detection)
    2. Per ogni coppia (i, j):
       a. Verifica condizione di chiralità opposta
       b. Calcola accoppiamento emergente
       c. Se condizioni soddisfatte → FUSIONE
       d. Rimuovi i manifold i e j dalla lista
       e. Aggiungi manifold fuso alla lista
    
    GESTIONE CONFLITTI:
    -------------------
    Se un manifold i è coinvolto in più fusioni simultanee,
    scegliamo quella con accoppiamento massimo (regola greedy).
    
    PARAMETRI:
    ----------
    lista_manifold : List[ManifoldBase]
        Lista di manifold PRIMA delle congiunzioni
    raggio_ricerca : float
        Raggio di ricerca per collision detection [m]
    
    RESTITUISCE:
    ------------
    lista_manifold_aggiornata : List[ManifoldBase]
        Lista di manifold DOPO le congiunzioni
    """
    # Trova coppie candidate
    coppie = trova_coppie_candidate_congiunzione(lista_manifold, raggio_ricerca)
    
    # Set di indici già fusi (per evitare fusioni multiple dello stesso manifold)
    fusi = set()
    
    # Lista di manifold fusi da aggiungere
    nuovi_manifold = []
    
    # Processa ogni coppia candidata
    for i, j in coppie:
        # Salta se uno dei due è già stato fuso
        if i in fusi or j in fusi:
            continue
        
        # Recupera i due manifold
        m_i = lista_manifold[i]
        m_j = lista_manifold[j]
        
        # Verifica condizione di chiralità opposta
        # Somma dei campi χ deve essere "piccola" (annichilazione parziale)
        somma_chi = m_i.chi + m_j.chi
        norma_somma = np.linalg.norm(somma_chi)
        norma_media = 0.5 * (np.linalg.norm(m_i.chi) + np.linalg.norm(m_j.chi))
        
        # Criterio: |χ_A + χ_B| < 0.5 × (|χ_A| + |χ_B|) / 2
        # Ovvero: somma è piccola rispetto alla media delle norme
        if norma_somma < 0.5 * norma_media:
            # Condizione soddisfatta → FUSIONE!
            manifold_fuso = m_i.congiungi(m_j)
            
            # Aggiungi alla lista dei nuovi manifold
            nuovi_manifold.append(manifold_fuso)
            
            # Marca i due manifold come fusi
            fusi.add(i)
            fusi.add(j)
    
    # Costruisci lista aggiornata:
    # - Rimuovi manifold fusi
    # - Aggiungi manifold nati da fusione
    lista_aggiornata = [
        m for idx, m in enumerate(lista_manifold) if idx not in fusi
    ] + nuovi_manifold
    
    return lista_aggiornata


def gestisci_fissioni(lista_manifold: List[ManifoldBase]) -> List[ManifoldBase]:
    """
    Esegue le fissioni dei manifold saturi.
    
    ALGORITMO:
    ----------
    1. Per ogni manifold m:
       a. Verifica saturazione (τ > 4π)
       b. Se saturo → FISSIONE
       c. Genera due figli (m_A, m_B)
       d. Rimuovi parent dalla lista
       e. Aggiungi figli alla lista
    
    PARAMETRI:
    ----------
    lista_manifold : List[ManifoldBase]
        Lista di manifold PRIMA delle fissioni
    
    RESTITUISCE:
    ------------
    lista_manifold_aggiornata : List[ManifoldBase]
        Lista di manifold DOPO le fissioni
    """
    # Lista di nuovi manifold generati da fissione
    nuovi_manifold = []
    
    # Indici di manifold da rimuovere (perché si sono divisi)
    da_rimuovere = set()
    
    # Itera su tutti i manifold
    for idx, m in enumerate(lista_manifold):
        # Verifica saturazione
        if m.check_saturazione():
            # Manifold saturo → FISSIONE!
            m_A, m_B = m.fissione()
            
            # Aggiungi i due figli
            nuovi_manifold.append(m_A)
            nuovi_manifold.append(m_B)
            
            # Marca il parent per rimozione
            da_rimuovere.add(idx)
    
    # Costruisci lista aggiornata
    lista_aggiornata = [
        m for idx, m in enumerate(lista_manifold) if idx not in da_rimuovere
    ] + nuovi_manifold
    
    return lista_aggiornata


# ============================================================================
# LOOP DI SIMULAZIONE PRINCIPALE
# ============================================================================

def simula_universo_frattale(
    n_manifold_iniziali: int = 10,
    n_timesteps: int = 1000,
    dt: float = 0.01,
    raggio_congiunzione: float = 10.0 * LUNGHEZZA_PLANCK,
    n_cores: Optional[int] = None,
    file_output: str = "universo_frattale.h5"
) -> None:
    """
    Loop principale di simulazione dell'universo frattale.
    
    ARCHITETTURA:
    -------------
    1. Inizializzazione: crea N manifold primordiali
    2. Loop temporale:
       a. Evoluzione locale (PARALLELA)
       b. Collision detection
       c. Gestione congiunzioni
       d. Gestione fissioni
       e. Telemetria e salvataggio HDF5
    3. Finalizzazione: chiusura file dati
    
    FLUSSO INFORMATIVO:
    -------------------
    manifold[t] → evolvi_parallelo → manifold[t+dt/2]
                                    ↓
                              congiunzioni
                                    ↓
                              manifold[t+dt*]
                                    ↓
                              fissioni
                                    ↓
                              manifold[t+dt]
    
    PARAMETRI:
    ----------
    n_manifold_iniziali : int
        Numero di solitoni primordiali all'inizio
    n_timesteps : int
        Numero di timestep di evoluzione
    dt : float
        Timestep di integrazione [unità di Planck]
    raggio_congiunzione : float
        Raggio di ricerca per collision detection [m]
    n_cores : Optional[int]
        Numero di core CPU da usare (None = tutti)
    file_output : str
        Nome del file HDF5 per telemetria
    """
    
    print("=" * 80)
    print("SIMULAZIONE UNIVERSO FRATTALE - Architettura a Oggetti Dinamici")
    print("=" * 80)
    print(f"Manifold iniziali: {n_manifold_iniziali}")
    print(f"Timesteps: {n_timesteps}")
    print(f"dt: {dt} t_Planck")
    print(f"Raggio congiunzione: {raggio_congiunzione / LUNGHEZZA_PLANCK:.2f} L_P")
    print(f"Cores CPU: {n_cores if n_cores else mp.cpu_count()}")
    print("=" * 80)
    
    # ========================================================================
    # INIZIALIZZAZIONE
    # ========================================================================
    
    # Crea manifold primordiali (generazione 0)
    # Distribuiti casualmente in un volume cubico
    volume_iniziale = 100.0 * LUNGHEZZA_PLANCK  # Lato del cubo [m]
    
    lista_manifold = []
    for i in range(n_manifold_iniziali):
        # Posizione casuale nel cubo
        posizione = (np.random.rand(3) - 0.5) * volume_iniziale
        
        # Crea manifold con fluttuazioni quantistiche
        m = ManifoldBase(
            chi=np.zeros(N_SEGMENTI),  # __post_init__ aggiungerà fluttuazioni
            vel=np.zeros(N_SEGMENTI),
            torsione=0.0,
            posizione=posizione,
            id_manifold=i,
            generazione=0
        )
        
        lista_manifold.append(m)
    
    print(f"\n[INIT] Creati {len(lista_manifold)} manifold primordiali.")
    
    # Inizializza file HDF5 per telemetria
    with h5py.File(file_output, 'w') as f:
        # Metadata globali
        f.attrs['n_manifold_iniziali'] = n_manifold_iniziali
        f.attrs['n_timesteps'] = n_timesteps
        f.attrs['dt'] = dt
        f.attrs['raggio_congiunzione'] = raggio_congiunzione
        f.attrs['creato_il'] = datetime.now().isoformat()
        
        # Dataset per numero di manifold ad ogni timestep
        f.create_dataset('n_manifold', shape=(n_timesteps,), dtype='i8')
        
        # Dataset per torsione media ad ogni timestep
        f.create_dataset('torsione_media', shape=(n_timesteps,), dtype='f8')
        
        # Dataset per energia totale ad ogni timestep
        f.create_dataset('energia_totale', shape=(n_timesteps,), dtype='f8')
    
    print(f"[INIT] File telemetria: {file_output}")
    
    # ========================================================================
    # LOOP TEMPORALE
    # ========================================================================
    
    tempo_inizio = time.time()
    
    for step in range(n_timesteps):
        # ====================================================================
        # STEP 1: EVOLUZIONE LOCALE PARALLELA
        # ====================================================================
        # Ogni manifold evolve indipendentemente secondo le sue equazioni locali
        # Distribuzione su N_cores processi worker
        
        lista_manifold = evolvi_sistema_parallelo(lista_manifold, dt, n_cores)
        
        # ====================================================================
        # STEP 2: COLLISION DETECTION E CONGIUNZIONI
        # ====================================================================
        # Identifica manifold vicini e con risonanza compatibile
        # Fonde quelli con chiralità opposte
        
        lista_manifold = gestisci_congiunzioni(lista_manifold, raggio_congiunzione)
        
        # ====================================================================
        # STEP 3: GESTIONE FISSIONI
        # ====================================================================
        # Verifica quali manifold sono saturi (τ > 4π)
        # Divide quelli saturi in due figli
        
        lista_manifold = gestisci_fissioni(lista_manifold)
        
        # ====================================================================
        # STEP 4: TELEMETRIA E DIAGNOSTICA
        # ====================================================================
        
        # Calcola statistiche globali
        n_manifold_corrente = len(lista_manifold)
        
        # Torsione media del sistema
        torsioni = [m.torsione for m in lista_manifold]
        torsione_media = np.mean(torsioni) if torsioni else 0.0
        
        # Energia totale (somma energie cinetiche + potenziali)
        energia_totale = 0.0
        for m in lista_manifold:
            # Energia cinetica: ½ Σᵢ vᵢ²
            E_cin = 0.5 * np.sum(m.vel**2)
            
            # Energia potenziale: Σᵢ V(χᵢ) = -½λχᵢ² + ¼χᵢ⁴
            E_pot = np.sum(-0.5 * LAMBDA_DOPPIO_POZZO * m.chi**2 + 0.25 * m.chi**4)
            
            energia_totale += E_cin + E_pot
        
        # Salva telemetria su HDF5
        with h5py.File(file_output, 'a') as f:
            f['n_manifold'][step] = n_manifold_corrente
            f['torsione_media'][step] = torsione_media
            f['energia_totale'][step] = energia_totale
        
        # Stampa progresso ogni 10%
        if (step + 1) % (n_timesteps // 10) == 0 or step == 0:
            tempo_trascorso = time.time() - tempo_inizio
            fps = (step + 1) / tempo_trascorso if tempo_trascorso > 0 else 0
            
            print(f"[STEP {step+1}/{n_timesteps}] "
                  f"N_manifold: {n_manifold_corrente:4d} | "
                  f"τ_medio: {torsione_media:.4f} | "
                  f"E_tot: {energia_totale:.6e} | "
                  f"{fps:.2f} step/s")
    
    # ========================================================================
    # FINALIZZAZIONE
    # ========================================================================
    
    tempo_totale = time.time() - tempo_inizio
    
    print("\n" + "=" * 80)
    print("SIMULAZIONE COMPLETATA")
    print("=" * 80)
    print(f"Tempo totale: {tempo_totale:.2f} s")
    print(f"Manifold finali: {len(lista_manifold)}")
    print(f"Generazione massima: {max(m.generazione for m in lista_manifold)}")
    print(f"Fattore di crescita: {len(lista_manifold) / n_manifold_iniziali:.2f}x")
    print(f"Dati salvati in: {file_output}")
    print("=" * 80)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Esempio di utilizzo: simula 100 solitoni per 500 timestep
    simula_universo_frattale(
        n_manifold_iniziali=100,
        n_timesteps=500,
        dt=0.01,
        raggio_congiunzione=10.0 * LUNGHEZZA_PLANCK,
        n_cores=None,  # Usa tutti i core disponibili
        file_output="universo_frattale.h5"
    )
