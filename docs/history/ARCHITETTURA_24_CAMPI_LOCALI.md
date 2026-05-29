# Architettura 24 Campi Locali - Transizione da Globale a Granulare

## Problema del Modello Attuale (Scalare Globale)

**Sistema Corrente**:
```python
stato_attuale = [χ, dχ/dλ]  # 2 valori scalari
```

**Limitazioni**:
- ✗ Tutto il manifold condivide UN SOLO valore di χ
- ✗ Densità DX/SX uniformi → nessuna anisotropia locale
- ✗ Impossibile formare clustering di materia
- ✗ Comportamento "cristallino" statico
- ✗ Bounce quantistico globale (tutto o niente)

---

## Soluzione Proposta (24 Campi Vettoriali)

**Nuovo Sistema**:
```python
stato_attuale = [χ₀, v₀, χ₁, v₁, ..., χ₂₃, v₂₃]  # 48 valori (24 segmenti × 2 stati)
```

**Vantaggi**:
- ✅ Ogni segmento ha il proprio χᵢ indipendente
- ✅ Densità locale: ρ_SX[i] = f(χᵢ, Kᵢ, errore_chiusuraᵢ)
- ✅ Anisotropia spontanea → formazione di strutture
- ✅ Clustering: materia si concentra dove torsione è alta
- ✅ Bounce locale: alcuni segmenti espandono mentre altri collassano

---

## Implementazione Tecnica

### 1. Matrice di Accoppiamento Topologico (24×24)

```python
def costruisci_matrice_accoppiamento_leech():
    """
    Costruisce la matrice di accoppiamento basata sul reticolo di Leech.
    
    Topologia:
    - Ogni segmento i ha 6 vicini più prossimi
    - Accoppiamento decrescente con distanza: w_ij ∝ 1 / dist_ij²
    - Simmetria cubottaedrica preservata
    
    Restituisce:
    -----------
    W : ndarray, shape (24, 24)
        Matrice di peso w_ij per l'accoppiamento tra segmento i e j.
    """
    N = 24
    W = np.zeros((N, N))
    
    # Angoli dei 24 segmenti uniformemente distribuiti
    angoli = np.linspace(0, 2*np.pi, N, endpoint=False)
    
    # Coordinate sul cerchio
    coords = np.column_stack([np.cos(angoli), np.sin(angoli)])
    
    # Calcolo distanze euclidee
    for i in range(N):
        for j in range(N):
            if i != j:
                # Distanza sul cerchio (metrica toroidale)
                diff = np.abs(i - j)
                dist_circle = min(diff, N - diff)
                
                # Peso inversamente proporzionale al quadrato della distanza
                # Vicini più prossimi (dist=1) hanno peso 1.0
                # Vicini secondi (dist=2) hanno peso 0.25
                # Opposti (dist=12) hanno peso ~0.007
                W[i, j] = 1.0 / (dist_circle**2 + 0.1)  # +0.1 per evitare div/0
    
    # Normalizzazione: ogni riga somma a 1
    W_normalizzata = W / W.sum(axis=1, keepdims=True)
    
    return W_normalizzata
```

### 2. Chiralità Locale (DX/SX per Segmento)

```python
def calcola_chiralita_locale(chi_vettore, curvatura_locale):
    """
    Calcola la prevalenza DX/SX per ciascuno dei 24 segmenti.
    
    Parametri:
    ----------
    chi_vettore : ndarray, shape (24,)
        Potenziale di scala per ogni segmento
    curvatura_locale : ndarray, shape (24,)
        Curvatura misurata localmente (da contorsione K)
        
    Restituisce:
    -----------
    densita_dx : ndarray, shape (24,)
        Densità di espansione (spazio) per segmento
    densita_sx : ndarray, shape (24,)
        Densità di condensazione (materia) per segmento
    """
    # Saturazione locale
    chi_sat = 150.0 * np.tanh(chi_vettore / 150.0)
    
    # Fattori chirali locali (ogni segmento ha il suo!)
    f_dx = np.exp(+chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    f_sx = np.exp(-chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    
    # Modulazione basata sulla curvatura locale
    # Dove K² è alta → densità SX aumenta (materia si concentra)
    # Dove K² è bassa → densità DX domina (spazio vuoto)
    modulazione_topologica = 1.0 + 0.5 * np.tanh(curvatura_locale / np.mean(curvatura_locale + 1e-12))
    
    densita_sx = f_sx * modulazione_topologica
    densita_dx = f_dx / modulazione_topologica
    
    return densita_dx, densita_sx
```

### 3. Evoluzione Accoppiata (Equazione di Campo Locale)

```python
def equazione_estado_einstein_cartan_24_campi(lambda_affine, stato_vettoriale, 
                                               matrice_accoppiamento, 
                                               contorsione_locale, 
                                               chiusura_locale):
    """
    Evoluzione geometrodinamica per 24 campi χᵢ accoppiati.
    
    Stato:
    ------
    stato_vettoriale = [χ₀, v₀, χ₁, v₁, ..., χ₂₃, v₂₃]  # shape (48,)
    
    Dinamica:
    ---------
    Per ogni segmento i:
    
      d²χᵢ/dλ² = F_local[i] + F_coupling[i] + F_torsion[i] + F_closure[i]
      
    dove:
      - F_local[i]:    Pressione locale del segmento
      - F_coupling[i]: Σⱼ w_ij * (χⱼ - χᵢ)  (diffusione tra vicini)
      - F_torsion[i]:  Forza da contorsione K²[i]
      - F_closure[i]:  Forza da errore chiusura spinoriale[i]
    """
    N_segmenti = 24
    
    # Estrazione stato: [χ₀, v₀, χ₁, v₁, ...] → χ e v separati
    chi_array = stato_vettoriale[::2]   # Indici pari: χᵢ
    vel_array = stato_vettoriale[1::2]  # Indici dispari: vᵢ
    
    # Forze locali (come prima, ma vettorializzate)
    chi_sat = 150.0 * np.tanh(chi_array / 150.0)
    f_dx = np.exp(+chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    f_sx = np.exp(-chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    
    # Densità locale per ciascun segmento
    indicatore_densita = 1.0 + np.abs(chi_array) / 100.0
    densita_totale = (f_sx + contorsione_locale) * indicatore_densita
    
    # Pressioni locali
    w = -1.0/3.0
    pressione_grav = w * densita_totale
    pressione_rep = BETA_REPULSIONE_SPIN * densita_totale**2
    
    # ACCOPPIAMENTO TRA VICINI (diffusione topologica)
    # Ogni segmento "sente" i vicini tramite matrice di accoppiamento
    forza_coupling = np.zeros(N_segmenti)
    for i in range(N_segmenti):
        # Differenza pesata con tutti i vicini
        forza_coupling[i] = np.sum(
            matrice_accoppiamento[i, :] * (chi_array - chi_array[i])
        )
    
    # Coefficiente di coupling (quanto forte è l'interazione?)
    kappa_coupling = 0.1  # Accoppiamento debole → anisotropia locale
                          # Accoppiamento forte → tende a omogeneità
    
    # FORZA DI CHIUSURA LOCALE (4π vincolo per segmento)
    k_chiusura = 50.0
    forza_chiusura = -k_chiusura * chiusura_locale
    
    # FORZA DI RICHIAMO ARMONICO (come prima)
    forza_richiamo = -OMEGA_RICHIAMO * chi_array
    
    # ACCELERAZIONE TOTALE PER OGNI SEGMENTO
    forza_totale = (
        pressione_rep - pressione_grav +
        kappa_coupling * forza_coupling +
        forza_chiusura +
        forza_richiamo
    )
    
    # Damping locale (stabilità numerica)
    damping_coefficiente = 0.15
    forza_viscosa = -damping_coefficiente * vel_array
    
    accelerazione = forza_totale + forza_viscosa
    
    # Costruzione derivata [dχ₀/dλ, dv₀/dλ, dχ₁/dλ, dv₁/dλ, ...]
    derivata = np.zeros(48)
    derivata[::2] = vel_array       # dχᵢ/dλ = vᵢ
    derivata[1::2] = accelerazione  # dvᵢ/dλ = Fᵢ
    
    return derivata
```

### 4. Generazione Geometria Locale

```python
def genera_mappatura_24_segmenti(chi_vettore, frame):
    """
    Genera il manifold 3D usando χᵢ locale per ogni segmento.
    
    Strategia:
    ----------
    - Il manifold è diviso in 24 settori angolari: [0, 2π/24], [2π/24, 4π/24], ...
    - Ogni settore usa il χᵢ corrispondente per calcolare:
        * Raggio locale: r_m[i] = f(χᵢ)
        * Perturbazioni: p_dx[i], p_sx[i]
        * Frequenza: freq[i]
        
    Restituisce un manifold "a segmenti" dove ogni settore ha densità diversa.
    """
    N_segmenti = 24
    punti_per_segmento = risoluzione_base // N_segmenti  # 2400 / 24 = 100
    
    theta_completo = np.linspace(0, 4*np.pi, risoluzione_base)
    
    # Array per memorizzare i risultati
    Xdx_completo = []
    Ydx_completo = []
    Zdx_completo = []
    Xsx_completo = []
    Ysx_completo = []
    Zsx_completo = []
    pdx_completo = []
    psx_completo = []
    
    # Genera ogni segmento con il suo χᵢ locale
    for i_seg in range(N_segmenti):
        # Indici del segmento
        idx_start = i_seg * punti_per_segmento
        idx_end = (i_seg + 1) * punti_per_segmento
        theta_seg = theta_completo[idx_start:idx_end]
        
        # χ locale per questo segmento
        chi_locale = chi_vettore[i_seg]
        chi_sat_locale = 150.0 * np.tanh(chi_locale / 150.0)
        
        # Geometria locale (simile a genera_mappatura originale)
        f_dx_locale = np.exp(+chi_sat_locale * COEFFICIENTE_ACCOPPIAMENTO)
        f_sx_locale = np.exp(-chi_sat_locale * COEFFICIENTE_ACCOPPIAMENTO)
        
        r_m_locale = float(N_segmenti) * ACCORCIAMENTO_ANGOLARE * np.exp(
            chi_sat_locale * COEFFICIENTE_ACCOPPIAMENTO
        )
        
        # ... (calcolo completo come in genera_mappatura)
        
        # Accumula risultati
        Xdx_completo.append(Xdx_seg)
        # ... etc
    
    # Concatena tutti i segmenti
    Xdx_final = np.concatenate(Xdx_completo)
    # ... etc
    
    # Raggio metrico medio (per compatibilità con codice esistente)
    rm_medio = np.mean([calcola_rm(chi_vettore[i]) for i in range(N_segmenti)])
    
    return Xdx_final, Ydx_final, Zdx_final, Xsx_final, Ysx_final, Zsx_final, rm_medio, ...
```

---

## Modifiche HDF5

```python
# Nuova struttura per salvare 24 campi
SCALARI_24_DTYPE = np.dtype([
    ('frame_id', 'i8'),
    ('chi_vettore', 'f8', (24,)),      # Array di 24 chi
    ('vel_vettore', 'f8', (24,)),      # Array di 24 velocità
    ('densita_sx', 'f8', (24,)),       # Densità SX locale
    ('densita_dx', 'f8', (24,)),       # Densità DX locale
    ('contorsione_locale', 'f8', (24,)),  # K² per segmento
    ('chiusura_locale', 'f8', (24,)),     # Errore 4π per segmento
    ('rm_medio', 'f8'),                # Raggio metrico medio
    ('g_geo', 'f8'),
    ('z_geo', 'f8'),
    # ... altri campi globali
])
```

---

## Test e Validazione

### Test 1: Clustering Spontaneo
**Setup**: Inizializza tutti i χᵢ a -4.5, applica perturbazione casuale ±0.1

**Aspettativa**:
- Alcuni segmenti collassano (χᵢ → -∞) → clustering SX
- Altri segmenti espandono (χᵢ → +∞) → vuoto DX
- Formazione di "grumi" di materia separati da spazio

### Test 2: Bounce Locale
**Setup**: Alcuni segmenti iniziano in collasso, altri in espansione

**Aspettativa**:
- Bounce NON sincroni
- Mentre segmento A ha bounce, segmento B continua a collassare
- "Respiro" del manifold: espansioni e contrazioni locali asincrone

### Test 3: Propagazione Torsione
**Setup**: Alta contorsione K² nel segmento 0, bassa negli altri

**Aspettativa**:
- Torsione si propaga ai vicini tramite accoppiamento
- Fronte d'onda di densità SX che viaggia lungo il manifold
- Solitoni "camminano" lungo la struttura a 24 segmenti

---

## Parametri Critici

```python
# Forza di accoppiamento tra segmenti
kappa_coupling = 0.1  # DEBOLE → anisotropia, clustering
                      # FORTE → omogeneità, comportamento globale

# Peso topologico nella chiralità
peso_curvatura = 0.5  # Quanto K² influenza densità locale

# Condizioni iniziali
chi_init_media = -4.5
chi_init_std = 0.5  # Variazione casuale iniziale
```

---

## Benefici Attesi

1. **Fisica Realistica**
   - Materia non uniforme (galassie, vuoti cosmici)
   - Bounce localizzati (fluttuazioni quantistiche)
   - Propagazione di perturbazioni (onde gravitazionali)

2. **Stabilità Numerica**
   - Accoppiamento diffusivo smorza instabilità
   - Bounce locali prevengono divergenze globali
   - Damping selettivo per segmento

3. **Emergenza di Complessità**
   - Auto-organizzazione spontanea
   - Pattern frattali nelle distribuzioni di densità
   - Transizioni di fase locali

---

**Autore**: Leonardo Peano con Claude (Senior Research Engineer mode)  
**Data**: 22 Maggio 2026  
**Versione**: 3.0 (Transizione a 24 Campi Locali)
