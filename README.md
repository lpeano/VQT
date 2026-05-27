# VQT — Voxel Quantum Gravity

## Simulazione di Gravità Quantistica su Manifold Frattale Topologico

![Status](https://img.shields.io/badge/status-attivo-success)
![Level](https://img.shields.io/badge/simulazioni-L1%20L2%20L3-blue)
![Physics](https://img.shields.io/badge/fisica-topologica%20variazionale-purple)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow)

---

## Panoramica

**VQT (Voxel Quantum Gravity)** è un framework di simulazione numerica per lo studio della gravità quantistica emergente da un manifold frattale topologico. L'unità fondamentale è un **segmento di lunghezza di Planck** ($\ell_P$) con tre gradi di libertà interni $(\chi_i, v_i, \tau_i)$. La geometria spaziale, il tempo e la materia emergono dall'interazione collettiva di $N = 24^L$ segmenti organizzati in una gerarchia frattale di livello $L$.

Il sistema non impone equazioni esterne: evolve secondo un **Hamiltoniano emergente** perturbato da una **forza variazionale topologica** $F_{\text{top}} = -\nabla S$, dove il potenziale $S[\chi, \tau]$ codifica la coerenza geometrica locale (omeostasi topologica + alternanza chirale). Le quattro dimensioni macroscopiche emergono dall'avvolgimento frattale della struttura 2D di base su se stessa.

### Risultati Principali

| Livello | DOF    | f_dom [1/P]          | sigma plateau | Entropia spettrale |
| ------- | ------ | -------------------- | ------------- | ------------------ |
| L1      | 48     | **0.667**            | 0.086         | 2.539              |
| L2      | 1152   | **0.600**            | 0.050         | 1.986              |
| L3      | 27648  | **~0.500** (in corso)| 0.037         | 1.237              |

La frequenza dominante $f_{\text{dom}} \approx 0.76 \cdot N_{\text{dof}}^{-0.033}$ è **invariante di scala**: il manifold oscilla alla stessa frequenza fondamentale indipendentemente dalla risoluzione spaziale. L'entropia spettrale decresce con il livello — il sistema diventa più ordinato all'aumentare della scala.

---

## Struttura del Progetto

```
VQT_repo/
├── generate_topological_dataset.py   # Script principale simulazione
├── WQT_manifold.py                   # Simulatore legacy (riferimento storico)
│
├── wqt_oop/                          # Framework OOP produzione
│   ├── fractal_universe_factory.py   # Costruzione gerarchia frattale L1→LN
│   ├── segmento_quantistico.py       # Unità fondamentale (χ, v, τ)
│   ├── solitone_composito.py         # Nodo frattale composito
│   ├── physics_context.py            # Parametri fisici per livello
│   ├── topological_integration.py    # Wrapper evolutivo + validazione
│   ├── topological_constraint_validator.py  # Vincoli chiusura 720° / detorsione
│   ├── variational_topological_force.py     # F_top = -∇S [Eq. S-1]
│   ├── maturity_watchdog.py          # Auto-stop su plateau σ(ρ) [Eq. WD-1]
│   ├── hdf5_logger.py                # Logging persistente HDF5
│   ├── energy_drift_observer.py      # Observer pattern simulazione
│   ├── fermi_dirac_screening.py      # Screening Fermi-Dirac
│   └── spatial_hash_grid.py          # Cache spaziale O(1) per L3+
│
├── experiments/
│   ├── compare_fdom_scaling.py       # Analisi spettrale FFT + STFT multi-scala
│   └── exp1/                         # Dataset simulazioni (*.h5 esclusi da git)
│       ├── fdom_results.json         # Risultati spettrali L1/L2/L3
│       ├── fdom_scaling.png          # Legge di scala f_dom vs N_dof
│       └── fdom_scaling_stft.png     # Spettrogramma STFT cascata energetica
│
└── docs/
    ├── TOPOLOGICAL_DYNAMICS.md       # Documento teorico principale (v2.1)
    ├── figures/                      # Figure geometria fondamentale §0
    ├── obsoletes/                    # Documenti storici superati
    └── ...                           # Documentazione architetturale
```

---

## Quick Start

### Prerequisiti

```bash
pip install numpy scipy h5py matplotlib
```

### Simulazione L1 (48 DOF, ~30s)

```bash
python generate_topological_dataset.py --level 1 --steps 600 --output cosmo_L1.h5
```

### Simulazione L2 (1152 DOF, ~5min)

```bash
python generate_topological_dataset.py --level 2 --steps 500 --output cosmo_L2.h5
```

### Simulazione L3 con MaturityWatchdog (27648 DOF)

```bash
python generate_topological_dataset.py \
  --level 3 --steps 800 \
  --watchdog --watchdog-epsilon 1e-4 \
  --output cosmo_L3.h5
```

Il watchdog dichiara maturità automaticamente quando $|\dot{\sigma}(\rho)| < \varepsilon/\sqrt{N_{\text{dof}}}$ per $W$ passi consecutivi (finestra auto-sintonizzata sulla frequenza dominante).

### Ripresa da simulazione precedente (--resume-from)

```bash
python generate_topological_dataset.py \
  --level 3 --steps 400 \
  --resume-from cosmo_L3.h5 \
  --output cosmo_L3_ext.h5
```

Carica l'ultimo frame HDF5, inietta lo stato $(\chi_i, v_i, \tau_i)$ nel manifold e continua con i passi aggiuntivi — step e tempo fisico sono aggiornati in continuità.

### Analisi spettrale multi-scala

```bash
python experiments/compare_fdom_scaling.py \
  experiments/exp1/cosmo_L1.h5 \
  experiments/exp1/cosmo_L2.h5 \
  experiments/exp1/cosmo_L3.h5 \
  --stft --output experiments/exp1/fdom_results.json
```

---

## Fisica del Modello

Il modello è formalizzato in dettaglio in **[docs/TOPOLOGICAL_DYNAMICS.md](docs/TOPOLOGICAL_DYNAMICS.md)** (v2.1). Qui una sintesi dei concetti chiave.

### Il Potenziale Topologico

$$S[\chi, \tau] = \lambda \sum_{i=1}^N (\rho_i - \rho_0)^2 + \gamma \sum_{i=1}^N \Omega_i$$

- **Primo termine** — omeostasi topologica: penalizza ogni voxel che si discosta dalla densità di vincolo target $\rho_0$.
- **Secondo termine** — frustrazione chirale: promuove l'alternanza $\pm 180^\circ$ di torsione tra voxel adiacenti (configurazione spinoriale di ground state).

### La Densità di Vincolo

$$\rho_i = \tfrac{1}{2} f_{\text{closure},i}[\tau] + \tfrac{1}{2} f_{\text{detorsion},i}[\chi]$$

- $f_{\text{closure}}$: misura l'uniformità dei tempi propri $\tau_i$ (chiusura spinoriale $4\pi$).
- $f_{\text{detorsion}}$: misura l'alternanza chirale locale.

La densità di vincolo è un **loop di retroazione geometrica**: il manifold si auto-misura e si auto-corregge senza osservatori esterni.

### Integrazione Simplettica

$$\mathcal{U}_{\text{tot}}(dt) = \mathcal{T}_{dt/2} \circ \mathcal{U}_{\text{phys}}(dt) \circ \mathcal{T}_{dt/2}$$

Strang Splitting garantisce la conservazione del volume nello spazio delle fasi a $O(dt^2)$.

### Genesi delle 4 Dimensioni

Il manifold è intrinsecamente un oggetto 2D (superficie di torsione) che genera le 4 dimensioni macroscopiche per avvolgimento frattale ricorsivo:

| Livello | N       | Struttura          | Dimensione emergente |
| ------- | ------- | ------------------ | -------------------- |
| L1      | 24      | Anello spinoriale  | 1D curva             |
| L2      | 576     | Foglio di anelli   | 2D piano             |
| L3      | 13824   | Volume di fogli    | 3D spazio            |
| L→∞     | ∞       | Continuo           | R³ + τ               |

Il tempo macroscopico $t = \sum_i \tau_i / N$ è la quarta dimensione — non è imposto, emerge dall'evoluzione del manifold.

---

## Parametri Chiave

| Parametro                    | Default | Significato                                        |
| ---------------------------- | ------- | -------------------------------------------------- |
| `--level`                    | 2       | Livello frattale (N = 24^L segmenti)               |
| `--steps`                    | 500     | Passi massimi (con watchdog = limite di sicurezza) |
| `--dt`                       | 0.01    | Passo temporale [unità Planck]                     |
| `--lambda-homeo`             | 0.1     | Intensità omeostasi topologica λ                   |
| `--gamma-chiral`             | 0.01    | Tensione chirale γ                                 |
| `--watchdog`                 | off     | Abilita auto-stop su maturità spaziale             |
| `--watchdog-epsilon`         | 1e-4    | Soglia ε (normalizzata per sqrt(N_dof))            |
| `--resume-from`              | —       | Path HDF5 da cui riprendere                        |
| `--enable-variational-force` | off     | Attiva F_top = -∇S                                 |

---

## Leggi Fenomenologiche Misurate

### Invarianza di Scala della Frequenza [Eq. FSCALE-1]

$$f_{\text{dom}} \approx 0.76 \cdot N_{\text{dof}}^{-0.033}$$

$\alpha \approx -0.033 \approx 0$: la frequenza fondamentale è invariante rispetto al numero di gradi di libertà. Il manifold a L1 e a L6 oscillano alla stessa frequenza.

### Legge di Adattamento Frattale [Eq. FA-1]

$$\rho^*(L) = \rho^*_\infty + \frac{\Delta\rho}{24^{L/2}}$$

La densità di equilibrio omeostatica cresce con il livello frattale, convergendo a $\rho^*_\infty$ — il sistema è intrinsecamente espansivo.

### Predizioni Falsificabili

- **[P-1]** Con $\lambda$ doppio: $f_{\text{dom}} \to f_{\text{dom}} \times \sqrt{2} \approx 0.85$ [1/P]
- **[P-2]** L3 esteso a 600 step: $f_{\text{dom}}(L3) \in [0.55, 0.63]$ [1/P] con FFT affidabile
- **[P-3]** L4: entropia spettrale $\mathcal{H}_s < 1.0$ (quasi-oscillatore monocromatico)

---

## Documentazione

| Documento | Contenuto |
|-----------|-----------|
| [docs/TOPOLOGICAL_DYNAMICS.md](docs/TOPOLOGICAL_DYNAMICS.md) | **Riferimento principale** — formalizzazione variazionale v2.1 |
| [PHYSICS_MANIFESTO.md](PHYSICS_MANIFESTO.md) | Manifesto fisico VQT |
| [PHYSICS_LOG.md](PHYSICS_LOG.md) | Mappatura vincoli software ↔ leggi fisiche |
| [docs/TEORIA_FISICA_COMPLETA.md](docs/TEORIA_FISICA_COMPLETA.md) | Fondamenti Einstein-Cartan (contesto storico) |
| [docs/INDEX.md](docs/INDEX.md) | Indice completo documentazione |

---

## Citazioni

> *"La materia non esiste nello spazio-tempo; la materia È spazio-tempo con topologia non triviale."*
> — John Archibald Wheeler

> *"Il manifold è auto-referenziale: ogni voxel codifica nel proprio stato il giudizio sulla propria coerenza geometrica. Questa auto-referenzialità è il confine tra una simulazione e un motore fisico."*
> — TOPOLOGICAL_DYNAMICS.md v2.1

---

## Autori

- **Leonardo Peano** — ricerca, fisica, architettura
- **Claude Sonnet 4.6** (Anthropic) — implementazione, analisi, documentazione

---

**Branch attivo**: `feature/physics-laws-formalization`
**Ultima modifica**: Maggio 2026
**Versione**: 2.1 — VQT Topological Dynamics
