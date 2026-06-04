# experiments/exp3 — Suite di test Peano-VQT

Raccolta di script per la caratterizzazione del kink phi^4 Kibble-Zurek
nella gerarchia frattale VQT. Ogni script e' autonomo e documentato
internamente; questo README fornisce l'indice navigabile e le dipendenze.

**Branch**: `research-backup` · **Ultimo aggiornamento**: 2026-06-04

---

## Come eseguire (tutti gli script)

```bash
cd c:\Users\lpeano\plank\VQT_repo   # root del repo
python experiments/exp3/<nome_script>.py [opzioni]
python experiments/exp3/<nome_script>.py --help   # mostra tutte le opzioni
```

---

## Indice degli script

### Infrastruttura

| Script | Scopo |
|---|---|
| `resume_manager.py` | **Libreria** (non eseguibile). Persistenza robusta per run lunghi: 3 file ruotanti (main / .tmp / .bak), recovery da corruzione, salvataggio profilo chi in .npy float32. |
| `analyze_exp3.py` | Analisi e grafici aggregati dei dati in `experiments/exp3/`. |

---

### Fondamenta fisiche (eseguire in questo ordine per capire il sistema)

#### 1. `test_falsificabilita.py`
Test A/B/C/B2 per stabilire se il drain e la costante sqrt(2) sono fisica reale
o artefatti. **Punto di partenza storico** della linea di ricerca corrente.
```bash
python experiments/exp3/test_falsificabilita.py
```
**Output**: verdetti sui 4 test di falsificabilita'.

---

#### 2. `test_soglia_formazione.py`
Mappa la soglia di formazione del difetto vs attraversamento di sqrt(2).
Fornisce la funzione `make(seed, chi_mean, level)` usata da tutti gli altri script.

```bash
python experiments/exp3/test_soglia_formazione.py --level 1 --seeds 10
python experiments/exp3/test_soglia_formazione.py --level 2 --seeds 4
```

| Opzione | Default | Descrizione |
|---|---|---|
| `--level` | 1 | Livello gerarchico (1=L1, 2=L2, 3=L3) |
| `--seeds` | 10 | Numero di seed indipendenti |
| `--pre` | `40,50,...,100` | Punti di pre-evoluzione da testare |
| `--quench-steps` | 1500 | Step massimi del quench |

**Output**: cross_sqrt2, soglia_massa, ritardo per seed. Figure: `figures/soglia_formazione_L{n}.png`

---

#### 3. `test_quench_mass.py`
Test di bimodalita': la massa e' presente/assente (bimodale) o continua?
```bash
python experiments/exp3/test_quench_mass.py
```
**Output**: distribuzione di E_psi_residual su 36 stati. Conferma bimodalita'.

---

### Caratterizzazione della massa e del kink

#### 4. `test_massa_gerarchica.py`
Misura M_tot, rho_M (densita'), IPR sulle foglie — aggregatore corretto che
evita il bias del root (il root vede medie, non picchi).

```bash
python experiments/exp3/test_massa_gerarchica.py --levels 1,2,3
python experiments/exp3/test_massa_gerarchica.py --levels 1,2,3 --seed 5
```

| Opzione | Default | Descrizione |
|---|---|---|
| `--levels` | `1,2,3` | Livelli da misurare (separati da virgola) |
| `--pre` | 60 | Step di pre-evoluzione |
| `--seed` | 1 | Seed |

**Output**: tabella M_tot/N^a, rho_M/N^b, loc_ratio. Legge di scala.

---

#### 5. `test_quench_localizzazione.py`
Sweep di chi_mean: per ogni valore misura loc_ratio post-quench (foglie).
Identifica la **finestra di localizzazione** (peak ~1.8-1.95) dove il kink
e' massimamente concentrato.

```bash
python experiments/exp3/test_quench_localizzazione.py --level 1 --seeds 8
python experiments/exp3/test_quench_localizzazione.py --level 2 --seeds 4 --chi-means 55,65,72,78,85,92,100
```

| Opzione | Default | Descrizione |
|---|---|---|
| `--level` | 1 | Livello gerarchico |
| `--seeds` | 6 | Seed per punto |
| `--chi-means` | `35,42,...,98` | Sweep di chi_mean |
| `--pre` | 40 | Step pre-evoluzione |
| `--quench-steps` | 1500 | Step quench |

**Output**: tabella loc_pre/loc_post/M_tot/regime per chi_mean. Figure: `figures/quench_localizzazione_L{n}.png`

---

#### 6. `test_riproducibilita_difetto.py`
Per ogni chi_mean, misura la **frazione di nucleazione** su N seed (no pooling).
Risponde: il difetto e' una fase fisica (>80%) o un evento raro (<20%)?

```bash
python experiments/exp3/test_riproducibilita_difetto.py --seeds 20 --chi-means 62,68,74
python experiments/exp3/test_riproducibilita_difetto.py --level 2 --seeds 20
```

| Opzione | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello |
| `--seeds` | 20 | Seed per punto |
| `--chi-means` | `62,68,74` | Valori di chi_mean |
| `--quench-steps` | 500 | Step quench |

**Output**: frazione nucleazione, dispersione M_tot, verdetto fase/evento-raro.
Figure: `figures/riproducibilita_difetto_L{n}.png`

---

#### 7. `test_soc_distribuzione.py`
Test SOC: la distribuzione P(rho_tors) nella finestra e' legge di potenza
(criticalita' auto-organizzata) o esponenziale (campo termico)?

> **NOTA**: il verdetto automatico ("SOC CONFERMATO") e' stato falsificato —
> era un artefatto di pooling di seed eterogenei. Lo script e' utile come
> infrastruttura (CCDF, fit potenza vs esponenziale) ma il suo verdetto
> automatico NON e' affidabile. Usare sempre `--seeds >= 10` e verificare
> manualmente.

```bash
python experiments/exp3/test_soc_distribuzione.py --level 2 --seeds 6
```

| Opzione | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello |
| `--seeds` | 6 | Seed per caso |
| `--chi-window` | 68.0 | chi_mean nella finestra |
| `--chi-plasma` | 95.0 | chi_mean controllo (sovra-saturo) |

---

#### 8. `test_biopsia_difetto_v2.py`
**Biopsia geometrica del kink** al punto di massima localizzazione (cm=68).
Misura: concentrazione a blocco, pattern angolare, chi_hot vs chi_cold.
Confirma il kink phi^4 (chi_hot ~ 0 = barriera del potenziale).

> Usare `v2`, non `v1` (v1 aveva il punto di misura sbagliato cm=74 e
> il test topologico invalido via tau_locale).

```bash
python experiments/exp3/test_biopsia_difetto_v2.py --seeds 15 --chi-mean 68
python experiments/exp3/test_biopsia_difetto_v2.py --seeds 10 --chi-mean 68 --quench-steps 500
```

| Opzione | Default | Descrizione |
|---|---|---|
| `--level` | 2 | Livello |
| `--seeds` | 15 | Seed |
| `--chi-mean` | 68.0 | **Usare 68 per max localizzazione** |
| `--hot-pct` | 99.0 | Percentile per nodi "caldi" (top 1%) |
| `--quench-steps` | 500 | Step quench |

**Output**: n_eff_block, uniformity angolare, chi_hot_mean, chi_cold_mean,
verdetto parete-di-dominio. Figure: `figures/biopsia_difetto_v2_L{n}.png`

---

### Quantizzazione gerarchica (ipotesi Peano-VQT, 2026-06-03)

#### 9. `test_quantizzazione_kink.py`
Test preliminare: le larghezze del kink preferiscono i divisori di 24?
Misura M_tot su N seed e distribuzione delle larghezze.

> **Risultato**: test falsificato nella forma attuale (soglia errata a cm=74).
> Il test corretto e' `test_quantizzazione_gerarchica.py`.

```bash
python experiments/exp3/test_quantizzazione_kink.py --seeds 50 --chi-mean 68
```

---

#### 10. `test_quantizzazione_gerarchica.py`  ← **SCRIPT PRINCIPALE**
**Il test decisivo** dell'ipotesi di quantizzazione gerarchica:
a ogni livello L, n_eff_block in {divisori di 24 < L}?

Supporta **resume da interruzione**: se il run viene interrotto, al
riavvio salta i seed gia' completati. File di ripresa in `resume/`.

```bash
# Verifica L2 (veloce, ~5 min)
python experiments/exp3/test_quantizzazione_gerarchica.py --level 2 --seeds 10 --chi-mean 68

# Test L3 (lento, ~3-4 ore per 10 seed)
python experiments/exp3/test_quantizzazione_gerarchica.py --level 3 --seeds 10 --chi-mean 68

# Con profilo chi salvato per costruire L4 (aggiunge ~54 KB/seed su disco)
python experiments/exp3/test_quantizzazione_gerarchica.py --level 3 --seeds 10 --chi-mean 68 --save-chi
```

| Opzione | Default | Descrizione |
|---|---|---|
| `--level` | 3 | Livello gerarchico |
| `--seeds` | 5 | Seed |
| `--chi-mean` | 74.0 | **Usare 68 per test quantizzazione** (max loc.) |
| `--pre` | 40 | Step pre-evoluzione |
| `--quench-steps` | 500 | Step quench |
| `--hot-pct` | 99.0 | Percentile nodi caldi |
| `--save-chi` | False | Salva profilo chi (.npy float32) per riuso a L+1 |

**Output**: n_eff_block per ogni profondita' gerarchica, verdetto vs predizione.
Figure: `figures/quantizzazione_gerarchica_L{n}.png`
Resume: `resume/quantizzazione_L{n}_cm{cm}.json` + `.bak` + `.tmp`

---

## Dipendenze tra script

```
test_soglia_formazione.py   <-- funzione make() usata da TUTTI gli altri
       |
       +-- test_quench_localizzazione.py
       +-- test_riproducibilita_difetto.py
       +-- test_biopsia_difetto_v2.py
       +-- test_quantizzazione_gerarchica.py  <-- usa resume_manager.py
       +-- test_soc_distribuzione.py          <-- usa test_biopsia_difetto_v2._collect_rho
```

---

## Output su disco

Tutti i grafici vanno in `experiments/exp3/figures/`.
I file di resume vanno in `experiments/exp3/resume/` (creata automaticamente).

---

## Risultati consolidati (al 2026-06-04)

| Fatto | Script | Status |
|---|---|---|
| Massa estensiva M_tot~N^1.01, rho_M~2.9/nodo invariante | test_massa_gerarchica | **[OSS]** |
| Finestra localizzazione peak~1.8-1.95 | test_quench_localizzazione | **[OSS]** |
| Fase robusta 100% nucleazione a peak~1.96 | test_riproducibilita_difetto | **[OSS]** |
| Kink phi^4: chi_hot~0 (barriera), chi_cold~±50 | test_biopsia_difetto_v2 | **[OSS]** |
| SOC falsificata (artefatto pooling) | test_soc_distribuzione | **[OSS]** |
| Quantizzazione L2: n_eff=1.0 in {1} | test_quantizzazione_gerarchica | **[OSS]** |
| Quantizzazione L3: n_eff in {1,2}? | test_quantizzazione_gerarchica | **run in corso** |
