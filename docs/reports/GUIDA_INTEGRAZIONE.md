# GUIDA INTEGRAZIONE DINAMICA HAMILTONIANA

## 📦 File Creati

1. **`dinamica_hamiltoniana_chiralita.py`** - Implementazione fisica hamiltoniana
2. **`test_dinamica_hamiltoniana.py`** - Script di validazione
3. **`GUIDA_INTEGRAZIONE.md`** - Questo documento

---

## 🎯 Obiettivo

Sostituire la logica di aggiornamento **globale omogenea** con un sistema di **trasporto locale** guidato dalla minimizzazione dell'energia di accoppiamento torsionale, permettendo la **separazione spontanea delle fasi** materia/spazio.

---

## ⚛️ Fisica Implementata

### Hamiltoniana del Sistema

```
E_tot = E_coupling + E_torsion

E_coupling[i] = α × Σⱼ w_ij × (K²_i - K²_j)²
E_torsion[i]  = β × (K²_i - 4π)²
```

### Equazioni di Trasporto

```
dρ_SX[i]/dt = -μ × ∂E/∂ρ_SX[i] + diffusione + attrazione_torsionale

dove:
- ∂E/∂ρ ≈ gradiente energia tra vicini
- attrazione_torsionale = f(K² - 720°)
- diffusione = D × ∇²ρ
```

### Conservazione

```
Σᵢ (ρ_SX[i] + ρ_DX[i]) = costante (globale)
```

---

## 🔧 Integrazione in WQT_manifold.py

### STEP 1: Importa Modulo

All'inizio di `WQT_manifold.py`, dopo gli altri import:

```python
# NUOVA DINAMICA HAMILTONIANA
from dinamica_hamiltoniana_chiralita import (
    update_dinamica_chiralita,
    calcola_energia_sistema
)
```

### STEP 2: Modifica Loop di Evoluzione

Trova la funzione `update(idx_frame, ...)` intorno alla linea ~2300.

**PRIMA** (codice attuale):

```python
# Calcola densità da chiralità globale
densita_dx, densita_sx = calcola_chiralita_locale_24_segmenti(
    nodi_sx, nodi_dx, chi_vettore,
    contorsione_k_vettore, errore_spinore_vettore
)

# Clip artificiale (VECCHIO METODO)
densita_sx = np.clip(densita_sx, 0, 100)
densita_dx = np.clip(densita_dx, 0, 100)
```

**DOPO** (nuovo sistema hamiltoniano):

```python
# ========================================================================
# NUOVA DINAMICA: Trasporto Hamiltoniano di Chiralità
# ========================================================================
# Aggiorna densità attraverso minimizzazione energia
densita_sx, densita_dx, flussi_step = update_dinamica_chiralita(
    stato_attuale=estado_vettoriale,
    dt=d_tau,
    matrice_accoppiamento=MATRICE_ACCOPPIAMENTO_LEECH,
    contorsione_locale=contorsione_k_vettore
)

# Logging flussi (aggiorna globale per output)
global flussi_netto_SX_globale, varianza_chi_globale
flussi_netto_SX_globale = flussi_step.copy()
varianza_chi_globale = np.var(chi_vettore)

# NO CLIP ARTIFICIALE! (protezione è dalla barriera di potenziale)
# densita_sx e densita_dx già protetti in update_dinamica_chiralita
```

### STEP 3: Aggiorna Logging Flussi

Nella sezione dove scrivi `flussi_24campi.log` (intorno alla linea ~2400):

```python
# Log stato termodinamico
if idx_frame % 10 == 0:  # Ogni 10 frames
    with open(log_flussi_path, "a") as f:
        varianza_flussi = np.var(flussi_netto_SX_globale)
        flusso_max = np.max(np.abs(flussi_netto_SX_globale))
        
        # Calcola energia totale sistema
        E_tot, E_coup, E_tors = calcola_energia_sistema(
            densita_sx, densita_dx,
            contorsione_k_vettore,
            MATRICE_ACCOPPIAMENTO_LEECH
        )
        
        f.write(f"Frame {idx_frame:5d}: "
                f"Var(χ)={varianza_chi_globale:8.2e}  "
                f"Var(flux)={varianza_flussi:8.2e}  "
                f"E_tot={E_tot:10.2f}  "
                f"Max|flux|={flusso_max:6.3f}\n")
```

### STEP 4: Rimuovi Clip Artificiali

Cerca e **RIMUOVI** tutti i `np.clip()` su densità:

```python
# RIMUOVI QUESTE RIGHE:
# densita_sx = np.clip(densita_sx, ...)
# densita_dx = np.clip(densita_dx, ...)
# densita_materia = np.clip(densita_materia, ...)
```

La protezione è ora garantita dalla **barriera di potenziale** (K² > 720°) e dal `np.maximum(ρ, 0)` interno alla funzione hamiltoniana.

---

## 🧪 Validazione Prima dell'Integrazione

**OBBLIGATORIO**: Esegui il test di validazione:

```bash
cd C:\Users\lpeano\plank\VQT
python test_dinamica_hamiltoniana.py
```

**Output atteso:**

```
✓ TEST 1: Energia minimizzata
✓ TEST 2: Carica conservata
✓ TEST 3: Clustering formato
✓ TEST 4: Numericamente stabile

RISULTATO: 4/4 test superati

🎉 VALIDAZIONE COMPLETA: Sistema pronto per integrazione!
```

Se vedi `4/4 test superati` → **PROCEDI CON INTEGRAZIONE**  
Se vedi `<4 test` → **AGGIUSTA PARAMETRI** (vedi sezione sotto)

---

## ⚙️ Tuning Parametri (se necessario)

Se i test non passano, modifica in `dinamica_hamiltoniana_chiralita.py`:

### Problema: Energia NON minimizzata

```python
# Aumenta coefficiente trasporto
MU_TRANSPORT = 0.35  # Da 0.25 → 0.35 (flussi più veloci)
```

### Problema: Carica NON conservata

```python
# Riduci diffusività
DIFFUSIVITA = 0.01  # Da 0.02 → 0.01 (meno perdite)
```

### Problema: Clustering debole

```python
# Aumenta accoppiamento torsionale
ALPHA_COUPLING = 0.08  # Da 0.05 → 0.08 (più attrazione)
```

### Problema: Instabilità numerica

```python
# Riduci mobilità
MU_TRANSPORT = 0.15  # Da 0.25 → 0.15 (evoluzione più lenta)
DIFFUSIVITA = 0.01   # Da 0.02 → 0.01 (più smoothing)
```

---

## 📊 Test Post-Integrazione

Dopo aver integrato in `WQT_manifold.py`:

### Test Breve (3 secondi)

```bash
python WQT_manifold.py --headless --fps 24 --duration 3 --db test_hamiltoniano.h5
```

**Verifica in `flussi_24campi.log`:**

- `Var(χ)` deve **crescere** nel tempo (clustering)
- `E_tot` deve **diminuire** o stabilizzarsi
- `Max|flux|` deve rimanere **< 10** (stabilità)

### Test Medio (30 secondi)

```bash
python WQT_manifold.py --headless --fps 24 --duration 30 --db test_hamiltoniano_30s.h5
```

**Analizza log:**

```bash
python -c "
import re
with open('flussi_24campi.log', 'r') as f:
    lines = f.readlines()
    
print('Primi 5 frames:')
for line in lines[:5]:
    print(line.strip())
    
print('\nUltimi 5 frames:')
for line in lines[-5:]:
    print(line.strip())
"
```

**Successo se:**
- Varianza χ aumenta (separazione fasi)
- Energia diminuisce o stabile
- Nessun `NaN` o `Inf`

---

## 🎨 Visualizzazione Playback

Dopo simulazione riuscita:

```bash
python WQT_manifold.py --playback --db test_hamiltoniano_30s.h5 --speed 5
```

**Cosa osservare:**
- **Clustering locale**: Zone colorate (alta densità SX) vs zone scure (bassa SX)
- **Bounce asincrono**: Regioni diverse rimbalzano in tempi diversi
- **Propagazione onde**: Perturbazioni si diffondono tra segmenti vicini

---

## 📈 Metriche di Successo

| Metrica | Obiettivo | Metodo Verifica |
|---------|-----------|-----------------|
| **Separazione Fasi** | Var(χ) cresce >100% | `flussi_24campi.log` |
| **Minimizzazione E** | E_tot finale < E_tot iniziale | `flussi_24campi.log` |
| **Conservazione Q** | \|ΔQ\| < 1e-6 | Verifica manuale log |
| **Clustering** | >30% segmenti con ρ_SX >> media | Playback visivo |
| **Stabilità** | Max\|flux\| < 10 | `flussi_24campi.log` |

---

## 🚨 Troubleshooting

### Errore: `ImportError: No module named dinamica_hamiltoniana_chiralita`

**Soluzione:**
```bash
cd C:\Users\lpeano\plank\VQT
# Verifica che il file esista
dir dinamica_hamiltoniana_chiralita.py
```

### Errore: `MATRICE_ACCOPPIAMENTO_LEECH not defined`

**Soluzione:**  
Assicurati che la matrice sia costruita all'inizio di `WQT_manifold.py`:

```python
# Dopo linea 450 circa
if USA_24_CAMPI_LOCALI:
    MATRICE_ACCOPPIAMENTO_LEECH = costruisci_matrice_accoppiamento_leech()
```

### Warning: `RuntimeWarning: divide by zero`

**Soluzione:**  
Verifica che le densità non siano mai esattamente zero. In `update_dinamica_chiralita()` c'è già protezione:

```python
if densita_sx_nuova[i] + densita_dx_nuova[i] < 1e-10:
    densita_sx_nuova[i] = 0.5
    densita_dx_nuova[i] = 0.5
```

### Energia aumenta invece di diminuire

**Possibili cause:**
1. `MU_TRANSPORT` troppo alto → Riduci a 0.15
2. Timestep `dt` troppo grande → WQT_manifold usa solver Radau (adattivo), dovrebbe andare bene
3. Torsione locale non aggiornata correttamente → Verifica che `contorsione_k_vettore` sia calcolato PRIMA di chiamare `update_dinamica_chiralita()`

---

## 📚 Riferimenti Teorici

### Fisica della Separazione Fasi

- **Spinodal Decomposition**: Sistema instabile si separa spontaneamente in fasi
- **Cahn-Hilliard Equation**: Equazione di diffusione con termine di accoppiamento non-locale
- **Energia Libera di Landau**: F = ∫[½(∇φ)² + f(φ)]dV

### Analogia con WQT

| Cahn-Hilliard | WQT Hamiltoniano |
|---------------|------------------|
| φ (campo ordine) | ρ_SX (densità materia) |
| ∇²φ (diffusione) | Laplaciano discreto |
| f(φ) (energia bulk) | E_torsion (K² - 720°)² |
| Accoppiamento ∇φ | Accoppiamento topologico w_ij |

### Torsione come Potenziale

L'equazione Einstein-Cartan permette torsione K ≠ 0 quando c'è spin/chiralità.

**Nel nostro modello:**
- K² < 720° (4π): Stato normale
- K² ≥ 720°: Barriera repulsiva → la materia **non può** entrare facilmente
- **MA**: se materia è già presente con K² > 720°, viene **intrappolata** (pozzo di potenziale)

Questo crea **bistabilità**:
- Zone vuote → K² basso → difficile accumulare materia
- Zone piene → K² alto → materia intrappolata → clustering stabile

---

## ✅ Checklist Integrazione

- [ ] File `dinamica_hamiltoniana_chiralita.py` creato
- [ ] File `test_dinamica_hamiltoniana.py` creato
- [ ] Test di validazione eseguito (`4/4 test superati`)
- [ ] Import aggiunto in `WQT_manifold.py`
- [ ] Loop `update()` modificato con nuova dinamica
- [ ] Clip artificiali rimossi
- [ ] Logging flussi aggiornato
- [ ] Test breve (3s) eseguito e passato
- [ ] Test medio (30s) eseguito e analizzato
- [ ] Playback visivo verificato (clustering presente)
- [ ] File copiati in `VQT_repo/` per backup

---

## 🎓 Prossimi Passi (Opzionale)

### Estensione 1: Accoppiamento Spin-Torsione

Modifica `update_dinamica_chiralita()` per includere:

```python
# Torsione indotta da gradiente chiralità
contorsione_indotta = GAMMA_SPIN * (densita_sx - densita_dx)
contorsione_totale = contorsione_locale + contorsione_indotta
```

### Estensione 2: Analisi Spettrale

Analizza autovalori della matrice jacobiana per predire instabilità:

```python
from scipy.linalg import eig

# Jacobiano del sistema
J = calcola_jacobiano(densita_sx, densita_dx, contorsione)
eigenvalues, _ = eig(J)

# Se Re(λ) > 0 → instabilità (separazione fasi)
print(f"Max Re(λ): {np.max(eigenvalues.real)}")
```

### Estensione 3: Temperatura Effettiva

Introduci fluttuazioni termiche:

```python
T_eff = 0.05  # Temperatura adimensionale
noise = np.sqrt(2 * T_eff * dt) * np.random.randn(24)
flussi_netto += noise
```

---

**Fine Guida**

Per domande o problemi, consulta i commenti in `dinamica_hamiltoniana_chiralita.py` o verifica i log generati durante l'esecuzione.
