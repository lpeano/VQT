# ARCHITETTURA FRATTALE LIVELLO 2 - Documentazione Tecnica

## 1. OVERVIEW

Implementazione completa della gerarchia frattale WQT con supporto ricorsivo fino a Livello 2 (MacroSolitoni).

### Struttura Gerarchica

```
Livello 2 (MacroSolitone)
├─ 24 × SolitoneComposito (Livello 1)
│  └─ 24 × SegmentoQuantistico (Livello 0)
│     └─ 2 DOF (χ, v)
│
TOTALE: 576 segmenti, 1152 DOF
```

---

## 2. COMPONENTI IMPLEMENTATI

### 2.1 `PhysicsContext` - Scaling Gerarchico

**File:** `physics_context.py`

**Legge di Scaling:**
```python
alpha_K^(n) = alpha_K^(0) · (24²)ⁿ     # Scalabilità geometrica torsione
lambda_exchange^(n) = lambda_ex^(0) · (24²)ⁿ  # Proporzionale ad alpha_K
sigma_chi^(n) = sigma_chi^(0) · √(24)ⁿ
length_scale^(n) = L^(0) · √(24)ⁿ
```

**Rapporto Dominanza Energetica:**
```
λ/α_K = costante ≈ 0.005 (0.5%)
```

**Valori per Livello:**
| Livello | α_K          | λ_exchange    | λ/α_K    |
|---------|--------------|---------------|----------|
| 0       | 1.0          | 5.0           | 5.000    |
| 1       | 576          | 2,880         | 5.000    |
| 2       | 331,776      | 1,658,880     | 5.000    |

### 2.2 `SolitoneComposito` - Composite Pattern Ricorsivo

**File:** `solitone_composito.py`

**Caratteristiche:**
- ✅ Accetta sia `SegmentoQuantistico` che `SolitoneComposito` come children
- ✅ `compute_hamiltonian()` ricorsivo: somma energie interne + accoppiamento
- ✅ `compute_barycenter()`: centro di massa nel campo χ
- ✅ Interazioni basate su distanza tra baricentri (Livello 2+)
- ✅ **CLIP forze**: ±1e6 per evitare singolarità numeriche

**Hamiltoniana Ricorsiva:**
```python
H_total = Σ H_child + H_coupling + H_torsion + H_exchange

dove:
  H_child = ricorsivo (chiama .energia_totale di ogni child)
  H_coupling = κ · Σ W_ij · (χᵢ-χⱼ)²
  H_torsion = α_K · Σ W_ij · (χᵢ-χⱼ)²  (vincolo geometrico)
  H_exchange = -λ · α_K · Σ W_ij · tanh(χᵢ/χ₀) · tanh(χⱼ/χ₀)
```

**Forze con Protezione Numerica:**
```python
F_i = -κ·Σ W_ij·2(χᵢ-χⱼ) + λ·α_K·Σ W_ij·sech²(χᵢ/χ₀)·tanh(χⱼ/χ₀)/χ₀

# CLIP per stabilità
F_i = np.clip(F_i, -F_max, F_max)  # F_max = 1e6
```

### 2.3 `macro_solitone_factory.py` - Factory Pattern

**Funzioni Principali:**
- `build_level_0_cluster()`: 24 segmenti atomici
- `build_level_1_soliton()`: Composito Livello 1 (24 segmenti)
- `build_level_2_macro()`: MacroSolitone (24 compositi = 576 segmenti)
- `build_hierarchy(level)`: Costruttore generico fino a livello N
- `print_hierarchy_info()`: Ispezione ricorsiva

**Esempio d'Uso:**
```python
from macro_solitone_factory import build_level_2_macro

# Crea MacroSolitone con 576 segmenti
macro = build_level_2_macro(
    lambda_exchange=5.0,
    v_range=(-0.01, 0.01),  # Cold Start
    seed=42
)

print(f"Livello: {macro.physics.level}")
print(f"DOF totali: {macro.get_num_dof()}")
print(f"Energia: {macro.energia_totale:.6e}")
```

### 2.4 `run_frattale_l2.py` - Simulazione Livello 2

**Parametri Ottimizzati:**
```python
# Cold Start ULTRA-FREDDO
v_init ∈ [-0.01, 0.01]  # 10x più freddo di Livello 1

# Timestep ridotto per stabilità
dt = 0.0001  # 10x più piccolo (gestisce α_K ~ 331k)

# Cooling dinamico
gamma = 0.1    per step < 100  (dissipazione forte)
gamma = 0.001  per step ≥ 100  (conservazione)

# Screening adattivo locale
rho_threshold = 50.0  # Cluster auto-protetti

# Decadimento spaziale
W_ij = exp(-d_ij / L_eff), L_eff = 3.0
```

**Metriche Monitorate:**
- `H_conserved` drift (target: < 1e-7)
- Configurazione compositi materia/spazio
- Baricentri χ_center di ogni composito
- Bilancio energetico (H_total, E_radiated)

---

## 3. VINCOLI CRITICI IMPLEMENTATI

### 3.1 Stabilità Numerica

✅ **CLIP forze**: `np.clip(forces, -1e6, 1e6)`
   - Evita singolarità in regioni χ → 0
   - Previene overflow nel calcolo di tanh/sech²

✅ **Timestep adattivo**: dt(L2) = dt(L1) / 10
   - Richiesto da α_K(L2) = 576 × α_K(L1)
   - Mantiene stabilità simplettica

✅ **Regolarizzazione tanh**: χ₀ = 4.5 (valore vacuo)
   - Smooth replacement di sgn(χ)
   - Derivate continue ovunque

### 3.2 Conservazione Energia Ricorsiva

```python
# Livello 0 (SegmentoQuantistico)
H = T + V_potential

# Livello 1 (SolitoneComposito)
H = Σ H_child + E_coupling + E_torsion + E_exchange

# Livello 2 (MacroSolitone)
H = Σ H_composito_L1 + E_coupling_L2 + E_torsion_L2 + E_exchange_L2
```

**Verifica:**
```python
H_conserved = H_total + E_radiated = costante
|dH_conserved| / H < 1e-7  # Target conservazione
```

### 3.3 NO Forze di Torsione Dirette

⚠️ **Importante:** E_torsion è un **vincolo geometrico emergente**, NON genera forze dinamiche.

```python
# ✅ CORRETTO
F_i = -∂(E_coupling + E_exchange) / ∂χᵢ

# ❌ ERRATO (instabilità numerica!)
F_i = -∂(E_coupling + E_torsion + E_exchange) / ∂χᵢ
```

**Motivazione Fisica:**
- E_torsion = K² = (∇χ)² è proprietà della **connessione** (gradienti)
- Non è energia localizzata nei nodi
- Scalare α_K ~ 331k renderebbe forze insostenibili

---

## 4. WORKFLOW DI SIMULAZIONE

### 4.1 Test Rapido (200 step)

```bash
cd wqt_oop
python run_frattale_l2.py
```

**Output Atteso:**
```
COLD UNIVERSE FRATTALE L2
N_composites = 24 (576 segmenti)
alpha_K(L2) = 331,776
lambda_exchange(L2) = 1,658,880
dt = 0.0001

Step    H_total    E_rad    H_cons   M/S  Bary_mean  gamma
  20   8.22e6   -1.05e5   8.12e6   12/12   -0.02   0.100000
  40   7.98e6   -8.94e4   7.89e6   13/11   +0.15   0.100000
...
```

### 4.2 Produzione (1000+ step)

Modificare in `run_frattale_l2.py`:
```python
sim.run(
    N_steps=1000,
    dt=0.0001,
    cooling_steps=200,  # Cooling fino a step 200
    gamma_cool=0.1,
    gamma_conserve=0.001,
    log_interval=50
)
```

---

## 5. RISULTATI ATTESI

### 5.1 Golden Run Livello 1 (Riferimento)

```
N_segments = 24
Transizioni = 15
Configurazione finale = 15/9 (stabile 500 step)
H_conserved drift = 0.000000%
```

### 5.2 Obiettivi Livello 2

- **Conservazione**: drift < 1e-6 (ammesso leggero degrado vs L1)
- **Stabilità**: configurazione converge dopo cooling
- **Clustering**: baricentri χ_center mostrano separazione materia/spazio
- **NO esplosioni**: H_total rimane finito (CLIP protegge)

### 5.3 Metriche Diagnostiche

```python
# Carica risultati
data = np.load('fractal_l2_history.npz')

# Verifica conservazione
drift = abs(data['H_conserved'][-1] - data['H_conserved'][0])
drift_rel = drift / data['H_conserved'][0]
assert drift_rel < 1e-6

# Verifica convergenza configurazione
n_matter_final_100 = data['n_composites_matter'][-100:]
assert np.std(n_matter_final_100) < 1.0  # Configurazione stabile
```

---

## 6. ESTENSIONE A LIVELLO 3+

### 6.1 Scaling Risorse

| Livello | Compositi | Segmenti | DOF   | α_K        | dt      |
|---------|-----------|----------|-------|------------|---------|
| 1       | 24        | 24       | 48    | 576        | 0.001   |
| 2       | 24        | 576      | 1152  | 331,776    | 0.0001  |
| 3       | 24        | 13,824   | 27,648| 1.91e8     | 0.00001 |

### 6.2 Limitazioni Computazionali

**Livello 2**: fattibile su workstation (RAM ~ 2GB, 10 min/1000 step)
**Livello 3**: richiede cluster (RAM ~ 50GB, GPU consigliata)

---

## 7. RIFERIMENTI

- `wqt_oop/physics_context.py` - Scaling gerarchico
- `wqt_oop/solitone_composito.py` - Composite ricorsivo
- `wqt_oop/segmento_quantistico.py` - Atomi base
- `wqt_oop/macro_solitone_factory.py` - Factory pattern
- `wqt_oop/run_frattale_l2.py` - Simulazione L2
- `GOLDEN_RUN_V1.md` - Baseline Livello 1

---

## 8. CHANGELOG

**v2.0 (Livello 2)**
- ✅ Scaling lambda_exchange proporzionale ad alpha_K
- ✅ CLIP forze (±1e6) per stabilità numerica
- ✅ Cold Start ultra-freddo (v ∈ [-0.01, 0.01])
- ✅ Cooling esteso (100 step)
- ✅ Timestep ridotto (dt = 0.0001)
- ✅ Compute_barycenter() per interazioni L2+

**v1.0 (Livello 1 - Golden Run)**
- ✅ Conservazione perfetta (drift = 0%)
- ✅ Transizione di fase 9/15 → 15/9
- ✅ Clustering emergente (500 step stabili)
- ✅ Screening adattivo locale
- ✅ Decadimento spaziale W_ij
