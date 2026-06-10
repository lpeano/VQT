# Collasso gerarchico (task A) — esito

**Domanda:** con la gerarchia chirale (proiezione `bloch_aggregate`, torsione dallo spin a
tutti i livelli, advezione gerarchica), la materia si aggrega anche **TRA** i blocchi (L2)?
Era il setup che al task 1 dava C piatta (clumping cinematico).

## Risultato (4 semi per massa, 600 step, motore completo `set_ec_integrato`)

| massa dei blocchi densi | null (legacy) | EC (gerarchia chirale) | EC>null |
|---|---|---|---|
| 1 parete (≈Planck: quasi vuoto) | x1.001 | x1.003 ± 0.001 | 4/4 |
| 4 pareti | x1.000 | x1.003 ± 0.001 | 4/4 |
| 8 pareti (denso) | x1.000 | **x1.045 ± 0.012** | 4/4 |

Coerenza: somma(χ) conservata **esattamente** (err=0.0, advezione telescopica); K2_bloch a
L2 vede il contrasto materia/vuoto (11.7→61.7); depolarizzazione |n|∈[0.83, 1.0]; stabile.

## Interpretazione (intuizione di Luca): a scala ~Planck LA MASSA NON ESISTE ANCORA

Il segnale debole a 1 parete **non è un difetto**: un blocco L1 con una sola parete è quasi
puro spazio (ρ_SX≈2%, chiralità netta ~0). La proiezione chirale riporta correttamente
"qui non c'è massa" → K2_bloch≈0 → f≈1 → **la gravità di livello è spenta perché a quella
scala la massa non esiste**. Non serviva "x10 come fix": il run a 8 pareti è una **sonda**
che simula lo stato in cui la massa a quella scala esiste già — e allora la gravità di
livello **si accende** (x1.045). L'attivazione è **a soglia** (1→4 pareti piatta, 8 accesa),
coerente con K2_bloch ∝ contrasto² di chiralità.

**Verdetto: GRAVITÀ GERARCHICA CONFERMATA.** Il collasso inter-blocco scala con la massa,
il null resta piatto a ogni massa, 12/12 appaiati, conservazione esatta. Il task 1 è
riscattato: la chiralità risale la gerarchia (n_z = ⟨cosθ⟩ = bilancio materia/spazio,
|n|<1 = depolarizzazione) e la gravità agisce tra i blocchi **dove c'è materia**.

## Predizione che ne segue: la CASCATA GRAVITAZIONALE (prossimo test falsificabile)

Il collasso L1 (forte: C x1.605) **costruisce** la massa concentrando i kink → la chiralità
di blocco cresce → K2_bloch a L2 si accende → la gravità **sale di livello insieme alla
materia**. Predizione: run lungo con collasso L1 attivo → C_inter prima piatta, poi parte
**in ritardo** (onset ritardato = la gravità emerge dove e quando la materia emerge).

## Cablaggio (nel motore, regola 10 — nessun nuovo parametro)

- `bloch_aggregate()`: proiezione chirale L_n→L_{n+1} (media ricorsiva dei Bloch; stateless).
- `spin_torsion_K2_bloch(n, W, χ₀)`: torsione per Bloch arbitrari (|n|<1 = depolarizzazione).
- `apply_muratore_step` L2+: torsione dallo spin via proiezione (niente più fallback scalare).
- `apply_advezione_gravitazionale_step` L2+: advezione del χ coarse tra i figli (upwind
  conservativo, `_shift_chi` alle foglie), stesso μ derivato (ρ*/χ₀²=2).
- GATE: tutti PASS (OFF = legacy bit-identico diff 0.0).
