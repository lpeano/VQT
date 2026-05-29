# VQT — Voxel/Variational Quantum Topology

## Simulazione di Gravità Quantistica su Manifold Frattale Topologico

![Status](https://img.shields.io/badge/status-attivo-success)
![Level](https://img.shields.io/badge/simulazioni-L1%20L2%20L3%20L4-blue)
![Physics](https://img.shields.io/badge/fisica-topologica%20variazionale-purple)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow)

---

## Panoramica

**VQT** è un framework di simulazione numerica per lo studio della gravità
quantistica emergente da un manifold frattale topologico. L'unità fondamentale è
un **segmento di lunghezza di Planck** ($\ell_P$) con tre gradi di libertà interni
$(\chi_i, v_i, \tau_i)$. La geometria spaziale, il tempo e la materia emergono
dall'interazione collettiva di $N = 24^L$ segmenti organizzati in una gerarchia
frattale di livello $L$.

La ricerca si sviluppa su una **doppia elica** di due rami che condividono lo
stesso motore (`wqt_oop/`):

- 🌌 **Ramo A — Cosmology / RG-flow**: il manifold come sistema variazionale
  autonomo. Analisi spettrale, invarianza di scala della frequenza, mappatura
  Einstein-Cartan discreta. È l'**impalcatura scientifica**.
- 🧬 **Ramo B — Peano-VQT**: auto-organizzazione della materia, triade energetica
  $(E_\chi, E_{RX}, E_\Psi)$, leggi di aggregazione. È il **cuore attuale**, emerso
  dal Ramo A.

> Come il Ramo A ha generato il Ramo B è spiegato in
> [docs/cosmology/EVOLUZIONE_TEORICA.md](docs/cosmology/EVOLUZIONE_TEORICA.md).

### Risultati principali

**Ramo A — spettroscopia del vuoto topologico**

| Livello | DOF    | f_dom [1/P]           | σ plateau | Entropia spettrale |
| ------- | ------ | --------------------- | --------- | ------------------ |
| L1      | 48     | **0.667**             | 0.086     | 2.539              |
| L2      | 1152   | **0.600**             | 0.050     | 1.986              |
| L3      | 27648  | **~0.500** (in corso) | 0.037     | 1.237              |

La frequenza dominante $f_{\text{dom}} \approx 0.76 \cdot N_{\text{dof}}^{-0.033}$ è
**invariante di scala**: il manifold oscilla alla stessa frequenza fondamentale
indipendentemente dalla risoluzione.

**Ramo B — auto-organizzazione (Peano-VQT)**

- **Cristallizzazione spontanea a numero di Leech**: 48 solitoni L1 distribuiti a
  caso si aggregano in un cluster stabile di **24** (step 600), senza vincoli
  geometrici imposti.
- **3 leggi misurate**: Aggregazione ferromagnetica, Repulsione topologica
  (frustrazione), Conservazione della triade $dE_\chi + dE_{RX} + dE_\Psi = 0$.
- Dettagli in [docs/peano/VQT_MANIFESTO_TEORICO.md](docs/peano/VQT_MANIFESTO_TEORICO.md).

---

## Struttura del Progetto

```
VQT_repo/
├── README.md  ·  requirements.txt  ·  .gitignore
│
├── wqt_oop/                  # 🔧 MOTORE (core di produzione, condiviso dai due rami)
│   ├── segmento_quantistico.py        # Unità fondamentale (χ, v, τ)
│   ├── solitone_composito.py          # Nodo frattale composito (24 figli/livello)
│   ├── physics_context.py             # Parametri scale-dependent, RG-flow
│   ├── energy_metrics.py              # Triade Peano-VQT (PeanoVQTAnalyzer)
│   ├── fractal_universe_factory.py    # Costruzione gerarchia L1→LN
│   ├── topological_constraint_validator.py  # Vincoli 720° / detorsione
│   ├── variational_topological_force.py     # F_top = -∇S
│   ├── fermi_dirac_screening.py · spatial_cache.py · hdf5_logger.py · ...
│
├── core/                     # API pulita (re-export da wqt_oop)
│
├── experiments/              # 🧬 Esperimenti Peano-VQT (Ramo B)
│   ├── genesis_run.py                 # Transizione vuoto→materia
│   ├── l2_aggregation_run.py          # Legame vs frustrazione topologica
│   ├── l4_self_assembly_run.py        # Auto-assembly 48 solitoni → cluster 24
│   ├── test_peano_integration.py      # Unit test della triade
│   ├── compare_fdom_scaling.py        # Analisi spettrale (Ramo A)
│   └── exp1/                          # Dataset run cosmologiche L1–L3 (*.h5)
│
├── tools/                    # Script standalone (auto-shim verso repo root)
│   ├── tests/        (5)     #   test motore (verlet, convergenza, timestep)
│   ├── validation/   (8)     #   audit/check/inspect/validate/verify run L3
│   ├── rendering/    (12)    #   generate_*, master_*video, manifold_*, torsion
│   └── analysis/     (3)     #   analyze_topo, compare_l2/scales
│
├── docs/                     # 📚 Documentazione (vedi docs/README.md)
│   ├── peano/                #   Ramo B: MANIFESTO, CHECKPOINT, INDEX (hub)
│   ├── cosmology/            #   Ramo A: TOPOLOGICAL_DYNAMICS, SCALING, RENDERING, EVOLUZIONE
│   ├── reference/            #   Spec valide: PHYSICS_MANIFESTO, PHYSICS_LOG, RG_FLOW
│   ├── reports/              #   Artefatti di processo (proposte, fix, audit)
│   ├── history/              #   Modelli pre-OOP superati
│   ├── obsoletes/            #   Patch archiviate
│   └── figures/              #   Figure §0
│
├── data/                     # Dataset HDF5 (cosmo_*.h5, peano_data.zip)
├── assets/  └─ media/        # Animazioni (.mp4 / .gif) + plot_genesi.png
├── logs/                     # Log di produzione delle run
└── legacy/                   # WQT_manifold.py (monolite pre-OOP, riferimento storico)
```

👉 Punto d'ingresso documentazione: **[docs/peano/INDEX.md](docs/peano/INDEX.md)**

---

## Quick Start

### Prerequisiti

```bash
pip install -r requirements.txt   # numpy, scipy, h5py, matplotlib
```

### Ramo B — Esperimenti Peano-VQT

```bash
# Genesi: transizione vuoto → materia (fase Ottaedrica → Icosaedrica)
python experiments/genesis_run.py

# Auto-assembly: 48 solitoni → cristallizzazione a cluster 24
python experiments/l4_self_assembly_run.py

# Unit test della triade energetica (dE_χ + dE_RX + dE_Ψ = 0)
python experiments/test_peano_integration.py
```

### Ramo A — Simulazioni cosmologiche (RG-flow / spettroscopia)

```bash
# L1 (48 DOF, ~30s)
python tools/rendering/generate_topological_dataset.py --level 1 --steps 600 --output cosmo_L1.h5

# L3 con MaturityWatchdog (27648 DOF)
python tools/rendering/generate_topological_dataset.py \
  --level 3 --steps 800 --watchdog --watchdog-epsilon 1e-4 --output cosmo_L3.h5

# Ripresa da run precedente
python tools/rendering/generate_topological_dataset.py \
  --level 3 --steps 400 --resume-from cosmo_L3.h5 --output cosmo_L3_ext.h5

# Analisi spettrale multi-scala
python experiments/compare_fdom_scaling.py \
  experiments/exp1/cosmo_L1.h5 experiments/exp1/cosmo_L2.h5 experiments/exp1/cosmo_L3.h5 \
  --stft --output experiments/exp1/fdom_results.json
```

> Il watchdog dichiara maturità quando $|\dot{\sigma}(\rho)| < \varepsilon/\sqrt{N_{\text{dof}}}$
> per $W$ passi consecutivi (finestra auto-sintonizzata su $f_{\text{dom}}$).

---

## Fisica del Modello

Formalizzazione completa in **[docs/cosmology/TOPOLOGICAL_DYNAMICS.md](docs/cosmology/TOPOLOGICAL_DYNAMICS.md)**.
Le leggi di auto-organizzazione in **[docs/peano/VQT_MANIFESTO_TEORICO.md](docs/peano/VQT_MANIFESTO_TEORICO.md)**.

### Il Potenziale Topologico (Ramo A)

$$S[\chi, \tau] = \lambda \sum_{i=1}^N (\rho_i - \rho_0)^2 + \gamma \sum_{i=1}^N \Omega_i$$

- **Omeostasi topologica** — penalizza la deviazione dalla densità di vincolo $\rho_0$.
- **Frustrazione chirale** — promuove l'alternanza $\pm 180^\circ$ (ground state spinoriale).

### La Triade Energetica (Ramo B)

$$H_{\text{coupling}} = E_\chi + E_{RX}, \qquad \text{drain: } E_\chi \to E_\Psi$$

con invariante esatto $dE_\chi + dE_{RX} + dE_\Psi = 0$. $E_\Psi$ (sink radiativo)
cresce monotonicamente ed è l'indicatore di condensazione/frustrazione.

### Integrazione Simplettica

$$\mathcal{U}_{\text{tot}}(dt) = \mathcal{T}_{dt/2} \circ \mathcal{U}_{\text{phys}}(dt) \circ \mathcal{T}_{dt/2}$$

Strang Splitting conserva il volume nello spazio delle fasi a $O(dt^2)$.

### Genesi delle 4 Dimensioni

| Livello | N       | Struttura          | Dimensione emergente |
| ------- | ------- | ------------------ | -------------------- |
| L1      | 24      | Anello spinoriale  | 1D curva             |
| L2      | 576     | Foglio di anelli   | 2D piano             |
| L3      | 13824   | Volume di fogli    | 3D spazio            |
| L→∞     | ∞       | Continuo           | R³ + τ               |

Il tempo macroscopico $t = \sum_i \tau_i / N$ è la quarta dimensione — emergente, non imposta.

---

## Leggi Fenomenologiche Misurate

### Ramo A — Invarianza di Scala della Frequenza [Eq. FSCALE-1]

$$f_{\text{dom}} \approx 0.76 \cdot N_{\text{dof}}^{-0.033} \qquad (\alpha \approx 0)$$

La frequenza fondamentale è invariante rispetto al numero di gradi di libertà.

### Ramo B — Le 3 Leggi Peano-VQT

1. **Aggregazione ferromagnetica**: solitoni iso-fase cristallizzano in cluster di 24.
2. **Repulsione topologica**: solitoni cross-fase si frustrano; $E_\Psi$ ~2.9× più alto.
3. **Conservazione della triade**: $dE_\chi + dE_{RX} + dE_\Psi = 0$, verificato (0 violazioni).

### Predizioni Falsificabili (Ramo A)

- **[P-1]** $\lambda$ doppio → $f_{\text{dom}} \times \sqrt{2} \approx 0.85$ [1/P]
- **[P-2]** L3 esteso a 600 step → $f_{\text{dom}}(L3) \in [0.55, 0.63]$ [1/P]
- **[P-3]** L4 → entropia spettrale $\mathcal{H}_s < 1.0$ (quasi-monocromatico)

---

## Documentazione

| Documento | Ramo | Contenuto |
|-----------|------|-----------|
| [docs/peano/INDEX.md](docs/peano/INDEX.md) | — | **Hub centrale** di navigazione |
| [docs/peano/VQT_MANIFESTO_TEORICO.md](docs/peano/VQT_MANIFESTO_TEORICO.md) | B | Le 3 leggi Peano-VQT |
| [docs/cosmology/TOPOLOGICAL_DYNAMICS.md](docs/cosmology/TOPOLOGICAL_DYNAMICS.md) | A | Formalizzazione variazionale (riferimento principale) |
| [docs/cosmology/EVOLUZIONE_TEORICA.md](docs/cosmology/EVOLUZIONE_TEORICA.md) | A→B | Come il Ramo A ha generato il Ramo B |
| [docs/reference/PHYSICS_MANIFESTO.md](docs/reference/PHYSICS_MANIFESTO.md) | — | Manifesto fisico VQT |
| [docs/reference/PHYSICS_LOG.md](docs/reference/PHYSICS_LOG.md) | — | Mappatura vincoli software ↔ leggi fisiche |
| [docs/history/TEORIA_FISICA_COMPLETA.md](docs/history/TEORIA_FISICA_COMPLETA.md) | — | Fondamenti Einstein-Cartan (contesto storico) |

---

## Citazioni

> *"La materia non esiste nello spazio-tempo; la materia È spazio-tempo con topologia non triviale."*
> — John Archibald Wheeler

> *"Il manifold è auto-referenziale: ogni voxel codifica nel proprio stato il giudizio
> sulla propria coerenza geometrica. Questa auto-referenzialità è il confine tra una
> simulazione e un motore fisico."*
> — TOPOLOGICAL_DYNAMICS.md

---

## Autori

- **Luca Peano** — ricerca, fisica, architettura
- **Claude** (Anthropic) — implementazione, analisi, documentazione

---

**Branch attivo**: `research-backup`
**Ultima modifica**: 2026-05-29
**Versione**: 3.0 — Doppia Elica (Cosmology A + Peano-VQT B)
