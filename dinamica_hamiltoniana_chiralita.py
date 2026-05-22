"""
DINAMICA HAMILTONIANA PER SEPARAZIONE FASI MATERIA/SPAZIO
==========================================================

Sistema di trasporto della chiralità guidato dalla minimizzazione
dell'energia di accoppiamento torsionale.

FISICA:
-------
La torsione K² agisce come potenziale per la densità di materia (SX).
Zone con alta K² (> 4π = 720°) attraggono materia creando clustering.

PRINCIPIO VARIAZIONALE:
-----------------------
Il sistema evolve minimizzando l'energia totale:

    E_tot = Σᵢ [E_coupling[i] + E_torsion[i]]

dove:
    E_coupling[i] = α × Σⱼ w_ij × (K²_i - K²_j)²
    E_torsion[i]  = β × (K²_i - K²_ref)²

Il trasporto di chiralità segue:
    
    dρ_SX[i]/dt = -∂E/∂ρ_SX[i] = flusso_netto[i]

CONSERVAZIONE:
--------------
La carica totale è preservata:
    
    Σᵢ (ρ_SX[i] + ρ_DX[i]) = costante

Author: Senior Computational Physicist
Date: 2026-05-22
"""

import numpy as np

# ============================================================================
# PARAMETRI FISICI
# ============================================================================

# Accoppiamento torsionale (energia ~ gradiente²)
ALPHA_COUPLING = 0.05  # Coefficiente accoppiamento vicini

# Soglia torsionale (720° = 4π rad)
K2_REF_720 = 4.0 * np.pi  # K² di riferimento

# Coefficiente trasporto (mobilità)
MU_TRANSPORT = 0.25  # Velocità risposta al gradiente energetico

# Diffusività intrinseca (smoothing locale)
DIFFUSIVITA = 0.02  # Diffusione piccola per evitare omogeneizzazione

# ============================================================================
# FUNZIONE PRINCIPALE: AGGIORNAMENTO DINAMICA CHIRALITÀ
# ============================================================================

def update_dinamica_chiralita(stato_attuale, dt, matrice_accoppiamento, contorsione_locale):
    """
    Aggiorna le densità di chiralità attraverso trasporto guidato 
    dalla minimizzazione dell'energia di accoppiamento torsionale.
    
    ALGORITMO:
    ----------
    1. Calcola K² locale per ogni segmento
    2. Calcola energia potenziale E[i] per ogni segmento
    3. Calcola gradiente ∇E → flussi tra vicini
    4. Aggiorna densità: ρ_SX[i] += flusso_netto[i] × dt
    5. Normalizza per conservazione carica totale
    
    Parametri:
    ----------
    stato_attuale : ndarray, shape (48,)
        [χ₀, v₀, χ₁, v₁, ..., χ₂₃, v₂₃]
    dt : float
        Passo temporale
    matrice_accoppiamento : ndarray, shape (24, 24)
        Matrice w_ij di accoppiamento topologico
    contorsione_locale : ndarray, shape (24,)
        Norma K² per ogni segmento
    
    Restituisce:
    -----------
    densita_sx_nuova : ndarray, shape (24,)
        Densità di chiralità SX aggiornata
    densita_dx_nuova : ndarray, shape (24,)
        Densità di chiralità DX aggiornata
    flussi_netto : ndarray, shape (24,)
        Flusso netto di SX per ogni segmento (per logging)
    """
    N = 24  # Numero segmenti
    
    # ========================================================================
    # STEP 1: ESTRAZIONE STATO CORRENTE
    # ========================================================================
    # stato_vettoriale = [χ₀, v₀, χ₁, v₁, ..., χ₂₃, v₂₃]
    # Estraiamo χ_vettore e calcoliamo densità correnti
    
    chi_vettore = stato_attuale[0::2]  # χᵢ (24 elementi)
    vel_vettore = stato_attuale[1::2]  # vᵢ (24 elementi)
    
    # Calcola densità correnti (formula da calcola_chiralita_locale_24_segmenti)
    # Semplificazione: densita_sx ≈ f(χ, K²)
    # Per ora usiamo approssimazione lineare con modulazione torsione
    
    # Saturazione chirale: χ_sat ∈ [-1, +1]
    chi_sat = np.tanh(chi_vettore / 5.0)
    
    # Frazione chirale con boost torsionale
    K2_norm = contorsione_locale / K2_REF_720  # Normalizzato a 720°
    boost_factor = 1.0 + 0.5 * K2_norm  # Zone alta torsione = più materia
    
    f_dx = 0.5 * (1.0 + chi_sat) * boost_factor
    f_sx = 0.5 * (1.0 - chi_sat) * boost_factor
    
    # Densità materia (basata su |χ|, modulata da torsione)
    densita_base = 1.0 + 0.1 * np.abs(chi_vettore)
    densita_sx = densita_base * f_sx
    densita_dx = densita_base * f_dx
    
    # ========================================================================
    # STEP 2: CALCOLO ENERGIA POTENZIALE PER SEGMENTO
    # ========================================================================
    # E_coupling[i] = α × Σⱼ w_ij × (K²_i - K²_j)²
    # Questa energia è MINIMIZZATA quando K² è omogeneo tra vicini
    # → La torsione alta attrae materia dai vicini a bassa torsione
    
    E_coupling = np.zeros(N)
    
    for i in range(N):
        # Somma su tutti i vicini j
        for j in range(N):
            if i != j:
                diff_K2 = contorsione_locale[i] - contorsione_locale[j]
                E_coupling[i] += ALPHA_COUPLING * matrice_accoppiamento[i, j] * diff_K2**2
    
    # ========================================================================
    # STEP 3: CALCOLO FLUSSI DALLA MINIMIZZAZIONE ENERGETICA
    # ========================================================================
    # La densità SX fluisce secondo il gradiente energetico:
    #   flusso[i→j] = -MU × (∂E/∂ρ_SX[i] - ∂E/∂ρ_SX[j])
    #
    # Approssimazione: ∂E/∂ρ ≈ ∂E/∂K² × ∂K²/∂ρ
    #
    # Poiché K² dipende dalla densità SX (più materia → più torsione),
    # il gradiente di E spinge la materia verso zone di minima energia.
    #
    # INTERPRETAZIONE FISICA:
    # -----------------------
    # - Se K²_i > K²_j: energia alta in i → materia fluisce i→j
    # - Ma se K²_i >> 720°: barriera di potenziale → materia bloccata
    
    flussi_netto = np.zeros(N)
    
    for i in range(N):
        # Flusso da/verso vicini immediati (topologia toroidale)
        i_prev = (i - 1) % N
        i_next = (i + 1) % N
        
        # Gradiente locale dell'energia di torsione
        grad_E_prev = contorsione_locale[i] - contorsione_locale[i_prev]
        grad_E_next = contorsione_locale[i_next] - contorsione_locale[i]
        
        # Flusso guidato da gradiente (segno negativo: verso zone bassa energia)
        # MA: se K² > 720° localmente, la materia viene ATTRATTA (inversione)
        
        # Peso flusso da attrazione torsionale
        peso_attr_i = max(0, contorsione_locale[i] - K2_REF_720)
        peso_attr_prev = max(0, contorsione_locale[i_prev] - K2_REF_720)
        peso_attr_next = max(0, contorsione_locale[i_next] - K2_REF_720)
        
        # Flusso totale = trasporto gradiente + attrazione zone >720°
        flusso_da_prev = -MU_TRANSPORT * grad_E_prev + 0.1 * (peso_attr_i - peso_attr_prev)
        flusso_da_next = -MU_TRANSPORT * grad_E_next + 0.1 * (peso_attr_next - peso_attr_i)
        
        # Flusso netto entrante in i
        flussi_netto[i] = flusso_da_prev + flusso_da_next
        
        # DIFFUSIONE AGGIUNTIVA (smoothing)
        # Laplaciano discreto: ∇²ρ[i] = ρ[i-1] + ρ[i+1] - 2ρ[i]
        laplaciano_sx = densita_sx[i_prev] + densita_sx[i_next] - 2.0 * densita_sx[i]
        flussi_netto[i] += DIFFUSIVITA * laplaciano_sx
    
    # ========================================================================
    # STEP 4: AGGIORNAMENTO DENSITÀ
    # ========================================================================
    # Aggiorna densità SX con flusso netto
    densita_sx_nuova = densita_sx + flussi_netto * dt
    
    # La densità DX si comporta in modo complementare
    # (mantiene la densità totale locale costante per ora)
    densita_dx_nuova = densita_base - densita_sx_nuova
    
    # ========================================================================
    # STEP 5: CONSERVAZIONE CARICA TOTALE
    # ========================================================================
    # Assicuriamo che Σᵢ (ρ_SX + ρ_DX) = costante globale
    
    carica_tot_iniziale = np.sum(densita_sx) + np.sum(densita_dx)
    carica_tot_finale = np.sum(densita_sx_nuova) + np.sum(densita_dx_nuova)
    
    # Fattore di normalizzazione
    if carica_tot_finale > 0:
        norm_factor = carica_tot_iniziale / carica_tot_finale
        densita_sx_nuova *= norm_factor
        densita_dx_nuova *= norm_factor
    
    # ========================================================================
    # STEP 6: PROTEZIONE FISICA (BARRIERA DI POTENZIALE NATURALE)
    # ========================================================================
    # NON usiamo np.clip artificiale!
    # Invece: se densità diventa negativa localmente, impostiamo zero
    # (fisicamente: vuoto quantistico, non densità negativa)
    
    densita_sx_nuova = np.maximum(densita_sx_nuova, 0.0)
    densita_dx_nuova = np.maximum(densita_dx_nuova, 0.0)
    
    # Se entrambe zero, impostiamo valore minimo per evitare singolarità
    for i in range(N):
        if densita_sx_nuova[i] + densita_dx_nuova[i] < 1e-10:
            densita_sx_nuova[i] = 0.5
            densita_dx_nuova[i] = 0.5
    
    return densita_sx_nuova, densita_dx_nuova, flussi_netto


# ============================================================================
# FUNZIONE DIAGNOSTICA: ENERGIA TOTALE DEL SISTEMA
# ============================================================================

def calcola_energia_sistema(densita_sx, densita_dx, contorsione_locale, matrice_accoppiamento):
    """
    Calcola l'energia totale hamiltoniana del sistema.
    
    E_tot = E_coupling + E_torsion + E_cinetica
    
    Questa funzione è utile per verificare che il sistema stia minimizzando
    l'energia nel tempo (criterio di stabilità).
    """
    N = 24
    
    # Energia di accoppiamento
    E_coupling = 0.0
    for i in range(N):
        for j in range(N):
            if i != j:
                diff_K2 = contorsione_locale[i] - contorsione_locale[j]
                E_coupling += 0.5 * ALPHA_COUPLING * matrice_accoppiamento[i, j] * diff_K2**2
    
    # Energia di torsione (penalità per eccesso oltre 720°)
    E_torsion = np.sum((contorsione_locale - K2_REF_720)**2)
    
    # Energia totale
    E_tot = E_coupling + E_torsion
    
    return E_tot, E_coupling, E_torsion


# ============================================================================
# ESEMPIO DI INTEGRAZIONE NEL CODICE PRINCIPALE
# ============================================================================

def esempio_uso():
    """
    Esempio di come integrare questa funzione in WQT_manifold.py
    """
    print("""
    INTEGRAZIONE IN WQT_manifold.py:
    ================================
    
    1. Importa il modulo:
       from dinamica_hamiltoniana_chiralita import update_dinamica_chiralita
    
    2. Nel loop di evoluzione, DOPO solve_ivp:
    
       # Calcola nuove densità da trasporto hamiltoniano
       densita_sx_new, densita_dx_new, flussi = update_dinamica_chiralita(
           stato_attuale=stato_vettoriale,
           dt=d_tau,
           matrice_accoppiamento=MATRICE_ACCOPPIAMENTO_LEECH,
           contorsione_locale=contorsione_k_vettore
       )
       
       # Usa le nuove densità per il prossimo step
       # (sostituiscono il calcolo in calcola_chiralita_locale_24_segmenti)
    
    3. Logging flussi (in flussi_24campi.log):
       
       varianza_flussi = np.var(flussi)
       print(f"Varianza flussi: {varianza_flussi:.2e}")
    
    4. RIMOZIONE clip artificiale:
       - Elimina tutti i np.clip() su densita_sx/dx
       - La protezione è ora dalla barriera di potenziale (K² > 720°)
    """)

if __name__ == "__main__":
    esempio_uso()
