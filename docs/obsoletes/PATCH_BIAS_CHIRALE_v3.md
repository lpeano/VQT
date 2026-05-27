# PATCH v3: Bias Chirale Amplificato per Rottura Simmetria
## Risoluzione "Universo Frustrato" (Var(χ) = 0)

**Data**: 2026-05-25  
**Versione**: v3.0 (post-analisi overflow, post-w(ρ), post-bias debole)  
**Problema risolto**: Campi congelati in configurazione simmetrica degenerata

---

## 🔴 PROBLEMA: "Universo Frustrato"

### Sintomi (Test v2, λ=0.002)

```
Frame 0-120:  Var(χ) = 0.00e+00  (TUTTI frame)
              Δχ = 1.42e-14       (precisione macchina, ZERO)
              Σχ = -108.96        (costante, mai cambia)
              E_coup = 0.00       (accoppiamento inattivo)
              STATUS: OMOGENEO     (NO separazione fasi)
```

### Diagnosi CTO

**Il sistema è in equilibrio metastabile ad alta simmetria**:

1. Tutti i 24 campi del Leech Lattice sono "impacchettati" nella stessa configurazione
2. Ogni tentativo di cadere nel pozzo (Materia SX, χ=-4.5) è contrastato dalla pressione dei campi adiacenti (Spazio DX, χ=+4.5)
3. Il bias chirale iniziale (λ=0.002) è **5 ordini di grandezza** troppo debole

**Analogia fisica**: Come cercare di far cadere una moneta di taglio in una stanza dove tutti spingono in direzioni opposte con forze uguali.

---

## 📊 ANALISI QUANTITATIVA: Forza Bias vs Forza Torsione

| Parametro | Valore | Calcolo |
|-----------|--------|---------|
| `Σχ` (somma campi) | -108.96 | Misurato |
| `E_tors` (energia torsione) | ~ 10³ - 10⁵ | Log flussi |
| `F_tors` (forza torsione) | √E_tors ≈ 316 | Stima ordine grandezza |

### Versione v2 (FALLITA): λ = 0.002

```
F_bias = λ · |Σχ| = 0.002 × 108.96 ≈ 0.22
Rapporto: F_bias / F_tors ≈ 0.22 / 316 ≈ 7×10⁻⁴
```

**Risultato**: Bias **1000× troppo debole** → campi non si muovono.

### Versione v3 (ATTUALE): λ = 2.0

```
F_bias = λ · |Σχ| = 2.0 × 108.96 ≈ 218
Rapporto: F_bias / F_tors ≈ 218 / 316 ≈ 0.7
```

**Risultato**: Bias **comparabile** a torsione → dovrebbe rompere simmetria.

---

## ✅ SOLUZIONE IMPLEMENTATA

### A. Amplificazione Bias Chirale (core_hamiltoniano.py)

**Funzione modificata**: `calcola_potenziale_multiscala()`

#### 1. Parametro λ aumentato

```python
# PRIMA (v2):
lambda_bias=0.002  # Troppo debole

# DOPO (v3):
lambda_bias=2.0    # 1000× più forte
```

#### 2. Termine di bias nel potenziale

```python
# Accoppiamento globale (rompe degenerazione)
somma_chi = np.sum(chi_vettore)  # Σχ (tutti i 24 campi)

# Potenziale bias (QUADRATICO in χ, LINEARE in forza)
V_bias = lambda_bias * somma_chi * chi_vettore  # λ·(Σχ)·χ_i

# Forza bias (COSTANTE per tutti i campi)
F_bias = -lambda_bias * somma_chi * np.ones(24)  # -λ·Σχ
```

**Fisica**:
- V_bias rompe simmetria χ → -χ (non è più invariante)
- F_bias è uguale per tutti i campi (forza "di campo medio")
- Preferenza energetica per configurazioni asimmetriche (Var(χ) > 0)

#### 3. Fase asimmetrica per ogni scala

```python
# Ogni scala ha ampiezza con fase naturale
fase_n = n * np.pi / 12.0  # 30° step (n=0,1,...,23)
A_n = A_0 * exp(-α·n) * (1 + 0.1·cos(fase_n))
```

**Effetto**: Impedisce "lock-in" di tutti i campi in fase (sincronizzazione forzata).

---

### B. Parametri Temporali Ridotti (WQT_manifold.py)

Per risolvere transizioni di fase fluide (non istantanee):

| Parametro | Prima | Dopo | Riduzione |
|-----------|-------|------|-----------|
| `d_tau_dinamico_base` | 0.02 | 0.01 | 2× |
| `delta_lambda` | 0.2 | 0.1 | 2× |

**Fisica**: Transizioni da χ=0 (massimo) a χ=±4.5 (minimi) richiedono alta risoluzione temporale per catturare la discesa nel pozzo inclinato.

---

### C. Fix Unicode (WQT_manifold.py)

| Vecchio | Nuovo | Motivo |
|---------|-------|--------|
| `⚠` | `[WARN]` | cp1252 Windows |
| `★BOUNCE!★` | `[BOUNCE]` | cp1252 Windows |
| `✓` | `OK` | cp1252 Windows |

---

## 🎯 RISULTATI ATTESI (v3)

Con λ=2.0 (forza bias comparabile a torsione):

### 1. Separazione Fasi ATTIVA

```
Frame 0:   Var(χ) = 0.00e+00  (configurazione iniziale)
Frame 10:  Var(χ) > 1.0e+00   (clustering inizia)
Frame 50:  Var(χ) > 1.0e+01   (separazione evidente)
Frame 100: Var(χ) > 5.0e+01   (clustering stabile)
```

### 2. Campi in Movimento

```
Δχ > 0.1 (variazioni misurabili)
Σχ variabile (non più costante)
Max|flux| > 1.0 (trasporto attivo tra regioni)
```

### 3. Energia Accoppiamento NON ZERO

```
E_coup > 0 (interazione tra campi attiva)
E_tors oscillante (redistribuzione energia)
```

### 4. Ciclo Completo

```
1. Contrazione (ρ↑, w≈-1/3)
2. Bounce (P_rep > P_grav)
3. Espansione (w→-1, ρ↓)
4. Clustering (Var(χ) cresce)
5. Raffreddamento (ρ→ρ_min)
6. Ritorno a (1)
```

---

## 📈 METRICHE DI SUCCESSO

| Metrica | v2 (FALLITO) | v3 (ATTESO) | Miglioramento |
|---------|--------------|-------------|---------------|
| Var(χ) @ 50 frame | 0.00e+00 | > 1.0e+01 | ∞ (da zero) |
| Δχ medio | 1.4e-14 | > 0.1 | 10¹³× |
| Max\|flux\| | 0.26 | > 1.0 | 4× |
| E_coup | 0.00 | > 1.0 | ∞ (da zero) |
| STATUS | OMOGENEO | CLUSTERING | Transizione |

---

## 🧪 VALIDAZIONE FISICA

### Conservazione Hamiltoniana

Anche con λ=2.0, il sistema rimane **puramente Hamiltoniano**:

```python
# VIETATO:
if chi[i] < 0:
    F[i] += bias  # ❌ Condizionale

# PERMESSO:
F_bias = -lambda_bias * np.sum(chi)  # ✅ Smooth, derivabile
```

### Limiti Termodinamici

1. **λ → 0**: Simmetria perfetta, Var(χ) = 0 (osservato in v2)
2. **λ ≈ F_tors**: Rottura simmetria, clustering spontaneo (v3)
3. **λ >> F_tors**: Bias domina, collasso su un solo minimo (non fisico)

**Scelta λ=2.0**: Nel regime (2), ottimale per separazione fasi.

---

## ⚠️ NOTE TECNICHE

### Perché λ·(Σχ)·χ e non λ·χ?

```python
# Opzione A: Bias locale (NON USATA)
V = λ * chi  # Rompe simmetria, ma NO accoppiamento globale

# Opzione B: Bias globale (IMPLEMENTATA)
V = λ * (np.sum(chi)) * chi  # Rompe simmetria + accoppiamento
```

**Motivo**: Con (B), il bias dipende dalla configurazione **globale** (Σχ), quindi:
- Configurazione simmetrica (Σχ≈0) → bias debole → stato metastabile
- Configurazione asimmetrica (Σχ≠0) → bias forte → stabilizza clustering

È un meccanismo di **auto-amplificazione** (feedback positivo controllato).

### Differenza da "Campo di Higgs"

| Higgs (Modello Standard) | Bias Chirale (WQT) |
|--------------------------|---------------------|
| Rottura spontanea | Rottura esplicita (λ≠0) |
| Simmetria gauge | Simmetria discreta (χ→-χ) |
| Bosone scalare | Campo spinoriale |
| Massa particelle | Preferenza Materia vs Spazio |

---

## 🚀 STATUS TEST

**File database**: `test_bias_forte.h5`  
**Durata**: 5 secondi (120 frame @ 24fps)  
**Processo**: PID 40748, avviato 11:57:28  
**Log attivi**: `stabilita.log`, `flussi_24campi.log`

**Comandi diagnostici**:
```powershell
# Verifica Var(χ)
Get-Content flussi_24campi.log | Select-String "Var\(chi\)" | Select-Object -First 20

# Verifica energia
Get-Content flussi_24campi.log | Select-String "E_tot" | Select-Object -First 20

# Verifica clustering
Get-Content flussi_24campi.log | Select-String "CLUSTERING" -Context 0,1
```

---

## ✅ CHECKLIST IMPLEMENTAZIONE

- [x] Bias chirale λ=2.0 nel potenziale multiscala
- [x] Fase asimmetrica A_n × (1 + 0.1·cos(n·π/12))
- [x] Passo temporale ridotto (dt: 0.02→0.01, δλ: 0.2→0.1)
- [x] Fix Unicode per compatibilità Windows
- [x] Documentazione tecnica completa
- [ ] **Test in esecuzione** (attesa risultati)
- [ ] Verifica Var(χ) > 10 @ frame 50
- [ ] Verifica clustering visibile in HDF5

---

**Firma**: Senior Physicist & Lead Software Engineer  
**Patch**: v3.0 - Bias Chirale Amplificato  
**Status**: ⏳ TEST IN CORSO (attesa 2-3 minuti)
