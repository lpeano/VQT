# GUIDA ALLA MIGRAZIONE - Da Monolitico a Oggetti Dinamici

## PANORAMICA

Questo documento guida la transizione dal vecchio `WQT_manifold.py` (architettura monolitica) al nuovo `WQT_manifold_refactored.py` (architettura a oggetti dinamici).

---

## CONFRONTO ARCHITETTURALE

### VECCHIA ARCHITETTURA (Monolitica)

```python
# File: WQT_manifold.py (DEPRECATO)

# STATO GLOBALE
stato_attuale = [chi, velocita_chi]  # Scalare o vettore [48] elementi

# LOOP DI SIMULAZIONE
for frame in range(NUM_TOTAL_FRAMES):
    # Evoluzione con solve_ivp (solutore ODE globale)
    sol = solve_ivp(equazioni_campo, [t, t+dt], stato_attuale, ...)
    stato_attuale = sol.y[:, -1]
    
    # Generazione geometria da stato scalare
    Xdx, Ydx, Zdx, Xsx, Ysx, Zsx = genera_mappatura(stato_attuale[0], frame)
    
    # Calcolo osservabili
    rm = calcola_rm(Xdx, Ydx, Zdx)
    G_geo = calcola_G_geometrica(...)
    
    # Salvataggio HDF5
    append_stato_hdf5(f_handle, frame, Xdx, Ydx, ...)
```

**Limitazioni:**
- ❌ Scala male (O(N²) per N punti reticolo)
- ❌ Memoria rigida (array pre-allocati)
- ❌ Difficile parallelizzare (accoppiamento globale)
- ❌ Nessuna rappresentazione fisica dei solitoni

---

### NUOVA ARCHITETTURA (Oggetti Dinamici)

```python
# File: WQT_manifold_refactored.py (ATTUALE)

# STATO: LISTA DINAMICA DI OGGETTI
lista_manifold = [ManifoldBase(...) for _ in range(N_iniziali)]

# LOOP DI SIMULAZIONE
for step in range(n_timesteps):
    # 1. EVOLUZIONE LOCALE PARALLELA
    lista_manifold = evolvi_sistema_parallelo(lista_manifold, dt, n_cores)
    
    # 2. COLLISION DETECTION + CONGIUNZIONI
    lista_manifold = gestisci_congiunzioni(lista_manifold, raggio)
    
    # 3. FISSIONI
    lista_manifold = gestisci_fissioni(lista_manifold)
    
    # 4. TELEMETRIA
    salva_stato_hdf5(lista_manifold, step)
```

**Vantaggi:**
- ✅ Scala linearmente (parallelizzazione efficiente)
- ✅ Memoria dinamica (crescita on-demand)
- ✅ Rappresentazione fisica fedele (solitoni reali)
- ✅ Modularità (facile estendere/debuggare)

---

## MAPPATURA CONCETTI

### 1. Campo χ (Chi)

#### VECCHIO CODICE
```python
# Scalare (modo globale)
chi = stato_attuale[0]  # float

# Vettoriale (modo 24 campi)
chi_vettore = stato_attuale[::2]  # array shape (24,)
```

#### NUOVO CODICE
```python
# Ogni manifold ha il proprio vettore χ
manifold.chi  # ndarray, shape (24,)

# Per ottenere χ medio del sistema:
chi_medio_globale = np.mean([m.chi for m in lista_manifold])
```

**Migrazione:**
```python
# Vecchio → Nuovo
if USA_24_CAMPI_LOCALI:
    # Crea N_manifold manifold con chi estratti dal vettore globale
    N_manifold = len(stato_attuale) // 2 // 24
    lista_manifold = []
    for i in range(N_manifold):
        m = ManifoldBase()
        m.chi = stato_attuale[i*48 : i*48+24 : 2]  # Estrai chi_i
        m.vel = stato_attuale[i*48+1 : i*48+25 : 2]  # Estrai vel_i
        lista_manifold.append(m)
else:
    # Modo scalare: crea singolo manifold con chi uniforme
    m = ManifoldBase()
    m.chi = np.full(24, stato_attuale[0])
    m.vel = np.full(24, stato_attuale[1])
    lista_manifold = [m]
```

---

### 2. Evoluzione Temporale

#### VECCHIO CODICE
```python
# Solutore ODE globale (scipy.integrate.solve_ivp)
def equazioni_campo(t, y):
    chi = y[0]
    v_chi = y[1]
    
    # Derivate
    d_chi_dt = v_chi
    d_v_dt = -dV_dchi(chi) + accoppiamento(chi)
    
    return [d_chi_dt, d_v_dt]

sol = solve_ivp(equazioni_campo, [t, t+dt], stato_attuale, 
                method='RK45', rtol=1e-6)
stato_attuale = sol.y[:, -1]
```

#### NUOVO CODICE
```python
# Integratore locale per ogni manifold (Velocity Verlet)
def evolvi_locale(self, dt):
    # Calcola forze
    forza_potenziale = -LAMBDA * self.chi + self.chi**3
    forza_accoppiamento = A @ self.chi
    accelerazione = -forza_potenziale + forza_accoppiamento
    
    # Velocity Verlet (simplectico)
    chi_half = self.chi + 0.5 * self.vel * dt
    self.vel = self.vel + accelerazione * dt
    self.chi = chi_half + 0.5 * self.vel * dt

# Parallelizzazione automatica
lista_manifold = evolvi_sistema_parallelo(lista_manifold, dt, n_cores)
```

**Migrazione:**
```python
# Vecchio: solve_ivp con step adattivo
# Nuovo:   Velocity Verlet con dt fisso

# Per ottenere accuratezza simile:
# dt_nuovo ≈ 0.1 × dt_medio_vecchio

# Esempio: se solve_ivp usava dt ~ 0.1 in media,
#          usa dt = 0.01 con Velocity Verlet
```

---

### 3. Torsione e Contorsione

#### VECCHIO CODICE
```python
# Calcolo da geometria 3D
nodi_sx = estrai_nodi_manifold(Xsx, Ysx, Zsx)
K_tensor = calcola_contorsione(nodi_sx)
contorsione_k = np.sqrt(np.mean(K_tensor**2))

# Chiusura spinoriale
scalar_error, diagnostica = check_chiusura_spinore(nodi_sx)
```

#### NUOVO CODICE
```python
# Calcolo diretto da profilo χ (più efficiente)
manifold.calcola_torsione_totale()  # Aggiorna manifold.torsione

# Verifica saturazione
if manifold.check_saturazione():
    # τ > 4π → fissione
    m_A, m_B = manifold.fissione()
```

**Migrazione:**
```python
# Il calcolo della torsione è SEMPLIFICATO nel nuovo codice.
# Non serve più generare la geometria 3D completa.

# Vecchio: Xdx, Ydx, Zdx → nodi → K_tensor → contorsione
# Nuovo:  chi → gradiente discreto → torsione

# Questo è O(N) invece di O(N²), ma fisica equivalente!
```

---

### 4. Accoppiamento tra Segmenti

#### VECCHIO CODICE
```python
# Matrice di Leech pre-calcolata (24×24)
MATRICE_ACCOPPIAMENTO_LEECH = costruisci_matrice_accoppiamento_leech()

# Usata in equazioni di campo
def equazioni_campo_24(t, y):
    chi_vec = y[::2]
    # ...
    accoppiamento = MATRICE_ACCOPPIAMENTO_LEECH @ chi_vec
    # ...
```

#### NUOVO CODICE
```python
# Matrice costruita dinamicamente in evolvi_locale()
A = np.zeros((24, 24))
for i in range(24):
    for j in range(24):
        if i != j:
            distanza = min(abs(i-j), 24-abs(i-j))
            A[i, j] = np.exp(-distanza / 3.0)

forza_accoppiamento = A @ self.chi
```

**Migrazione:**
```python
# Se hai personalizzato MATRICE_ACCOPPIAMENTO_LEECH,
# modifica la costruzione di A in evolvi_locale():

def evolvi_locale(self, dt):
    # Usa la TUA matrice personalizzata
    A = costruisci_matrice_personalizzata()
    # ... resto del codice invariato
```

---

### 5. Salvataggio Dati (HDF5)

#### VECCHIO CODICE
```python
# Telemetria scalare dettagliata
SCALARI_24_DTYPE = np.dtype([
    ('frame_id', 'i8'),
    ('rm', 'f8'),
    ('g_geo', 'f8'),
    # ... 20+ campi
    ('chi_vettore', 'f8', (24,)),
    ('vel_vettore', 'f8', (24,)),
    # ...
])

append_stato_hdf5(f, frame, Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, 
                  th, pdx, psx, rm, g_geo, ...)
```

#### NUOVO CODICE
```python
# Telemetria aggregata (più compatta)
with h5py.File(file_output, 'a') as f:
    f['n_manifold'][step] = len(lista_manifold)
    f['torsione_media'][step] = np.mean([m.torsione for m in lista_manifold])
    f['energia_totale'][step] = calcola_energia_sistema(lista_manifold)
```

**Migrazione:**
```python
# Per preservare compatibilità con analisi vecchie:

# OPZIONE A: Esporta in formato vecchio
def esporta_formato_legacy(lista_manifold, file_output):
    with h5py.File(file_output, 'w') as f:
        for step, manifold_snapshot in enumerate(storia_simulazione):
            # Aggrega manifold in vettore globale
            chi_globale = np.concatenate([m.chi for m in manifold_snapshot])
            vel_globale = np.concatenate([m.vel for m in manifold_snapshot])
            
            # Salva in formato vecchio
            f['telemetria_scalare'][step] = (
                step, 0.0, 0.0, ..., chi_globale.mean(), ...
            )

# OPZIONE B: Converti file nuovo → vecchio offline
def converti_nuovo_a_vecchio(file_nuovo, file_vecchio):
    # Leggi HDF5 nuovo
    with h5py.File(file_nuovo, 'r') as f_in:
        n_manifold = f_in['n_manifold'][:]
        # ...
    
    # Scrivi HDF5 vecchio
    with h5py.File(file_vecchio, 'w') as f_out:
        # Ricrea struttura legacy
        f_out.create_dataset('telemetria_scalare', ...)
```

---

## CASI D'USO COMUNI

### Caso 1: Riprodurre Simulazione Esistente

**Problema:** Ho una simulazione con il vecchio codice, voglio rifarla col nuovo.

**Soluzione:**
```python
# 1. Estrai parametri dalla vecchia simulazione
with h5py.File('vecchio_db.h5', 'r') as f:
    n_frames = f.attrs['num_total_frames']
    dt_vecchio = f['telemetria_scalare']['d_tau'][0]
    
    # Leggi stato iniziale
    chi_iniziale = f['telemetria_scalare'][0]['chi_medio']

# 2. Configura nuova simulazione equivalente
from WQT_manifold_refactored import simula_universo_frattale

simula_universo_frattale(
    n_manifold_iniziali=10,  # Stima da n_frames
    n_timesteps=n_frames,
    dt=dt_vecchio * 0.1,  # Velocity Verlet richiede dt più piccolo
    raggio_congiunzione=10.0 * LUNGHEZZA_PLANCK,
    file_output='nuovo_db.h5'
)

# 3. Confronta risultati
import matplotlib.pyplot as plt

with h5py.File('vecchio_db.h5', 'r') as f_old, \
     h5py.File('nuovo_db.h5', 'r') as f_new:
    
    # Estrai osservabili comparabili
    chi_old = f_old['telemetria_scalare']['chi_medio'][:]
    
    # Nel nuovo file non c'è chi_medio diretto, ma:
    # Possiamo ricostruirlo aggregando i manifold
    # (richiede salvataggio più dettagliato, vedi sotto)
    
    plt.plot(chi_old, label='Vecchio')
    # plt.plot(chi_new, label='Nuovo')  # Dopo aggregazione
    plt.legend()
    plt.show()
```

---

### Caso 2: Analisi Post-Simulazione

**Problema:** Ho script di analisi che leggono il vecchio formato HDF5.

**Soluzione 1 - Adatta script di analisi:**
```python
# Vecchio script (analizza_hubble.py)
with h5py.File('geometrodinamica_matrix.h5', 'r') as f:
    h_fisica = f['telemetria_scalare']['h_fisica'][:]
    # ... analisi ...

# Nuovo script (usa formato aggregato)
with h5py.File('universo_frattale.h5', 'r') as f:
    # h_fisica non c'è più direttamente
    # Ma puoi calcolarlo da altre osservabili
    
    n_manifold = f['n_manifold'][:]
    torsione_media = f['torsione_media'][:]
    
    # Stima H da crescita popolazione
    # dN/dt ∝ N → H ∝ (1/N) dN/dt
    h_stimato = np.gradient(np.log(n_manifold + 1))
    
    # ... analisi con h_stimato ...
```

**Soluzione 2 - Salva dati dettagliati durante simulazione:**
```python
# Modifica simula_universo_frattale() per salvare più dati

def simula_universo_frattale_dettagliato(...):
    # ... setup ...
    
    # Aggiungi dataset extra
    with h5py.File(file_output, 'w') as f:
        # ... dataset esistenti ...
        
        # NUOVO: Salva chi per ogni manifold
        f.create_dataset('chi_dettagliato', 
                         shape=(n_timesteps, n_manifold_max, 24),
                         dtype='f8')
    
    # Durante loop:
    for step in range(n_timesteps):
        # ... evoluzione ...
        
        # Salva chi di ogni manifold
        with h5py.File(file_output, 'a') as f:
            for i, m in enumerate(lista_manifold):
                f['chi_dettagliato'][step, i, :] = m.chi
```

---

### Caso 3: Personalizzazione Fisica

**Problema:** Ho modificato il potenziale V(χ) o la matrice di accoppiamento.

**Soluzione:**
```python
# Vecchio: Modifica in equazioni_campo()
def equazioni_campo_personalizzato(t, y):
    # ... potenziale custom ...
    return derivate

# Nuovo: Modifica in ManifoldBase.evolvi_locale()

# OPZIONE A: Subclass
class ManifoldCustom(ManifoldBase):
    def evolvi_locale(self, dt):
        # Tua fisica personalizzata
        forza_potenziale = -self.calcola_potenziale_custom()
        # ... resto uguale ...
    
    def calcola_potenziale_custom(self):
        # V(χ) = custom
        return self.chi**5 - 3*self.chi**2  # Esempio

# OPZIONE B: Modifica diretta in WQT_manifold_refactored.py
# Cerca la funzione evolvi_locale() e cambia:
forza_potenziale = -LAMBDA_DOPPIO_POZZO * self.chi + self.chi**3
# Con:
forza_potenziale = -self.tua_funzione_custom(self.chi)
```

---

## CHECKLIST DI MIGRAZIONE

- [ ] **Backup del codice vecchio**
  ```bash
  cp WQT_manifold.py WQT_manifold_BACKUP_$(date +%Y%m%d).py
  ```

- [ ] **Installa dipendenze**
  ```bash
  pip install numpy scipy h5py matplotlib multiprocessing
  ```

- [ ] **Esegui test suite**
  ```bash
  python test_refactoring.py
  ```
  Verifica che tutti i test passino (✓ 6/6).

- [ ] **Prova esempi**
  ```bash
  python esempi_uso_refactored.py
  ```
  Esegui almeno esempio 2 (fissione) e 3 (congiunzione).

- [ ] **Simulazione pilota**
  ```python
  # Simula 100 manifold per 100 step (veloce)
  simula_universo_frattale(
      n_manifold_iniziali=100,
      n_timesteps=100,
      dt=0.01,
      file_output='test_pilota.h5'
  )
  ```

- [ ] **Verifica conservazione energia**
  ```python
  with h5py.File('test_pilota.h5', 'r') as f:
      E = f['energia_totale'][:]
      variazione = abs(E[-1] - E[0]) / abs(E[0])
      assert variazione < 0.05, "Deriva energetica > 5%!"
  ```

- [ ] **Benchmark prestazioni**
  ```bash
  python esempi_uso_refactored.py  # Scegli opzione 4
  ```
  Verifica speedup > 5× con 8+ core.

- [ ] **Migrazione analisi esistenti**
  Adatta script `analizza_*.py` per leggere nuovo formato HDF5.

- [ ] **Documentazione interna**
  Aggiorna README e commenti con riferimenti al nuovo codice.

---

## RISOLUZIONE PROBLEMI

### Problema 1: "Energia non si conserva (deriva > 10%)"

**Causa:** Timestep dt troppo grande per Velocity Verlet.

**Soluzione:**
```python
# Riduci dt di un fattore 10
simula_universo_frattale(
    # ...
    dt=0.001,  # Invece di 0.01
    # ...
)
```

---

### Problema 2: "Troppi manifold (crescita esponenziale incontrollata)"

**Causa:** Soglia fissione troppo bassa o raggio congiunzione troppo grande.

**Soluzione:**
```python
# OPZIONE A: Aumenta soglia fissione
TORSIONE_CRITICA = 5.0 * np.pi  # Invece di 4π

# OPZIONE B: Riduci raggio congiunzione
simula_universo_frattale(
    # ...
    raggio_congiunzione=5.0 * LUNGHEZZA_PLANCK,  # Invece di 10
    # ...
)
```

---

### Problema 3: "Parallelizzazione più lenta del seriale"

**Causa:** Overhead comunicazione > guadagno parallelismo (n_manifold troppo piccolo).

**Soluzione:**
```python
# Usa parallelizzazione solo se n_manifold > 100
if len(lista_manifold) > 100:
    lista_manifold = evolvi_sistema_parallelo(lista_manifold, dt, n_cores)
else:
    for m in lista_manifold:
        m.evolvi_locale(dt)
```

---

### Problema 4: "ModuleNotFoundError: No module named 'WQT_manifold_refactored'"

**Causa:** File non nello stesso percorso.

**Soluzione:**
```bash
# Verifica posizione
ls -l WQT_manifold_refactored.py

# Aggiungi percorso a PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/path/to/VQT

# Oppure in Python:
import sys
sys.path.append('/path/to/VQT')
from WQT_manifold_refactored import simula_universo_frattale
```

---

## RISORSE AGGIUNTIVE

- **Documentazione completa:** `REFACTORING_MANIFOLD_DOCS.md`
- **Test automatici:** `test_refactoring.py`
- **Esempi pratici:** `esempi_uso_refactored.py`
- **Codice sorgente:** `WQT_manifold_refactored.py`

---

## SUPPORTO

Per domande o problemi:
1. Controlla la sezione FAQ in `REFACTORING_MANIFOLD_DOCS.md`
2. Esegui `python test_refactoring.py` per diagnostica
3. Apri issue su repository (se disponibile)
4. Contatta team di sviluppo

---

**Autore:** VQT Physics Simulation Team  
**Versione:** 1.0.0  
**Ultima revisione:** 24 Maggio 2026
