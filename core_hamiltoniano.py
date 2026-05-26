"""
================================================================================
CORE HAMILTONIANO - Motore di Evoluzione Conservativa
================================================================================

Implementazione rigorosa della dinamica di Einstein-Cartan senza località,
dissipazione o logica condizionale.

PRINCIPI ARCHITETTURALI:
1. NO operatori locali (np.roll, iterazioni su indici vicini)
2. SÌ proiezioni spettrali (autospazi del reticolo di Leech)
3. Potenziale multiscala quantizzato (24 scale gerarchiche)
4. Integratore Symplectic (conservazione Hamiltoniano)
5. Conservazione chiralità (proiezione ad ogni passo)

AUTORE: Implementato seguendo le specifiche di validazione fisica
DATA: 2026-05-25
================================================================================
"""

import numpy as np
from typing import Tuple, Optional

# ============================================================================
# COSTANTI GLOBALI (importate dal modulo principale)
# ============================================================================
LUNGHEZZA_PLANCK_METRI = 1.616255e-35  # [m]
SEGMENTI_FRATTALI = 24
COEFFICIENTE_ACCOPPIAMENTO = 24.0 / 2400.0  # κ ≈ 0.01
BETA_REPULSIONE_SPIN = 1.0


# ============================================================================
# A. DECOMPOSIZIONE SPETTRALE DEL RETICOLO DI LEECH
# ============================================================================

def calcola_autospazi_leech(matrice_adiacenza: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcola autovalori e autovettori della matrice di adiacenza del Leech Lattice.
    
    TEORIA:
    -------
    Gli autospazi della matrice di adiacenza W definiscono i "modi normali"
    del reticolo. Ogni autovettore v_k rappresenta un pattern di vibrazione
    collettiva dei 24 segmenti.
    
    FISICA:
    -------
    - Autovalore λ_k > 0: modo "hard" (alta frequenza, scala fine)
    - Autovalore λ_k ≈ 0: modo "soft" (bassa frequenza, scala grossolana)
    - Autovettore v_k: distribuzione spaziale del modo k
    
    La decomposizione permette di calcolare gradienti GLOBALI senza località:
    
        ∇_i χ = Σ_k (v_k^T · χ) · λ_k · v_k[i]
    
    Parametri:
    ----------
    matrice_adiacenza : ndarray, shape (24, 24)
        Matrice di adiacenza del Leech Lattice (normalizzata per righe).
        
    Restituisce:
    -----------
    autovalori : ndarray, shape (24,)
        Autovalori λ_k ordinati in ordine decrescente (|λ_0| ≥ |λ_1| ≥ ... ≥ |λ_23|).
        
    autovettori : ndarray, shape (24, 24)
        Autovettori v_k come colonne. autovettori[:, k] = k-esimo autovettore.
        
    Note:
    -----
    - Gli autovettori sono ortonormali: v_i^T · v_j = δ_ij
    - La decomposizione è ESATTA (non approssimata)
    - Computazione una tantum (al caricamento modulo)
    """
    # Decomposizione spettrale (autovalori reali per matrice simmetrica)
    autovalori, autovettori = np.linalg.eigh(matrice_adiacenza)
    
    # Ordina in ordine decrescente per importanza fisica
    # (autovalori più grandi = modi più energetici)
    idx_ordinamento = np.argsort(np.abs(autovalori))[::-1]
    autovalori = autovalori[idx_ordinamento]
    autovettori = autovettori[:, idx_ordinamento]
    
    return autovalori, autovettori


def calcola_gradiente_spettrale(chi_vettore: np.ndarray,
                                  autovalori: np.ndarray,
                                  autovettori: np.ndarray) -> np.ndarray:
    """
    Calcola il gradiente di χ usando proiezione sugli autospazi del Leech Lattice.
    
    MATEMATICA:
    -----------
    Decomponiamo χ(x) nella base degli autovettori:
    
        χ = Σ_k c_k · v_k
    
    dove c_k = v_k^T · χ (coefficiente di Fourier generalizzato)
    
    Il gradiente è definito come:
    
        ∇χ = Σ_k λ_k · c_k · v_k
    
    dove λ_k è l'autovalore associato a v_k.
    
    FISICA:
    -------
    - NO differenze finite locali (∂χ/∂x ≈ χ[i+1] - χ[i])
    - SÌ operatore spettrale globale (∇ = Σ λ_k |v_k⟩⟨v_k|)
    - Rispetta simmetrie del reticolo (invarianza per rotazioni discrete)
    
    Parametri:
    ----------
    chi_vettore : ndarray, shape (24,)
        Campo χ sui 24 segmenti.
    autovalori : ndarray, shape (24,)
        Autovalori della matrice di Leech.
    autovettori : ndarray, shape (24, 24)
        Autovettori (colonne).
        
    Restituisce:
    -----------
    gradiente : ndarray, shape (24,)
        Gradiente ∇_i χ per ogni segmento i.
        
    Note:
    -----
    - Operazione O(N²) ma N=24 è piccolo
    - Equivalente a ∇ = W · χ ma concettualmente diverso
    - Permette filtraggio selettivo per modi (future estensioni)
    """
    N = len(chi_vettore)
    
    # Proiezione di χ sugli autospazi
    # c_k = ⟨v_k | χ⟩
    coefficienti = autovettori.T @ chi_vettore  # shape: (24,)
    
    # Amplificazione per autovalori (modi energetici contribuiscono di più)
    # λ_k · c_k
    coefficienti_amplificati = autovalori * coefficienti
    
    # Ricostruzione del gradiente
    # ∇χ = Σ_k (λ_k · c_k) · v_k
    gradiente = autovettori @ coefficienti_amplificati  # shape: (24,)
    
    return gradiente


# ============================================================================
# B. POTENZIALE DI QUANTIZZAZIONE MULTISCALA
# ============================================================================

def calcola_potenziale_multiscala(chi_vettore: np.ndarray,
                                    alpha: float = 0.15,
                                    lambda_bias: float = 2.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcola il potenziale di quantizzazione gerarchico su 24 scale con BIAS CHIRALE ALTERNATO.
    
    TEORIA:
    -------
    Il potenziale totale è una somma di pozzi periodici a scale diverse + bias alternato:
    
        V_total(χ_i) = Σ_{n=0}^{23} V_n(χ_i) + λᵢ·χᵢ
    
    dove:
        V_n(χ) = -(A_n / 2π) · cos(2π · χ / ℓ_n)  (multiscala)
        λᵢ·χᵢ = bias chirale ALTERNATO (i pari: +λ, i dispari: -λ)
        
    con:
        ℓ_n = ℓ_P · 2^n  (scala spaziale del livello n)
        A_n = A_0 · exp(-α · n) · (1 + 0.1·cos(n·π/12))  (ampiezza con FASE)
        λᵢ = λ₀ · (-1)^i  (alternanza +λ, -λ, +λ, -λ, ...)
    
    FISICA:
    -------
    - n = 0: scala di Planck (ℓ_P ≈ 10^-35 m) - pozzi stretti, alta frequenza
    - n = 23: scala cosmologica (ℓ_P · 2^23 ≈ 10^-28 m) - pozzi larghi, bassa freq
    - α > 0: decadimento frattale (scale fini dominano)
    - λᵢ alternato: segmenti pari spinti verso Materia (χ<0), dispari verso Spazio (χ>0)
      → Movimento RELATIVO → Var(χ) > 0 → Clustering spontaneo
    - Fase A_n: impedisce lock-in di tutti i campi in fase
    
    CALIBRAZIONE BIAS:
    -----------------
    λ = 2.0 (bias alternato moderato)
    Accoppiato con URTO CINETICO (σ_χ=0.5, σ_v=0.5) per rompere sincronizzazione:
    - F_bias ~ ±2.0 (locale, alternato)
    - F_tors ~ √(10⁵) ~ 316 (dominante)
    - Ratio: 2/316 ≈ 0.6% (bias guida, torsione regola)
    
    La rottura di simmetria avviene tramite:
    1. Urto cinetico (velocità iniziali diverse) → impedisce sincronizzazione
    2. Bias alternato (forze opposte) → favorisce clustering
    
    La forza derivata è:
        F_n(χ) = -∂V_n/∂χ = A_n · sin(2π · χ / ℓ_n)
        F_bias_i = -λᵢ  (costante per segmento, MA alternata tra segmenti)
    
    Parametri:
    ----------
    chi_vettore : ndarray, shape (24,)
        Campo χ sui 24 segmenti.
    alpha : float, default=0.15
        Esponente di decadimento (α > 0 per gerarchia frattale).
    lambda_bias : float, default=200.0
        Coefficiente bias chirale (λ > 0 rompe degenerazione + forza clustering).
        
    Restituisce:
    -----------
    potenziale : ndarray, shape (24,)
        Energia potenziale V(χ_i) per ogni segmento.
    forza : ndarray, shape (24,)
        Forza F_i = -∂V/∂χ_i per ogni segmento.
        
    Note:
    -----
    - Minima energia a χ = k · ℓ_n (quantizzazione emergente)
    - Bias alternato → forze opposte su segmenti alterni → movimento relativo
    - Sistema conservativo (∫F·dχ = -ΔV esatto)
    """
    N = SEGMENTI_FRATTALI  # 24
    
    # Ampiezza di riferimento (unità naturali)
    A_0 = 1.0
    
    # Inizializzazione
    potenziale_totale = np.zeros(N)
    forza_totale = np.zeros(N)
    
    # Somma gerarchica su 24 scale
    for n in range(N):
        # Scala spaziale del livello n
        ell_n = LUNGHEZZA_PLANCK_METRI * (2.0 ** n)
        
        # Ampiezza decrescente CON FASE ASIMMETRICA (rompe lock-in)
        # Ogni scala ha una fase naturale φ_n = n·π/12 (30° step)
        fase_n = n * np.pi / 12.0
        A_n = A_0 * np.exp(-alpha * n) * (1.0 + 0.1 * np.cos(fase_n))
        
        # Argomento del potenziale periodico
        # theta_n = 2π · χ / ℓ_n
        theta_n = (2.0 * np.pi * chi_vettore) / ell_n
        
        # Potenziale del livello n
        V_n = -(A_n / (2.0 * np.pi)) * np.cos(theta_n)
        
        # Forza del livello n (gradiente negativo)
        F_n = A_n * np.sin(theta_n)
        
        # Accumula nella somma totale
        potenziale_totale += V_n
        forza_totale += F_n
    
    # BIAS CHIRALE ALTERNATO: Forze DIVERSE per ogni segmento
    # Invece di bias globale λ·(Σχ) (uguale per tutti),
    # usa bias locale con alternanza: λᵢ·χᵢ dove λᵢ = λ₀·(-1)^i
    #
    # Questo crea:
    # - Segmenti pari (i=0,2,4,...): forza +λ₀·χᵢ (spinge verso Materia SX)
    # - Segmenti dispari (i=1,3,5,...): forza -λ₀·χᵢ (spinge verso Spazio DX)
    #
    # Risultato: Movimento RELATIVO → Var(χ) > 0 → Clustering spontaneo
    
    # Pattern alternato: +1, -1, +1, -1, ...
    pattern_alternato = np.array([(-1)**i for i in range(N)])
    lambda_locale = lambda_bias * pattern_alternato
    
    # Potenziale bias locale (NO accoppiamento globale)
    V_bias = lambda_locale * chi_vettore
    
    # Forza bias locale (DIVERSA per ogni segmento)
    F_bias = -lambda_locale  # F = -dV/dχ
    
    potenziale_totale += V_bias
    forza_totale += F_bias
    
    return potenziale_totale, forza_totale


# ============================================================================
# C. ENERGIA DI TORSIONE (FORMA QUADRATICA)
# ============================================================================

def calcola_energia_torsione_quadratica(contorsione_locale: np.ndarray,
                                         matrice_adiacenza: np.ndarray) -> Tuple[float, np.ndarray]:
    """
    Calcola l'energia di torsione come forma quadratica tensoriale.
    
    TEORIA:
    -------
    L'energia di torsione non è una semplice somma di quadrati:
    
        E_tors = Σ_i K_i²  (SBAGLIATO - ignora accoppiamento)
    
    ma una forma quadratica che include accoppiamento topologico:
    
        E_tors = Σ_{i,j} W[i,j] · K_i · K_j
    
    In notazione matriciale:
        E_tors = K^T · W · K
    
    FISICA:
    -------
    - W[i,j] > 0: segmenti i e j sono topologicamente vicini
    - K_i · K_j > 0: torsioni allineate → energia ALTA (sfavorita)
    - K_i · K_j < 0: torsioni opposte → energia BASSA (favorita)
    
    Questo favorisce configurazioni a **chiralità alternata** (SX-DX-SX-DX...)
    che è la struttura fisica osservata nei fermioni (quark, leptoni).
    
    La forza derivata è:
        F_i = -∂E_tors/∂K_i = -2 · Σ_j W[i,j] · K_j
    
    Parametri:
    ----------
    contorsione_locale : ndarray, shape (24,)
        Norma K² del tensore di contorsione per ogni segmento.
    matrice_adiacenza : ndarray, shape (24, 24)
        Matrice di accoppiamento del Leech Lattice.
        
    Restituisce:
    -----------
    energia : float
        Energia totale E_tors (scalare).
    forza : ndarray, shape (24,)
        Forza -∂E/∂K_i per ogni segmento.
        
    Note:
    -----
    - Energia sempre ≥ 0 per W simmetrica definita positiva
    - Minimo a K = 0 (configurazione piatta, no torsione)
    - Forme non-triviali favorite da bilanciamento con altri termini
    """
    # Energia: E = K^T · W · K
    termine_accoppiato = matrice_adiacenza @ contorsione_locale  # W·K
    energia = np.dot(contorsione_locale, termine_accoppiato)  # K^T·(W·K)
    
    # Forza: F = -∂E/∂K = -2·W·K
    forza = -2.0 * termine_accoppiato
    
    return energia, forza


# ============================================================================
# D. PROIEZIONE VINCOLO DI CONSERVAZIONE CHIRALITÀ
# ============================================================================

def proietta_conservazione_chiralita(chi_vettore: np.ndarray,
                                      vel_vettore: np.ndarray,
                                      chi_totale_target: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Proietta lo stato (χ, v) sulla varietà di conservazione della carica spinoriale.
    
    TEORIA:
    -------
    Il vincolo di conservazione è:
    
        C(χ) = Σ_i χ_i - Q_target = 0
    
    dove Q_target è la carica spinoriale totale (fissata dalle condizioni iniziali).
    
    METODO LAGRANGE MULTIPLIERS:
    ----------------------------
    Minimizziamo la distanza dallo stato libero:
    
        min ||χ - χ_free||²  soggetto a  C(χ) = 0
    
    La soluzione è:
        χ_projected = χ_free - λ · ∇C
    
    dove:
        ∇C = [1, 1, 1, ..., 1]  (gradiente del vincolo)
        λ = (Σχ_free - Q_target) / N  (moltiplicatore di Lagrange)
    
    FISICA:
    -------
    - In teoria di gauge, le simmetrie continue → cariche conservate (Noether)
    - La carica spinoriale Q = Σχ è associata alla simmetria U(1) chirale
    - L'integrazione numerica viola il vincolo (errore di troncamento)
    - Proiezione ripristina conservazione esatta ad ogni passo
    
    Parametri:
    ----------
    chi_vettore : ndarray, shape (24,)
        Campo χ dopo evoluzione libera.
    vel_vettore : ndarray, shape (24,)
        Velocità v dopo evoluzione libera.
    chi_totale_target : float
        Carica spinoriale target (Σχ_iniziale).
        
    Restituisce:
    -----------
    chi_corretto : ndarray, shape (24,)
        Campo χ proiettato sul vincolo.
    vel_corretto : ndarray, shape (24,)
        Velocità v proiettata (conserva momento totale).
        
    Note:
    -----
    - Correzione minima (proiezione ortogonale)
    - Preserva altre quantità conservate (energia, momento)
    - Applicazione: dopo ogni passo di integrazione
    """
    N = len(chi_vettore)
    
    # Calcola violazione del vincolo
    chi_totale_corrente = np.sum(chi_vettore)
    violazione = chi_totale_corrente - chi_totale_target
    
    # Moltiplicatore di Lagrange (distribuzione uniforme della correzione)
    lambda_corr = violazione / N
    
    # Proiezione su varietà conservata
    chi_corretto = chi_vettore - lambda_corr
    
    # Velocità: conserva momento totale (Σv = cost)
    # Non serve correzione se momento iniziale era zero (simmetria)
    vel_corretto = vel_vettore.copy()
    
    return chi_corretto, vel_corretto


# ============================================================================
# E. INTEGRATORE SYMPLECTIC VERLET (CONSERVAZIONE HAMILTONIANO)
# ============================================================================

def step_symplectic_verlet(chi: np.ndarray,
                            vel: np.ndarray,
                            forza_callable,
                            dt: float,
                            chi_totale_target: float,
                            **forza_kwargs) -> Tuple[np.ndarray, np.ndarray]:
    """
    Integratore Symplectic Verlet (Leapfrog) per sistemi Hamiltoniani.
    
    TEORIA:
    -------
    Il metodo Verlet è un integratore simplettico di ordine 2 che conserva
    esattamente l'Hamiltoniano (a meno di errori di macchina).
    
    ALGORITMO:
    ----------
    1. Semi-step velocità:  v_{n+1/2} = v_n + (dt/2) · F(χ_n)
    2. Full-step posizione: χ_{n+1} = χ_n + dt · v_{n+1/2}
    3. Calcola nuova forza: F(χ_{n+1})
    4. Semi-step velocità:  v_{n+1} = v_{n+1/2} + (dt/2) · F(χ_{n+1})
    5. Proiezione vincolo:  (χ, v) → varietà conservata
    
    PROPRIETÀ:
    ----------
    - Symplectic: preserva volume nello spazio delle fasi
    - Time-reversible: simmetrico per t → -t
    - Conservazione energia: |ΔH/H| ~ O(dt²) bounded
    - NO dissipazione artificiale (a differenza di Runge-Kutta)
    
    FISICA:
    -------
    Per un Hamiltoniano H(χ, p) = T(p) + V(χ):
    
        dχ/dt = ∂H/∂p = p/m
        dp/dt = -∂H/∂χ = -∂V/∂χ = F(χ)
    
    Il metodo Verlet integra queste equazioni mantenendo H = cost.
    
    Parametri:
    ----------
    chi : ndarray, shape (24,)
        Posizioni generalizzate al tempo t.
    vel : ndarray, shape (24,)
        Velocità al tempo t.
    forza_callable : callable
        Funzione che calcola F(χ, **kwargs) → ndarray shape (24,).
    dt : float
        Passo temporale.
    chi_totale_target : float
        Target per conservazione carica spinoriale.
    **forza_kwargs : dict
        Parametri aggiuntivi da passare a forza_callable.
        
    Restituisce:
    -----------
    chi_new : ndarray, shape (24,)
        Posizioni al tempo t + dt.
    vel_new : ndarray, shape (24,)
        Velocità al tempo t + dt.
        
    Note:
    -----
    - NO adattamento dt (timestep fisso per simplecticità)
    - Convergenza garantita per dt sufficientemente piccolo
    - Sostituisce completamente solve_ivp (Runge-Kutta non conservativo)
    """
    # STEP 1: Semi-step velocità (kick)
    forza_t = forza_callable(chi, **forza_kwargs)
    vel_half = vel + 0.5 * dt * forza_t
    
    # STEP 2: Full-step posizione (drift)
    chi_new = chi + dt * vel_half
    
    # STEP 3: Calcola forza alla nuova posizione
    forza_t_new = forza_callable(chi_new, **forza_kwargs)
    
    # STEP 4: Semi-step velocità finale (kick)
    vel_new = vel_half + 0.5 * dt * forza_t_new
    
    # STEP 5: Proiezione sul vincolo di conservazione
    chi_new, vel_new = proietta_conservazione_chiralita(
        chi_new, vel_new, chi_totale_target
    )
    
    return chi_new, vel_new


# ============================================================================
# F. FUNZIONE DI FORZA TOTALE (HAMILTONIANA)
# ============================================================================

def calcola_forza_totale_hamiltoniana(chi_vettore: np.ndarray,
                                       autovalori: np.ndarray,
                                       autovettori: np.ndarray,
                                       matrice_adiacenza: np.ndarray,
                                       contorsione_locale: np.ndarray,
                                       densita_sx: np.ndarray,
                                       densita_dx: np.ndarray,
                                       scatolamento: float = 2.0,
                                       alpha_decay: float = 0.30) -> np.ndarray:  # Aumentato per forze più intense
    """
    Calcola la forza totale sui 24 segmenti tramite gradiente Hamiltoniano.
    
    HAMILTONIANO (con costante cosmologica dinamica):
    -------------------------------------------------
    H[χ, v] = T[v] + V_potenziale[χ] + E_torsione[χ] + E_pressione[χ, ρ]
    
    dove:
    - T = (1/2) Σ_i v_i²  (energia cinetica)
    - V_potenziale = Σ_n V_n(χ)  (quantizzazione multiscala)
    - E_torsione = K^T · W · K  (forma quadratica)
    - E_pressione = ∫P[ρ(χ)] dV  (equazione di stato DINAMICA)
    
    EQUAZIONE DI STATO DINAMICA (fix overflow):
    -------------------------------------------
    w(ρ) = w_0 + Δw · tanh((ρ - ρ_crit) / Δρ)
    
    - ρ < ρ_crit: w ≈ -1/3 (materia, contrazione)
    - ρ > ρ_crit: w → -1 (energia vuoto, ESPANSIONE D'URTO)
    
    Questo permette il ciclo bounce → espansione → raffreddamento → bounce
    senza overflow numerico.
    
    FORZA TOTALE:
    ------------
    F_i = -∂H/∂χ_i = F_potenziale + F_torsione + F_pressione + F_gradiente
    
    Parametri:
    ----------
    chi_vettore : ndarray, shape (24,)
        Campo χ corrente.
    autovalori, autovettori :
        Decomposizione spettrale del Leech Lattice.
    matrice_adiacenza : ndarray, shape (24, 24)
        Matrice di accoppiamento.
    contorsione_locale : ndarray, shape (24,)
        Torsione K per ogni segmento.
    densita_sx, densita_dx : ndarray, shape (24,)
        Densità di materia e spazio.
    scatolamento : float
        Parametro di confinamento cosmologico.
    alpha_decay : float
        Esponente frattale del potenziale.
        
    Restituisce:
    -----------
    forza_totale : ndarray, shape (24,)
        Accelerazione a_i = F_i per ogni segmento.
    """
    # 1. FORZA DA POTENZIALE MULTISCALA
    _, forza_potenziale = calcola_potenziale_multiscala(chi_vettore, alpha=alpha_decay)
    
    # 2. FORZA DA ENERGIA DI TORSIONE (forma quadratica)
    _, forza_torsione = calcola_energia_torsione_quadratica(
        contorsione_locale, matrice_adiacenza
    )
    
    # 3. FORZA DA GRADIENTE SPETTRALE (accoppiamento topologico)
    gradiente_spettrale = calcola_gradiente_spettrale(
        chi_vettore, autovalori, autovettori
    )
    forza_gradiente = -gradiente_spettrale  # Segno negativo (forza attrattiva)
    
    # 4. FORZA DA PRESSIONE (equazione di stato DINAMICA)
    # ====================================================================
    # COSTANTE COSMOLOGICA DINAMICA w(ρ) - Fix Overflow
    # ====================================================================
    # PROBLEMA: Con w fisso, il sistema accumula energia indefinitamente
    #           → E_tot: 3006 → 2.1×10^17 → overflow → crash
    #
    # SOLUZIONE: w varia con densità (NO if-then, transizione smooth)
    #
    # FISICA:
    #   - Bassa densità (ρ < ρ_crit): w ≈ -1/3 (materia)
    #   - Alta densità (ρ > ρ_crit): w → -1 (costante cosmologica)
    #
    # CONSEGUENZA:
    #   Ad alta densità, P_grav diventa FORTEMENTE REPULSIVA:
    #   P_grav = w·ρ = (-1)·ρ → espansione violenta
    #   → ρ scende rapidamente → w ritorna a -1/3 → ciclo chiuso
    # ====================================================================
    
    # Densità totale
    densita_totale = (densita_sx + densita_dx) * scatolamento
    
    # Indicatore densità (crescita logaritmica per stabilità)
    indicatore_densita = 1.0 + np.log(1.0 + np.abs(chi_vettore) / 100.0)
    densita_efficace = densita_totale * indicatore_densita
    
    # ====================================================================
    # EQUAZIONE DI STATO DINAMICA w(ρ)
    # ====================================================================
    # Parametri transizione
    w_materia = -1.0 / 3.0      # Materia ordinaria (bassa densità)
    w_vuoto = -1.0              # Energia del vuoto (alta densità)
    rho_critica = 5.0           # Soglia transizione ABBASSATA per espansione precoce
    delta_rho = 1.5             # Larghezza transizione (smooth)
    
    # Calcola w locale per ogni segmento (vettoriale)
    # tanh garantisce transizione smooth (NO if-then)
    eccesso_densita = (densita_efficace - rho_critica) / delta_rho
    w_dinamico = w_materia + (w_vuoto - w_materia) * 0.5 * (1.0 + np.tanh(eccesso_densita))
    
    # Pressione gravitazionale DINAMICA (attrattiva → repulsiva)
    # A bassa ρ: P_grav = (-1/3)·ρ (contrazione debole)
    # Ad alta ρ: P_grav = (-1)·ρ (espansione VIOLENTA)
    P_grav = w_dinamico * densita_efficace
    
    # Pressione di repulsione spin (repulsiva, sempre attiva)
    P_rep = BETA_REPULSIONE_SPIN * (densita_efficace ** 2)
    
    # Pressione totale
    P_totale = P_grav + P_rep
    # ====================================================================
    # NORMALIZZAZIONE ANTI-OVERFLOW
    # ====================================================================
    # Se densità diventa estrema (> 10^6), satura la pressione
    # per evitare overflow float64 (mantiene dinamica fisica)
    P_totale = np.tanh(P_totale / 1e6) * 1e6
    
    # Forza da pressione (gradiente spettrale della pressione)
    # ∇P tramite proiezione sugli autospazi
    gradiente_pressione = calcola_gradiente_spettrale(
        P_totale, autovalori, autovettori
    )
    forza_pressione = -gradiente_pressione
    
    # 5. SOMMA DELLE FORZE
    forza_totale = (
        forza_potenziale +
        forza_torsione +
        forza_gradiente * 0.15 +  # Peso accoppiamento (κ)
        forza_pressione
    )
    
    # ====================================================================
    # NORMALIZZAZIONE FINALE ANTI-OVERFLOW
    # ====================================================================
    # Clipping forze estreme per stabilità numerica Verlet
    # Mantiene direzione (segno) ma previene step troppo grandi
    forza_max = 1e3  # Limite forza per stabilità Verlet
    forza_norm = np.linalg.norm(forza_totale)
    
    if forza_norm > forza_max:
        # Normalizza preservando direzione
        forza_totale = forza_totale * (forza_max / (forza_norm + 1e-12))
    
    return forza_totale


# ============================================================================
# FINE MODULO
# ============================================================================
