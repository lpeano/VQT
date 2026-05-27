# WQT MANIFOLD - VERSIONE INTEGRATA

## 🎯 Panoramica

Questa è la **versione definitiva integrata** che combina:

✅ **Architettura refactorata** (oggetti dinamici `ManifoldBase`)  
✅ **Visualizzazione 3D completa** (compatibile con originale)  
✅ **Telemetria HDF5 backward-compatible**  
✅ **Tutte le modalità** (interattivo, headless, playback, film)  
✅ **Parallelizzazione HPC** (multiprocessing)  

---

## 🚀 Modalità di Esecuzione

### 1. **Modalità Interattiva** (Default)

Simulazione real-time con visualizzazione 3D:

```powershell
python WQT_manifold_integrated.py --n-manifold 10 --duration 30
```

**Caratteristiche:**
- Animazione 3D live con matplotlib
- 4 subplot laterali: torsione, popolazione, energia, generazione
- Salvataggio automatico HDF5
- Usa tutti i core CPU disponibili

**Controlli:**
- Chiudi finestra per terminare

---

### 2. **Modalità Headless**

Solo calcolo numerico (ideale per cluster HPC):

```powershell
python WQT_manifold_integrated.py --headless --n-manifold 50 --duration 60 --db cosmologia_run01.h5
```

**Caratteristiche:**
- Nessuna interfaccia grafica
- Massima velocità di calcolo
- Output: solo file HDF5
- Ideale per lunghe simulazioni batch

**Output di esempio:**
```
[HEADLESS] Inizio calcolo 1440 frame...
[HEADLESS] Frame 100/1440 | N_manifold: 12
[HEADLESS] Frame 200/1440 | N_manifold: 15
...
[HEADLESS] ✓ Simulazione completata. Dati salvati in cosmologia_run01.h5
```

---

### 3. **Modalità Playback**

Rendering da file HDF5 esistente:

```powershell
# Solo animazione (non implementato in v1.0)
python WQT_manifold_integrated.py --playback --db cosmologia_run01.h5

# Generazione filmato MP4
python WQT_manifold_integrated.py --playback --film --db cosmologia_run01.h5 --output cosmologia.mp4 --fps 30
```

**Requisiti:**
- **FFmpeg** installato e nel PATH di sistema

**Output:**
```
[PLAYBACK] Compilazione video MP4...
[PLAYBACK] ✓ Video salvato: cosmologia.mp4
```

---

### 4. **Modalità Film** (Solo Generazione Video)

Simula + renderizza + compila video automaticamente:

```powershell
python WQT_manifold_integrated.py --film --n-manifold 20 --duration 15 --fps 24 --output universo_frattale.mp4
```

**Pipeline:**
1. Simulazione headless
2. Rendering frame come PNG
3. Compilazione MP4 con FFmpeg
4. Salvataggio HDF5

---

## 📊 Parametri Configurabili

| Argomento | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `--n-manifold` | int | 10 | Numero manifold primordiali iniziali |
| `--duration` | int | 15 | Durata simulazione in secondi |
| `--fps` | int | 24 | Frame al secondo (rendering/film) |
| `--db` | str | `geometrodinamica_integrated.h5` | File HDF5 telemetria |
| `--cores` | int | None | Numero core CPU (None = tutti) |
| `--speed` | int | 1 | Velocità playback (riservato) |
| `--output` | str | None | Nome file MP4 output |

---

## 🔬 Struttura Fisica

### Evoluzione Dinamica

Il sistema evolve secondo **Velocity Verlet** simplectico:

```
dχ/dτ = v
dv/dτ = -∂V/∂χ + A·χ
```

Dove:
- **V(χ) = λχ² - ¼χ⁴** (potenziale doppio pozzo)
- **A** = matrice accoppiamento emergente tra segmenti

### Eventi Topologici

1. **Fissione** (τ > 4π):
   - Manifold saturo si divide in due
   - Conservazione chiralità totale
   - Separazione spaziale isotropica

2. **Congiunzione** (distanza < λ_Planck × 10):
   - Fusione tra manifold di chiralità opposta
   - Risonanza di fase > 0.5
   - Annichilazione parziale

### Parallelizzazione

Evoluzione locale distribuita su pool di processi:

```python
evolvi_sistema_parallelo(lista_manifold, dt=0.01, n_cores=8)
```

**Speedup teorico:** ~0.7N su N core (overhead comunicazione)

---

## 📁 Output HDF5

### Struttura File

```
geometrodinamica_integrated.h5
├── /telemetria_scalare [compound dataset]
│   ├── frame_id (int64)
│   ├── rm (float64)
│   ├── chi_medio (float64)
│   ├── v_chi_medio (float64)
│   ├── torsione_media (float64)
│   ├── n_manifold (int64)
│   ├── energia_totale (float64)
│   └── generazione_max (int64)
└── Attributi:
    ├── creato_il (ISO timestamp)
    ├── num_total_frames (int)
    └── architettura (str)
```

### Lettura Dati

```python
import h5py
import numpy as np

with h5py.File('geometrodinamica_integrated.h5', 'r') as f:
    telemetria = f['telemetria_scalare'][:]
    
    # Estrazione serie temporali
    frame_ids = telemetria['frame_id']
    popolazione = telemetria['n_manifold']
    torsione = telemetria['torsione_media']
    energia = telemetria['energia_totale']
    
    # Plot
    import matplotlib.pyplot as plt
    plt.plot(frame_ids, popolazione)
    plt.xlabel('Frame')
    plt.ylabel('N(t)')
    plt.title('Evoluzione Popolazione Manifold')
    plt.show()
```

---

## 🧪 Test Rapido

```powershell
# Test 1: Simulazione breve interattiva
python WQT_manifold_integrated.py --n-manifold 5 --duration 5

# Test 2: Calcolo headless veloce
python WQT_manifold_integrated.py --headless --n-manifold 10 --duration 10

# Test 3: Generazione filmato 10 secondi
python WQT_manifold_integrated.py --film --n-manifold 8 --duration 10 --fps 24 --output test_film.mp4
```

---

## ⚙️ Requisiti di Sistema

### Software

- **Python** ≥ 3.8
- **NumPy** ≥ 1.20
- **h5py** ≥ 3.0
- **matplotlib** ≥ 3.3
- **FFmpeg** (solo per modalità film)

### Installazione FFmpeg

**Windows:**
```powershell
# Con Chocolatey
choco install ffmpeg

# Manuale: https://ffmpeg.org/download.html
# Aggiungere bin\ al PATH
```

**Verifica installazione:**
```powershell
ffmpeg -version
```

### Hardware Consigliato

- **CPU:** Multi-core (6+ core consigliati)
- **RAM:** 8 GB minimo, 16 GB consigliato
- **Storage:** 100 MB per HDF5 (100k frame)

---

## 🔍 Confronto con Versione Originale

| Caratteristica | Originale (`WQT_manifold.py`) | Integrata (`WQT_manifold_integrated.py`) |
|----------------|-------------------------------|------------------------------------------|
| Architettura | Monolitica (array globale) | Object-Oriented (ManifoldBase) |
| Integrazione | solve_ivp (RK45) | Velocity Verlet (simplectico) |
| Parallelizzazione | ❌ Nessuna | ✅ multiprocessing.Pool |
| Conservazione energia | ~5% drift | <1% drift |
| Scalabilità | O(1) manifold | O(N) manifold dinamici |
| Fissione/Congiunzione | ❌ Teorica | ✅ Implementata |
| Visualizzazione | ✅ Completa | ✅ Completa + metriche |
| Backward compatibility | N/A | ✅ HDF5 compatibile |

---

## 🐛 Troubleshooting

### Errore: "FFmpeg non trovato"

**Soluzione:**
```powershell
# Verifica PATH
$env:Path -split ';' | Select-String ffmpeg

# Aggiungi manualmente (esempio)
$env:Path += ";C:\ffmpeg\bin"
```

### Errore: "HDF5 file locked"

**Soluzione:**
```powershell
# Variabile d'ambiente già impostata nello script
# Se persiste, rimuovi file manualmente
Remove-Item geometrodinamica_integrated.h5.lock -Force
```

### Plot 3D non visibile

**Causa:** Backend matplotlib non interattivo

**Soluzione:**
```python
# Forza backend
import matplotlib
matplotlib.use('TkAgg')  # o 'Qt5Agg'
```

### Prestazioni lente

**Soluzioni:**
1. Riduci `--n-manifold` (es: 5-10)
2. Riduci risoluzione rendering (modifica `RISOLUZIONE_RENDERING = 1200`)
3. Usa `--headless` per evitare overhead grafico
4. Aumenta `--cores` per parallelizzazione

---

## 📚 Riferimenti

- **Documentazione completa:** [REFACTORING_MANIFOLD_DOCS.md](REFACTORING_MANIFOLD_DOCS.md)
- **Guida migrazione:** [GUIDA_MIGRAZIONE.md](GUIDA_MIGRAZIONE.md)
- **Esempi interattivi:** [esempi_uso_refactored.py](esempi_uso_refactored.py)
- **Test suite:** [test_refactoring.py](test_refactoring.py)

---

## 📝 Note di Versione

### v1.0.0 - Versione Integrata Iniziale

**Nuove funzionalità:**
- ✅ Integrazione completa architettura refactorata
- ✅ Visualizzazione 3D con 4 subplot metriche
- ✅ Modalità headless/playback/film
- ✅ Telemetria HDF5 estesa
- ✅ Parallelizzazione multi-core

**Limitazioni note:**
- Playback interattivo non implementato (solo --film)
- Geometria 3D usa solo manifold rappresentante (non tutti)
- Collision detection naive O(N²)

**Prossimi sviluppi:**
- Albero spaziale per collision detection O(N log N)
- Render multi-manifold con instancing
- Controlli interattivi (pause/play, speed slider)

---

## 📧 Supporto

Per domande o bug report, consultare:
- **README principale:** [README.md](README.md)
- **Documentazione fisica:** [README_FISICA_COMPLETA.md](README_FISICA_COMPLETA.md)

---

**Licenza:** MIT  
**Autori:** Refactoring Team  
**Data:** 2025

---

> *"La realtà emerge dalla danza frattale di infiniti universi-solitoni in equilibrio topologico"*  
> — Wheeler-Quantum-Topology Theory
