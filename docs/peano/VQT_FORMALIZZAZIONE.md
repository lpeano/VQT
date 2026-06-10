# VQT — Formalizzazione: statica, dinamica, ipotesi aperte

**Versione**: 2026-06-09 (motore Einstein-Cartan COMPLETO, torsione dallo spin)
**Branch**: `physics/einstein-cartan-saturation`

Documento di sintesi formale del modello VQT (Voxel Quantum Theory) sul settore di
Einstein-Cartan **completamente integrato**: la torsione e' sorgentata dallo SPIN, e da
quell'unica torsione discendono saturazione (bounce), espansione, gravita' (clumping),
dilatazione del tempo e direzione del tempo. Distingue cio' che e' *derivato/misurato* da
cio' che e' *postulato* o *congetturato*.

Etichette: **[D]** derivato/misurato col codice · **[P]** postulato (scelta dichiarata) ·
**[H]** ipotesi da verificare · **[I]** interpretazione (non derivata dalla dinamica).

> Nota terminologica. Il termine di creazione di volume alla scala fondamentale, chiamato
> informalmente "muratore di Planck", qui e': **termine di emissione di volume alla scala
> di Planck** (o *espansione metrica di fondo*).

## Schema d'insieme

![Schema delle interazioni del sistema VQT](../figures/vqt_sistema.png)

*Quadro completo del motore Einstein-Cartan integrato. **A sinistra** il diagramma delle
interazioni: la fondazione (reticolo di Leech -> R_geo; scala di Planck) e il voxel (campo
+ spinore) alimentano lo SPINORE, da cui si calcola la **torsione sorgentata dallo spin
K²_spin** (cuore); quell'unica torsione guida le quattro facce tipo-RG (saturazione/bounce,
espansione+gravita'/clumping, tempo proprio attivo, direzione del tempo). Frecce piene =
relazione (genera/guida), tratteggiate = feedback. **A destra**: tutte le **COSTANTI**
(con stato: derivata / topologica / fisica / postulata / eliminata) e tutte le **FORMULE
DI DERIVAZIONE**. Generato (riproducibile) da `tools/rendering/genera_diagramma_vqt.py`.*

---

## 1. Oggetto e ontologia

VQT descrive lo spaziotempo come **manifold frattale gerarchico**: ogni livello L(n) e'
N = 24 unita' del livello inferiore (24 = numero di contatto del reticolo di Leech /
cubottaedro). L'unita' fondamentale e' il **voxel** (livello L0).

Ogni voxel porta:
- un **campo** (chi, v): scalare chi (parte reale) e velocita' coniugata v = dchi/dt, in
  un doppio pozzo `V(chi)=beta_pot(chi^2-chi0^2)^2`;
- uno **SPINORE** psi = cos(theta/2)|0> + sin(theta/2) e^{i phi}|1>, con
  **beta/alpha = tan(theta/2) e^{i phi} = PENDENZA DEL KINK** (il campo complesso di cui chi
  e' la parte reale). theta (latitudine di Bloch) viene dalla pendenza locale del campo;
  phi (fase) e' la torsione spinoriale.

**Chiralita' = materia vs spazio** (derivata dallo spinore):
  rho_SX = sin^2(theta/2) = "materia", rho_DX = cos^2(theta/2) = "spazio", rho_SX+rho_DX=1.
La **materia e' la complessita' chirale/topologica** dello spaziotempo emergente (i kink,
le pareti di dominio dove theta e' alta), non un'entita' separata. Un voxel isolato non
ha geometria: la **torsione e' relazionale**, emerge tra voxel (vedi §3.3).

---

## 2. Statica

### 2.1 Reticolo e geometria di accoppiamento
Ogni blocco e' una cella di N = 24 nodi con matrice di accoppiamento `W` di simmetria
Leech (cubottaedro, 12 vicini), **normalizzata per riga** (somma riga = 1, diagonale 0).
Il Laplaciano del grafo `L = D - W` (D = diag delle somme di riga) codifica la rigidezza
geometrica (e' l'Hessiano, a meno di un fattore, dell'energia di torsione).

### 2.2 Scala metrica
Per **ancoraggio [P]**, il fondo della gerarchia (L0) coincide con la scala di Planck:
    ell_voxel(L0) = ell_Planck ,  t_step = t_Planck ,  E_voxel = Theta = E_Planck .
L'auto-similarita' fissa il **rapporto** tra livelli [D]: un aggregato = 24 voxel (12
"monti" + 12 "valli"), una mezza onda = 1 voxel = 1/24 dell'aggregato. Lunghezza per
livello `ell_L = 24^(L/d) ell_Planck` (d=3 -> fattore 24^(1/3)~2.884, protone ~ L43).

### 2.3 Struttura spinoriale (180/720 topologica)
Lo spinore avvolge sull'anello di 24: il twist per legame e'
    tau_i = 4pi/N + pi*(-1)^i   (half-twist 180 a chiralita' alternata),
con `sum tau_i = 4pi` per costruzione -> **chiusura 720 (spin-1/2) ESATTA e TOPOLOGICA**
(e^{i 4pi}=1: lo spinore ritorna a se' dopo 720, non 360). Le costanti 180=pi e 720=4pi
sono **topologiche**, non tarabili.

### 2.4 Rigidezza e costante gravitazionale emergente
G non e' fondamentale: e' l'**inverso della rigidezza elastica dello spaziotempo**
(gravita' indotta, Sakharov 1967; entropica, Verlinde 2011). Rigidezza geometrica scalare:
    R_geo = 4 kappa_geo <lambda_k(L) : lambda_k>0>   (modi di deformazione, esclude il modo nullo).
**[D]** Per W normalizzata per riga, analiticamente `R_geo = 4 kappa_geo N/(N-1) = 4*24/23
= 4.174`: dipende **solo da N=24** (topologico), **scala-invariante** (non 24^L). Quindi
`beta = Theta/R_geo` (analogo di G). I **rapporti** beta_i/beta_j = R_j/R_i sono fissati
dalla geometria; resta una sola unita' Theta (Planck). Rigidezza **fisica**:
- diluizione metrica `R_phys = R_geo/a^2` (a = fattore di scala locale);
- **irrigidimento da materia [D]**: i kink aumentano la rigidezza, `R_local = R_geo(1+K2_spin/rho*)`.

### 2.5 Inventario delle costanti

| Grandezza | Stato | Origine |
|---|---|---|
| N = 24 | [D] | reticolo di Leech (numero di contatto) |
| R_geo = 4N/(N-1) = 4.174 | [D] | spettro Laplaciano (topologico) |
| rho* = 2 chi0^2 = (sqrt2 chi0)^2 | [D] misurato | scala parete di dominio (sqrt2 Jitterbug) |
| 180=pi, 720=4pi | topologiche | twist / chiusura spin-1/2 |
| chi0 (VEV del campo) | fisica | minimo del doppio pozzo |
| Theta = E_Planck, ell_Planck | [P] ancoraggio | fondo gerarchia = scala di Planck |
| coeff (emissione di fondo) | [P] scala | tasso di emissione (~T_eff), da calibrare |
| alpha_K, kappa, lambda~24^(2L), gamma | ELIMINATE | leggi di scala postulate (dissolte, §4) |

Le costanti numeriche del rilassamento spinoriale (ratei) sono passi d'integrazione (come
dt), non valori fisici. Nessuna scala fisica e' hardcoded: chi0 = physics.chi_stable, rho*
derivato, 180/720 topologici.

---

## 3. Dinamica

### 3.1 Substrato di campo
Evoluzione simplettica (Verlet) con forza di doppio pozzo `F=-V'(chi)` + smorzamento di
fluttuazione-dissipazione. Nucleo verificato; tutti i termini EC sono **additivi** (flag
opt-in, default OFF -> legacy bit-identico).

### 3.2 Spinore: beta/alpha = pendenza, 180/720 esatto
Lo spinore (theta, dphi) di ogni blocco rilassa (stabile):
- **theta**: `tan(theta/2) -> |pendenza del kink|` (= |gradiente di chi|/chi0): beta/alpha
  segue il campo. E' il legame campo <-> spinore.
- **dphi**: imposto = tau_i (twist topologico) -> **winding = 4pi ESATTO** (chiusura 720),
  senza parametri.

### 3.3 Torsione SORGENTATA DALLO SPIN (cuore di Einstein-Cartan)
La torsione non e' il gradiente scalare di chi, ma viene dallo SPIN (densita' di spin =
vettore di Bloch n = <psi|sigma|psi>):
    K2_spin_i = chi0^2 * sum_j W_ij |n_i - n_j|^2 ,   |n_i-n_j|^2 = 2 - 2 n_i.n_j .
Scalata per chi0^2 -> stesse unita' fisiche (una parete spinoriale da' ~2 chi0^2 = rho*).
**Lo spin genera la torsione; questa torsione guida tutto il resto** (3.4-3.8).

### 3.4 Saturazione / bounce (sullo SPIN)
Dove K2_spin > rho* gli spin si ALLINEANO (theta verso la media pesata dei vicini) ->
riduce la torsione: e' la **pressione di degenerazione di spin / bounce** di Einstein-
Cartan, ora agente sullo spin stesso. Soglia **derivata** `rho* = 2 chi0^2` [D] (scala
della parete di dominio, costante sqrt(2) Ottaedro->Cubottaedro). Effetto: la densita'/
torsione non supera rho* -> **densita' massima finita, niente singolarita'** (tetto morbido).

### 3.5 Espansione metrica
Ogni blocco ha un fattore di scala `a`. Torsione fisica = K2_spin/a^2. Tasso tipo-Hubble:
    H = a'/a = H_bounce + H_emissione ,
    H_bounce = beta_sat <(K2_spin/a^2 - rho*)+>        (relief locale dell'eccesso),
    H_emissione = coeff / (1 + K2_spin/rho*)            (emissione di volume di fondo,
        uniforme, modulata dalla rigidezza).
`a <- a(1 + H dt)`. **Auto-regolante**: eccesso di torsione -> espansione -> diluisce la
torsione -> il termine si spegne (punto fisso `a* = sqrt(maxK2_spin/rho*)`). G **attiva**:
`beta_sat = Theta/R_phys = beta_baseline a^2 / (1+K2_spin/rho*)` (verificato stabile, la
diluizione ~1/a^2 regola il feedback).

### 3.6 Gravita' emergente (clumping)
Il termine di emissione **uniforme** modulato dalla rigidezza: nei vuoti (K2_spin basso)
l'espansione e' piena; nella materia (K2_spin alto) e' soppressa. Quindi lo spazio si crea
nei vuoti, la materia si **addensa**. **[D]** Verificato sul motore completo: a(vuoto) >
a(materia) -> clumping, con torsione sorgentata dallo spin. Unificazione: **la stessa
forza e' spinta espansiva (frame spaziotempo) e attrazione (frame materia)**; repulsione
(bounce ad alta densita') e attrazione (clumping a densita' moderata) sono due regimi di
un unico termine EC. Omogeneita' **solo locale** (FLRW locali cucite, mai globale).

### 3.7 Tempo proprio ATTIVO (gravita' -> tempo)
Il campo (materia) evolve nel **tempo proprio locale** dt_local = dt * f, con
    f = 1 - <K2_spin>/rho*  (proper_time_factor).
- materia (K2 < rho*): 0 < f < 1 -> la fisica locale RALLENTA (non solo l'orologio);
  **[D]** ~31% piu' lenta nei nuclei densi;
- bounce (K2 = rho*): f = 0 (orizzonte); estremo (K2 > rho*): f < 0 (inversione, ma la
  saturazione cap-pa K2 a rho* -> f non scende sotto 0 in dinamica normale).
Parameter-free (rho* derivato). E' il legame **gravita' -> tempo proprio**: la massa
rallenta il tempo come in Relativita' Generale.

### 3.8 DIREZIONE DEL TEMPO (emerge dall'integrazione SX+DX)
Decomponendo il tempo proprio per chiralita' (diagnostico, non cambia la dinamica):
    tau_SX = int f rho_SX (materia),  tau_DX = int f rho_DX (spazio).
**[I]** Con Feynman-Stueckelberg (antimateria = materia indietro nel tempo), la materia
contribuisce col segno opposto: la direzione NETTA e' l'**integrazione**
    tau_netto = tau_DX - tau_SX = int f cos(theta)   (cos theta = rho_DX - rho_SX).
**[D] Misurato** (test_inversione_tempo.py, 600 step): ~6-8% dei voxel (nuclei di materia,
theta>pi/2) hanno tempo netto INDIETRO; lo spazio AVANTI; il netto **globale AVANTI**.
**Conseguenza [I]**: la freccia del tempo NON e' imposta, **emerge** dall'integrazione di
due tempi opposti; e' in avanti perche' **lo spazio domina il volume**. Inversione globale
-> regione materia-dominata (core densissimo). Non richiede f<0: l'inversione vive nella
chiralita'.

**Perche' il tempo e' piu' lento dove c'e' materia/gravita' [D].** Tempo netto: vuoto=3.000
(tau_DX=3.0, tau_SX=0), materia=1.750 (tau_DX=1.91, tau_SX=0.16) -> **42% piu' lento**. Due
contributi: (1) **f<1** dominante (la massa dilata il ritmo, tau_DX 3.0->1.91); (2)
**cancellazione chirale** (piu' materia=SX indietro che si sottrae al tempo-spazio avanti).
La dilatazione gravitazionale del tempo EMERGE da questa integrazione avanti/indietro.

### 3.9 Cosmogenesi (condizione iniziale)
L'origine e' lo stato **simmetrico** (chi ~ 0, massimo instabile) + un **seme stocastico**.
**[D]**: col seme -> rottura spontanea di simmetria (SSB) -> domini -> torsioni -> materia
-> espansione; **senza** seme resta sul massimo instabile (niente universo). L'universo
nasce da una fluttuazione.

---

## 4. Risultati verificati [D]

- **Einstein-Cartan integrato**: la torsione e' sorgentata dallo spin (K2_spin); saturazione
  (sullo spin), espansione, gravita', dilatazione e direzione del tempo discendono tutte da
  quell'unica torsione. Spinore normalizzato, beta/alpha=pendenza (err ~1e-3), 720 esatto.
- **Dissoluzione dei coupling postulati**: appiattendo le leggi 24^L (incluso lambda~24^(2L))
  la fenomenologia non cambia ne' diverge -> dipendenza di scala superflua e rimossa.
- **G topologica e scala-invariante**: R_geo = 4.174 a ogni livello (dal 24, non 24^L).
- **G non-monotona con la scala**: la rigidezza fisica traccia la scala della materia ->
  G(L) puo' avere un massimo interno (ingrediente per la tensione di Hubble).
- **Gravita' (clumping)**: vuoti espandono > materia (torsione dallo spin).
- **Tempo proprio attivo**: la materia ~31% piu' lenta; direzione del tempo emergente
  (materia indietro / spazio avanti, netto avanti); dilatazione gravitazionale spiegata.
- **"Febbre" = transiente**, non legge di scala (artefatto di non-equilibrio).
- **Cosmogenesi**: SSB da seme stocastico; senza dadi niente universo.

Tutti i GATE/self-test PASS; legacy bit-identico con flag OFF.

---

## 5. Ipotesi ancora da verificare [H]

1. **Collasso dinamico**: il clumping e' finora *differenza di tasso di espansione*. Resta
   da mostrare la **migrazione/aggregazione** della materia in strutture (firma forte).
2. **Calibrazione fisica (Hubble)**: coeff e Theta non sono predetti (`ell_Planck=
   sqrt(hbar G/c^3)` -> ancorare = scegliere G). Passare a km/s/Mpc e predire il gap
   early-vs-late.
3. **Bounce vero**: il bounce e' un tetto morbido (densita' -> rho*), non un rimbalzo con
   rovesciamento. Permettere l'overshoot (e l'inversione del tempo che ne segue).
4. **Flip di chiralita' al bounce**: accoppiare l'inversione del tempo al flip SX<->DX
   (materia<->antimateria), CPT-like.
5. **Aritmetica 180/720**: relazione esatta tra le 24 mezze onde spaziali e la chiusura 4pi.
6. **Oscillazione SSB**: l'ordine "respira" -> meta-stabilita' o bagno FDT?
7. **Origine di coeff**: tasso di emissione ~T_eff da derivare (potrebbe deprecare il
   termostato FDT separato).
8. **Ancoraggio di Planck** [P]: il fondo = scala di Planck e' postulato (auto-similarita'
   senza scala).
9. **rho*_geometrico == rho*_EC**: coincidenza Leech / soglia EC, da dimostrare.

---

## 6. Sintesi del funzionamento

Ogni voxel e' un **campo (chi) + uno spinore** (beta/alpha = pendenza del kink, twist 180
alternato che chiude a 720). Dallo SPINORE si calcola la **densita' di spin** (vettore di
Bloch) e quindi la **torsione** K2_spin: lo spin genera la torsione. Quell'unica torsione
guida tutto:
- la **saturazione/bounce** (sullo spin) mette un tetto alla densita' (rho*, niente
  singolarita');
- l'**espansione metrica** + l'irrigidimento da materia fanno espandere i vuoti piu' della
  materia -> la materia si **addensa** (gravita'/clumping: spinta=attrazione, due frame);
- la massa **rallenta il tempo proprio** (attivo: la fisica locale rallenta, ~31%), e la
  **direzione del tempo emerge** dall'integrazione materia(indietro)+spazio(avanti) - in
  avanti perche' lo spazio domina il volume.
La costante gravitazionale e' l'inverso della rigidezza (topologica, R_geo=4*24/23; scala-
dipendente solo via lo stato -> G non-monotona). La materia, chiralita' (SX), nasce dalla
complessita' dello spaziotempo. Le condizioni iniziali: simmetrico + seme stocastico
(cosmogenesi). Tutte le leggi di scala postulate del modello precedente sono superflue: i
coefficienti sono derivati dalla geometria (N=24, sqrt(2)) o ancorati a un'unica scala
(Planck). Nessun valore fisico hardcoded.
