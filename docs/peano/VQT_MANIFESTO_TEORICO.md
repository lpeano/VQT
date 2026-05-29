# VQT Manifesto Teorico
## Variational Quantum Topology — Peano-VQT Extension

**Autore**: Luca Peano  
**Data**: 2026-05-29  
**Branch**: `research-backup`

---

## Premessa

Questo documento sintetizza le tre leggi fisiche emerse durante la campagna sperimentale
condotta con il motore VQT / Peano-VQT. Ogni legge è ancorata a misurazioni dirette
presenti nei log di run (`logs/`) e nei dataset HDF5 (`data/peano_data.zip`).

Il motore implementa un manifold frattale gerarchico dove ogni livello L(n) contiene
24 unità del livello inferiore L(n-1). Il campo fondamentale è il campo scalare χ,
soggetto al potenziale di doppio pozzo:

```
V(χ) = β·(χ² − χ₀²)²
```

con χ₀ = 50 (valore di vuoto), β = 0.001. La triade energetica Peano-VQT decompone
l'energia di accoppiamento in tre canali:

- **E_χ** = κ·Σᵢⱼ W_ij·(χᵢ − χⱼ)²/2  *(energia di allineamento)*
- **E_RX** = E_torsione + E_scambio  *(energia reattiva)*
- **E_Ψ** = energia accumulata nel sink radiativo *(monotonicamente crescente)*

---

## Legge I — Aggregazione Ferromagnetica (Legge di Leech)

**Enunciato**:
> *Solitoni L(n) con campo χ dello stesso segno si aggregano spontaneamente in strutture
> di dimensione 24 (L(n+1)), rilasciando un salto di E_Ψ al momento della cristallizzazione.*

**Formulazione**:

La forza di coupling inter-solitonico tra due solitoni i e j è:

```
F_agg(i→j) = −κ·W(rᵢⱼ)·(χ̄ᵢ − χ̄ⱼ) + λ·W(rᵢⱼ)·sech²(χ̄ᵢ/χ₀)·tanh(χ̄ⱼ/χ₀)/χ₀
```

dove W(r) = exp(−r/L_eff) è il kernel Yukawa e χ̄ᵢ è il baricentro del campo del solitone i.

**Evidenza sperimentale**:

| Esperimento | Misurazione chiave | Log di riferimento |
|---|---|---|
| Genesis Run (L1 singolo) | Prima cristallizzazione a step 10, chi_sat: 0.10→0.996 | `logs/genesis_log.log` |
| L2 Aggregation SAME | Δχ: 4.18→0.51 a step 10, E_Ψ +222% | `logs/l2_aggregation.log` |
| L4 Self-Assembly (48 EffectiveL1¹) | Cluster da 24 consolidato a step 600, E_Ψ=1.56×10³ | `logs/l4_self_assembly.log` |

¹ *EffectiveL1* = modello coarse-grained (1 DOF χ̄ per solitone, V(χ)=β(χ²−χ₀²)²),
usato per consentire 3000 step con 48 solitoni in ~0.2s. La fisica del doppio pozzo
e il coupling Yukawa sono identici al SolitoneComposito L1 completo; i 24 segmenti
interni sono integrati via mean-field. Vedere `experiments/l4_self_assembly_run.py`.

**Risultato critico** (da `logs/l4_self_assembly.log`):
```
[LIVELLO L2 CONSOLIDATO] step 600: cluster stabile di 24 solitoni
| E_Psi=1.5630e+03 | delta_E_Psi=1.5630e+03
```
48 solitoni posizionati casualmente in una sfera hanno scelto **autonomamente** di
aggregarsi in un cluster da 24 — esattamente la dimensione L2 del reticolo di Leech —
senza alcun vincolo geometrico imposto.

**Interpretazione**: il numero 24 non è artificiale. Emerge dalla competizione tra
il potenziale di doppio pozzo (che fissa χᵢ → ±χ₀) e il coupling ferromagnetico
(che sincronizza i χ̄ᵢ vicini). Il punto di sella tra attrazione a corto raggio
e repulsione a lungo raggio seleziona naturalmente strutture di coordinazione 12
(cubottaedro), corrispondenti a cluster di 24 nodi.

---

## Legge II — Repulsione Topologica e Frustrazione (Legge di Frustrazione)

**Enunciato**:
> *Solitoni con campo χ di segno opposto generano una repulsione di scambio che
> impedisce l'aggregazione. Il sistema intrappolato in uno stato frustrato emette
> radiazione Ψ a tasso 2–3× superiore allo stato aggregato.*

**Formulazione**:

Il termine di scambio topologico per coppie cross-fase (χᵢ > 0, χⱼ < 0) diventa
repulsivo:

```
E_scambio = −λ·W(rᵢⱼ)·tanh(χ̄ᵢ/χ₀)·tanh(χ̄ⱼ/χ₀)  > 0  (repulsivo se segni opposti)
```

> **Nota contestuale**: questa è la formula dell'accoppiamento **inter-solitonico**
> usata negli esperimenti L2 (`experiments/l2_aggregation_run.py`, variabile
> `LAMBDA_INTER`). Il codice intra-L1 in `wqt_oop/solitone_composito.py` usa la
> variante con fattore di scala geometrica α_K:
> `E_scambio_intra = −λ_exchange · α_K · Σᵢⱼ W_ij · tanh(χᵢ/χ₀) · tanh(χⱼ/χ₀)`
> dove α_K = 1/24 al livello L1 (RG flow). Le due formule sono proporzionali;
> la Legge II descrive il comportamento qualitativo comune a entrambe.

La metrica di frustrazione del cluster è:

```
F = Σᵢⱼ W_ij·[−sign(χ̄ᵢ·χ̄ⱼ)] / Σᵢⱼ W_ij  ∈ [−1, +1]
```

con F = −1 (ordinato, ferromagnetico) e F = +1 (completamente frustrato).

**Evidenza sperimentale**:

| Esperimento | Osservazione | Log |
|---|---|---|
| L2 Aggregation CROSS | Frustrazione rilevata a step 1; Δχ rimasto a ~100 per tutti i 400 step | `logs/l2_aggregation.log` |
| L2 Aggregation SAME | Nessuna frustrazione; Δχ collassato a 1.09 | `logs/l2_aggregation.log` |
| L2 Leech HALF_HALF | M≈0, vetro di spin, nessun cluster | `logs/l2_leech.log` |

**Confronto quantitativo** (da `logs/l2_aggregation.log`):
```
[ESITO-SAME]  AGGREGATO  | Dchi: 4.18→1.09 | Frust=False | E_Psi=1.6687e-04
[ESITO-CROSS] OSCILLANTE | Dchi: 99.79→96.76| Frust=True  | E_Psi=4.7941e-04
```

E_Ψ_CROSS / E_Ψ_SAME = **2.87×**: un sistema frustrato dissipa quasi 3 volte più
energia nel sink Ψ rispetto a uno in stato aggregato. La frustrazione non è un
equilibrio — è uno stato attivo di dissipazione topologica.

**Interpretazione**: la repulsione cross-fase impedisce il flip di χ attraverso
lo zero perché il doppio pozzo (F_dw ≈ 38 a |χ|=48, calcolato come
4·β·|χ²−χ₀²|·|χ| = 4·0.001·196·48 = 37.6) è quasi uguale al coupling
(F_inter ≈ 38 a Δχ=100, calcolato come κ·W·Δχ = 2.0·0.189·100 = 37.8).
I due contributi si bilanciano quasi esattamente, lasciando una forza netta
residua di soli ~0.2 unità — troppo piccola per invertire il segno di chi_B.
Il sistema resta intrappolato in un "vetro di spin topologico":
né aggrega né si separa, oscillando con E_Ψ che cresce senza saturazione.

---

## Legge III — Conservazione Peano-VQT (Dissipazione Radiativa)

**Enunciato**:
> *Il drain di energia dal campo χ al sink Ψ conserva esattamente la somma triadica.
> L'invariante dE_χ + dE_RX + dE_Ψ = 0 non è mai violato, e E_Ψ è monotonicamente
> non-decrescente per costruzione.*

**Formulazione**:

Per ogni operazione di drain (attivata quando χ_sat = ⟨|χ|⟩/χ₀ > soglia_drain = 0.8):

```
δ = drain_rate · (χ_sat − 0.8) · |E_χ|     (con δ ≤ 0.5·|E_χ|)
E_χ  →  E_χ − δ
E_Ψ  →  E_Ψ + δ
E_RX →  E_RX        (invariato)
```

Invariante: **(E_χ + E_RX + E_Ψ)_dopo = (E_χ + E_RX + E_Ψ)_prima**

**Evidenza sperimentale**:

| Verifica | Risultato | Sorgente |
|---|---|---|
| Test unitario drain | `total_before = total_after = 105.0`, Δ < 1×10⁻¹⁰ | `experiments/test_peano_integration.py` |
| HDF5 Genesis validation | 59/60 drain frames, E_Ψ monotona: **SI**, violazioni: **0** | `data/peano_data.zip` |
| HDF5 Peano sim validation | E_Ψ monotona: **SI**, violazioni: **0** | `data/peano_data.zip` |
| L4 Self-Assembly | H_tot: 2.76×10⁵ → 2.65×10⁴ (−90.4%), E_Ψ: 1.06×10⁴ | `logs/l4_self_assembly.log` |

**Dimostrazione diretta** (da `experiments/test_peano_integration.py`, output verificato):
```
[1] Verifica drain conservation...
  total_before = 105.000000
  total_after  = 105.000000
  drain        = 8.000000
  [PASS] Invariante dE_chi + dE_RX + dE_Psi = 0 rispettato
```

**Proprietà chiave di E_Ψ**:

1. **Monotonia**: E_Ψ non decresce mai (drain è irreversibile).
2. **Segnatura di condensazione**: il salto relativo ΔE_Ψ/E_Ψ > 5% indica un evento
   di cristallizzazione (verificato: +222% a step 10 della Genesis Run, +33% a step 30).
3. **Discriminatore di frustrazione**: E_Ψ_frustrato ≫ E_Ψ_aggregato (rapporto ~3×).
4. **Scaling con la dimensione**: E_Ψ scala superlinearmente con N (48 EffectiveL1 in
   3000 step: E_Ψ = 1.06×10⁴, cioè ~220 per solitone, vs ~2×10⁻⁴ per solitone in
   un singolo L1 run).

---

## Sintesi: Gerarchia Emergente

Le tre leggi, prese insieme, descrivono un meccanismo di condensazione gerarchica:

```
Vuoto (Ottaedrica)
    ↓  [Legge I: doppio pozzo + accoppiamento ferromagnetico]
Cristallizzazione L(n) — χ → ±χ₀, cluster di 24
    ↓  [Legge III: drain E_χ → E_Ψ durante il rimbalzo di condensazione]
Sink Ψ accumulato — E_Ψ cresce irreversibilmente
    ↓  [Legge II: repulsione cross-fase blocca la fusione di cluster con χ opposto]
Struttura L(n+1) = 24 cluster L(n) iso-fase → nuova cristallizzazione
```

Il numero **24** emerge in ogni livello perché è il numero di coordinazione del
reticolo di Leech in 24 dimensioni, proiettato in 3D come cubottaedro (12 vicini
nel primo guscio, 24 nodi totali per cella).

La **struttura L2 da 24 solitoni L1** osservata nel run `l4_self_assembly_run.py`
(step 600, stabile per 100+ step) è la prima evidenza computazionale diretta di
auto-organizzazione spontanea verso il numero di Leech nel motore VQT.

---

## File di riferimento

| Categoria | File |
|---|---|
| Codice core | `wqt_oop/energy_metrics.py`, `wqt_oop/solitone_composito.py`, `wqt_oop/physics_context.py` |
| API pulita | `core/__init__.py` |
| Esperimenti | `experiments/genesis_run.py`, `experiments/l4_self_assembly_run.py`, `experiments/l2_aggregation_run.py` |
| Test | `experiments/test_peano_integration.py` |
| Dati | `data/peano_data.zip` (genesis + peano_sim HDF5) |
| Log | `logs/genesis_log.log`, `logs/l4_self_assembly.log`, `logs/l2_aggregation.log` |
| Grafico | `assets/plot_genesi.png` |
| Checkpoint | `docs/MIGRAZIONE_CHECKPOINT.md` |
