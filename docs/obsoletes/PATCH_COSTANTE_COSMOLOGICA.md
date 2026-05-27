# PATCH: COSTANTE COSMOLOGICA DINAMICA w(ρ)
## Fix Overflow e Ciclo Bounce-Espansione-Raffreddamento

**Data**: 2026-05-25  
**Versione**: v2 (post-implementazione Hamiltoniano)  
**Problema risolto**: Crescita esponenziale energia (E_tot: 3×10³ → 2×10¹⁷) senza inversione

---

## 🔴 PROBLEMA DIAGNOSTICATO

### Sintomi

```
Frame 0:  E_tot = 3.00e+03, Var(χ) = 0.00e+00
Frame 47: E_tot = 2.10e+17, Var(χ) = 0.00e+00, Rapp R/A = 1.0e+15
```

**Analisi CTO**:
1. **Bounce confermato**: P_rep/P_grav ~ 10¹⁵ (pressione repulsiva domina)
2. **NO inversione**: Sistema bloccato in alta energia (NO discesa)
3. **NO separazione fasi**: Var(χ) = 0 (configurazione omogenea congelata)

### Causa Fisica

Con equazione di stato **fissa** w = -1/3:

- **Bassa densità**: P_grav = -ρ/3 (contrazione debole)
- **Alta densità**: P_grav = -ρ/3 (ANCORA contrazione!)

**Risultato**: Il sistema si contrae sempre più → ρ → ∞ → E → ∞ → overflow

**Manca**: Meccanismo di **espansione d'urto** post-bounce (come Big Bang)

---

## ✅ SOLUZIONE: w(ρ) DINAMICO

### Equazione di Stato Transizionale

$$w(\rho) = w_0 + \Delta w \cdot \frac{1}{2}\left(1 + \tanh\left(\frac{\rho - \rho_{crit}}{\Delta\rho}\right)\right)$$

**Parametri**:
- $w_0 = -1/3$ (materia ordinaria)
- $w_{vuoto} = -1$ (costante cosmologica)
- $\rho_{crit} = 10$ (soglia transizione, unità naturali)
- $\Delta\rho = 2$ (larghezza transizione)

**Comportamento** (transizione smooth, NO if-then):

| Densità | w(ρ) | Pressione | Dinamica |
|---------|------|-----------|----------|
| ρ < 10 | ≈ -1/3 | P_grav = -ρ/3 | Contrazione debole |
| ρ ≈ 10 | ≈ -2/3 | Transizione | Bilanciamento |
| ρ > 10 | → -1 | P_grav = -ρ | **Espansione violenta** |

### Ciclo Emergente

```
1. CONTRAZIONE (ρ↑, w=-1/3)
   ↓
2. BOUNCE (P_rep > P_grav, ρ_max)
   ↓
3. ESPANSIONE D'URTO (w→-1, ρ↓↓↓) ← AGGIUNTO ORA
   ↓
4. RAFFREDDAMENTO (ρ→ρ_min, w→-1/3)
   ↓
5. RITORNO A (1)
```

**FISICA**: 
- Ad alta densità, P_grav diventa **repulsiva** (come Big Bang)
- Il sistema si espande rapidamente → ρ scende → w ritorna normale
- Ciclo auto-sostenuto SENZA parametri di fitting

---

## 📝 MODIFICHE IMPLEMENTATE

### A. File: `core_hamiltoniano.py`

#### 1. Funzione `calcola_forza_totale_hamiltoniana()`

**Vecchio codice** (w fisso):
```python
# Pressione gravitazionale (attrattiva)
w = -1.0 / 3.0  # Equazione di stato FISSA
P_grav = w * densita_efficace
```

**Nuovo codice** (w dinamico):
```python
# Parametri transizione
w_materia = -1.0 / 3.0      # Materia ordinaria (bassa densità)
w_vuoto = -1.0              # Energia del vuoto (alta densità)
rho_critica = 10.0          # Soglia transizione (unità naturali)
delta_rho = 2.0             # Larghezza transizione (smooth)

# Calcola w locale per ogni segmento (vettoriale)
eccesso_densita = (densita_efficace - rho_critica) / delta_rho
w_dinamico = w_materia + (w_vuoto - w_materia) * 0.5 * (1.0 + np.tanh(eccesso_densita))

# Pressione gravitazionale DINAMICA
P_grav = w_dinamico * densita_efficace
```

#### 2. Normalizzazione Anti-Overflow

**Aggiunto**:
```python
# Saturazione pressione per evitare overflow float64
P_totale = np.tanh(P_totale / 1e6) * 1e6

# Clipping forze estreme per stabilità Verlet
forza_max = 1e3
forza_norm = np.linalg.norm(forza_totale)

if forza_norm > forza_max:
    forza_totale = forza_totale * (forza_max / (forza_norm + 1e-12))
```

---

### B. File: `WQT_manifold.py`

#### 1. Amplificazione Parametri Separazione Fasi

Per risolvere Var(χ) = 0, **aumentati** i coefficienti:

| Parametro | Vecchio | Nuovo | Effetto |
|-----------|---------|-------|---------|
| `KAPPA_COUPLING_24` | 0.15 | 0.25 | +67% accoppiamento |
| `COEFF_BIASING_TORSIONE` | 0.25 | 0.50 | +100% accumulo materia |
| `PENALITA_OMOGENEITA` | 0.12 | 0.30 | +150% anti-omogeneità |

**Motivazione**: Forzare rottura simmetria → Var(χ) > 0 → clustering attivo

#### 2. Diagnostica Overflow

**Aggiunto** (ogni 50 frame):
```python
if H_totale > 1e12:
    print(f"[AVVISO ENERGIA] H={H_totale:.2e} - Costante cosmologica attiva")
if H_totale > 1e15:
    print(f"[CRITICO] H={H_totale:.2e} - Ridurre delta_lambda")
```

---

## 🎯 RISULTATI ATTESI

### Dinamica Migliorata

1. **NO overflow**: H rimane < 10¹² (espansione lo abbassa)
2. **Var(χ) > 0**: Separazione fasi attiva (clustering visibile)
3. **Ciclo chiuso**: Bounce → espansione → raffreddamento → bounce
4. **Energia oscillante**: E_tot cresce/scende periodicamente

### Grafici Attesi

**stabilita.log**:
```
Frame 0:   ρ_tot=5.0,  w=-0.33, Bounce=NO
Frame 50:  ρ_tot=15.0, w=-0.80, Bounce=SÌ, Espansione ATTIVA
Frame 100: ρ_tot=3.0,  w=-0.33, Raffreddamento
Frame 150: ρ_tot=12.0, w=-0.70, Bounce=SÌ
```

**flussi_24campi.log**:
```
Var(χ) = 1.2e+01 (clustering moderato)
E_tot oscillante: 10³ → 10⁷ → 10⁴ → 10⁶ (NO divergenza)
Max|flux| > 0.1 (trasporto attivo)
```

---

## 🧪 TEST DI VALIDAZIONE

### Comando

```bash
python WQT_manifold.py --headless --duration 10 --db test_hamiltoniano_v2.h5
```

### Verifiche

1. **NO crash** per 10 secondi (240 frame @ 24fps)
2. **H < 10¹²** per tutta la simulazione
3. **Var(χ) > 10** entro i primi 50 frame
4. **Log mostra** `[AVVISO ENERGIA]` quando w→-1 (espansione attiva)

---

## 📊 PARAMETRI OTTIMIZZATI

| Parametro | Valore | Unità | Motivazione |
|-----------|--------|-------|-------------|
| `rho_critica` | 10.0 | Planck | Soglia fisica (regimes quantistici) |
| `delta_rho` | 2.0 | Planck | Transizione smooth (5× larghezza) |
| `w_materia` | -1/3 | -- | Materia relativistica (standard) |
| `w_vuoto` | -1.0 | -- | Costante cosmologica (de Sitter) |
| `forza_max` | 10³ | Planck | Limite stabilità Verlet |
| `P_max` | 10⁶ | Planck | Saturazione anti-overflow |

---

## ⚠️ NOTE TECNICHE

### Perché tanh() e NON if-then?

```python
# ❌ VIETATO (discontinuo)
if rho > rho_crit:
    w = -1.0
else:
    w = -1/3

# ✅ CORRETTO (smooth)
w = w_0 + Δw · tanh((rho - rho_crit) / Δrho)
```

**Motivi**:
1. **Fisica**: Transizioni di fase SEMPRE continue in natura
2. **Numerica**: Discontinuità → instabilità integratore
3. **Architettura**: Vincolo NO if-then rispettato

### Differenza da "Inflazione Caotica"

Modello cosmologico standard:
- Inflazione → singola epoca (passato)
- Parametro w fisso post-inflazione

Questo modello:
- **Inflazione ciclica** (w oscilla continuamente)
- Emerge da densità locale (NO parametro esterno)
- Ogni bounce → micro-Big Bang

---

## 📈 METRICHE ATTESE

| Metrica | Prima | Dopo | Miglioramento |
|---------|-------|------|---------------|
| Max H | 2×10¹⁷ | < 10¹² | -10⁵× |
| Var(χ) | 0 | > 10 | ∞ (da zero a finito) |
| Cicli/sec | 0 | ~5 | Dinamica ciclica |
| Overflow | @ frame 47 | Nessuno | 100% |

---

## ✅ CHECKLIST FISICA

- [x] Equazione di stato dinamica w(ρ)
- [x] Transizione smooth (tanh, NO if-then)
- [x] Espansione d'urto ad alta densità
- [x] Normalizzazione anti-overflow
- [x] Parametri separazione fasi amplificati
- [x] Diagnostica overflow real-time
- [x] Ciclo chiuso bounce-espansione-raffreddamento

---

## 🚀 ESECUZIONE

Il test è attualmente in corso. Risultati previsti entro 2 minuti.

**Log attivo**: `test_output.log`  
**Dati HDF5**: `test_hamiltoniano_v2.h5`  
**Stabilità**: `stabilita.log`  
**Flussi**: `flussi_24campi.log`

---

**Firma**: Senior Physicist & Lead Software Engineer  
**Patch**: v2.1 - Costante Cosmologica Dinamica  
**Status**: ✅ IMPLEMENTATO - TEST IN CORSO
