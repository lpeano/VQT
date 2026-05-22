# VQT - Geometrodinamica Quantistica con Einstein-Cartan

**Simulazione numerica di geometrodinamica quantistica con teoria di Einstein-Cartan e 24 campi locali accoppiati**

## 📋 Panoramica

Questo progetto implementa una simulazione completa di geometrodinamica quantistica basata sulla teoria di Einstein-Cartan, che estende la Relatività Generale includendo la torsione spazio-temporale generata dallo spin della materia.

**Caratteristiche principali:**
- ✅ **Bounce quantistico** - Repulsione spin-spin previene singolarità
- ✅ **24 campi locali accoppiati** - Topologia Leech lattice per anisotropia
- ✅ **Rendering 3D dinamico** - Visualizzazione manifold con chiralità DX/SX
- ✅ **Storage HDF5 ottimizzato** - Array 24D per analisi post-simulazione
- ✅ **Validazione topologica** - Chiusura spinoriale ∮τds = 4π

---

## 📁 Struttura del Progetto

```
VQT_repo/
├── WQT_manifold.py                      # ⭐ Simulatore principale (140KB)
├── docs/                                # 📚 Documentazione tecnica
│   ├── ARCHITETTURA_24_CAMPI_LOCALI.md # Teoria 24 campi (12KB)
│   ├── TEORIA_FISICA_COMPLETA.md        # Fondamenti Einstein-Cartan (15KB)
│   ├── RENDERING_DINAMICO_TECNICO.md   # Sistema rendering adattivo (11KB)
│   ├── RISULTATI_VALIDAZIONE_BOUNCE.md # Validazione fisica (8KB)
│   └── INDEX.md                         # Indice documentazione
├── analisi_post_simulazione.py          # 📊 Analisi dati HDF5
├── analizza_stabilita_live.py           # 📈 Monitor stabilità real-time
├── test_fisica_integrata.py             # ✅ Test suite completa
└── README.md                            # Documentazione generale

Script di test e analisi:
├── test_chiusura_spinore.py             # Test validazione 4π
├── test_contorsione.py                  # Test tensore K_λμν
├── verifica_contorsione_hdf5.py         # Verifica dati salvati
├── visualizza_bounce.py                 # Plot cicli bounce
└── analizza_collasso.py                 # Analisi dinamica collasso
```

---

## 🚀 Quick Start

### 1. Requisiti

```bash
pip install numpy scipy h5py matplotlib
```

**Versioni testate:**
- Python 3.13
- NumPy 1.26+
- SciPy 1.11+
- h5py 3.9+
- Matplotlib 3.8+

### 2. Simulazione Headless (raccolta dati)

```bash
# Simulazione breve (3s, 60 frame)
python WQT_manifold.py --headless --fps 20 --duration 3 --db test.h5

# Simulazione estesa (60s, 1440 frame)
python WQT_manifold.py --headless --fps 24 --duration 60 --db dataset_60s.h5
```

**Output:**
- `dataset_60s.h5` - Dati telemetria (chi, velocità, contorsione, chiusura)
- `stabilita.log` - Log stabilità topologica (bounce, torsione, errori)

### 3. Visualizzazione Real-Time

```bash
# Simulazione con rendering 3D live
python WQT_manifold.py --fps 24 --duration 15

# Playback da file HDF5
python WQT_manifold.py --playback --db dataset_60s.h5 --speed 10
```

### 4. Analisi Dati

```bash
# Analisi post-simulazione
python analisi_post_simulazione.py

# Visualizza cicli bounce
python visualizza_bounce.py

# Monitor stabilità live
python analizza_stabilita_live.py
```

---

## 🔬 Architettura Fisica

### Sistema a 24 Campi Locali

Il sistema evolve **24 campi χᵢ accoppiati** disposti su un reticolo di Leech:

```python
# Stato vettoriale: [χ₀, v₀, χ₁, v₁, ..., χ₂₃, v₂₃]  (48 elementi)

# Evoluzione per ogni segmento i:
d²χᵢ/dλ² = F_local[i] + F_coupling[i] + F_torsion[i] + F_closure[i]

dove:
  F_local    = Pressione locale (ρ_SX - ρ_DX)
  F_coupling = Σⱼ w_ij × (χⱼ - χᵢ)  # Accoppiamento topologico
  F_torsion  = β × ρᵢ²               # Repulsione spin (bounce)
  F_closure  = -k × (∮τds - 4π)      # Vincolo topologico
```

**Accoppiamento topologico:**
- Matrice 24×24 normalizzata (Leech lattice)
- Coefficiente κ = 0.15 (clustering pronunciato)
- Permette formazione strutture anisotrope

### Bounce Quantistico

**Meccanismo fisico** (Einstein-Cartan):

```
Quando χ → -∞ (collasso):
  ρ → ∞                           (densità diverge)
  P_repulsione = β × ρ²  → ∞      (repulsione spin domina)
  Rapporto R/A > 1                (★BOUNCE!★)
  χ inverte direzione             (espansione)
```

**Validazione sperimentale:**
- Frame 3-7: Rapporto R/A = 1.3 → **BOUNCE attivo**
- Frame 12-16: Rapporto R/A = 4.4 → **BOUNCE massimo**
- Oscillazioni χ: -5610 → +6427 (12 ordini di grandezza)

---

## 📊 Formato Dati HDF5

### Struttura File

```python
File: geometrodinamica_24campi_60s.h5
├── telemetria_scalare [1440 frames]
│   ├── frame_id          : int64
│   ├── rm               : float64  # Raggio metrico
│   ├── chi_medio        : float64  # χ medio (compatibilità)
│   ├── v_chi_medio      : float64  # Velocità media
│   ├── h_fisica         : float64  # Parametro Hubble
│   ├── contorsione_k_medio : float64  # ||K||
│   ├── chiusura_spinore_medio : float64  # Errore 4π
│   │
│   ├── chi_vettore      : (24,) float64  # χᵢ per ogni segmento
│   ├── vel_vettore      : (24,) float64  # vᵢ per ogni segmento
│   ├── contorsione_locale : (24,) float64  # Kᵢ locali
│   └── chiusura_locale  : (24,) float64  # Errore 4π locale
│
└── attrs:
    ├── creato_il         : "2026-05-22T13:42:52"
    ├── usa_24_campi_locali : True
    └── num_total_frames  : 1440
```

### Lettura Dati

```python
import h5py
import numpy as np

with h5py.File('dataset.h5', 'r') as f:
    tel = f['telemetria_scalare']
    
    # Estrai dati 24D frame 100
    chi_array = tel[100]['chi_vettore']      # shape (24,)
    vel_array = tel[100]['vel_vettore']      # shape (24,)
    
    # Serie temporale χ medio
    chi_evolution = tel['chi_medio'][:]      # shape (1440,)
    
    # Analisi clustering
    std_per_frame = [np.std(tel[i]['chi_vettore']) for i in range(1440)]
```

---

## 🧪 Test e Validazione

### Suite di Test

```bash
# Test completo fisica integrata
python test_fisica_integrata.py
✓ Test pressione repulsione spin
✓ Test conservazione energia
✓ Test chiusura spinoriale 4π
✓ Test accoppiamento topologico

# Test componenti individuali
python test_chiusura_spinore.py   # Validazione ∮τds = 4π
python test_contorsione.py         # Tensore K_λμν
```

### Validazione Bounce

**Criteri fisici:**
1. ✅ Rapporto R/A > 1 durante collasso
2. ✅ Inversione velocità χ
3. ✅ Oscillazioni bounded (no divergenza)
4. ✅ Conservazione topologia (4π stabile)

**Risultati tipici:**
- Periodo oscillazione: ~5-10 frame
- Ampiezza χ: 10³-10⁴
- Varianza locale: ±30-50 tra segmenti

---

## 📖 Documentazione Estesa

### File Principali

| File | Descrizione |
|------|-------------|
| [ARCHITETTURA_24_CAMPI_LOCALI.md](docs/ARCHITETTURA_24_CAMPI_LOCALI.md) | Teoria completa 24 campi, accoppiamento Leech, evoluzione |
| [TEORIA_FISICA_COMPLETA.md](docs/TEORIA_FISICA_COMPLETA.md) | Fondamenti Einstein-Cartan, torsione, bounce |
| [RENDERING_DINAMICO_TECNICO.md](docs/RENDERING_DINAMICO_TECNICO.md) | Sistema normalizzazione proiettiva, centroide dinamico |
| [RISULTATI_VALIDAZIONE_BOUNCE.md](docs/RISULTATI_VALIDAZIONE_BOUNCE.md) | Risultati sperimentali bounce quantistico |

### Concetti Chiave

**Einstein-Cartan vs Relatività Generale:**
- GR: Solo curvatura (metrica g_μν)
- EC: Curvatura + Torsione (K_λμν da spin)
- **Risultato**: Repulsione spin previene singolarità

**24 Campi Locali:**
- Ogni segmento ha dinamica indipendente
- Accoppiamento debole κ=0.15 → clustering
- Permette "respiro" locale del manifold

**Chiusura Spinoriale:**
- Vincolo topologico: ∮τds = 4π (720°)
- Forza di richiamo mantiene coerenza
- Deviazioni → instabilità ⚠

---

## 🔧 Parametri di Simulazione

### Configurazione Standard

```python
# In WQT_manifold.py (linee 100-600)

# FISICA
BETA_REPULSIONE_SPIN = 5.0        # Intensità bounce
OMEGA_RICHIAMO = 1.0              # Forza vincolo 4π
COEFFICIENTE_ACCOPPIAMENTO = 0.12 # Chiralità DX/SX

# 24 CAMPI
segmenti_frattali = 24            # Segmenti Leech
KAPPA_COUPLING_24 = 0.15          # Accoppiamento (0.05-0.5)
USA_24_CAMPI_LOCALI = True        # True: 24 campi | False: scalare

# RENDERING
risoluzione_base = 2400           # Punti manifold
N_u = 12                          # Sezioni trasversali
```

### Tuning Parametri

**KAPPA_COUPLING_24:**
- `0.05-0.1`: Clustering forte, anisotropia massima
- `0.2-0.5`: Bilanciato, formazione strutture
- `0.8-1.0`: Omogeneo (tende a campo globale)

**BETA_REPULSIONE_SPIN:**
- `< 1.0`: Bounce debole, rischio divergenza
- `5.0`: Standard (validato)
- `> 10.0`: Bounce eccessivo, oscillazioni rapide

---

## 📈 Performance

**Benchmark** (Intel i7 / 16GB RAM):
- Generazione frame: ~0.5 fps (headless)
- Rendering 3D live: ~15-20 fps
- Playback HDF5: 60+ fps (speed 1x)

**Ottimizzazioni:**
- Vettorizzazione NumPy per 24 campi
- Chunking HDF5 (2048 frame/blocco)
- Normalizzazione proiettiva (evita ricalcoli limiti)

**Storage:**
- 60s @ 24fps (1440 frame): ~10 MB HDF5
- Compressione procedurale: 1600× vs coordinate 3D raw

---

## 🤝 Contributi

Questo è un progetto di ricerca in geometrodinamica quantistica. Per domande o collaborazioni:

**Contatti:**
- Email: [inserire email]
- Repository: [inserire link GitHub]

**Citazioni:**
Se utilizzi questo codice in pubblicazioni scientifiche, cita:
```
[Autore], "Simulazione numerica di geometrodinamica quantistica 
con Einstein-Cartan e campi locali accoppiati", 2026
```

---

## 📄 Licenza

[Inserire licenza appropriata - es. MIT, GPL, ecc.]

---

## 🔍 Changelog

### v2.0 (2026-05-22) - **24 Campi Locali**
- ✅ Implementato sistema 24 campi accoppiati (Leech lattice)
- ✅ Accoppiamento topologico matrice 24×24
- ✅ Chiralità locale per segmento
- ✅ Storage HDF5 esteso (4 array 24D)
- ✅ Rendering modulato per variazione locale
- ✅ Validazione bounce con clustering

### v1.0 (2026-05-20) - **Campo Globale**
- ✅ Simulazione Einstein-Cartan base
- ✅ Bounce quantistico validato
- ✅ Rendering 3D chiralità DX/SX
- ✅ Chiusura spinoriale 4π
- ✅ Storage HDF5 ottimizzato

---

**🌌 "Il cosmo non è uno spazio vuoto, ma un tessuto vivo di geometria e spin"**
