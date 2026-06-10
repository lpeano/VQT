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

## Pezzo mancante (prossimo task concreto)

**Back-reaction metrica → campo**: l'espansione differenziale deve *retroagire* sul campo come
termine di trasporto/advezione (coordinate comoventi), così che la materia sia trascinata verso
le regioni dense / dal gradiente di tempo proprio. È esattamente il **trasporto di densità
chirale** già abbozzato in `wqt_oop/reference/` (chiralita_ec.py). Senza quel termine il motore
ha espansione ma non *aggregazione*.
