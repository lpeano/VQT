# Architettura della vettorizzazione del motore VQT

**Branch**: `perf/evolve-vectorized` · **Data**: 2026-06-04 · **Status**: ANALISI (nessun codice ancora)

> Documento di progettazione. Obiettivo: 20-50x sul tempo di quench eliminando il
> loop Python per-foglia, **senza cambiare la fisica** (le equazioni restano identiche;
> cambia solo l'organizzazione dei calcoli). Validazione via GATE statistico.

---

## 1. Motivazione e contesto

Il collo di bottiglia della ricerca e' il tempo di quench: L2 ~18s (dopo il quick
win), L3 ~25min, L4 ~8h (stima). Ogni sweep e' ore di attesa. Prima di accumulare
altri risultati lenti, conviene rendere veloce il motore.

**Quick win gia' fatto** (branch `perf/scalar-clip-fastmath`, commit 220b0ab):
sostituite le operazioni numpy su SCALARI (np.clip/exp/sqrt) con equivalenti
puri/math, bit-identici. Speedup 2.3x (43s -> 18.5s per quench L2). GATE err 2e-11.

Questo documento affronta la leva GRANDE: eliminare il **loop Python su N foglie**.

---

## 2. Profiling: dove va il tempo

Profiling di un quench L2 (576 foglie, 200 step), PRIMA del quick win:

| Funzione | chiamate | tempo cum. | nota |
|---|---|---|---|
| `SegmentoQuantistico.evolve` | 115.200 | 16.1s | loop per-foglia (576x200) |
| `np.clip` (scalare) | 1.910.084 | 8.8s | **rimosso dal quick win** |
| `_apply_damping_kick` | 775.882 | 6.7s | FDT + exp + clip per foglia |
| `_compute_conservative_force` | 775.882 | 5.0s | -dV/dchi + clip per foglia |
| `compute_hamiltonian` (ricorsivo) | 600.600 | 2.5s | chiamato 2x/step |
| `_transfer_heat_to_children` | 4.904 | 1.0s | riscaldamento (np.random) |

DOPO il quick win, sparisce ~10s di overhead numpy scalare. Il residuo dominante e'
il **loop Python**: 115k chiamate `evolve` + 775k `_apply_damping_kick` + 775k
`_compute_conservative_force`, tutte invocazioni Python per-oggetto. Questo overhead
e' incomprimibile finche' iteriamo oggetto-per-oggetto: e' il costo del dispatch
Python, non del calcolo. La vettorizzazione lo elimina alla radice.

---

## 3. Architettura attuale: Array of Structures (AoS)

```
SolitoneComposito (blocco L1)
  ├─ children: [SegmentoQuantistico x24]   # lista di OGGETTI
  │     ogni foglia: chi, vel, tau_locale, gamma_damping, _local_friction,
  │                  _H_eq, _T_eff, _gamma_effective, + params (beta, chi_0, ...)
  └─ coupling_matrix: ndarray[24,24]        # circolante, decadimento esponenziale
```

Flusso di `SolitoneComposito.evolve(dt)` (solitone_composito.py:687):
1. `_compute_damping_coefficient()` -> gamma da Var(tau)
2. `compute_hamiltonian()` -> H_before  [RICORSIVO, 1a volta]
3. set gamma in ogni figlio (loop)
4. `_compute_coupling_forces()` -> internal_forces[24]  [GIA' VETTORIZZATO: W @ chi]
5. **loop: per ogni figlio, `child.evolve(dt, force_i)`**  <- IL BOTTLENECK
6. fermi cooling (se screening)
7. `compute_hamiltonian()` -> H_after  [RICORSIVO, 2a volta]
8. E_rad = H_before - H_after; se >0: `_transfer_heat_to_children` (np.random)

`SegmentoQuantistico.evolve(dt, force)` per foglia, Strang splitting:
- `_apply_damping_kick(dt/2)`: FDT gamma = tanh(deltaH); vel *= exp(-gamma dt/2); clip
- Verlet conservativo: half-kick, drift chi, force update, half-kick
- `_apply_damping_kick(dt/2)` di nuovo
- adaptive sub-stepping (CFL) se |F - F_prev| > soglia

**Osservazione chiave**: il coupling (passo 4) e' GIA' un'operazione matrice-vettore
vettorizzata. Il problema NON e' il coupling: e' che ogni foglia viene evoluta da un
oggetto Python separato (passo 5), con tutte le sue operazioni scalari.

---

## 4. Il principio: da AoS a Structure of Arrays (SoA)

Invece di N oggetti, ciascuno con i suoi scalari (chi, vel, ...), tenere **array**
a livello di blocco: chi[N], vel[N], tau[N], H_eq[N], T_eff[N]. Tutte le operazioni
per-foglia diventano operazioni su array numpy in C — una chiamata invece di N.

Mappatura delle operazioni (tutte vettorizzabili senza un solo `if` per-foglia):

| Operazione scalare (per foglia) | Versione vettoriale (su array[N]) |
|---|---|
| `F = -4 beta chi (chi^2 - chi0^2) + ext` | stesso, su array (broadcast) |
| `dH = H - H_eq` | array - array |
| `gamma = g0 (1 + b tanh(dH/(a kB Teff)))` | `np.tanh` su array |
| `vel *= exp(-gamma dt/2)` | `np.exp` su array |
| `chi += vel dt` (drift Verlet) | array += array * dt |
| `vel += F/m dt/2` (kick) | array += array * dt/2 |
| `vel = clip(vel, -vmax, vmax)` | `np.clip` su array (VELOCE su array!) |
| `F = clip(F, -fmax, fmax)` | `np.clip` su array |

Nota: `np.clip` era lento SUI SCALARI (overhead dispatch per chiamata), ma e'
velocissimo SUGLI ARRAY (una chiamata C su N elementi). La vettorizzazione lo
re-include senza penalita' e senza alcun `if`.

---

## 5. Le sfide (e come affrontarle)

### 5.1 Adaptive sub-stepping (CFL) — RISOLTO (profiling 2026-06-04)
`SegmentoQuantistico.evolve` fa sub-stepping se `|F - F_prev| > threshold` (=100)
per una foglia: n_steps = 4 (o 8 se drift>10%), altrimenti 1.

**MISURA (quench L2 reale, conteggio diretto _apply_damping_kick / evolve):**
  n_steps medio = 3.37  ->  ~79% delle foglie-step attivano il sub-stepping.
Il sub-stepping e' QUASI SEMPRE attivo. Conseguenze:
  - DECISIONE: in vettoriale usare n_steps GLOBALE per blocco (la strategia
    conservativa 5.1a): n_steps = 4 se max(|dF|) del blocco supera la soglia.
    Dato che basta 1 foglia su 24 e il 79% gia' le supera, il blocco usera' 4
    quasi sempre. Costo extra ~nullo, ZERO if per-foglia. Niente maschere.
  - NOTA: il sub-stepping rende il quench 3.37x piu' costoso. Non si tocca
    (cambierebbe la precisione dell'integrazione = potenzialmente la fisica), ma
    spiega perche' i quench sono lenti. La vettorizzazione replica i 4 sub-step,
    molto piu' veloce del loop Python.

### 5.2 compute_hamiltonian chiamato 2x/step
Serve per E_rad (riscaldamento gerarchico). E' ricorsivo. Va vettorizzato anch'esso
(H = somma di KE + V + coupling, tutte calcolabili su array). Oppure: calcolare E_rad
in forma chiusa dalla variazione di stato senza due passate complete.

### 5.3 Gerarchia (L2, L3, L4)
Un blocco L1 = 24 foglie -> primo livello di vettorizzazione. A L2, 24 blocchi L1;
a L3, 576. Due approcci:
  - vettorizzare DENTRO il blocco L1 (24 foglie) e iterare sui blocchi: speedup ~24x
    sul costo-foglia, ma resta un loop sui blocchi.
  - vettorizzare TUTTE le foglie del sistema insieme (13824 a L3) in un unico array
    con coupling a blocchi (matrice sparse block-diagonale): speedup massimo.
  Il secondo e' piu' veloce ma richiede gestire il coupling block-diagonal. Il primo
  e' incrementale e piu' sicuro. **Iniziare dal primo (blocco L1), poi estendere.**

### 5.4 Riscaldamento gerarchico stocastico
`_transfer_heat_to_children` usa np.random (gia' fonte del non-determinismo noto).
Va replicato in vettoriale mantenendo il seeding deterministico. Attenzione:
l'ordine di consumo del RNG cambia -> traiettoria diversa (ma distribuzione uguale,
vedi GATE statistico).

---

## 6. Tre strategie implementative

### Strategia A — Refactoring SoA completo
Riscrivere SegmentoQuantistico/SolitoneComposito per usare array internamente.
- PRO: massimo speedup, architettura pulita.
- CONTRO: invasivo, rompe TUTTA la codebase (test, analisi, hdf5 logger). Viola
  "non toccare evolve() legacy". Mesi di lavoro + re-validazione totale. **SCARTATA.**

### Strategia B — "Vectorized leaf evolver" additivo [RACCOMANDATA per iniziare]
Una nuova classe/funzione `evolve_block_vectorized(block_L1, dt, ext_forces)` che:
  1. estrae gli array (chi, vel, ...) dai 24 oggetti foglia del blocco;
  2. esegue l'INTERA evoluzione del blocco in vettoriale (Verlet + FDT + clip + coupling);
  3. riscrive gli array negli oggetti foglia.
Attivabile con flag opt-in (`use_vectorized=True`); `evolve()` legacy resta default.
- PRO: additivo, legacy intatto, GATE-abile, incrementale.
- CONTRO: l'estrai/riscrivi ogni step ha un overhead (ma ammortizzato su 24 foglie).
  Speedup atteso: ~10-20x (non il massimo, per l'overhead estrai/riscrivi per-step).

### Strategia C — "Full-array quench" [il vero obiettivo, dopo B]
Estrarre gli array UNA VOLTA all'inizio del quench, evolvere su array per tutti i
500 step (replicando coupling + FDT + riscaldamento + sub-stepping in vettoriale),
riscrivere negli oggetti SOLO alla fine. Gli oggetti sono congelati durante il quench.
- PRO: speedup massimo (20-50x), nessun overhead estrai/riscrivi per-step.
- CONTRO: richiede replicare TUTTA la logica del motore in vettoriale (incluso il
  riscaldamento gerarchico e il sub-stepping). Piu' lavoro, piu' superficie di GATE.
  Specifico per il QUENCH (freeze_and_measure_mass), non per evolve() generale.

---

## 7. Roadmap incrementale raccomandata

1. **[FATTO 2026-06-04] Profilare il sub-stepping** (5.1): n_steps medio 3.37,
   ~79% attivo -> strategia conservativa (n_steps globale per blocco). DECISO.
2. **Strategia B** su un blocco L1 (24 foglie): `evolve_block_vectorized`. GATE
   statistico su L1. Se PASS, ho la base e un primo speedup (~10x sul costo-foglia).
3. **Strategia C** per il quench: full-array su tutto il sistema (L1/L2/L3), coupling
   block-diagonale sparse. GATE statistico su L2 (chi_c, p). Questo da' il 20-50x.
4. Integrare come percorso opt-in in `freeze_and_measure_mass(..., vectorized=True)`.

Ogni passo additivo, ogni passo con GATE prima di fidarsi.

---

## 8. Il GATE statistico (NON bit-per-bit)

La vettorizzazione cambia l'ORDINE delle somme float -> differenze ~1e-16 -> in un
sistema CAOTICO si amplificano -> traiettorie diverse. MA il sistema e' GIA' stocastico
(np.random nel riscaldamento) e tutte le conclusioni sono statistiche d'ensemble.
Quindi una traiettoria diversa = una realizzazione diversa della STESSA distribuzione.

**Protocollo GATE**: per N=30 seed, calcolare con loop-legacy E con vettoriale:
  - frazione di nucleazione (M_tot>1)
  - chi_c (fit logistico)
  - n_def medio per chi_mean
Confrontare le DISTRIBUZIONI (medie + barre), non i singoli valori. Se coincidono
entro le barre statistiche -> EQUIVALENZA FISICA garantita (stesso ensemble).

Criterio di PASS: |chi_c_loop - chi_c_vect| < barre combinate; le curve n_def(chi)
sovrapponibili entro sem. (vedi gotcha non-determinismo in CLAUDE.md per il razionale.)

---

## 9. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Vettorizzazione altera la fisica | GATE statistico obbligatorio; legacy resta default |
| Sub-stepping mal replicato | profilare prima; approccio conservativo se raro |
| Riscaldamento stocastico diverso | seeding deterministico; verificare distribuzione RNG |
| Bug silenziosi (NaN, broadcast) | test su L1 con stati noti prima di L2/L3 |
| Overhead estrai/riscrivi (strat. B) | ammortizzato su 24 foglie; strat. C lo elimina |
| Coupling block-diagonale complesso | scipy.sparse block_diag; gia' usato altrove nel repo |

---

## 10. Sintesi

- Il bottleneck residuo (dopo il quick win 2.3x) e' il **loop Python per-foglia**.
- La cura e' **AoS -> SoA**: array invece di oggetti, operazioni numpy invece di loop.
- Approccio **additivo e incrementale**: Strategia B (leaf evolver, ~10x) poi C
  (full-array quench, 20-50x), mai toccando evolve() legacy.
- Validazione **statistica** (distribuzione, non bit), perche' il sistema e' caotico
  e stocastico: la fisica e' la distribuzione, non la singola traiettoria.
- Primo passo concreto: **profilare il sub-stepping**, poi `evolve_block_vectorized`
  su un blocco L1 con GATE.
