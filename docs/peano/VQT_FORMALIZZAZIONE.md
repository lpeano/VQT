# VQT — Formalizzazione: statica, dinamica, ipotesi aperte

**Versione**: 2026-06-09 · **Branch di riferimento**: `physics/einstein-cartan-saturation`

Documento di sintesi formale del modello VQT (Voxel Quantum Theory) come ricostruito
sul settore di Einstein-Cartan. Descrive la **statica** (struttura, costanti, scala),
la **dinamica** (equazioni e meccanismi), il **funzionamento** d'insieme, e le **ipotesi
ancora da verificare**. Distingue rigorosamente cio' che e' *derivato/misurato* da cio'
che e' *postulato* o *congetturato*.

Convenzione: i risultati sono etichettati **[D]** derivato/misurato col codice,
**[P]** postulato (scelta fisica dichiarata), **[H]** ipotesi da verificare.

> Nota terminologica. In discussioni informali il termine di creazione di volume alla
> scala fondamentale e' stato chiamato in modo allegorico "muratore di Planck". In questo
> documento si usa la denominazione scientifica **termine di emissione di volume alla scala
> di Planck** (o *espansione metrica di fondo*).

---

## 1. Oggetto e ontologia

VQT descrive lo spaziotempo come un **manifold frattale gerarchico**: ogni livello L(n)
e' composto da N = 24 unita' del livello inferiore (24 = numero di contatto del reticolo
di Leech / cubottaedro). L'unita' fondamentale e' il **voxel** (livello L0).

- **Voxel**: grado di liberta' di campo, stato (chi, v) — campo scalare chi e velocita'
  coniugata v = dchi/dt — con potenziale a doppio pozzo, piu' una fase spinoriale locale
  tau (chiusura geometrica). Un voxel isolato non possiede geometria: la **torsione e' una
  proprieta' relazionale**, emerge solo nell'interazione tra voxel.
- **Materia**: i difetti topologici del campo (kink, pareti di dominio) sono la materia.
  In VQT la materia e' la **complessita' topologica dello spaziotempo emergente**: nasce
  dalle torsioni del reticolo, non e' un'entita' separata.

---

## 2. Statica

### 2.1 Reticolo e geometria di accoppiamento
Ogni blocco e' un anello/cella di N = 24 nodi con matrice di accoppiamento `W` di
simmetria Leech (cubottaedro, 12 vicini), **normalizzata per riga** (somma di riga = 1,
diagonale nulla). Il Laplaciano del grafo

    L = D - W ,   D = diag(somme di riga di W)

ne codifica la rigidezza geometrica (e' l'Hessiano, a meno di un fattore, dell'energia
di torsione).

### 2.2 Scala metrica
Il voxel acquista scala fisica per **ancoraggio [P]**: il fondo della gerarchia (L0,
non ulteriormente suddivisibile) coincide con la scala di Planck:

    ell_voxel(L0) = ell_Planck ,   t_step = t_Planck ,   E_voxel = Theta = E_Planck .

L'auto-similarita' fissa il **rapporto** tra livelli [D]: un aggregato e' 24 voxel
(12 "monti" + 12 "valli"), una mezza onda = 1 voxel = 1/24 dell'aggregato. La lunghezza
per livello e' `ell_L = 24^(L/d) ell_Planck` (d = dimensione di disposizione; d=3 ->
fattore lineare 24^(1/3) ~ 2.884, protone ~ L43).

### 2.3 Rigidezza e costante gravitazionale emergente
G non e' fondamentale: e' l'**inverso della rigidezza elastica dello spaziotempo**
(gravita' indotta, Sakharov 1967; gravita' entropica, Verlinde 2011). La rigidezza
geometrica scalare di un blocco e'

    R_geo = 4 kappa_geo <lambda_k(L) : lambda_k > 0>    (modi di deformazione, esclude il modo nullo gauge).

**[D]** Per W normalizzata per riga vale analiticamente `R_geo = 4 kappa_geo N/(N-1) =
4*24/23 = 4.174`: dipende **solo da N = 24** (topologico), e' **scala-invariante** (non
24^L). Confermato sul reticolo di Leech reale (identico a ogni livello). La costante
gravitazionale emergente segue:

    beta = Theta / R_geo .

Sono i **rapporti** beta_i/beta_j = R_j/R_i ad essere determinati dalla geometria (nessun
numero strutturale libero); resta l'unica unita' dimensionale Theta (scala di Planck).

La rigidezza **fisica** include due correzioni dinamiche (vedi §3):
- **diluizione metrica**: `R_phys = R_geo / a^2` (a = fattore di scala locale);
- **irrigidimento da materia [D]**: i kink aumentano la rigidezza locale,
  `R_local = R_geo (1 + K2/rho*)` (knob-free, rho* derivato §3.2).

### 2.4 Inventario delle costanti

| Grandezza | Stato | Origine |
|---|---|---|
| N = 24 | [D] | reticolo di Leech (numero di contatto) |
| R_geo = 4N/(N-1) = 4.174 | [D] | spettro Laplaciano (topologico) |
| rho* = 2 chi0^2 = (sqrt2 chi0)^2 | [D] misurato | scala parete di dominio (costante sqrt2 Jitterbug) |
| chi0 (VEV del campo) | fisica | minimo del doppio pozzo |
| 4pi, pi (chiusura 720, twist 180) | topologiche | spin-1/2 |
| Theta = E_Planck, ell_Planck | [P] ancoraggio | fondo gerarchia = scala di Planck |
| coeff (emissione di fondo) | [P] scala | tasso di emissione (~T_eff); valore da calibrare |
| alpha_K, kappa, lambda~24^(2L), gamma | da eliminare | leggi di scala postulate (dissolte, §4) |

---

## 3. Dinamica

### 3.1 Substrato di campo
Su ogni voxel l'evoluzione e' simplettica (Verlet) con forza di doppio pozzo
`F = -V'(chi)`, `V(chi) = beta_pot (chi^2 - chi0^2)^2`, piu' smorzamento di
fluttuazione-dissipazione (bagno termico effettivo). Questo nucleo e' il riferimento
verificato; tutti i termini sotto sono **additivi** (attivabili a flag, default inattivi,
il nucleo legacy resta bit-identico).

### 3.2 Settore di torsione (Einstein-Cartan)
Densita' di torsione di gradiente per nodo:

    K2_i = sum_j W_ij (chi_i - chi_j)^2 .

**Saturazione a soffitto (pressione di degenerazione di spin / bounce):**

    E_sat = beta_sat * sum_i ((K2_i - rho*)+)^2 ,   F_chi = -dE_sat/dchi ,

con `(x)+` parte positiva (one-sided): sotto rho* la forza e' nulla (vuoto e domini
stabili), sopra rho* la torsione in eccesso e' respinta (bounce, no singolarita').
Soglia derivata `rho* = 2 chi0^2` [D]: e' la scala della parete di dominio / del campo
disordinato (misurata: parete K2 ~ 2 chi0^2). E' la costante geometrica sqrt(2)
(Ottaedro -> Cubottaedro).

**Chiusura spinoriale (720 gradi):**

    E_clo = kappa_clo (sum_i tau_i - 4pi)^2 ,

guida la fase spinoriale alla chiusura a 4pi (spin-1/2). Le forze EC sono gradienti di
energie ben definite (conservative, verificate vs gradiente numerico, err ~5e-11).

### 3.3 Espansione metrica
Ogni blocco porta un **fattore di scala locale a** (default 1). La torsione *fisica*
(per volume fisico) e' `K2/a^2`. Il tasso di espansione (analogo del parametro di Hubble)
e' la somma di due contributi:

    H = a'/a = H_bounce + H_emissione

- **H_bounce** (relief locale della torsione in eccesso):
  `H_bounce = beta_sat <(K2_i/a^2 - rho*)+>` (media per-nodo della parte positiva ->
  risposta **locale**: pareti/difetti localizzati sorgentano espansione anche se la media
  del blocco e' sotto rho*).
- **H_emissione** (termine di emissione di volume alla scala di Planck, *uniforme*,
  modulato dalla rigidezza):
  `H_emissione = coeff / (1 + K2/rho*)`.

L'aggiornamento e' `a <- a (1 + H dt)`. Il sistema e' **auto-regolante** (feedback
negativo): un eccesso di torsione produce espansione, l'espansione diluisce la torsione
(K2/a^2 cala), il termine si spegne. Punto fisso del bounce `a* = sqrt(maxK2/rho*)`.

**Accoppiamento gravita'-rigidezza (G attiva):** il coefficiente beta_sat e' esso stesso
funzione della rigidezza fisica, `beta_sat = Theta/R_phys = beta_baseline a^2` (eventualmente
`/(1+K2/rho*)` con l'irrigidimento da materia): dove lo spazio e' rigido (materia),
l'espansione e' soppressa. Verificato **stabile** (no runaway: la diluizione ~1/a^2
regola il feedback).

### 3.4 Gravita' emergente
Combinando il termine di emissione **uniforme** con l'irrigidimento da materia
(`H_emissione = coeff/(1+K2/rho*)`):

- nei **vuoti** (K2 basso) l'espansione e' piena;
- nella **materia** (K2 alto) e' soppressa.

Quindi lo spazio si crea preferenzialmente nei vuoti, la materia si **addensa** (clumping).
**[D]** Verificato: a(vuoto) > a(materia) -> concentrazione della materia.

Interpretazione unificante: **la stessa forza e' una spinta espansiva nel riferimento
dello spaziotempo e un'attrazione nel riferimento della materia**. Repulsione (bounce ad
alta densita', anti-singolarita') e attrazione (clumping a densita' moderata) sono i due
regimi di un unico termine di Einstein-Cartan.

### 3.5 Omogeneita' e disomogeneita'
L'omogeneita' non e' imposta: e' un **risultato**. Sorgente di torsione uniforme ->
espansione uniforme (cosmologia FLRW locale); sorgente concentrata -> espansione locale
(curvatura = gravita'). Nel manifold frattale l'omogeneita' e' **solo locale** (molte
regioni FLRW locali cucite), mai globale.

### 3.6 Cosmogenesi (condizione iniziale)
L'origine e' lo stato **simmetrico** (chi ~ 0, massimo instabile del doppio pozzo:
nessuna struttura) piu' un **seme stocastico** (fluttuazione del vuoto). **[D]**: con il
seme si ha rottura spontanea di simmetria (SSB) -> domini +-chi0 -> torsioni -> materia ->
espansione; **senza** seme il campo resta sul massimo instabile (nessuna struttura).
L'universo nasce da una fluttuazione.

---

## 4. Risultati verificati [D]

- **Dissoluzione dei coupling postulati**: appiattendo le leggi di scala 24^L (incluso il
  termine "esplosivo" lambda~24^(2L)) la fenomenologia (densita' di difetti) non cambia e
  il sistema non diverge -> la dipendenza di scala postulata e' superflua e rimovibile.
- **G topologica e scala-invariante**: R_geo = 4.174 a ogni livello (dal 24, non 24^L).
- **G non-monotona con la scala**: la rigidezza fisica (e quindi G) traccia la scala a cui
  si concentra la materia -> G(L) puo' avere un massimo interno (non monotona). E' un
  ingrediente del tipo richiesto per la tensione di Hubble (differenza early-vs-late).
- **"Febbre" = transiente**, non legge di scala: la KE per nodo riscalda e poi raffredda
  (FDT); il preteso esponente di scala e' un artefatto di non-equilibrio.
- **Saturazione + scala metrica + cosmogenesi + clumping** verificati come sopra.

---

## 5. Ipotesi ancora da verificare [H]

1. **Collasso dinamico**: il clumping e' finora una *differenza di tasso di espansione*
   (vuoti > materia). Resta da mostrare la **migrazione/aggregazione dinamica** della
   materia in strutture in un'evoluzione lunga (firma forte della gravita').
2. **Calibrazione fisica (Hubble)**: il valore assoluto di coeff e di Theta non e'
   predetto (l'ancoraggio fissa l'unita', non G — `ell_Planck = sqrt(hbar G/c^3)`). Resta
   da passare a unita' fisiche e predire il gap di espansione tra scale (early-vs-late).
3. **Oscillazione SSB**: l'ordine non si assesta ma "respira" (sale a ~1, ridiscende).
   Da distinguere meta-stabilita' (frustrazione chirale) vs bagno termico FDT.
4. **Aritmetica 180/720**: la relazione esatta tra le 24 mezze onde spaziali (12 monti +
   12 valli) e la chiusura spinoriale a 720 gradi (doppio rivestimento) e' da fissare.
5. **Riduzione spinoriale**: il codice rappresenta il voxel come scalare reale chi + fase
   tau, riduzione del campo spinoriale (up/down, twist alternato). La rappresentazione
   complessa/spinoriale completa e' da formalizzare.
6. **Termine di emissione di fondo**: l'origine fisica di coeff (tasso di emissione ~T_eff)
   e' una scelta; va legato in modo derivato alla scala (e potrebbe rendere ridondante il
   bagno termico separato).
7. **Ancoraggio di Planck** [P]: che il fondo della gerarchia *sia* la scala di Planck e'
   un postulato (l'auto-similarita' e' senza scala), non una derivazione.
8. **rho*_geometrico == rho*_EC**: coincidenza concettuale tra la scala del reticolo di
   Leech e la soglia di Einstein-Cartan, da dimostrare.

---

## 6. Sintesi del funzionamento

Lo spaziotempo emerge dall'aggregazione di voxel (statica: reticolo di Leech, scala di
Planck, rigidezza topologica R_geo). La sua disomogeneita' genera torsioni e quindi
difetti = materia. Il settore di Einstein-Cartan fornisce una **pressione di torsione**
che (i) localmente satura la densita' ad alta torsione (bounce, no singolarita') e (ii)
globalmente sostiene un'espansione metrica. Un termine di **emissione di volume di fondo**
alla scala di Planck, modulato dalla rigidezza (che la materia aumenta), fa espandere i
vuoti piu' della materia: la materia si addensa. La medesima pressione e' spinta espansiva
(spaziotempo) e attrazione (materia). La costante gravitazionale e' l'inverso della
rigidezza, topologica e scala-dipendente solo attraverso lo stato (G non-monotona). Le
condizioni iniziali sono lo stato simmetrico piu' una fluttuazione stocastica
(cosmogenesi). Tutte le leggi di scala postulate del modello precedente risultano
superflue: i coefficienti rilevanti sono derivati dalla geometria (N = 24, sqrt(2)) o
ancorati a un'unica scala (Planck).
