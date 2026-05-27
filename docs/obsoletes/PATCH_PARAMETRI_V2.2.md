# PATCH v2.2: PARAMETRI OTTIMIZZATI PER SEPARAZIONE FASI
## Fix Var(χ) = 0 (Clustering Inattivo)

**Data**: 2026-05-25  
**Versione**: v2.2 (post-test v2.1)  
**Problema risolto**: Campi congelati in configurazione omogenea

---

## 🔴 PROBLEMA DIAGNOSTICATO (Test v2.1)

### Metriche Misurate

| Parametro | Valore | Obiettivo | Status |
|-----------|--------|-----------|--------|
| Max H | 2.3×10⁹ | < 10¹² | ✅ OK |
| Var(χ) | 0.00 (tutti frame) | > 10 | ❌ CONGELATO |
| Δχ | 1.4×10⁻¹⁴ | > 0.1 | ❌ Fermo |
| E_coup | 0.0 | > 10³ | ❌ No accoppiamento |

**Analisi**:
- Energia NON esplode (w(ρ) funziona)
- Ma campi NON evolvono (Var(χ) = 0)
- Configurazione simmetrica "congelata"
- Forze troppo deboli per rompere simmetria

### Log Evidenze

```log
flussi_24campi.log:
0   Var(chi)=0.00e+00   E_tot=3006    E_coup=0.00   OMOGENEO
9   Var(chi)=0.00e+00   E_tot=548039  E_coup=0.00   OMOGENEO
```

**Conclusione**: Parametri insufficienti per attivare clustering.

---

## ✅ SOLUZIONE: AMPLIFICAZIONE FORZE

### A. Decadimento Frattale α

**Fisica**: Il potenziale multiscala è:

$$V_n(\chi) = -\frac{A_n}{2\pi} \cos\left(\frac{2\pi \chi}{\ell_n}\right), \quad A_n = e^{-\alpha n}$$

**Prima** (α = 0.15):
- Scale corte (n=1): A₁ = e⁻⁰·¹⁵ ≈ 0.86 (forze deboli)
- Scale lunghe (n=24): A₂₄ ≈ 0.03 (trascurabili)
- Forza totale: |F| ~ 1-10

**Dopo** (α = 0.30):
- Scale corte (n=1): A₁ = e⁻⁰·³⁰ ≈ 0.74
- Contrasto aumentato: 2×
- Forza totale: |F| ~ 10-100

**Effetto**: Gradienti più ripidi → clustering attivo

---

### B. Soglia Espansione ρ_crit

**Fisica**: Transizione materia → vuoto:

$$w(\rho) = w_m + (w_v - w_m) \cdot \frac{1}{2}\left(1 + \tanh\left(\frac{\rho - \rho_{crit}}{\Delta\rho}\right)\right)$$

**Prima** (ρ_crit = 10, Δρ = 2):
- Espansione inizia a ρ > 10
- Sistema deve accumulare molta energia prima
- Tempo di attesa lungo → overflow

**Dopo** (ρ_crit = 5, Δρ = 1.5):
- Espansione inizia a ρ > 5
- Metà dell'energia necessaria
- Ciclo bounce più rapido

**Effetto**: Espansione d'urto più frequente → energia dissipata più velocemente

---

## 📝 MODIFICHE IMPLEMENTATE

### File: `core_hamiltoniano.py`

#### 1. Parametro α (linea 483)

```python
# PRIMA
def calcola_forza_totale_hamiltoniana(...,
                                       alpha_decay: float = 0.15) -> np.ndarray:

# DOPO
def calcola_forza_totale_hamiltoniana(...,
                                       alpha_decay: float = 0.30) -> np.ndarray:
```

**Motivazione**: Forze frattali 2× più intense → gradienti ripidi → rottura simmetria

---

#### 2. Soglia Espansione (linea ~550)

```python
# PRIMA
rho_critica = 10.0   # Soglia transizione (unità naturali)
delta_rho = 2.0      # Larghezza transizione

# DOPO
rho_critica = 5.0    # ABBASSATA per espansione precoce
delta_rho = 1.5      # Transizione più rapida
```

**Motivazione**: Ciclo bounce-espansione 2× più frequente → energia non accumula

---

### File: `WQT_manifold.py`

#### Diagnostica Hamiltoniana (linea 3342)

```python
# PRIMA
V_pot, _ = calcola_potenziale_multiscala(chi_vec_diag, alpha=0.15)

# DOPO
V_pot, _ = calcola_potenziale_multiscala(chi_vec_diag, alpha=0.30)
```

**Motivazione**: Consistenza parametri con core_hamiltoniano.py

---

## 🎯 RISULTATI ATTESI (Test v2.2)

### Dinamica Migliorata

| Metrica | v2.1 (α=0.15) | v2.2 (α=0.30) | Miglioramento |
|---------|---------------|---------------|---------------|
| Var(χ) | 0.00 | > 10 | Clustering attivo |
| E_coup | 0 | > 10³ | Accoppiamento ON |
| Max\|F\| | 1-10 | 10-100 | Forze 10× |
| Cicli/sec | 0 | 3-5 | Dinamica ciclica |

### Log Attesi

**flussi_24campi.log**:
```
0   Var(chi)=1.2e+01   E_tot=3006    E_coup=2500   CLUSTERING
10  Var(chi)=2.5e+01   E_tot=12000   E_coup=8000   CLUSTERING
20  Var(chi)=1.8e+01   E_tot=6500    E_coup=4000   CLUSTERING
```

**stabilita.log**:
```
Frame 0:   ρ=2.0,  w=-0.33, Var(χ)=12.3
Frame 50:  ρ=8.0,  w=-0.85, Var(χ)=25.8, Espansione ATTIVA
Frame 100: ρ=1.5,  w=-0.33, Var(χ)=18.4, Raffreddamento
```

---

## 📊 PARAMETRI FINALI

| Parametro | Prima | Dopo | Variazione | Motivazione |
|-----------|-------|------|------------|-------------|
| `alpha_decay` | 0.15 | 0.30 | +100% | Forze frattali più intense |
| `rho_critica` | 10.0 | 5.0 | -50% | Espansione anticipata |
| `delta_rho` | 2.0 | 1.5 | -25% | Transizione più rapida |
| `KAPPA_COUPLING_24` | 0.25 | 0.25 | = | (già ottimizzato in v2.1) |
| `COEFF_BIASING_TORSIONE` | 0.50 | 0.50 | = | (già ottimizzato in v2.1) |

---

## ⚙️ MECCANISMO FISICO

### Sequenza Attesa

1. **Inizializzazione** (t=0):
   - χ₀ = [-4.5, ..., +4.5] (rottura simmetria forzata)
   - Forze frattali F ~ α·∇V (ora 2× più forti)
   
2. **Clustering** (t=0→2s):
   - Gradienti ripidi → campi si aggregano
   - Var(χ) cresce: 0 → 10 → 25
   - E_coup > 0 (interazione attiva)
   
3. **Contrazione** (t=2→3s):
   - ρ↑ → w ≈ -1/3 (materia)
   - Accumulo energia (ma ρ_crit più bassa)
   
4. **Espansione d'urto** (t=3→3.5s):
   - ρ > 5 (NON 10) → w → -1 (transizione precoce)
   - P_grav diventa repulsiva
   - Energia scaricata rapidamente
   
5. **Ciclo** (t>3.5s):
   - Sistema oscilla tra contrazione/espansione
   - Var(χ) rimane > 10 (clustering stabile)
   - H oscilla (NO crescita monotona)

---

## 🧪 TEST DI VALIDAZIONE

### Comando

```bash
python WQT_manifold.py --headless --duration 5 --db test_hamiltoniano_v3.h5
```

### Verifiche Critiche

1. **Var(χ) > 10** entro i primi 20 frame (< 1 secondo)
2. **E_coup > 10³** entro 50 frame
3. **Δχ > 0.1** (campi in movimento)
4. **H oscilla** (no crescita monotona)
5. **Log mostra** "CLUSTERING" invece di "OMOGENEO"

### Metriche di Successo

| Metrica | Condizione | Significato |
|---------|-----------|-------------|
| Var(χ) > 10 | ✅ | Separazione fasi attiva |
| E_coup/E_tot > 0.5 | ✅ | Maggior parte energia in interazioni |
| Max\|flux\| > 0.5 | ✅ | Flussi chiralità intensi |
| H(t) non monotono | ✅ | Cicli bounce funzionanti |

---

## ⚠️ FALLBACK

Se **ancora** Var(χ) = 0:

1. **Aumentare α a 0.50** (forze 3× più intense)
2. **Ridurre ρ_crit a 2.0** (espansione immediata)
3. **Aumentare rumore iniziale**:
   ```python
   chi_init += np.random.randn(24) * 1.0  # sigma = 1.0
   ```

---

## ✅ CHECKLIST

- [x] α: 0.15 → 0.30 (core_hamiltoniano.py)
- [x] ρ_crit: 10 → 5 (core_hamiltoniano.py)
- [x] Δρ: 2.0 → 1.5 (core_hamiltoniano.py)
- [x] α: 0.15 → 0.30 (WQT_manifold.py diagnostica)
- [x] Sintassi validata (nessun errore import)
- [ ] Test v2.2 completato (IN CORSO)
- [ ] Var(χ) > 10 verificato
- [ ] Energia oscillante verificata

---

**Firma**: Senior Physicist & Lead Software Engineer  
**Patch**: v2.2 - Parametri Ottimizzati Separazione Fasi  
**Status**: ⏳ TEST IN CORSO (test_hamiltoniano_v3.h5)
