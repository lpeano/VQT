# Collasso dinamico — esito

**Domanda (Luca):** sul motore Einstein-Cartan completo, la materia *migra e si aggrega*
(densità di difetti che cresce nei grumi), o vediamo *solo* espansione differenziale
(`a_vuoto > a_denso`) senza vera migrazione? È la prova forte che "guadagna la parola gravità".

**Metrica** (derivata SOLO dal campo χ, identica per motore EC e legacy → confronto onesto):
per ogni voxel `rho_SX = sin²(θ/2)`, `θ = 2·atan|pendenza_kink|`; per blocco L1
`D_b = media(rho_SX)`; concentrazione `C = Var_b(D_b)/media_b(D_b)²`.

## Risultato (run 2026-06-10, 600 step, level=2, 6 blocchi densi)

| | C(0) | C(fine) | crescita |
|---|---|---|---|
| **Motore EC completo** | 2.99 | 2.99 | **x1.001** |
| **Legacy (EC off, null)** | 2.99 | 2.99 | x1.001 |

- Espansione (EC): `a_vuoto/a_denso = 1.0028` → l'espansione differenziale **c'è**.
- Concentrazione: **PIATTA**, e **identica al null legacy**. Spinore sano (norma_err 2e-16, winding→4π).

## Verdetto: NEGATIVO (onesto) — il clumping è CINEMATICO

La materia **non migra**. Motivo **architetturale**: il fattore di scala `a` è per-blocco e
modula l'espansione (voxel_count, β), ma in `evolve_with_muratore` **non trasporta χ tra i
blocchi**. Non esiste un canale fisico per la migrazione: l'espansione è "dipinta sopra", non
muove la materia. Nessuna durata di run lo cambierà — manca il meccanismo.

## Pezzo mancante (poi risolto — vedi sotto)

**Back-reaction metrica → campo**: l'espansione differenziale deve *retroagire* sul campo come
termine di trasporto/advezione (coordinate comoventi), così che la materia sia trascinata verso
le regioni dense / dal gradiente di tempo proprio. È esattamente il **trasporto di densità
chirale** già abbozzato in `wqt_oop/reference/` (chiralita_ec.py). Senza quel termine il motore
ha espansione ma non *aggregazione*.

---

# Task 1b — Advezione gravitazionale M1: COLLASSO CONFERMATO

**Meccanismo (scelta di Luca):** la metrica retroagisce sul campo. χ è advettato da
`u = -μ·∇f`, con `f = 1 - K2_spin/ρ*` **per-voxel** = potenziale gravitazionale (lo *stesso* f
che dilata il tempo). Al kink K2 è alta → `f` ha un minimo (al cuore `f<0`: tempo invertito) →
`-∇f` punta verso il kink da entrambi i lati → χ confluisce → i difetti si **fondono** = collasso.
Forma conservativa upwind sull'anello → `Σχ` invariato (ridistribuzione, non creazione).
Implementato additivo dietro flag `advezione_enabled/advezione_mu` (`set_advezione(μ)`); OFF →
legacy bit-identico (GATE muratore [2] diff=0.0).

## Risultato (anello 24 voxel, 8 semi, 600 step, μ=2)

| | crescita C (media ± σ) | range | M1 > null |
|---|---|---|---|
| **LEGACY (null)** | **x1.000 ± 0.001** | [0.999, 1.000] | — |
| **EC + M1 (μ=2)** | **x1.605 ± 0.324** | [1.017, 1.987] | **8/8 semi** |

Finestra di mobilità (crescita C media su 8 semi): μ=1 → x1.02, **μ=2 → x1.60** (sweet spot,
|χ|max 59), μ=4 → x1.26, μ=8 → x1.34, μ=16 → x1.58 (|χ|max 68). Sotto μ~1 la diffusione
numerica dell'upwind vince; il collasso è **caotico** (sensibile alle IC → si misura l'ensemble).

## Verdetto: POSITIVO — la parola "gravità" è guadagnata

Il **null legacy non aggrega mai** (x1.000 su tutti i semi); l'advezione da `-∇f` **aggrega
sempre** (8/8), in modo stabile (`|χ|max` bounded). Lo stesso `f` che rallenta gli orologi
(dilatazione gravitazionale) **trascina la materia e fonde i difetti**: migrazione vera, non
solo espansione differenziale. È la chiusura del cerchio gravità ↔ tempo proprio.

**Aperto (per dopo):** μ è una mobilità di trasporto (1 coefficiente, non legge di scala) —
derivarla/ancorarla; advezione **gerarchica** (inter-blocco L2+) per l'aggregazione tra blocchi
(qui dimostrata intra-anello); collasso → bounce vero quando `f<0` al cuore (task 2).
