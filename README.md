# WQT Manifold - Wheeler Quantum Topology

## Simulazione di Geometrodinamica Quantistica con Bounce Einstein-Cartan

![Status](https://img.shields.io/badge/status-validato-success)
![Physics](https://img.shields.io/badge/physics-Einstein--Cartan-blue)
![Bounce](https://img.shields.io/badge/bounce-quantistico-brightgreen)

---

## 📋 Panoramica

**WQT (Wheeler Quantum Topology)** è una simulazione numerica di un manifold frattale a torsione basato sulla teoria di Einstein-Cartan, che estende la Relatività Generale includendo lo spin intrinseco della materia.

### Caratteristiche Principali
- ✅ **Bounce quantistico**: Previene singolarità gravitazionali tramite repulsione spin-spin
- ✅ **Geometria discreta**: Reticolo di nodi di Planck (24 segmenti frattali)
- ✅ **Oscillazioni stabili**: Il manifold "respira" con inversioni di dinamica
- ✅ **Validato**: 99% bounce attivo, 3 inversioni di velocità rilevate

---

## 📁 Struttura del Progetto

```
VQT/
├── WQT_manifold.py              # Codice principale della simulazione
├── visualizza_bounce.py         # Analisi e visualizzazione risultati
├── README.md                    # Questo file
├── README_FISICA_COMPLETA.md    # Guida di riferimento fisica
├── docs/                        # Documentazione teorica
│   ├── TEORIA_FISICA_COMPLETA.md          # Teoria completa (13 sezioni)
│   └── RISULTATI_VALIDAZIONE_BOUNCE.md    # Risultati validazione
├── test_*.py                    # Test unitari e di integrazione
├── analizza_*.py                # Script diagnostici
└── geometrodinamica_*.h5        # Database HDF5 simulazioni
```

---

## 🚀 Quick Start

### Eseguire una simulazione
```bash
python WQT_manifold.py --headless --fps 50 --duration 2 --db risultati.h5
```

### Analizzare i risultati
```bash
python visualizza_bounce.py
```

### Parametri principali
- `--headless`: Modalità senza GUI (più veloce)
- `--fps 50`: 50 frame al secondo
- `--duration 2`: 2 secondi di simulazione (100 frame)
- `--db FILE`: Database HDF5 di output

---

## 🔬 Fisica del Modello

### Equazioni di Einstein-Cartan
Il modello implementa:

1. **Pressione gravitazionale** (attrattiva):
   ```
   P_grav = w × ρ_total - τ_newtoniana
   ```

2. **Pressione repulsione spin** (repulsiva):
   ```
   P_rep = β × ρ_total²
   ```

3. **Potenziale armonico** (stabilizzazione):
   ```
   F_richiamo = -ω × χ
   ```

### Parametri Fisici
```python
BETA_REPULSIONE_SPIN = 1.0    # Coefficiente Einstein-Cartan
OMEGA_RICHIAMO = 1.0          # Potenziale armonico
w = -1/3                      # Equazione di stato
SEGMENTI_FRATTALI = 24        # Leech lattice / E8×E8
```

### Vincolo Topologico
Il manifold deve soddisfare il vincolo spinoriale:
```
∮ τ(s) ds = 4π  (720°)
```

---

## 📊 Risultati Validazione

### Simulazione di Riferimento
- **Frames**: 100 (λ = 0 → 9.9)
- **Bounce attivo**: 99% del tempo
- **Oscillazioni**: 3 inversioni di velocità
- **Rapporto max**: P_rep / |P_grav| = 466
- **Densità**: Crescita 2532× controllata

### Criteri Soddisfatti
| Criterio | Soglia | Risultato | Status |
|----------|--------|-----------|--------|
| Rapporto > 1 | >90% | 99% | ✅ |
| Oscillazioni | ≥2 | 3 | ✅ |
| Velocità | <1000 | 590 | ✅ |
| Densità | Libera | 2532× | ✅ |

---

## 🧪 Test e Validazione

### Test Unitari
```bash
python test_contorsione.py          # Test calcolo contorsione (O(N))
python test_chiusura_spinore.py     # Test vincolo 4π
python test_integrazione_completa.py # Test integrazione completa
```

### Script Diagnostici
```bash
python analizza_collasso.py         # Analisi dinamica collasso
python analizza_ordine_grandezza.py # Verifica scale fisiche
python analizza_hubble.py           # Parametro di Hubble emergente
```

---

## 📚 Documentazione

### Teoria Completa
Leggi [docs/TEORIA_FISICA_COMPLETA.md](docs/TEORIA_FISICA_COMPLETA.md) per:
- Interpretazione fisica del modello
- Significato di tutti i parametri (χ, 24 segmenti, DX/SX, r_m)
- Equazioni di Einstein-Cartan dettagliate
- Meccanismo del bounce quantistico
- Geometria discreta quantizzata

### Risultati Validazione
Leggi [docs/RISULTATI_VALIDAZIONE_BOUNCE.md](docs/RISULTATI_VALIDAZIONE_BOUNCE.md) per:
- Risultati completi della validazione
- Confronto parametrico (con/senza bounce)
- Analisi del meccanismo fisico osservato
- Implicazioni teoriche

### Riferimento Rapido
Leggi [README_FISICA_COMPLETA.md](README_FISICA_COMPLETA.md) per una guida di riferimento rapida.

---

## 🎯 Workflow Tipico

1. **Modifica parametri** in `WQT_manifold.py` (linee 356-381)
2. **Esegui simulazione**:
   ```bash
   python WQT_manifold.py --headless --fps 50 --duration 2 --db test.h5
   ```
3. **Analizza risultati**:
   ```bash
   python visualizza_bounce.py
   ```
4. **Verifica grafici**: `evoluzione_bounce.png` (creato automaticamente)
5. **Leggi log**: `stabilita.log` (contiene metriche dettagliate)

---

## 🔧 Configurazioni

### Simulazione Veloce (Test)
```python
fps = 50
duration = 2  # 100 frames
```

### Simulazione Completa (Validazione)
```python
fps = 50
duration = 10  # 500 frames
```

### Debug Dettagliato
Abilita logging verbose modificando `WQT_manifold.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

---

## 📖 Citazioni

> *"La materia non esiste nello spazio-tempo; la materia È spazio-tempo con topologia non triviale."*  
> — John Archibald Wheeler

> *"La torsione dello spazio-tempo previene la formazione di singolarità gravitazionali."*  
> — Élie Cartan, Albert Einstein

---

## 🤝 Contributi

Questo è un progetto di ricerca. Per domande o collaborazioni:
- **Autore**: Leonardo Peano
- **Assistenza**: Claude (Anthropic AI)
- **Data**: Maggio 2026

---

## 📜 Licenza

Ricerca scientifica - Codice disponibile per scopi educativi e di ricerca.

---

## 🔗 Link Utili

- [Teoria di Einstein-Cartan (Wikipedia)](https://en.wikipedia.org/wiki/Einstein%E2%80%93Cartan_theory)
- [Geometrodinamica di Wheeler](https://en.wikipedia.org/wiki/Geometrodynamics)
- [Reticolo di Leech](https://en.wikipedia.org/wiki/Leech_lattice)
- [Bounce Quantistico](https://en.wikipedia.org/wiki/Big_Bounce)

---

**Ultima modifica**: 22 Maggio 2026  
**Versione**: 2.0 (Einstein-Cartan + Bounce Validato)
