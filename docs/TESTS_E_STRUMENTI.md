# VQT — Guida completa ai test e agli strumenti

**Branch**: `research-backup` · **Aggiornamento**: 2026-06-04

Questo documento e' il riferimento unico per tutti i test, benchmark e strumenti
di analisi del progetto VQT. Per ogni script: scopo fisico, quando usarlo, come
lanciarlo con tutti i parametri, e cosa aspettarsi in output.

**Regola**: ogni nuovo test aggiunto al progetto deve essere documentato qui.

---

## Indice rapido

| Categoria | Script | Tempo | Stato |
|---|---|---|---|
| **Suite di regressione** | `test_peano_vqt.py` | ~1s | PASS obbligatorio |
| | `test_fast_evolver_equivalence.py` | ~5s | PASS obbligatorio |
| | `test_evolve_fast_equivalence.py` | ~30s | PASS obbligatorio |
| | `test_peano_integration.py` | ~5s | PASS obbligatorio |
| **Calibrazione** | `calibrate_peano_vqt.py` | ~1s | su dati HDF5 |
| **Benchmark** | `benchmark_validator.py` | ~10s | performance |
| | `tools/benchmarks/benchmark_sparse.py` | ~5s | performance |
| | `tools/benchmarks/benchmark_spectral.py` | ~5s | performance |
| **Numerica** | `tools/tests/test_baseline_symplectic.py` | ~5s | verifica solver |
| | `tools/tests/test_convergence.py` | ~10s | ordine convergenza |
| | `tools/tests/test_pure_verlet.py` | ~5s | verifica Verlet |
| **Fisica Peano-VQT** | `test_falsificabilita.py` | ~5 min | fondamenta |
| | `test_soglia_formazione.py` | ~10-30 min | dipende da level |
| | `test_quench_mass.py` | ~5 min | bimodalita' massa |
| | `test_transizione_dinamica.py` | ~10 min | soglia sqrt(2) |
| | `test_massa_gerarchica.py` | ~5 min | legge di scala |
| | `test_quench_localizzazione.py` | ~30-60 min | finestra kink |
| | `test_riproducibilita_difetto.py` | ~20-50 min | fase vs evento |
| | `test_biopsia_difetto_v2.py` | ~15-30 min | geometria kink |
| | `test_soc_distribuzione.py` | ~20 min | SOC (falsificata) |
| | `test_quantizzazione_gerarchica.py` | ~4 ore (L3) | ipotesi Z_24 |
| | `test_termodinamica_kink.py` | ~50 min (L2) | legge KZ, chi_c, nu |

---

## Sezione 1 — Suite di regressione obbligatoria

Questi test vanno eseguiti dopo **ogni modifica al codice** in `wqt_oop/`.
Tutti devono passare (exit 0) prima di fare commit.

### 1.1 `wqt_oop/test_peano_vqt.py`

**Cosa fa**: verifica i 7 invarianti fondamentali della teoria Peano-VQT:
soglia Jitterbug sqrt(2), segnale chi_max (non chi_mean), conservazione del
drain (`dE_chi + dE_RX + dE_Psi = 0`), classificazione fasi geometriche,
guard per-step contro il double-drain, backward compatibility dell'API.
E' il test piu' importante: se fallisce, qualcosa di fondamentale e' rotto.

```bash
cd VQT_repo
python -m wqt_oop.test_peano_vqt
```

**Nessun parametro.** Output atteso:
```
7/7 test superati
Costante Jitterbug sqrt(2): IMPLEMENTAZIONE VERIFICATA
```

---

### 1.2 `wqt_oop/test_fast_evolver_equivalence.py`

**Cosa fa**: verifica che `FastEvolver` (percorso accelerato, Verlet/Forest-Ruth)
riproduca gli stessi osservabili collettivi dell'integrazione di riferimento (RK45)
entro tolleranza di macchina, su L1 e con drain attivo. 5 test indipendenti.
Garantisce che il percorso veloce non alteri la fisica.

```bash
python -m wqt_oop.test_fast_evolver_equivalence
```

**Nessun parametro.** Output atteso: `5/5 test superati`.

---

### 1.3 `wqt_oop/test_evolve_fast_equivalence.py`

**Cosa fa**: test CANCELLO (gate) per `evolve_fast()` su L2.
Confronta `evolve()` (legacy, riferimento) con `evolve_fast()` (accelerato)
su un SolitoneComposito L2 per N step, verifica che gli osservabili collettivi
(E_chi, chi_mean, chi_max) divergano meno della tolleranza definita.
Va eseguito prima di usare `evolve_fast()` in produzione.

```bash
python -m wqt_oop.test_evolve_fast_equivalence
```

**Nessun parametro.** Output atteso: `GATE PASS`.

---

### 1.4 `experiments/test_peano_integration.py`

**Cosa fa**: 4 test di integrazione del sistema completo:
(1) drain conserva la triade, (2) nessun drain sotto soglia,
(3) SolitoneComposito espone correttamente la triade energetica,
(4) guard per-step previene double-drain in `evolve()`.

```bash
python experiments/test_peano_integration.py
```

**Nessun parametro.** Output atteso: 4 test PASS.

---

## Sezione 2 — Calibrazione

### 2.1 `wqt_oop/calibrate_peano_vqt.py`

**Cosa fa**: verifica sperimentale della costante Jitterbug (soglia sqrt(2))
sui file HDF5 storici (L2/L3/L4). Misura chi_max_peak / chi_stable su tutti
i frame disponibili e confronta con sqrt(2) = 1.4142. Risultato atteso: 5/8+
file entro il 10% di errore. Serve per validare la calibrazione del modello
su dati reali, non sintetici.

```bash
python -m wqt_oop.calibrate_peano_vqt
```

**Nessun parametro** (legge automaticamente i file HDF5 in `experiments/exp1/`).
Output: tabella per file con chi_max_peak/chi_stable, errore relativo, verdetto.

---

## Sezione 3 — Benchmark di performance

Questi script misurano la velocita' del codice, non la correttezza fisica.
Eseguirli dopo refactoring o ottimizzazioni per verificare che le performance
non degradino.

### 3.1 `benchmark_validator.py`

**Cosa fa**: misura il throughput del `TopologicalConstraintValidator`
(vettorizzato da Gemini ~5x rispetto alla versione originale). Confronta
la versione vettorizzata con quella di riferimento.

```bash
python benchmark_validator.py
```

Output: tempo/step per la versione vettorizzata vs riferimento, speedup.
**Atteso**: ~5x speedup.

---

### 3.2 `tools/benchmarks/benchmark_sparse.py`

**Cosa fa**: benchmark delle operazioni sparse su matrice di coupling L4
(N=331,776). Misura il costo di `csr_matrix.dot()` e delle somme per riga
su dataset realistici.

```bash
python tools/benchmarks/benchmark_sparse.py
```

**Nessun parametro.** Output: tempi in secondi per le operazioni chiave.

---

### 3.3 `tools/benchmarks/benchmark_spectral.py`

**Cosa fa**: benchmark della decomposizione spettrale (DFT su Z_24) vs
il coupling diretto. Utile per valutare se il percorso spettrale (attualmente
SPERIMENTALE con bug 38%) potrebbe essere competitivo una volta corretto.

```bash
python tools/benchmarks/benchmark_spectral.py
```

> **Nota**: il percorso spettrale ha un bug di deriva 38%. Non usarlo in
> produzione (`use_spectral_linear=False` e' il default sicuro).

---

## Sezione 4 — Validazione numerica del solver

### 4.1 `tools/tests/test_baseline_symplectic.py`

**Cosa fa**: verifica che il Velocity Verlet con dt globale uniforme preservi
la proprieta' simplettica (volume nello spazio delle fasi conservato).
Test post-rollback: conferma la stabilita' dopo la rimozione del multi-rate.
Drift atteso < 1e-8.

```bash
python tools/tests/test_baseline_symplectic.py
```

**Nessun parametro.** Output: drift dell'area simplettica dopo N step.

---

### 4.2 `tools/tests/test_convergence.py`

**Cosa fa**: verifica l'ordine di convergenza del solver (Verlet: ordine 2,
Forest-Ruth: ordine 4). Confronta la soluzione numerica con una soluzione
analitica nota al variare di dt. Serve a verificare che nessuna modifica
al solver abbia degradato l'ordine.

```bash
python tools/tests/test_convergence.py
```

**Nessun parametro.** Output: ordine di convergenza misurato per Verlet e Forest-Ruth.

---

### 4.3 `tools/tests/test_pure_verlet.py`

**Cosa fa**: test minimale del Velocity Verlet in isolamento (senza coupling,
senza drain). Verifica conservazione dell'energia e reversibilita' per un
oscillatore armonico semplice.

```bash
python tools/tests/test_pure_verlet.py
```

---

## Sezione 5 — Fisica Peano-VQT (linea di ricerca principale)

Questi script implementano la ricerca scientifica. Vanno eseguiti in ordine
logico (ogni script usa funzioni dei precedenti). Tutti producono grafici
in `experiments/exp3/figures/`.

**Dipendenza comune**: tutti importano `make()` da `test_soglia_formazione.py`.

---

### 5.1 `experiments/exp3/test_falsificabilita.py`

**Cosa fa e perche'**: prima di fare qualsiasi misura costosa (L3, L4),
questo script esegue 4 test di falsificabilita' che stabiliscono se i fenomeni
osservati sono fisica reale o artefatti del codice:
- **Test A**: la soglia sqrt(2) emerge dai dati storici o e' hardcoded?
- **Test B**: il drain_rate e' robusto (fisica) o il drain scala linearmente
  con drain_rate (artefatto)?
- **Test C**: senza drain il sistema resta stabile?
- **Test B2**: E_Psi_anchored (geometrica) e' stabile indipendentemente dal
  drain_rate?

**Risultati storici**: Test A confermato (sqrt(2) emerge), Test B falsificato
(E_Psi ~ 15.7 * drain_rate = artefatto), Test C confermato (sistema stabile),
Test B2 confermato (E_Psi_anchored robusta).

```bash
python experiments/exp3/test_falsificabilita.py
```

**Nessun parametro CLI.** Legge i file HDF5 in `experiments/exp1/`.
Output: verdetti per i 4 test. Tempo: ~5 min.

---

### 5.2 `experiments/exp3/test_soglia_formazione.py`

**Cosa fa e perche'**: risponde alla domanda "sqrt(2) e' l'istante di formazione
della massa?". Evolve il sistema fino a 100 step registrando chi_max(t), trova
il momento in cui chi_max attraversa sqrt(2)*chi_stable (cross_sqrt2), poi
quencha copie del sistema a diversi tempi pre (40, 50, ..., 100 step) e misura
la massa residua. Confronta cross_sqrt2 con la soglia di formazione.

**Risultato**: NON coincidono. Cross_sqrt2 ~ 12 step, soglia_massa ~ 63 step
(ritardo +51). Struttura a due tempi: sqrt(2) e' PREREQUISITO, non evento.
Il ritardo e' invariante di scala (L1: +50.4, L2: +54.2).

Fornisce anche la funzione `make(seed, chi_mean, level)` usata da tutti gli
altri script della suite.

```bash
python experiments/exp3/test_soglia_formazione.py --level 1 --seeds 10
python experiments/exp3/test_soglia_formazione.py --level 2 --seeds 4
python experiments/exp3/test_soglia_formazione.py --level 3 --seeds 2 --quench-steps 400
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 1 | Livello gerarchico (1=24 nodi, 2=576, 3=13824) |
| `--seeds` | 10 | Numero di seed indipendenti |
| `--pre` | `40,50,60,70,80,90,100` | Punti di pre-evoluzione da testare (CSV) |
| `--quench-steps` | 1500 | Step massimi del quench per ciascun punto |

**Output**: tabella per seed con cross_sqrt2, soglia_massa, ritardo.
Figure: `figures/soglia_formazione_L{n}.png`.

---

### 5.3 `experiments/exp3/test_quench_mass.py`

**Cosa fa e perche'**: verifica la bimodalita' della massa. Su 36 stati L1,
quencha a temperatura zero e misura E_psi_residual. Risponde: la massa e'
quantizzata (presente/assente) o e' un continuo? Determina anche la soglia
temporale: sotto quanti step non si forma mai massa, sopra quanti si forma
sempre.

**Risultato**: bimodale (24/36 massivi ~1360, 12/36 a zero). Soglia:
< 40 step → 0% massivi, >= 100 step → 100% massivi.

```bash
python experiments/exp3/test_quench_mass.py
```

**Nessun parametro CLI.** Output: distribuzione E_psi_residual, soglie.

---

### 5.4 `experiments/exp3/test_transizione_dinamica.py`

**Cosa fa e perche'**: misura E_Psi_anchored (metrica geometrica istantanea,
senza drain) in funzione del tempo durante l'evoluzione. Visualizza come la
metrica di frustrazione topologica cresce durante l'attraversamento di sqrt(2)
e stabilizza dopo il congelamento del kink.

```bash
python experiments/exp3/test_transizione_dinamica.py
```

**Nessun parametro CLI.** Output: grafico E_Psi_anchored(t) con marcatore
sqrt(2). Conferma la struttura a due tempi.

---

### 5.5 `experiments/exp3/test_massa_gerarchica.py`

**Cosa fa e perche'**: misura la massa (frustrazione topologica) aggregando
correttamente su TUTTA la gerarchia, senza il bias del root. Il root di un
sistema L3 vede solo le medie dei 24 figli L2 (filtro passa-basso) e restituisce
E_Psi~0 anche quando la frustrazione e' alta. Questo script usa
`compute_hierarchical_mass()` che scende fino alle foglie.

**Risultato chiave**: M_tot ~ N^1.01 (massa estensiva), rho_M ~ 2.9/nodo
invariante di scala da L1 a L3. La "no-massa" a L3 era un artefatto del root.

```bash
python experiments/exp3/test_massa_gerarchica.py --levels 1,2,3
python experiments/exp3/test_massa_gerarchica.py --levels 1,2,3 --seed 5 --pre 60
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--levels` | `1,2,3` | Livelli da misurare, separati da virgola |
| `--seed` | 1 | Seed per l'inizializzazione |
| `--pre` | 60 | Step di pre-evoluzione prima della misura |

**Output**: tabella M_tot, rho_M, loc_ratio per livello. Legge di scala M~N^a.

---

### 5.6 `experiments/exp3/test_quench_localizzazione.py`

**Cosa fa e perche'**: sweep di chi_mean per trovare la FINESTRA di
localizzazione del kink. Per ogni valore di chi_mean: pre-evolve fino al
picco, quencha T→0, misura loc_ratio = IPR * N sulle foglie dello stato
congelato. Identifica il regime dove il difetto e' massimamente concentrato
(particella) vs distribuito (campo).

**Risultato chiave**: finestra peak ~ 1.8-1.95 dove loc_ratio L2 = 57
(n_eff ~ 10 nodi su 576 = 1.7% del reticolo). Al di fuori della finestra:
campo distribuito. La localizzazione e' un effetto di scala + finestra.

```bash
python experiments/exp3/test_quench_localizzazione.py --level 1 --seeds 8
python experiments/exp3/test_quench_localizzazione.py --level 2 --seeds 4 \
  --chi-means 55,65,72,78,85,92,100
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 1 | Livello gerarchico |
| `--seeds` | 6 | Seed per punto dello sweep |
| `--chi-means` | `35,42,48,55,62,70,78,88,98` | Valori di chi_mean da testare (CSV) |
| `--pre` | 40 | Step di pre-evoluzione |
| `--quench-steps` | 1500 | Step massimi del quench |

**Output**: tabella loc_pre/loc_post/M_tot/regime per chi_mean.
Figure: `figures/quench_localizzazione_L{n}.png`.

---

### 5.7 `experiments/exp3/test_riproducibilita_difetto.py`

**Cosa fa e perche'**: risponde alla domanda "il difetto e' una fase fisica
riproducibile o un evento raro?". Per ogni chi_mean, esegue N seed
INDIPENDENTI (no pooling) e misura: (a) frazione di nucleazione (quanti seed
producono un difetto reale con M_tot > 1), (b) distribuzione di loc_ratio
per seed, (c) dispersione di M_tot tra i seed con difetto.

**Risultato chiave**:
- peak ~ 1.72: nucleazione 75% (bordo d'entrata, bistabile)
- peak ~ 1.84: 100% ma M_tot su 5.4 decadi (bordo transizione)
- peak ~ 1.96: 100% e M_tot su 0.6 decadi = **FASE FISICA SOLIDA**

```bash
python experiments/exp3/test_riproducibilita_difetto.py --seeds 20 --chi-means 62,68,74
python experiments/exp3/test_riproducibilita_difetto.py --level 2 --seeds 20 \
  --quench-steps 500
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello gerarchico |
| `--seeds` | 20 | Seed per punto (minimo 10 per statistica affidabile) |
| `--chi-means` | `62,68,74` | Valori di chi_mean da testare (CSV) |
| `--pre` | 40 | Step di pre-evoluzione |
| `--quench-steps` | 500 | Step massimi del quench |

**Output**: frazione nucleazione, dispersione M_tot, verdetto fase/evento-raro.
Figure: `figures/riproducibilita_difetto_L{n}.png`.

---

### 5.8 `experiments/exp3/test_biopsia_difetto_v2.py`

**Cosa fa e perche'**: biopsia geometrica del kink al punto di massima
localizzazione (chi_mean=68). Tre test corretti:
- **Test 1**: concentrazione a blocco (n_eff_block: il kink e' in 1 o molti
  blocchi L1?)
- **Test 2**: pattern angolare dei nodi caldi (intra-blocco: casuale o strutturato?)
- **Test 3**: chi_hot_mean vs chi_cold_mean — se chi_hot ~ 0 e chi_cold ~ ±50:
  PARETE DI DOMINIO confermata (kink phi^4 che attraversa la barriera del
  potenziale).

**Risultato chiave**: n_eff_block = 1.4 (difetto in 1 blocco L1 su 24).
chi_hot ~ 33-46 (depleto, con core a chi ~ -42÷-49 = attraversamento barriera).
Kink phi^4 Kibble-Zurek confermato.

> **USARE SEMPRE `--chi-mean 68`** (massima localizzazione, non 74).
> `test_biopsia_difetto.py` (v1) e' deprecato: aveva cm=74 e test topologico
> invalido via tau_locale.

```bash
python experiments/exp3/test_biopsia_difetto_v2.py --seeds 15 --chi-mean 68
python experiments/exp3/test_biopsia_difetto_v2.py --seeds 15 --chi-mean 68 \
  --quench-steps 500
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello gerarchico |
| `--seeds` | 15 | Seed |
| `--chi-mean` | 68.0 | **Non cambiare: 68 = max localizzazione** |
| `--hot-pct` | 99.0 | Percentile per nodi "caldi" (top 1%) |
| `--quench-steps` | 500 | Step quench |

**Output**: n_eff_block, uniformity angolare, chi_hot_mean, chi_cold_mean,
verdetto parete-di-dominio. Figure: `figures/biopsia_difetto_v2_L{n}.png`.

---

### 5.9 `experiments/exp3/test_soc_distribuzione.py`

**Cosa fa e perche'**: testa se la distribuzione P(rho_tors) nella finestra
di localizzazione segue una legge di potenza (criticalita' auto-organizzata,
SOC) o una legge esponenziale (campo termico). Usa la CCDF (piu' robusta del
binning) e confronta R^2 dei due fit. Include un controllo: stesso test nel
regime sovra-saturo.

> **ATTENZIONE — VERDETTO AUTOMATICO NON AFFIDABILE**: a 2 seed sembrava
> potenza (R2=0.95, alpha=1.73). A 6 seed R2 crolla a 0.79, alpha salta a 1.16.
> La "retta" e' un artefatto di pooling di seed eterogenei (il plot connette
> due cluster separati, non una vera power-law). SOC FALSIFICATA.
> Lo script e' utile come infrastruttura per la CCDF ma il suo verdetto
> automatico va verificato manualmente. Usare almeno 10 seed.

```bash
python experiments/exp3/test_soc_distribuzione.py --level 2 --seeds 10
python experiments/exp3/test_soc_distribuzione.py --level 2 --seeds 10 \
  --chi-window 68 --chi-plasma 95
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello |
| `--seeds` | 6 | Seed per caso (**usare >= 10**) |
| `--chi-window` | 68.0 | chi_mean nella finestra di localizzazione |
| `--chi-plasma` | 95.0 | chi_mean controllo (sovra-saturo, fuori finestra) |
| `--xmin-pct` | 60.0 | Percentile minimo per il fit sulla coda |

**Output**: R2 potenza vs esponenziale per i due regimi, verdetto comparativo.
Figure: `figures/soc_distribuzione_L{n}.png`.

---

### 5.10 `experiments/exp3/test_quantizzazione_gerarchica.py`

**Cosa fa e perche'**: verifica l'ipotesi di quantizzazione gerarchica Z_24
(Peano-VQT, 2026-06-03). Ipotesi: a ogni livello L, il numero di sotto-blocchi
che il kink occupa appartiene all'insieme dei divisori di 24 < L.
L=2: solo {1}; L=3: {1,2}; L=4: {1,2,3}; etc. Misura n_eff_block a ogni
profondita' gerarchica e confronta con la predizione.

**Risultato al 2026-06-04**:
- L2, cm=68: n_eff_block = 1.0 per i seed con difetto reale → predizione {1} CONFERMATA
- L3, cm=68: run in corso (predizione {1,2})

**Supporta resume da interruzione**: se il run viene interrotto, rilanciare
lo stesso comando — i seed gia' completati vengono saltati. File di ripresa
in `experiments/exp3/resume/`. 3 copie ruotanti per recovery da crash.

Con `--save-chi`: salva anche il profilo chi per foglia come file `.npy float32`
(~54 KB per L3) per permettere la ricostruzione incrementale del livello L+1
senza rieseguire L.

```bash
# Verifica L2 (veloce, ~5 min, usa cm=68 per test quantizzazione)
python experiments/exp3/test_quantizzazione_gerarchica.py \
  --level 2 --seeds 10 --chi-mean 68

# Test L3 (lento, ~3-4 ore per 10 seed — lasciare girare in background)
python experiments/exp3/test_quantizzazione_gerarchica.py \
  --level 3 --seeds 10 --chi-mean 68

# Con profilo chi per costruire L4 in futuro
python experiments/exp3/test_quantizzazione_gerarchica.py \
  --level 3 --seeds 10 --chi-mean 68 --save-chi

# Resume dopo interruzione: stessa riga — i seed gia' fatti vengono saltati
python experiments/exp3/test_quantizzazione_gerarchica.py \
  --level 3 --seeds 10 --chi-mean 68
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 3 | Livello gerarchico da testare |
| `--seeds` | 5 | Numero di seed indipendenti |
| `--chi-mean` | 74.0 | **Usare 68 per test quantizzazione** (max loc.) |
| `--pre` | 40 | Step di pre-evoluzione |
| `--quench-steps` | 500 | Step massimi del quench |
| `--hot-pct` | 99.0 | Percentile nodi "caldi" per il calcolo n_eff |
| `--save-chi` | False | Salva profilo chi (.npy float32) per riuso a livello L+1 |

**Output**: n_eff_block per ogni profondita' gerarchica, frazione seed nella
predizione, verdetto. Figure: `figures/quantizzazione_gerarchica_L{n}.png`.
Resume: `resume/quantizzazione_L{n}_cm{cm}.json` + `.bak` + `.tmp`.

---

### 5.11 `experiments/exp3/test_termodinamica_kink.py`

**Cosa fa e perche'** (Task A): mappa la curva di nucleazione n(chi_mean) e
stima l'esponente critico di Kibble-Zurek nu. Per ogni chi_mean dello sweep,
esegue N_seed quench indipendenti e conta la frazione che nuclea un kink
(M_tot > 1). La curva n(chi_mean) sale da 0 (sotto-critico) a 1 (saturo),
attraversando una transizione. Da questa:
- chi_c = chi_mean dove n = 0.5 (punto critico, interpolato)
- nu = pendenza di log(n) vs log(epsilon), con epsilon = (chi_mean - chi_c)/chi_stable
- cooperativity = varianza osservata / varianza binomiale indipendente
  (1 = nucleazione stocastica indipendente; > 1 = cooperativa/topologica)

**Perche' serve**: trasforma il modello da fenomenologico a PREDITTIVO. Se
nu ~ 1, il sistema e' nella classe di universalita' del phi^4 1D classico.
Inoltre, chi_c determina il "punto di rugiada" per testare la quantizzazione
gerarchica nel regime diluito (1 solo kink) anziche' denso.

> **NOTA sullo sweep**: i valori chi_mean 58-78 sono tutti nel regime SATURO
> (nucleazione 100%) a L2 — la transizione e' piu' in basso. Usare uno sweep
> che parte da ~46 per catturare la salita 0->100%.

**Supporta resume da interruzione** (ResumeManager): se il run si interrompe,
rilanciare lo stesso comando — i (chi_mean, seed) gia' completati vengono saltati.

```bash
# Sweep per catturare la transizione di nucleazione (L2, ~50 min)
python experiments/exp3/test_termodinamica_kink.py \
  --level 2 --seeds 20 --chi-means 46,48,50,52,54,56,58,60,62

# Resume dopo interruzione: stessa riga
python experiments/exp3/test_termodinamica_kink.py \
  --level 2 --seeds 20 --chi-means 46,48,50,52,54,56,58,60,62
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello gerarchico (L2 = N=576, ~50 min; L3 ~15-20 ore) |
| `--seeds` | 20 | Seed per punto dello sweep |
| `--chi-means` | `58,...,78` | Sweep di chi_mean (CSV). **Spostare in basso (~46-62) per la transizione** |
| `--pre` | 40 | Step di pre-evoluzione |
| `--quench-steps` | 500 | Step massimi del quench |

**Output**: per chi_mean → frazione nucleazione, cooperativity, M_tot medio.
Poi: chi_c stimato, esponente nu (fit KZ), R2.
Figure: `figures/termodinamica_kink_L{n}.png`.
Resume: `resume/termodinamica_L{n}_cm{cm}.json`.

> NOTA: il "fit KZ / esponente nu" e' stato poi RIMOSSO in favore del fit logistico
> (la curva e' una probabilita' di nucleazione, non una densita' di difetti vs
> velocita' di quench). Vedi analyze_termodinamica.py (6.4).

---

### 5.12 `experiments/exp3/test_termodinamica_kink_par.py` (PARALLELO)

**Cosa fa e perche'**: versione PARALLELA di 5.11 (multiprocessing sui seed).
I seed sono fisicamente indipendenti -> parallelo == seriale (verificato dal GATE
5.13). Riduce lo sweep L3 da ~8h a ~2h. Codice ADDITIVO (motore intatto).
Determinismo: seeda `np.random` per-task (il motore usa np.random globale nel
riscaldamento gerarchico -> senza seeding il sistema e' stocastico run-to-run).

```bash
python experiments/exp3/test_termodinamica_kink_par.py \
  --level 3 --seeds 5 --chi-means 60,66,72,78 --workers 6 --quench-steps 500
# Ripresa dopo interruzione: stesso comando (resume crash-safe)
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 3 | Livello gerarchico |
| `--seeds` | 5 | Seed per punto |
| `--chi-means` | `60,66,72,78` | Sweep chi_mean (CSV) |
| `--workers` | 0 (auto) | Processi paralleli (0 = core fisici - 1) |
| `--pre` | 40 | Step pre-evoluzione |
| `--quench-steps` | 500 | Step quench |

**Output**: ogni seed loggato appena pronto (ETA live), poi fit logistico + confronto
di scala chi_c L vs L2. Figure: `figures/termodinamica_par_L{n}.png`.

---

### 5.13 `experiments/exp3/test_equivalenza_parallelo.py` (GATE)

**Cosa fa e perche'**: GATE di equivalenza seriale-vs-parallelo. Calcola gli stessi
seed in seriale e via pool, confronta M_tot bit-per-bit. Con il seeding
deterministico DEVE dare errore 0 (i seed sono deterministici). Se PASS, il
parallelo e' fisicamente equivalente e usabile su L3/L4.

```bash
python experiments/exp3/test_equivalenza_parallelo.py --level 2 --seeds 4 --chi-mean 68
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello |
| `--seeds` | 4 | Seed da confrontare |
| `--chi-mean` | 68.0 | chi_mean del test |
| `--workers` | 4 | Worker paralleli |
| `--tol` | 1e-9 | Tolleranza relativa max |

**Output**: tabella seriale vs parallelo per seed, errore max, GATE PASS/FAIL.

---

### 5.14 `experiments/exp3/test_soglia_geometrica.py`

**Cosa fa e perche'**: mappa la soglia GEOMETRICA (difetto localizzato se
loc_ratio>5) per confrontarla con quella energetica (M_tot>1). ESITO: la soglia
geometrica e' un artefatto (fondo di fluttuazioni fredde ~30%); NON esiste una
"doppia transizione" (V5 falsificato). Lo script resta come record/infrastruttura.

```bash
python experiments/exp3/test_soglia_geometrica.py --seeds 15 --chi-means 42,46,50,54,58,62
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello |
| `--seeds` | 15 | Seed per punto |
| `--chi-means` | `50,54,58,62,66` | Sweep chi_mean |
| `--quench-steps` | 500 | Step quench |

**Output**: curva n_loc(chi_mean), fit, rapporto di gap (falsificato). ResumeManager.

---

### 5.15 `experiments/exp3/test_densita_difetti.py` (PARALLELO)

**Cosa fa e perche'**: dopo aver scoperto che il difetto e' PUNTUALE, conta
n_def = numero di nodi deviati dal pozzo dominante (|chi-pozzo|>30) vs chi_mean.
Mappa la crescita da "1 difetto" (soglia) a "plasma" (sovra-saturazione).
Statistica termodinamica pura. Parallelo + seeding + resume.

```bash
python experiments/exp3/test_densita_difetti.py --level 2 --seeds 10 \
  --chi-means 60,64,68,72,76,80,85,90 --workers 6
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello |
| `--seeds` | 10 | Seed per punto |
| `--chi-means` | `60,...,90` | Sweep chi_mean |
| `--workers` | 0 (auto) | Worker paralleli |
| `--quench-steps` | 500 | Step quench |

**Output**: n_def medio +- std per chi_mean, fit crescita. Figure:
`figures/densita_difetti_L{n}.png`. Il worker calcola anche M_tot (nel resume),
quindi un run da' SIA densita' SIA frazione di nucleazione binaria.
> NOTA: l'esponente della crescita e' DEGENERE con chi_c (corr -0.94). Per misurarlo
> servono sweep fitto solo-critico (no plasma) + chi_c indipendente + ~30-50 seed.

---

### 5.16 `experiments/exp3/test_osservabili_rg.py` (PARALLELO) — P1 programma RG

**Cosa fa e perche'**: primo passo del programma RG (docs/peano/METODO_SCALING_RG.md).
Misura, sullo STESSO ensemble di quench, TUTTI gli osservabili che "fluiscono" con
la scala, cosi' da confrontarli tra L2, L3, L4 (i tre punti del flusso RG). Serve a
testare CNG A (invarianza di rho_M/Gamma = punto fisso RG) e CNG B (stabilita' della
chiusura Psi_L). Riusa freeze_and_measure_mass + compute_hierarchical_mass +
compute_geometric_E_psi (motore INTATTO, additivo). Parallelo + seeding
deterministico + persistenza JSON propria crash-safe (.tmp+os.replace, .bak).

Osservabili per quench (su stato congelato): M_tot, rho_M (=M_tot/n_foglie),
Psi_L (=M_tot/N_dof), localization_ratio, regime, E_RX, E_psi_anchored, frustration,
closure_err_norm, detorsion_quality, n_def, t_quench_s.

```bash
# smoke test L2 (veloce, ~1 min con 4 worker):
python experiments/exp3/test_osservabili_rg.py --level 2 --seeds 2 \
  --chi-means 64,68,72 --workers 4
# campagna L3:
python experiments/exp3/test_osservabili_rg.py --level 3 --seeds 10 \
  --chi-means 58,60,62,64,66,68 --workers 6
# singolo quench L4 per t_quench_s (decide vettorizzazione Strategia B):
python experiments/exp3/test_osservabili_rg.py --level 4 --seeds 1 \
  --chi-means 62 --workers 1
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello (24^L foglie) |
| `--seeds` | 5 | Seed per punto |
| `--chi-means` | `62,...,72` | Sweep chi_mean |
| `--pre` | 40 | Step di pre-evoluzione prima del quench |
| `--quench-steps` | 500 | Step quench |
| `--workers` | 0 (auto) | Worker paralleli |

**Output**: tabella osservabili per chi_mean (media +- sem), chi_c (fit logistico),
+ summary JSON in `experiments/exp3/rg_summary/osservabili_L{n}.json` (lo leggeranno
P2/P3 per il fit di flusso RG). Resume in `resume/osservabili_L{n}_cm{xx}.json`.

**[OSS] Smoke test L2 (2026-06-05, 2 seed, cm 64/68/72)**: strumento verificato
funzionante. M_tot bimodale (vuoto ~5e-4 vs kink ~10^2-10^3), n_def 0->1->4,
rho_M(cm72)=2.17, chi_c/stable=1.318 (vicino all'1.338 noto; barra infinita perche'
3 punti/2 seed danno uno scalino: serve sweep fitto + piu' seed). t_quench L2 ~30s.
> NOTA: per chi_c con barre vere serve sweep fitto attorno alla soglia + >=10 seed.
> Il summary JSON e' il ponte verso P2 (fit FSS) e P3 (mappa RG).

---

## Sezione 6 — Strumenti di analisi e generazione dati

### 6.1 `experiments/exp3/analyze_exp3.py`

**Cosa fa**: analisi aggregata dei dati in `experiments/exp3/` — legge i file
HDF5 generati dai run e produce grafici di sintesi (E_chi, E_RX, E_Psi,
chi_max nel tempo).

```bash
python experiments/exp3/analyze_exp3.py
```

---

### 6.1b `experiments/exp3/analyze_termodinamica.py`

**Cosa fa**: analisi IDEMPOTENTE separata dalla raccolta dati. Legge tutti gli
archivi resume `termodinamica_L{n}_cm*_done_*.json`, aggrega la curva di
nucleazione, fa il fit LOGISTICO (chi_c, larghezza w — il modello corretto per
una probabilita' di nucleazione, NON una power-law/KZ), calcola la cooperativity.
Rieseguibile in ~1s senza ricalcolare i quench. Pattern: separare raccolta
(costosa, test_termodinamica*) da analisi (veloce, idempotente).

```bash
python experiments/exp3/analyze_termodinamica.py --level 2
python experiments/exp3/analyze_termodinamica.py --level 3 --mtot-min 1.0
```

| Parametro | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello da analizzare |
| `--mtot-min` | 1.0 | Soglia M_tot per classificare un kink |
| `--exclude-before` | `20260604_1400` | Ignora archivi prima di questo timestamp (scarta smoke test) |

**Output**: tabella frazione/cooperativity per chi_mean, chi_c e w (fit logistico),
figura `figures/termodinamica_aggregata_L{n}.png`.

---

### 6.2 `tools/rendering/generate_topological_dataset.py`

**Cosa fa**: generatore CLI per creare dataset HDF5 di traiettorie VQT.
Supporta il percorso accelerato (`--fast-evolver`) e la modalita' di
ereditarieta' da run precedenti (`--inherit`). Produce file `cosmo_L*.h5`.

```bash
python tools/rendering/generate_topological_dataset.py \
  --level 3 --steps 600 --dt 0.02 \
  --fast-evolver \
  --inherit experiments/exp1/cosmo_L3_ext3.h5 --inherit-percentile 75 \
  --output experiments/exp3/cosmo_L3.h5 \
  --watchdog --watchdog-window 50
```

---

### 6.3 `wqt_oop/analyze_hotspots.py` / `analyze_rg_flow.py`

Strumenti di analisi post-hoc per i dati Ramo A (cosmologia/RG-flow).
Leggono file HDF5 e producono grafici di hotspot e flusso di rinormalizzazione.

```bash
python wqt_oop/analyze_hotspots.py
python wqt_oop/analyze_rg_flow.py
```

---

## Sezione 7 — Librerie di supporto (non eseguibili)

| File | Descrizione |
|---|---|
| `experiments/exp3/resume_manager.py` | Persistenza robusta per run lunghi. 3 file ruotanti, recovery da corruzione, salvataggio profilo chi in .npy float32. Importabile da qualsiasi script. |

---

## Appendice — Pattern per nuovi test

Ogni nuovo script di test deve seguire questo template:

```python
"""
================================================================================
NOME TEST — titolo descrittivo della domanda scientifica
================================================================================

Cosa fa e PERCHE': spiega la domanda fisica che risponde, non solo cosa calcola.
Contesto: quale risultato precedente motiva questo test?

Risultato atteso: cosa ci aspettiamo di vedere (falsificabile).

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_nome.py [opzioni]
  python experiments/exp3/test_nome.py --help
================================================================================
"""
import argparse
# ...

def main():
    ap = argparse.ArgumentParser(description="breve descrizione")
    ap.add_argument("--level", type=int, default=2, help="livello gerarchico")
    ap.add_argument("--seeds", type=int, default=10, help="seed indipendenti")
    # ... tutti i parametri con help esplicito ...

if __name__ == "__main__":
    main()
```

**Documentare subito in `docs/TESTS_E_STRUMENTI.md`** aggiungendo:
- Sezione con: cosa fa e perche', parametri (tabella), output, figura prodotta.
