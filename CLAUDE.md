# CLAUDE.md — Guida operativa per VQT_repo

Questo file viene letto automaticamente all'inizio di ogni sessione.
Leggilo SEMPRE prima di iniziare a lavorare, insieme al checkpoint.

---

## 0. PATTERN COMPORTAMENTALI OBBLIGATORI

Questi non sono suggerimenti: sono regole apprese da errori reali in questo progetto.

1. **TIENI AGGIORNATO IL CHECKPOINT.** Il file `docs/peano/MIGRAZIONE_CHECKPOINT.md`
   e' la memoria di lungo termine del progetto. Ad OGNI sessione:
   - All'inizio: leggi la sezione ">>> PROSSIMI TASK PRIORITARI <<<" in testa.
   - Durante: aggiorna lo stato man mano che completi i task.
   - Alla fine: aggiorna i prossimi task e committa. NON lasciare il checkpoint
     disallineato dal lavoro reale (e' gia' successo: indicava "PIANIFICATO"
     quando il lavoro era fatto).

2. **VERIFICA PRIMA DI DOCUMENTARE.** Errore gia' commesso e corretto: ho scritto
   "speedup 100-1000x" PRIMA di fare il benchmark; il valore reale era ~6x. NON
   scrivere numeri di performance o claim fisici nella documentazione finche' non
   sono MISURATI. Se scrivi una stima, etichettala esplicitamente come "stima".

3. **NON DOCUMENTARE CIO' CHE NON E' OSSERVATO.** La teoria si documenta DOPO che
   l'esperimento l'ha confermata, non prima. (Vedi TASK 1 nel checkpoint: il drain
   non e' ancora stato osservato in un run reale.)

4. **CODICE ADDITIVO, NON SOSTITUTIVO.** `SolitoneComposito.evolve()` e tutto il
   motore legacy NON vanno modificati. Le ottimizzazioni si aggiungono come nuovi
   metodi/moduli con flag opt-in (es. `evolve_fast`, `--fast-evolver`). Il default
   resta sempre il comportamento classico verificato.

5. **OGNI MODIFICA FISICA VA VERIFICATA con un test di equivalenza** contro un
   riferimento (RK45, o evolve() classico). Pattern usato: test che confrontano
   osservabili collettivi entro tolleranza. Vedi `test_*_equivalence.py`.

6. **Branch di lavoro: `research-backup`.** Commit in italiano, descrittivi.
   Chiudi i messaggi di commit con: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
   Committa e pusha quando l'utente lo chiede o a fine task significativo.

7. **NON c'e' solo Claude.** A volte Gemini lavora in parallelo sullo stesso repo
   (scrive nel checkpoint, committa). All'inizio sessione verifica `git log` per
   commit non tuoi e processi Python attivi (run lanciati da altri). Chiedi prima
   di fermare processi altrui.

8. **PIANIFICA PRIMA DI AGIRE (regola di Luca, 2026-06-10).** Prima di intraprendere
   QUALSIASI azione non banale: **(a) PROGETTA/PIANIFICA** il passo (cosa, perche',
   come, rischi/alternative); **(b) SEGNA i TODO nel checkpoint**
   (`docs/peano/MIGRAZIONE_CHECKPOINT.md`, blocco "PER DOMANI"/task) — e usa anche
   TodoWrite per il tracking della sessione; **(c) SOLO DOPO esegui.** Niente azioni
   "a braccio": prima il piano scritto, poi il codice. Vale in particolare per
   operazioni git (merge/push), refactor, rifondazioni doc e nuovi esperimenti.

9. **UN FOLDER PER ESPERIMENTO (regola di Luca, 2026-06-10).** Ogni esperimento sta
   in una propria cartella sotto `experiments/`, e il NOME della cartella RIFLETTE il
   nome dell'esperimento (es. `experiments/collasso_dinamico/`, non `experiments/exp3/`
   con dentro N test scollegati). Dentro: lo script del test + eventuali output/figure/
   note di quell'esperimento. Vale per i NUOVI esperimenti (i vecchi `expN/` si
   migrano solo se richiesto).

10. **IL MOTORE E' LA STELLA POLARE (regola di Luca, 2026-06-10).** Quando un test
    CONFERMA una caratteristica fisica, quella caratteristica va INTEGRATA SUBITO nel
    motore completo (`set_ec_integrato` la deve accendere), nello STESSO ciclo di
    lavoro: test confermato = motore aggiornato + GATE ri-eseguiti. Il motore deve
    rimanere SEMPRE coerente alla teoria validata; non deve mai servire un attivatore
    separato per una fisica gia' confermata. Tutti i test successivi usano il motore
    cosi' integrato (mai versioni parziali). Luca NON deve doverlo chiedere.

---

## 1. COS'E' IL PROGETTO

VQT (Voxel Quantum Theory) / Peano-VQT: motore di simulazione di un manifold
frattale gerarchico. Ogni livello L(n) contiene 24 unita' del livello inferiore.
Campo scalare chi con potenziale doppio pozzo V(chi) = beta*(chi^2 - chi_stable^2)^2.

Due rami complementari:
- **Ramo A (Cosmologia/RG-flow)**: generazione dati, gerarchia 24^L, sigma_inf,
  S_residual, transizione termodinamica L->L+1. Genera cosmo_L*.h5.
- **Ramo B (Peano-VQT)**: triade energetica, drain Jitterbug, nascita materia.
  E_Psi, costante sqrt(2), fasi geometriche.
- **Unificazione**: E_Psi (B) <-> S_residual (A);
  sigma_inf = sqrt(E_Psi / (lambda_homeo * N_dof)).

---

## 2. INVARIANTI FISICI (non violare senza motivo esplicito)

- **Triade Peano-VQT**: `dE_chi + dE_RX + dE_Psi = 0` (conservata dal drain).
- **Soglia Jitterbug**: `chi_max / chi_stable = sqrt(2) ~ 1.4142` (costante geometrica
  Ottaedro->Cubottaedro di Fuller). E' la soglia del drain. Calibrata su L2/L3/L4.
- **chi_stable = 50.0** (VEV del campo, default in PhysicsContext). Il minimo del
  doppio pozzo DEVE coincidere con chi_stable (fix 2026-05-26: era 4.5 hardcoded,
  causava collasso nel pozzo sbagliato).
- **Segnale di saturazione = chi_MAX** (non chi_mean): e' la singolarita' locale.
- **Fasi geometriche**: chi_max/chi_stable < 1.0 Ottaedrica; 1.0..sqrt(2)
  Cubottaedrica (VE); >= sqrt(2) Icosaedrica (materia).
- **Solver-indipendenza**: gli osservabili collettivi non dipendono dal metodo di
  integrazione (T_dom invariante). Questo legittima i metodi accelerati.

---

## 3. MAPPA DEI FILE

```
wqt_oop/                          Pacchetto di produzione
  solitone_composito.py           Livello N>=1. evolve() [legacy] + evolve_fast() [accelerato]
  segmento_quantistico.py         Livello 0. GIA' Verlet+Strang simplettico
  physics_context.py              Parametri scala-dipendenti. for_level(chi_mean_init=...)
  energy_metrics.py               PeanoVQTAnalyzer, EnergyTriad, GeometricPhase, load_h5_and_validate
  fast_evolver.py                 FastEvolver: evoluzione accelerata foglie L1 (Verlet/Forest-Ruth)
  spectral_coupling.py            SpectralBasis (DFT su Z_24). SPERIMENTALE (bug splitting 38%)
  symplectic_step.py              verlet_step, forest_ruth_step, strang_splitting_step
  topological_constraint_validator.py  Validator (vettorizzato ~5x da Gemini)
  topological_integration.py      TopologicalEvolutionWrapper (use_fast_evolver flag)
  hdf5_logger.py                  Output HDF5 (salva E_chi/E_RX/E_Psi per frame)
  test_peano_vqt.py               7 test teoria Peano-VQT
  test_fast_evolver_equivalence.py    5 test equivalenza L1 vs RK45 + drain
  test_evolve_fast_equivalence.py     GATE: evolve vs evolve_fast su L2
CoreEngine_v2/                    Automazione gerarchica (Gemini)
  global_state.py                 S_residual, transition_potential, GlobalState persistente
  recursive_manifold_manager.py   auto_advance, bootstrap, run_next_level
  phase_transition_signal.py      Segnale di saturazione termodinamico
tools/rendering/generate_topological_dataset.py   Generatore dati CLI (--fast-evolver)
experiments/exp1/                 Dati storici L1/L2/L3/L4
experiments/exp3/                 Run nuovi (--fast-evolver) + analyze_exp3.py + figures/
docs/peano/MIGRAZIONE_CHECKPOINT.md   CHECKPOINT — leggi/aggiorna sempre
docs/peano/VQT_MANIFESTO_TEORICO.md   Teoria (tre leggi, sqrt(2), triade)
docs/cosmology/SPECTRAL_METHODS.md    Metodi accelerati (numeri reali ~6x)
docs/cosmology/ARCHITETTURA_SCALING_MASSIVO.md  Architettura performance
```

---

## 4. COMANDI CHIAVE

```bash
cd VQT_repo

# Test (rapidi, eseguili dopo ogni modifica)
python -m wqt_oop.test_peano_vqt                  # teoria Peano-VQT (7/7)
python -m wqt_oop.test_fast_evolver_equivalence   # equivalenza L1 (5/5)
python -m wqt_oop.test_evolve_fast_equivalence    # GATE L2 (evolve vs evolve_fast)

# Calibrazione costante Jitterbug su dati storici
python -m wqt_oop.calibrate_peano_vqt

# Generatore dati (path accelerato additivo)
python tools/rendering/generate_topological_dataset.py \
  --level 3 --steps 600 --dt 0.02 --fast-evolver \
  --inherit experiments/exp1/cosmo_L3_ext3.h5 --inherit-percentile 75 \
  --output experiments/exp3/cosmo_L3.h5 --watchdog --watchdog-window 50

# Analisi + grafici exp3
python experiments/exp3/analyze_exp3.py

# Benchmark validator vettorizzato
python benchmark_validator.py
```

---

## 5. AMBIENTE (Windows)

- Encoding: console cp1252. NON usare caratteri non-ASCII (frecce ->, sigma) negli
  output stampati: causano UnicodeEncodeError. Usa ASCII nei print/log.
- File HDF5 lockati da processi attivi: leggi con `swmr=True` o aspetta la fine.
- Per leggere dati h5 mentre un run scrive: usare copia o swmr.
- Verifica processi: `Get-Process python*`. Command line: `Get-CimInstance Win32_Process`.

---

## 6. STATO CORRENTE (aggiorna a fine sessione)

Vedi `docs/peano/MIGRAZIONE_CHECKPOINT.md` sezione ">>> PROSSIMI TASK PRIORITARI <<<".

Sintesi al 2026-06-01:
- Infrastruttura completa e verificata (FastEvolver ~6x, validator ~5x, test tutti PASS).
- **TASK 1 aperto [priorita' massima]**: osservare E_Psi crescere in un run reale
  (il drain non e' mai scattato in produzione; chi_max sempre < soglia 70.7).
- **TASK 2**: documento unificato Ramo A+B, solo DOPO Task 1.

---

## 7. GOTCHA TECNICI APPRESI

- Il path **spettrale** (`use_spectral_linear=True`) ha un bug (deriva 38%):
  SPERIMENTALE, non usarlo. Default = Verlet/Forest-Ruth puro (verificato).
- Bottleneck reale L4: (1) `compute_hamiltonian()` ricorsivo 2x/step;
  (2) il validator (ora vettorizzato). NON il loop di integrazione.
- `cosmo_L3_merged.h5` ha 0 frame (vuoto). Usa `cosmo_L3_ext3.h5` (600 frame).
- Il drain scatta solo se chi_max >= sqrt(2)*chi_stable = 70.7. Nei run brevi con
  chi_mean=50 NON scatta (chi_max ~55-60). Serve run lungo o inherit ad alto chi.
- get_total_E_psi() aggrega E_Psi da tutti i livelli: il drain scatta a L1, ma il
  root L3/L4 vede solo medie (~50). Senza aggregazione E_Psi sembra sempre 0.
- **NON-DETERMINISMO DEL MOTORE (scoperto 2026-06-04)**: `SolitoneComposito.`
  `_transfer_heat_to_children` (riscaldamento gerarchico, riga ~1098) usa
  `np.random.rand()` GLOBALE non seedato. Quindi il sistema e' STOCASTICO
  run-to-run: lo stesso seed da' risultati diversi. Le STATISTICHE aggregate
  (medie/frazioni d'ensemble) restano valide (rumore termico = parte del modello),
  ma il singolo seed NON identifica una realizzazione e i risultati non sono
  riproducibili. FIX: `np.random.seed(seed + k*cm)` all'inizio del quench
  (vedi test_termodinamica_kink_par.py::_quench_one). Sempre seedare per run
  riproducibili o confronti seriale-vs-parallelo.
- **PARALLELISMO (2026-06-04)**: i seed sono indipendenti -> parallelizzabili con
  multiprocessing (test_termodinamica_kink_par.py, --workers). Pattern: spawn,
  OMP_NUM_THREADS=1 nei worker (no oversubscription), seeding deterministico,
  ResumeManager per crash-safety. SEMPRE verificare con il GATE
  test_equivalenza_parallelo.py (deve dare err=0 bit-per-bit) prima di fidarsi.
  Speedup ~5x con 6 worker. Tempo quench: L2 ~42s, L3 ~25min, L4 ~8h (stima).
- **DISTINZIONE DI DOMINIO**: "legge dei divisori di 24" ha senso SOLO su conteggi
  (n_eff_block). NON su grandezze continue (M_tot energia estensiva ~N, chi_c
  ampiezza). Cercare "multipli di 24" su energie/ampiezze e' numerologia.
- **FIT CRITICI**: vicino a una soglia, l'esponente p e chi_c sono DEGENERI
  (anti-correlati). Fissare chi_c da fonte indipendente (es. nucleazione binaria)
  prima di fittare p. Escludere i punti di saturazione (plasma, taglia finita)
  che gonfiano la pendenza. La legge di potenza critica vale solo per eps->0.
