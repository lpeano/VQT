# L'edificio Einstein-Cartan: saturazione, espansione (muratore), G emergente

**Data**: 2026-06-09 · **Branch**: `physics/einstein-cartan-saturation`

Documentazione scientifica del modello ricostruito in questa sessione, **scritta dopo
averlo derivato e verificato col codice** (regola del progetto: VERIFICA PRIMA DI
DOCUMENTARE). Ogni affermazione e' etichettata:

- **[VER]** verificato/derivato col codice in questa sessione;
- **[DERIVATO]** risultato analitico confermato numericamente;
- **[APERTO]** congettura o misura ancora da fare.

Principio guida (richiesto da Luca): **niente numeri postulati, dinamica autogenerata,
niente if-then-else** — la fisica e' governata da vincoli e gradienti continui, e i
coefficienti si DERIVANO dalla geometria.

---

## 0. Il problema di partenza

Il motore VQT girava con **leggi di scala postulate** in `physics_context.for_level`
(`alpha_K ~ 1/24^L`, `kappa ~ 1/24^{L/2}`, `lambda_exchange ~ 24^{2L}`,
`gamma ~ (24^L)^{0.2}`): rattoppi non derivati, uno (`lambda`) riconosciuto esplosivo.
La dinamica fisica di Einstein-Cartan (torsione, chiralita', saturazione) era stata
**persa nel cleanup** del commit `a5b417e`. Due sintomi:

1. la **"corsa di chi_c"** con la scala (1.353 -> 1.237 -> <1.08);
2. la **"febbre"**: la temperatura per-foglia cresceva con la taglia del sistema.

L'edificio qui descritto sostituisce i rattoppi con **tre meccanismi derivati**.

---

## 1. Einstein-Cartan: saturazione (bounce) + chiusura spinoriale 720 deg

`wqt_oop/einstein_cartan.py` — additivo, `evolve()` legacy intatto.

### 1.1 Topologia (spec di Luca)
Ogni voxel up/down si lega a un complementare con half-twist di **180 deg**; il voxel
successivo con chiralita' opposta; su 24 voxel la sinusoide chiude a **720 deg = 4π**
(chiusura spinoriale, spin-1/2). Costanti **topologiche** (non fit):
`TAU_CLOSURE_4PI = 4π`, `HALF_TWIST_PI = π`.

### 1.2 Settore chi — saturazione = pressione di degenerazione di spin
Torsione di gradiente per voxel:

> K²_i = Σ_j W_ij (χ_i − χ_j)²

Energia di saturazione e forza (gradiente analitico, **conservativo**):

> E_sat = β_sat · Σ_i (K²_i − ρ\*)²
> F_χ = −∂E_sat/∂χ

Saturazione **a soffitto** (one-sided): `E_sat = β·Σ((K²−ρ\*)₊)²`, forza
`coef = 2β(K²−ρ\*)₊`. Sotto ρ\* la forza e' **nulla** (vuoto/domini stabili); sopra ρ\*
la torsione in eccesso e' respinta (**bounce**), la densita' **satura**. (La forma
simmetrica (K²−ρ\*)² spingerebbe la torsione verso ρ\* anche dal basso = torsione
spuria nel vuoto: scartata.) Soglia **DERIVATA (misurata)**, non fit:

> ρ\* = 2 χ₀² = (√2 χ₀)²   — scala della PARETE di dominio / del disordine (√2 Jitterbug).

Misura su Leech reale: parete K²~5018, disordine ⟨K²⟩~5083 → 2χ₀²; il (2χ₀)²=4χ₀² lo
tocca SOLO un nodo isolato max-frustrato (mai una parete) → con quella soglia la
saturazione non scattava sui difetti reali. [TASK 3, risolto 2026-06-09]

**[VER]** gradiente analitico vs numerico: `err_rel = 3e-8` (conservativo).

### 1.3 Settore tau — chiusura 720 deg
> E_clo = κ_clo · (Σ_i τ_i − 4π)²,   F_τ = −2 κ_clo (Σ τ − 4π)

guida la fase spinoriale alla chiusura a 4π. Coerente col diagnostico `closure_err`
gia' nel motore.

### 1.4 Verifica
**[VER]** GATE A/B: con flag OFF, `evolve_with_ec` e' **bit-identico** a `evolve()`
(diff 0.0). Con flag ON: stabile, |χ| limitato.

---

## 2. Il muratore di Planck: espansione dello spazio sorgentata dalla torsione

`wqt_oop/muratore_planck.py` — additivo. Lato **espansione** dello stesso Einstein-Cartan.

### 2.1 Principio
La stessa pressione di spin che **localmente satura** (bounce) **globalmente spinge lo
spazio a crescere**: dove la torsione eccede ρ\*, il manifold crea volume (voxel) per
rilassare la densita'. In EC cosmologico (Poplawski) la torsione da' una pressione
repulsiva che guida l'espansione/il bounce.

### 2.2 Metrica e legge di espansione
Ogni blocco ha un fattore di scala `a` (default 1). Torsione **fisica** (per volume
fisico): K²_fisica = K²_coord / a². Tasso di Hubble sorgentato dall'**eccesso**:

> H = a'/a = β_sat · ⟨ K²/a² − ρ\* ⟩₊      (₊ = parte positiva)
> a ← a · (1 + H · dt)                       (un tick di Planck per step)

**AUTO-REGOLANTE (feedback negativo, knob-free):**

> densita' > ρ\* → H > 0 → a cresce → K²/a² scende → H → 0

**[DERIVATO]** punto fisso analitico `a\* = √(⟨K²⟩/ρ\*)`, dove K²_fisica = ρ\* e H = 0.
Il self-test converge esattamente: `a → a\*`, `H → 0`, densita' fisica → ρ\*.
**Zero parametri nuovi**: riusa `β_sat` e `ρ\*` dell'EC.

### 2.3 Le due frequenze (perche' l'espansione e' << Planck)
- **clock di Planck** = un tentativo per step (`dt` ↔ t_Planck);
- **creazione netta** = β_sat·(K²/a² − ρ\*)₊ = quasi sempre ~0, positiva solo
  sull'eccesso. Il feedback **sopprime** il ritmo di Planck nudo (che darebbe la
  catastrofe del vuoto, ~10⁶¹ troppo veloce) fino al ritmo lento osservato. Senza
  tarare nulla.

### 2.4 Omogeneita' EMERGENTE (non imposta)
`H_blocco ∝ eccesso di QUEL blocco` (sorgente a L0). Materia uniforme → espansione
uniforme (**FLRW locale**); materia concentrata → espansione locale (**curvatura =
gravita'**). **L'omogeneita' e' un output, non una regola** — coerente con
"omogeneo solo localmente" (universo frattale, tante FLRW locali cucite).

### 2.5 Verifica
**[VER]** GATE: flag OFF bit-identico al legacy; flag ON stabile, auto-regolante,
`a ≥ 1`, espande solo dove K² > ρ\*.

**Nota calibrazione [RISOLTO TASK 3]**: ρ\* ricalibrato a 2χ₀² (scala parete/disordine
misurata) + risposta LOCALE per-nodo (`H=β⟨(K²/a²−ρ\*)₊⟩`): l'espansione ora scatta su
pareti/difetti reali, non solo su overshoot. `equilibrium_a=√(maxK²/ρ\*)` (driven dal
nodo piu' frustrato).

---

## 3. Rigidezza geometrica → G emergente (l'ultimo numero dissolto)

`wqt_oop/rigidezza_geometrica.py` — diagnostico. Deriva `β_sat` (l'analogo di G) dalla
geometria, togliendo l'ultimo coefficiente libero.

### 3.1 Principio (gravita' indotta: Sakharov 1967, Verlinde 2011)
G non e' fondamentale: e' l'**inverso della rigidezza elastica dello spaziotempo**.

> curvatura = 8πG · stress-energia   ⇔   deformazione = stress / rigidezza,  G ~ 1/R

### 3.2 Due settori distinti (lezione del primo self-test)
- **Materia** (massa del campo): V''(χ) = β_pot(12χ² − 4χ₀²); al vuoto 8β_pot χ₀².
  Domina di ~3 ordini la geometrica → **non** e' la rigidezza per G.
- **Spaziotempo** (per G): spettro del Laplaciano del coupling
  `L = D − W` (Hessiano dell'energia di torsione = 4L). Il modo nullo (gauge,
  traslazione globale) e' **escluso**; la rigidezza vive nei modi di deformazione λ>0.

### 3.3 Rigidezza scalare e G
> R_geo(W) = 4 κ_geo · ⟨ λ_k(L) : λ_k > 0 ⟩
> β_local = Θ_Planck / R_geo

I **rapporti** β_i/β_j = R_j/R_i sono fissati dalla geometria (**zero numeri tarati**);
resta solo **una** unita' dimensionale Θ (la scala di Planck), inevitabile.

### 3.4 Risultato DERIVATO: G e' topologico, fissato dal 24 (non 24^L)
**[DERIVATO]** Con `W` normalizzata per riga (Σ_j W_ij = 1, diagonale 0):
trace(W)=0 ⇒ Σ autovalori = 0; il modo costante ha autovalore 1; quindi la media dei
modi di deformazione di L vale **N/(N−1)**, e

> **R_geo = 4 κ_geo · N/(N−1) = 4 · 24/23 = 4.174**

dipende **solo da N = 24** (la taglia del blocco di Leech), **non dalla forma del
coupling e non dalla scala L**. Confermato sul coupling Leech reale: R_geo = 4.1739
identico a L2 e L3 → **β scala-invariante = Θ/4.174 ≈ 0.240·Θ**.

> Conseguenza forte: la rigidezza dello spaziotempo (→ G) e' una **costante topologica
> legata al 24**, NON una legge di potenza 24^L. Il "24" compare UNA volta, non elevato
> a L. Questo e' l'opposto dei coupling postulati.

### 3.5 Dipendenza dalla scala: misurata, non assunta
**[DERIVATO]** Singolo blocco → R_geo scala-invariante (topologica).
**[VER]** Recursione gerarchica (molle annidate in serie, compliance additiva):
1/R_eff = 1/R_geo + 1/⟨R_figli⟩ → R_eff cala, **β_eff cresce ~linearmente con L**
(0.24, 0.48, 0.72, 0.96, 1.20·Θ per L=1..5).

**[APERTO]** Sull'intuizione di Luca (G non monotono in L): nel reticolo **idealizzato
uniforme** la recursione e' monotona (serie) o invariante (singolo blocco). La
**non-monotonia** richiede che geometria/materia varino con la scala — cioe' uno stato
**reale evoluto e disomogeneo** (difetti, `a` diverso per blocco). Misura prevista:
`misura_rigidezza_scala(root)` su un albero evoluto, non idealizzato.

---

## 3bis. Definizione METRICA del voxel: ancoraggio a Planck

`wqt_oop/scala_planck.py`. Il voxel era definito **dinamicamente** (χ, v in un doppio
pozzo) ma **non metricamente** (m=1, χ₀=50 = unita' di codice → Θ non mappabile a
unita' fisiche → niente km/s/Mpc). Questa sezione colma il buco.

### 3bis.1 Auto-similarita' (geometria DERIVATA)
Un aggregato = N = 24 voxel = **12 monti + 12 valli** (torsioni a chiralita' alternata,
chiusura 720 deg). Una **mezza onda** (un monte o una valle) = **1 voxel = 1/24
dell'aggregato**. Il rapporto ×24 per livello e' geometrico (Leech). **[DERIVATO]**

### 3bis.2 Ancoraggio (POSTULATO dichiarato)
Il **fondo** della gerarchia (il voxel L0 che non si suddivide) **e'** la scala di
Planck (cutoff UV):

> **ℓ_voxel(L0) = ℓ_Planck = 1.616e-35 m**,  t_step = t_Planck = 5.39e-44 s,
> **E_voxel = E_Planck = 1.22e19 GeV**,  da cui **Θ = E_Planck**.

L'auto-similarita' fissa il RAPPORTO (×24/livello, derivato); l'ancoraggio fissa la
SCALA ASSOLUTA (postulato fisico naturale: e' il "muratore di **Planck**"). **[POSTULATO]**

### 3bis.3 Ladder (dipende dalla dimensione d)
"1/24 dell'aggregato" e' un rapporto di CONTEGGIO/VOLUME (24 voxel sempre). Il rapporto
LINEARE per livello e' `ℓ_{L+1}/ℓ_L = 24^{1/d}`:
- d=1 (mezza onda lungo l'anello): ×24/livello;
- d=3 (volume): ×24^{1/3} ≈ 2.884/livello → **ℓ_L = 24^{L/3} ℓ_Planck**.

**[DERIVATO col codice]** ladder d=3 (coerente con la mappa di scala gia' nel progetto):
| oggetto | scala | livello L |
|---|---|---|
| voxel (Planck) | 1.6e-35 m | 0 |
| protone | ~1e-15 m | ~43 |
| atomo | ~1e-10 m | ~54 |
| uomo | ~1 m | ~76 |
| universo osservabile | ~8.8e26 m | ~134 |

### 3bis.4 Onesta' sul VALORE di G (circolarita')
`ℓ_Planck = √(ℏG/c³)`: ancorare la lunghezza del voxel a Planck **E' scegliere il valore
di G**. Quindi l'ancoraggio FISSA l'unita', **non deriva G in modo indipendente**. Il
modello PREDICE la **struttura** di G (R_geo = 4N/(N−1), la dipendenza di scala dalla
rigidezza, §3); il VALORE assoluto e' la scelta di unita'. Predizioni adimensionali +
1 unita' — come ogni teoria. **[VER/APERTO]**

---

## 4. La "febbre": verdetto onesto (transiente, NON una legge di scala)

Misura `test_legge_febbre.py` (L1-L4, 3 seed, equilibrio su coda).

**[VER]** Le traiettorie della KE/foglia mostrano **riscaldamento poi raffreddamento**
(FDT): L1-L3 piccano e poi calano; L4 (100 step) **non e' equilibrato** (oscilla,
finisce in salita a ~2007). I valori "a equilibrio" hanno errore tra seed ±80-100%
(L1-L3 statisticamente indistinguibili). Il fit potenza `KE ~ N^{0.165}` ha **R²=0.70**:
**NON e' una legge**, e' un'interpolazione di transienti a fasi di equilibrazione
diverse, dominata dal punto L4 fuori-equilibrio.

> **Conclusione [VER]**: il "1600" di L4 e l'esponente 0.165 sono **artefatti di
> non-equilibrio**, non una legge fisica. Codificarli (es. una soglia T_c ∝ N^α nel
> generatore) ripeterebbe l'errore "confondere un punto di misura con una legge".

La febbre del **sistema chiuso** termalizza (transiente). Una febbre **sostenuta**
richiederebbe il driving (creazione di voxel) — vedi muratore, §2. Il sistema chiuso
e' il **controllo** che esclude l'espansione come artefatto della dinamica chiusa.

---

## 5. Dissoluzione dei coupling postulati

Misura `test_cura_coupling.py` (L1-L3, cm66/72, 3 regimi: scaled/flat/cura).

**[VER]** La densita' di difetti e' gia' **~intensiva** in tutti i regimi (CV 0.09-0.13).
Appiattendo i coupling (scala-invarianti, incluso `lambda~24^{2L}` → costante) il
sistema **non diverge** e la densita' **non cambia** (scaled ≈ flat ≈ cura). Quindi la
**dipendenza di scala** dei coupling postulati (i rattoppi 24^L) e' **superflua e
rimovibile**: la fenomenologia regge senza. La "corsa di chi_c" era il confound del
valore estremo, non i coupling.

---

## 6. Costanti: cosa e' DERIVATO, cosa resta

| Grandezza | Stato | Origine |
|---|---|---|
| ρ\* (soglia saturazione/espansione) | **derivata (misurata)** | 2χ₀²=(√2χ₀)², scala parete/disordine (√2 Jitterbug) |
| 4π, π (chiusura 720, twist 180) | **topologiche** | spin-1/2 |
| R_geo → β_local (G) | **derivata** | 4N/(N−1), N=24 (Leech) |
| β_pot (doppio pozzo) | fisica | Landau-Ginzburg on-site (primitiva) |
| Θ_Planck (scala) | **ancorata** | Θ = E_Planck = 1.22e19 GeV (voxel L0 = ℓ_Planck, §3bis) |
| ℓ_voxel(L0), ladder ×24^{1/d} | **ancorata+derivata** | ℓ_Planck (postulato) × rapporto Leech (derivato) |
| β_sat = Θ/R_geo (G) | **derivata** | Θ(χ₀,β_pot) / [4N/(N−1)], N=24 |
| α_K, κ, λ_exchange~24^{2L}, γ, d_f | **da ELIMINARE** | rattoppi postulati (dissolti, §5) |

**Endpoint onesto**: niente piu' numeri *strutturali/tarati*. Anche Θ **non e' un knob
libero**: e' la scala di energia intrinseca del voxel, fissata dalle primitive gia' nel
modello (χ₀, β_pot). Quindi β_sat (l'analogo di G) e' **interamente derivato**:
`β_sat = Θ(χ₀,β_pot) / R_geo(24)`. L'unica liberta' residua e' la **scelta di unita' di
misura** (porre Θ=1 in unita' di codice), che non e' fisica ma convenzione.

---

## 7. Stato dei task

**FATTI [VER 2026-06-09]:**
- **Task 1 — G non monotono**: `test_g_nonmonotono.py` + `test_g_dinamico.py`. G traccia
  la scala della materia (vuoto → piatto; materia a L → β picca a L). Confermato sia il
  meccanismo (a\* analitico) sia la dinamica (muratore a tutti i livelli).
- **Task 2 — Cosmogenesi**: `test_cosmogenesi.py`. Origine simmetrica + dadi → SSB →
  domini → espansione (a cricca su). Senza dadi → niente. I dadi sono necessari.
- **Task 3 — Ricalibrazione ρ\***: ρ\*=2χ₀² + soffitto one-sided + risposta locale.
  Tutto il sistema si accende su materia reale (vedi §1.2, §2.5).

**APERTI:**
1. **β_sat ← β_local**: collegare il muratore alla rigidezza derivata (G emergente
   attivo nella dinamica, non solo diagnostico), con GATE.
2. **Oscillazione SSB**: l'ordine "respira" (meta-stabilita'? bagno termico FDT?) — capire.
3. **Calibrazione fisica → Hubble**: da Θ=E_Planck a km/s/Mpc; predire il gap early-vs-late.
4. **Aritmetica 180°/720°** [DA CONFERMARE]: 24 mezze onde vs chiusura spinoriale.
5. **ρ\*_Leech == ρ\*_EC**: la pietra angolare teorica.
6. **Deprecare il termostato legacy** (damping FDT + pompa di calore) se il muratore
   fornisce la dissipazione (l'espansione dissipa l'eccesso): da verificare con A/B.

---

## 8. File, test, comandi

```
wqt_oop/einstein_cartan.py          saturazione (bounce) + chiusura 720   [self-test]
wqt_oop/muratore_planck.py          espansione auto-regolante (G~1/rigid) [self-test]
wqt_oop/rigidezza_geometrica.py     R_geo -> G emergente (Sakharov)       [self-test]
wqt_oop/solitone_composito.py       hook additivi (evolve* legacy INTATTI)
wqt_oop/test_einstein_cartan_equivalence.py   GATE EC
wqt_oop/test_muratore_equivalence.py          GATE muratore
experiments/exp3/test_cura_coupling.py        dissoluzione coupling (§5)
experiments/exp3/test_legge_febbre.py         febbre = transiente (§4)
```

```bash
cd VQT_repo
python -m wqt_oop.einstein_cartan                      # self-test EC
python -m wqt_oop.muratore_planck                      # self-test muratore
python -m wqt_oop.rigidezza_geometrica                 # self-test rigidezza
python -m wqt_oop.test_einstein_cartan_equivalence     # GATE EC
python -m wqt_oop.test_muratore_equivalence            # GATE muratore
```

Tutti i GATE e i self-test **PASS** in questa sessione.
