# Checkpoint VQT - Ultimo Aggiornamento: 2026-05-29 (sessione corrente)

## Stato Attuale

- [X] Analisi stato su disco (energy_metrics.py mancante, solitone_composito.py classico)
- [X] **Blocco 1/4** — Creazione `wqt_oop/energy_metrics.py` (PeanoVQTAnalyzer, EnergyTriad, PhaseTransitionEvent)
- [X] **Blocco 2/4** — Modifica `wqt_oop/solitone_composito.py`
  - [X] Import di PeanoVQTAnalyzer, EnergyTriad
  - [X] Attributi `_peano_analyzer`, `_last_triad`, `_triad_step` in `__init__`
  - [X] Refactoring `compute_hamiltonian_coupling()` con estrazione dei tre componenti (E_chi_raw, E_torsion, E_exchange_val) e side-effect triade con guard per-step
  - [X] Aggiunta metodo `get_energy_triad()`
  - [X] Aggiornamento `get_energy_budget()` con chiavi `E_chi`, `E_RX`, `E_Psi`
- [X] **Blocco 3/4** — Modifica `wqt_oop/hdf5_logger.py`
  - [X] `_extract_frame_data()` salva E_chi, E_RX, E_Psi come scalari
  - [X] `load_from_hdf5()` carica E_chi, E_RX, E_Psi con default 0.0 (backward-compat)
- [X] **Blocco 4/4** — Creazione `wqt_oop/test_peano_integration.py`
  - [X] Test 1: drain conserva dE_chi + dE_RX + dE_Psi = 0
  - [X] Test 2: nessun drain sotto soglia
  - [X] Test 3: SolitoneComposito espone triade corretta
  - [X] Test 4: guard per-step previene double-drain
- [X] **Tutti e 4 i test passati** (eseguiti, output verificato)

## Analisi

### Cosa è stato fatto

**Architettura della triade Peano-VQT:**
- `E_chi` = kappa_coupling × E_coupling (energia di allineamento χ)
- `E_RX` = E_torsion + E_exchange (energia reattiva: geometria + scambio topologico)
- `E_Psi` = energia accumulata nel sink radiativo (cresce monotonicamente via drain)

**Invariante conservato per l'operazione di drain:**
`dE_chi + dE_RX + dE_Psi = 0`
→ verificato: total_before = total_after = 105.0 nel test unitario

**Decisione architetturale critica:**
`compute_hamiltonian_coupling()` **mantiene la firma `-> float`** (non è stata cambiata in `-> dict`).
Ragione: l'interfaccia astratta `AbstractSoliton` e 5 punti nel codice usano il valore come float.
La triade è accessibile tramite `get_energy_triad()` e `get_energy_budget()`.

**Guard per-step (`_triad_step`):**
Impedisce il double-drain nelle due chiamate che `evolve()` fa a `compute_hamiltonian_coupling()`
(una per H_before, una per H_after). Verificato con il Test 4.

**Valore di H_coupling in un caso reale (L1, 24 figli, chi≈50, chi_stable=50):**
- E_chi = +8.38e0, E_RX = -9.81e0, H_coup = -1.26e0
- Il termine di scambio topologico (E_exchange) è fortemente ferromagnetico a L1
  perché lambda_exchange scala come 24^(2*level) = 576× mentre alpha_K scala come 1/24.
  Questo è fisicamente atteso: a scala nucleare (L1) l'interazione di scambio domina.

## Prossimo Task

**Nessun task obbligatorio rimasto nella sessione corrente.**

Possibili estensioni future (non urgenti):
1. Integrare la triade nel rendering `hdf5_playback.py` / `visualizer.py` (plot E_chi/E_RX/E_Psi vs step)
2. Verificare che `physics_context.py` abbia parametri ottimali per la soglia di saturazione χ
3. Eseguire una simulazione produzione completa e verificare che E_Psi cresca in modo regolare
4. Valutare se `chi_stable` debba scalare con il livello in `PhysicsContext.for_level()`
   (attualmente è 50.0 fisso a tutti i livelli — potrebbe causare saturazione prematura a L2+)

## Stato del Codice

| File | Stato | Modifiche |
|------|-------|-----------|
| `wqt_oop/energy_metrics.py` | **NUOVO** | EnergyTriad, PhaseTransitionEvent, PeanoVQTAnalyzer |
| `wqt_oop/solitone_composito.py` | **MODIFICATO** | Import, __init__ (3 attr), compute_hamiltonian_coupling (refactoring+triade), get_energy_triad (nuovo), get_energy_budget (+E_chi/E_RX/E_Psi) |
| `wqt_oop/hdf5_logger.py` | **MODIFICATO** | _extract_frame_data (+E_chi/E_RX/E_Psi), load_from_hdf5 (+E_chi/E_RX/E_Psi backward-compat) |
| `wqt_oop/test_peano_integration.py` | **NUOVO** | 4 test, tutti PASS |
| `wqt_oop/physics_context.py` | INVARIATO | Nessuna modifica necessaria |
| `wqt_oop/abstract_soliton.py` | INVARIATO | Firma `-> float` preservata intenzionalmente |

## Note Tecniche per Ripresa

- In caso di ECONNRESET: leggere questo file, poi leggere `wqt_oop/energy_metrics.py` per verificare che esista su disco.
- Il test si esegue con: `python -m wqt_oop.test_peano_integration` dalla root del repo.
- I valori di `chi_saturation_threshold=0.8` e `drain_rate=0.1` sono i default nel `_peano_analyzer` di `SolitoneComposito.__init__`. Possono essere personalizzati passando un `PeanoVQTAnalyzer` configurato diversamente.

---
## Analisi Analitica Run 2026-05-29 11:58

### Conclusioni fisiche (estratte da osservazioni_simulazione.log + HDF5)

**Fase**: 100% Icosaedrica (chi_sat ∈ [0.91, 1.08]) per tutti i 300 step.
**Attractor**: chi_sat staziona intorno a 1.0 ± 0.10 → campo χ ancorato a chi_stable.
**E_Psi**: monotone crescente da 9.7e-6 a 2.28e-4 (×23), invariante verificata.
**E_RX >> E_chi**: E_RX ≈ 1100-1600, E_chi ≈ 1e-5 to 2e-4. Scambio ferromagnetico dominante a chi≈chi_stable.
**H_dissipazione**: −44% in 300 step (sistema sovra-smorzato, gamma≈0.0095). Non è stabilizzazione ma dissipazione sistematica.
**Condensazione**: il frame_000000 coincide con t=0 perché il sistema era già in fase icosaedrica all'inizializzazione (chi_mean=45≈chi_stable). Il "punto di nascita" non è stato una transizione, era uno stato iniziale.

### Per osservare la nascita della materia come transizione
Servono: chi_mean=5 (chi_sat_0=0.10, fase Ottaedrica), N_STEPS=2000.
Aspettarsi: Ottaedrica → Cubottaedrica → Icosaedrica, con E_Psi che salta al momento della condensazione.

---
## Run di Validazione — 2026-05-29 11:58

- File HDF5: `peano_sim_20260529_115818.h5`
- Frames: 60
- E_Psi finale: 2.2859e-04
- Drain frames: 59
- E_Psi monotona: SI
- Fasi: {'Ottaedrica': 0, 'Cubottaedrica': 0, 'Icosaedrica': 60}
- Condensazione (icosaedrica): SI (frame frame_000000)
- Tempo simulazione: 8.3s

---
## GENESIS RUN — 2026-05-29 12:28

**Config**: chi_mean=5.0, N_STEPS=2000, dt=0.1

**Domanda a) Prima cristallizzazione icosaedrica**: step 10

**Domanda b) Salto E_Psi al momento della cristallizzazione**: 0.0000e+00

**Primo drain attivato**: step 20

**Validazione HDF5**:
- Frames: 100
- E_Psi finale: 1.0734e-04
- E_Psi monotona: SI
- Drain frames: 59
- Fasi: {'Ottaedrica': 0, 'Cubottaedrica': 1, 'Icosaedrica': 99}
- Condensazione confermata: SI (frame frame_000001)

**N. eventi registrati**: 19
**Tempo simulazione**: 42.6s
**File**: genesis_20260529_122803.h5

---
## L2 Aggregation Run — 2026-05-29 13:05

**Parametri**: kappa_inter=2.0, lambda=0.5, W_AB=0.189, N=400

| Scenario | Esito | Dchi_0 | Dchi_f | Fase A | Fase B | Frustrazione | E_Psi |
|----------|-------|--------|--------|--------|--------|--------------|-------|
| SAME  | AGGREGATO | 4.18 | 1.086 | Icosaedrica | Icosaedrica | NO | 1.6687e-04 |
| CROSS | OSCILLANTE | 99.79 | 96.759 | Icosaedrica | Icosaedrica | SI | 4.7941e-04 |

**Conclusione**: OSCILLANTE cross-fase, frustrazione rilevata.

---
## L2 Leech Run — 2026-05-29 13:22

**Config**: 24 L1 solitoni, kappa_NN=1.5, N_NN=6, N_STEPS=100

**a) Solitoni nel cluster principale**:
- ALL_POSITIVE: **0/24** (POLVERE DI PARTICELLE)
- HALF_HALF: **0/24** (POLVERE DI PARTICELLE)

**b) E_Psi collettiva (indicatore legame)**:
- ALL_POSITIVE: 1.6388e+04
- HALF_HALF: 1.6920e+04

**c) Esito**:
- ALL_POSITIVE: **POLVERE DI PARTICELLE**
- HALF_HALF: **POLVERE DI PARTICELLE**

| Modo | chi_sat | M | Frustr | Cluster | E_Psi |
|------|---------|---|--------|---------|-------|
| ALL_POS | 0.4086 | 0.4039 | -0.8295 | 0/24 | 1.6388e+04 |
| HALF_HALF | 0.2576 | -0.0729 | -0.2103 | 0/24 | 1.6920e+04 |

---
## L4 Self-Assembly — 2026-05-29 13:40

**Config**: 48 L1 (EffectiveL1), 3000 step, kappa_NN=2.0, R=9.0

**a) Cluster formati**: 8 cluster | dimensioni: [25, 8, 5, 5, 2, 1, 1, 1]

**b) E_Psi collettiva**: 1.0640e+04

**c) Esito**: **STRUTTURA CRISTALLINA (dominio maggioritario)**
- Multipli di 12: SI (1 cluster)
- CN_mean finale: 7.21 (target: 12.0)
- M (ordine): 0.7489
- chi_sat: 0.9741
- H_tot: 2.7600e+05 -> 2.6453e+04 (-90.4%)

**Livelli consolidati**: L2: step 600 size=24
**Tempo run**: 0.19s
