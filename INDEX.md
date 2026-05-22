# WQT MANIFOLD - Indice Documentazione

## 📚 Documentazione Completa

### 🎯 Guide Introduttive
1. **[README.md](README.md)** - Overview generale del progetto
2. **[GUIDA_INTEGRAZIONE.md](GUIDA_INTEGRAZIONE.md)** - Come integrare i 4 moduli
3. **[README_FISICA_COMPLETA.md](README_FISICA_COMPLETA.md)** - Teoria fisica dettagliata

### 📖 Documentazione Tecnica Approfondita
Tutte le guide sono in [`docs/`](docs/):

- **[docs/INDEX.md](docs/INDEX.md)** - Indice completo della documentazione tecnica
- **[docs/TEORIA_FISICA_COMPLETA.md](docs/TEORIA_FISICA_COMPLETA.md)** - Teoria Einstein-Cartan completa
- **[docs/ARCHITETTURA_24_CAMPI_LOCALI.md](docs/ARCHITETTURA_24_CAMPI_LOCALI.md)** - Sistema 24 campi accoppiati
- **[docs/SISTEMA_TERMODINAMICO_APERTO.md](docs/SISTEMA_TERMODINAMICO_APERTO.md)** - Dinamica hamiltoniana
- **[docs/RENDERING_DINAMICO_TECNICO.md](docs/RENDERING_DINAMICO_TECNICO.md)** - Sistema visualizzazione
- **[docs/RISULTATI_VALIDAZIONE_BOUNCE.md](docs/RISULTATI_VALIDAZIONE_BOUNCE.md)** - Validazione Big Bounce

---

## 🚀 Quick Start

### Esecuzione Base
```bash
# Simulazione 3 secondi @ 24fps (headless)
python WQT_manifold.py --headless --duration 3 --fps 24 --db output.h5

# Playback visualizzazione 3D
python WQT_manifold.py --playback --db output.h5 --speed 2
```

### Analisi Dati
```bash
# Leggi telemetria HDF5
python read_telemetry.py output.h5

# Analisi post-simulazione
python analisi_post_simulazione.py output.h5

# Analisi Hubble
python analizza_hubble.py output.h5
```

---

## 📦 Struttura Codebase

### Core System
- **`WQT_manifold.py`** (3639 righe) - Simulatore geometrodinamica principale
  - Equazioni Einstein-Cartan
  - 24 campi locali accoppiati (Leech lattice)
  - Big Bounce quantistico
  - Conservazione carica spinoriale Σχ
  
- **`dinamica_hamiltoniana_chiralita.py`** (299 righe) - Separazione fasi materia/spazio
  - Trasporto chiralità
  - Minimizzazione energia
  - Calcolo energie (E_tot, E_coup, E_tors)

### Tools
- **`read_telemetry.py`** - Lettura telemetria HDF5
- **`analisi_post_simulazione.py`** - Analisi frame-by-frame
- **`analizza_hubble.py`** - Estrazione parametro Hubble

### Dataset HDF5 di Successo
- **`cosmologia_conservata.h5`** - 240 frame (10s), Σχ = -108.96 conservata ✅
- **`geometrodinamica_matrix.h5`** - Dataset di riferimento

---

## 🔬 Fisica Implementata

### Equazione di Campo (Einstein-Cartan)
```
R_μν - (1/2)g_μν R + K²_μν = 8πG T_μν
```
dove:
- **R_μν**: Tensore di Ricci (curvatura)
- **K_μν**: Tensore di contorsione (torsione)
- **T_μν**: Tensore energia-impulso
- **G**: Costante gravitazionale emergente

### Vincoli Topologici
1. **Chiusura Spinoriale**: ∮ τ ds = 4π (720°)
2. **Conservazione Carica**: Σχᵢ = -108.96 (gauge constraint)
3. **Simmetria Leech**: 24 segmenti accoppiati (E8×E8)

### Meccanismi Fisici Chiave
- **Variable Light Speed**: c_locale = 1/(1 + α×ρ_SX/ρ_tot)
- **Quantum Radiation**: γ = 0.25 quando E_tors > 1000 (Planck units)
- **Big Bounce**: P_rep = β×ρ² (repulsione spin-spin Einstein-Cartan)
- **Gain Control Topologico**: K = tanh((K_raw - μ)/(2σ))×5 + μ

---

## 📊 Risultati Validazione

### Test Successo (cosmologia_conservata.h5)
```
✓ 240 frame completati (10 secondi fisici @ 24fps)
✓ rm_ema = 1.825116 m COSTANTE
✓ Σχ = -108.96 ± 1e-6 (conservazione perfetta)
✓ E_coup = 4-6 (accoppiamento attivo)
✓ Max|flux| > 0 (trasporto chiralità funzionante)
✓ Nessuna divergenza numerica
```

### Prima del Fix (cosmologia_10s.h5 - FAILED)
```
❌ 59/240 frame (25% completamento)
❌ Var(χ) → 3790 (divergenza)
❌ Σχ: -108 → -28428 (violazione conservazione)
❌ Crash del solutore Radau
```

---

## 🎓 Citazioni

Se utilizzi questo codice per ricerca, cita:

```bibtex
@software{wqt_manifold_2026,
  title = {WQT Manifold - Einstein-Cartan Geometrodynamics with Charge Conservation},
  author = {Luca Peano},
  year = {2026},
  note = {24-field coupled system with Big Bounce and topological constraints}
}
```

---

## 📝 Licenza

Questo progetto è distribuito sotto licenza MIT.

---

## 🔗 Collegamenti Rapidi

- **Teoria**: [docs/TEORIA_FISICA_COMPLETA.md](docs/TEORIA_FISICA_COMPLETA.md)
- **Architettura**: [docs/ARCHITETTURA_24_CAMPI_LOCALI.md](docs/ARCHITETTURA_24_CAMPI_LOCALI.md)
- **Risultati**: [docs/RISULTATI_VALIDAZIONE_BOUNCE.md](docs/RISULTATI_VALIDAZIONE_BOUNCE.md)
- **Issue Tracker**: https://github.com/lpeano/VQT/issues

---

**Ultimo aggiornamento**: 22 Maggio 2026  
**Versione**: 1.0.0 (Conservazione Σχ implementata)
