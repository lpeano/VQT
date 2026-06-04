# Formalizzazione: la massa come difetto topologico congelato nella VQT

**Per "Il Muratore di Planck" — capitolo sulla genesi della massa**
**Data**: 2026-06-03 · **Branch**: `research-backup`

---

## Avvertenza epistemica (leggere prima)

Questo documento formalizza risultati ottenuti per via simulativa. Per onestà
scientifica, ogni affermazione e' marcata con il suo status:

- **[DEF]** Definizione operativa (vera per costruzione).
- **[OSS]** Osservazione empirica (misurata; riportata con incertezza e dominio di validita').
- **[CNG]** Congettura / cornice interpretativa (plausibile, non ancora dimostrata).

Dominio di validita' attuale dei risultati empirici: livelli L1 (N=24 nodi) e
L2 (N=576 nodi), 4–10 realizzazioni per livello. La scalabilita' a L≥3 e la forma
funzionale delle leggi di scala restano da verificare.

---

## 0. Notazione (coerente in tutto il documento)

| Simbolo | Significato |
|---|---|
| $N=24^L$ | numero di segmenti foglia al livello $L$ |
| $\chi_i$ | campo scalare (parametro d'ordine) sul nodo $i$ |
| $\chi_0$ | valore di vuoto (VEV), $\chi_0 = \texttt{chi\_stable} = 50$ |
| $v_i=\dot\chi_i$ | velocita' coniugata |
| $W_{ij}$ | matrice di accoppiamento (Leech/cubottaedrica), simmetrica, circolante su $Z_{24}$ |
| $\alpha_K$ | costante di accoppiamento di torsione |
| $\beta$ | profondita' del doppio pozzo |
| $\tau_i$ | tempo proprio locale (fase spinoriale) |
| $K^2_i$ | contorsione locale |

Potenziale di Landau–Ginzburg (doppio pozzo):
$$V(\chi)=\beta\left(\chi^2-\chi_0^2\right)^2 .$$

Equazione del moto (sistema aperto, smorzamento $\gamma$):
$$m\,\ddot\chi_i = -\frac{\partial V}{\partial \chi_i} \;-\; \alpha_K\,(L_{\mathrm{graph}}\chi)_i \;-\; \gamma\,\dot\chi_i,
\qquad L_{\mathrm{graph}} = D - W,\;\; D_{ii}=\textstyle\sum_j W_{ij}.$$

---

## 1. Soglia geometrica $\sqrt{2}$ vs energia di frustrazione $E_{\Psi}^{\mathrm{anc}}$

### 1.1 Definizione formale

**[DEF] Soglia geometrica (invariante di Jitterbug).**
Si definisce *saturazione topologica* la quantita' adimensionale
$$s(t)=\frac{\chi_{\max}(t)}{\chi_0},\qquad \chi_{\max}(t)=\max_{i\in\text{foglie}}|\chi_i(t)| .$$
La **soglia di Jitterbug** e' il valore critico
$$s_\star=\sqrt{2},$$
rapporto volumetrico della trasformazione Ottaedro $\to$ Cubottaedro (Vector
Equilibrium) nella geometria di Fuller. Le fasi geometriche sono classificate da:
$$\text{Ottaedrica } (s<1),\quad \text{Cubottaedrica } (1\le s<\sqrt2),\quad \text{Icosaedrica } (s\ge\sqrt2).$$

**[DEF] Densita' di torsione ed energia reattiva.** Per ogni nodo
$$\rho^{\mathrm{tors}}_i=\sum_j W_{ij}\,(\chi_i-\chi_j)^2,
\qquad E_{\mathrm{tors}}=\tfrac12\,\alpha_K\sum_i \rho^{\mathrm{tors}}_i .$$

**[DEF] Energia di frustrazione ancorata.** Definita tramite i due invarianti
topologici del reticolo — il deficit di chiusura spinoriale a $720^\circ$ e la
qualita' del pattern di detorsione:
$$
E_{\Psi}^{\mathrm{anc}}
= E_{\mathrm{tors}}\;\bigl(1-Q_{\mathrm{det}}\bigr)\;\bigl(1+\varepsilon_{\mathrm{clo}}\bigr),
$$
con
$$
\varepsilon_{\mathrm{clo}}=\frac{1}{360^\circ}\,\Bigl|\,\bigl(\textstyle\sum_i\tau_i\bigr)\bmod 4\pi\,\Bigr|_{\to 0},
\qquad
Q_{\mathrm{det}}=\frac{\#\{k:\,\Delta\rho^{\mathrm{tors}}_k\,\Delta\rho^{\mathrm{tors}}_{k+1}<0\}}{\#\{k\}} ,
$$
dove $|\cdot|_{\to0}$ denota la distanza dal multiplo di $4\pi$ piu' vicino e
$\Delta\rho^{\mathrm{tors}}_k=\rho^{\mathrm{tors}}_{k+1}-\rho^{\mathrm{tors}}_{k}$.

### 1.2 Derivazione analitica (disaccoppiamento dei due oggetti)

La quantita' $s(t)$ e' un *funzionale del campo all'istante $t$* sensibile ai
**picchi locali**. La quantita' $E_{\Psi}^{\mathrm{anc}}$ e' un *funzionale della
configurazione globale* sensibile alla **frustrazione** (mancata chiusura +
disordine del pattern di torsione). I due non sono proporzionali:

- $s$ puo' superare $\sqrt2$ con $E_{\Psi}^{\mathrm{anc}}\!\to0$ se la
  configurazione, pur avendo un picco, e' geometricamente rilassabile
  ($Q_{\mathrm{det}}\to1$, $\varepsilon_{\mathrm{clo}}\to0$).
- $E_{\Psi}^{\mathrm{anc}}$ resta finita anche dopo che $s$ e' ridisceso sotto
  $\sqrt2$, se la frustrazione si e' "bloccata" (§3).

**[OSS] Falsificazione del legame puntuale $s=\sqrt2 \Leftrightarrow$ massa.**
Il punto di massima curvatura di $E_{\Psi}^{\mathrm{anc}}(s)$ lungo la traiettoria
non cade a $\sqrt2$ e, soprattutto, **si sposta con il dominio esplorato**
(L1: ginocchio $\approx1.45$; L2: $\approx0.77$). Cio' dimostra che la coincidenza
apparente e' un artefatto della forma della curva, non una soglia fisica: la
soglia geometrica e l'energia di frustrazione sono **osservabili distinti**.

### 1.3 Interpretazione verbale

$\sqrt2$ misura *quanto in alto* arriva localmente il campo — un evento di
ampiezza, geometrico, istantaneo. $E_{\Psi}^{\mathrm{anc}}$ misura *quanto il
tessuto non riesce a richiudersi* — uno stato di frustrazione, topologico,
persistente. La massa appartiene alla seconda categoria: non e' un'altezza
raggiunta, ma una cicatrice rimasta.

### 1.4 Connessione con Kibble–Zurek

Nel linguaggio delle transizioni di fase, $s$ e' il parametro di controllo che
porta il sistema *attraverso* la regione critica; $E_{\Psi}^{\mathrm{anc}}$ e' la
densita' di difetti topologici che la dinamica *intrappola* attraversandola.
Kibble–Zurek separa esplicitamente il *controllo* (attraversamento) dall'*esito*
(difetti): la sezione §2 ne quantifica la separazione temporale.

---

## 2. La struttura a due tempi: $t_{\mathrm{cross}}\to\Delta t_{\mathrm{relax}}\to t_{\mathrm{freeze}}$

### 2.1 Definizione formale

**[DEF]** Dato un cammino dinamico $\{\chi_i(t)\}$:
$$
t_{\mathrm{cross}}=\min\{t:\; s(t)\ \text{attraversa}\ \sqrt2\},
$$
$$
t_{\mathrm{freeze}}=\min\{t:\; \mathcal{Q}[\chi(t)]\ \text{ha massa residua}\ E_{\Psi}^{\mathrm{anc}}>\theta\},
$$
dove $\mathcal{Q}$ e' l'operatore di quench (§3) e $\theta$ una soglia di
significativita'. Il **ritardo di intrappolamento** e'
$$\boxed{\;\Delta t_{\mathrm{relax}} = t_{\mathrm{freeze}} - t_{\mathrm{cross}}\;}$$

### 2.2 Derivazione analitica / risultati di scala

**[OSS]** Misure su $\{1{,}\dots\}$ realizzazioni indipendenti:

| livello | $N$ | $t_{\mathrm{cross}}$ | $t_{\mathrm{freeze}}$ | $\Delta t_{\mathrm{relax}}$ | $\mathrm{corr}(t_{\mathrm{cross}},t_{\mathrm{freeze}})$ |
|---|---|---|---|---|---|
| L1 | 24  | $13.6\pm2.0$ | $64\pm8$  | $\mathbf{+50.4}$ | $-0.92$ |
| L2 | 576 | $20.8\pm1.9$ | $75\pm17$ | $\mathbf{+54.2}$ | $-0.67$ |

**[OSS] Invarianza di scala del ritardo.** Mentre $t_{\mathrm{cross}}$ e
$t_{\mathrm{freeze}}$ crescono con $L$, la loro differenza e' (entro l'incertezza)
**indipendente dal livello**:
$$\Delta t_{\mathrm{relax}}(L_1)\approx\Delta t_{\mathrm{relax}}(L_2)\approx 50\text{–}54\ \text{step}.$$
Questo identifica $\Delta t_{\mathrm{relax}}$ come la grandezza fisica robusta del
processo (non $t_{\mathrm{cross}}$ ne' $t_{\mathrm{freeze}}$ separatamente).

**[OSS] Anticorrelazione.** $\mathrm{corr}(t_{\mathrm{cross}},t_{\mathrm{freeze}})<0$:
piu' precocemente il sistema attraversa $\sqrt2$, piu' tardi (in tempo assoluto)
congela il difetto — coerente con un'iniezione dinamica maggiore che richiede
piu' rilassamento. **[CNG]** La forma funzionale di questa relazione e il suo
limite a $L\to\infty$ non sono ancora determinati.

### 2.3 Interpretazione verbale

La materia non nasce nell'istante in cui il campo "si spezza" ($t_{\mathrm{cross}}$):
nasce piu' tardi, quando la dinamica frustrata, non riuscendo a rilassare,
**si blocca** ($t_{\mathrm{freeze}}$). Tra i due istanti c'e' un intervallo
caratteristico — un "tempo di gestazione" del difetto — che il modello mantiene
costante al crescere della scala.

### 2.4 Connessione con Kibble–Zurek

Nel paradigma KZ la densita' di difetti e' fissata al *freeze-out time* $\hat t$,
quando il tempo di rilassamento $\tau_{\mathrm{relax}}$ eguaglia il tempo
caratteristico dell'attraversamento. Qui $\Delta t_{\mathrm{relax}}$ e'
l'analogo discreto di $\hat t$ misurato dall'attraversamento di $\sqrt2$:
$$t_{\mathrm{freeze}} = t_{\mathrm{cross}} + \Delta t_{\mathrm{relax}},
\qquad \Delta t_{\mathrm{relax}}\ \text{quasi-invariante di scala}.$$
**[CNG]** Se valesse la legge di scala KZ standard
$n_{\mathrm{def}}\propto \tau_Q^{-\nu/(1+z\nu)}$, ci si attenderebbe una dipendenza
prevedibile della frazione massiva dal tasso di attraversamento; la verifica
quantitativa di questa legge e' il prossimo test (L3 + scan del rate).

---

## 3. Il quench come operatore di proiezione topologica

### 3.1 Definizione formale

**[DEF] Operatore di quench.** Sia $\Phi_{\Delta t}$ il flusso dinamico di un
passo. L'operatore di quench $\mathcal{Q}$ e' la composizione di flusso smorzato
e raffreddamento esplicito delle velocita', iterata fino al congelamento:
$$
\mathcal{Q}=\lim_{n\to\infty}\bigl(\,C_\lambda\circ \Phi_{\Delta t}\,\bigr)^{n},
\qquad C_\lambda:\;v_i\mapsto \lambda\,v_i,\;\; 0<\lambda<1 ,
$$
con criterio di arresto sull'energia cinetica
$$T(t)=\tfrac12 m\textstyle\sum_i v_i^2 \;\longrightarrow\; 0
\qquad\bigl(T/T_0<10^{-10}\bigr).$$
La *massa a riposo* di una configurazione e' definita come
$$\boxed{\;M[\chi]\;=\;E_{\Psi}^{\mathrm{anc}}\!\bigl(\mathcal{Q}[\chi]\bigr)\;}$$

### 3.2 Derivazione analitica (perche' e' una proiezione)

Con $\lambda<1$ e nessuna forza esterna, $\mathcal{Q}$ realizza un *gradient flow*
sovrasmorzato verso un minimo locale di $H=T+V+E_{\mathrm{coupling}}$:
$$\frac{d}{dt}H\Big|_{\mathcal{Q}} = -\gamma_{\mathrm{eff}}\sum_i v_i^2 \le 0,
\qquad \mathcal{Q}^2=\mathcal{Q}\ \text{(idempotenza sullo stato congelato)}.$$
L'idempotenza ($\mathcal{Q}$ applicato a uno stato gia' congelato lo lascia
invariato) e' la proprieta' che qualifica $\mathcal{Q}$ come **proiettore**:
dallo spazio degli stati dinamici alla varieta' degli stati fondamentali locali.

**[OSS] Irriducibilita' e bimodalita'.** Su 36 stati L1 quenchati
($T/T_0\to0$ in tutti):
$$M[\chi]\in\{\,\approx 0\,\}\ \cup\ \{\,\approx 1.36\times10^3\,\},$$
con il 67% degli stati nel ramo massivo. La massa non e' eliminabile dal quench
(irriducibile) ed e' **bimodale**: difetto presente o assente, non un continuo.

**[OSS] Selezione dinamica del ramo.** La probabilita' di finire nel ramo massivo
dipende dalla storia: $0\%$ per cammini brevi ($t<40$ step), $100\%$ per cammini
lunghi ($t\ge100$ step) — la transizione e' governata da $t_{\mathrm{freeze}}$ (§2).

### 3.3 Interpretazione verbale

Il quench e' la "procedura di laboratorio" che pesa una configurazione: spegne
ogni agitazione e lascia solo cio' che e' geometricamente inevitabile. Cio' che
resta — la frustrazione che nemmeno il raffreddamento totale puo' sciogliere — e'
la massa a riposo. La bimodalita' dice che questa massa e' *quantizzata in
presenza/assenza*: una particella o c'e' o non c'e'.

### 3.4 Connessione con Kibble–Zurek

$\mathcal{Q}$ e' l'operatore che rende *osservabile* il difetto KZ: proiettando
fuori l'energia cinetica, isola la componente topologica congelata. Il
diagramma completo della genesi della massa nella VQT e':
$$
\underbrace{s\!:\,1\to\sqrt2}_{\text{ingresso regime (geometria)}}
\;\xrightarrow{\;\Delta t_{\mathrm{relax}}\approx 50\;}\;
\underbrace{\text{congelamento}}_{\text{difetto KZ}}
\;\xrightarrow{\;\mathcal{Q}\;}\;
\underbrace{M[\chi]=E_{\Psi}^{\mathrm{anc}}}_{\text{massa a riposo, misurabile}} .
$$

---

## 4. Ipotesi di quantizzazione gerarchica — divisori di $Z_{24}$ come livelli energetici

> **Status epistemico**: [CNG] — congettura motivata da dati preliminari a L2.
> Run di verifica a L3 in corso al momento della stesura (2026-06-03).

### 4.1 Motivazione fisica

Il blocco L1 e' un **ring discreto di 24 nodi** con matrice di accoppiamento
circolante $W$. Ogni matrice circolante su $\mathbb{Z}_{24}$ ha come autovettori
le armoniche di Fourier discrete:
$$\mathbf{v}_m = \bigl(1,\,\omega^m,\,\omega^{2m},\ldots,\omega^{23m}\bigr),
\qquad \omega = e^{2\pi i/24},\quad m=0,1,\ldots,23,$$
con autovalori
$$\lambda_m = \sum_{j=0}^{23} W_{0j}\,\omega^{mj}.$$
Il sistema ha quindi la **simmetria discreta** $Z_{24}$: le rotazioni di $k\cdot
(2\pi/24)$ sul ring lasciano $W$ invariata.

Un kink $\phi^4$ che si estende su $w$ nodi consecutivi del ring e' una
**configurazione coerente** del campo solo se l'onda "entra" nel ring senza
sfasamento residuo — ovvero solo se la larghezza $w$ divide il perimetro $N=24$.
Questa e' la condizione di **commensurabilita'**:
$$w \;\Big|\; 24 \quad\Longleftrightarrow\quad w\in\{1,2,3,4,6,8,12,24\}\,.$$
Larghezze non-divisori generano un termine di mismatch nel potenziale effettivo
e sono dinamicamente instabili: il kink si collassa al divisore piu' vicino.

### 4.2 Generalizzazione gerarchica

**[CNG] Ipotesi Peano–VQT (2026-06-03):** a ogni livello $L$ della gerarchia, il
numero di sotto-blocchi del livello $L-1$ che il kink occupa appartiene all'insieme
$$\mathcal{D}_L \;=\; \{d\in\mathrm{Div}(24)\;:\; d < L\},$$
dove $\mathrm{Div}(24) = \{1,2,3,4,6,8,12,24\}$.

| Livello | $\mathcal{D}_L$ | Modi accessibili |
|---|---|---|
| $L=2$ | $\{1\}$ | 1 solo blocco L1 |
| $L=3$ | $\{1, 2\}$ | 1 o 2 blocchi L2 |
| $L=4$ | $\{1, 2, 3\}$ | 1, 2 o 3 blocchi L3 |
| $L=6$ | $\{1, 2, 3, 4\}$ | aggiunge il modo $d=4$ |
| $L=8$ | $\{1, 2, 3, 4, 6\}$ | aggiunge $d=6$ |
| $L=12$ | $\{1,2,3,4,6,8\}$ | aggiunge $d=8$ |
| $L=24$ | $\{1,2,3,4,6,8,12\}$ | tutti tranne $d=24$ (kink sistema-scala) |

**Perche' $d < L$ e non $d \le L$?** Un kink che occupa esattamente $L$
sotto-blocchi avrebbe dimensione uguale all'intero livello corrente: non e' piu'
un difetto localizzato ma un'eccitazione sistema-scala (analogo di un modo globale
vs un modo locale). Il vincolo $d < L$ garantisce che il kink resti *sub-esteso*.

### 4.3 Analogia con gli orbitali atomici

La struttura e' isomorfa alla quantizzazione degli orbitali idrogeno-simili:

| Atomo | VQT gerarchica |
|---|---|
| Numero quantico principale $n$ | Livello $L$ |
| Numero quantico angolare $\ell=0,\ldots,n-1$ | Larghezza $d\in\mathcal{D}_L$ |
| Vincolo $\ell < n$ | Vincolo $d < L$ |
| Aggiunta di un nuovo $\ell$ a ogni $n$ | Sblocco di un divisore a ogni $L$ |
| Orbitale $s$ (stato fondamentale) | Kink di larghezza 1 (piu' localizzato) |
| Orbitali $p, d, f, \ldots$ (stati eccitati) | Kink piu' larghi |

La differenza chiave: nell'atomo la simmetria e' $O(3)$ continua, qui e' $Z_{24}$
discreta. Conseguenza: non tutti i valori interi $1,2,\ldots,L-1$ sono permessi,
solo quelli che dividono 24.

**Nota sulle rappresentazioni irriducibili.** Per $O(3)$ continuo, ogni livello $n$
ha $n^2$ stati (degenerazione da $-\ell$ a $+\ell$ per ogni $\ell=0,\ldots,n-1$).
Per $Z_{24}$ discreto il conteggio e' diverso: ogni livello $L$ aggiunge 1 nuovo
modo (il divisore piu' grande in $\mathcal{D}_L\setminus\mathcal{D}_{L-1}$, se esiste),
non $2L-1$ modi. Lo spettro e' molto piu' **parsimonioso** di quello atomico: a $L=24$
ci sono al piu' 7 modi, dove l'atomo di idrogeno avrebbe $24^2=576$ stati. Questa
parsimonia e' una firma della struttura discreta vs continua, non un limite della teoria.

### 4.4 Livelli energetici del kink e confronto con la serie di Rydberg

Per un kink di larghezza $w$ su un ring di 24 nodi con coupling nearest-neighbour
$W_{nn}$, il campo passa linearmente da $+\chi_0$ a $-\chi_0$ in $w$ nodi. La
densita' di torsione per nodo nel core del kink e':
$$\rho_{\mathrm{tors}}^{(\mathrm{core})} \approx W_{nn}\left(\frac{2\chi_0}{w}\right)^2,$$
quindi l'energia totale del kink vale:
$$E_{\mathrm{kink}}(w) \approx \frac{1}{2}\,\alpha_K\cdot w \cdot W_{nn}
\cdot \frac{4\chi_0^2}{w^2} = \frac{2\,\alpha_K\,W_{nn}\,\chi_0^2}{w}\,.$$

**[CNG] Spettro previsto** (con $\alpha_K=0.042$, $W_{nn}=0.145$, $\chi_0=50$):

| $w$ | Modo $m=24/w$ | $E_{\mathrm{kink}}(w)$ (unita' sim.) |
|---|---|---|
| 1 | $m=24$ | 30.4 (stato fondamentale) |
| 2 | $m=12$ | 15.2 |
| 3 | $m=8$ | 10.1 |
| 4 | $m=6$ | 7.6 |
| 6 | $m=4$ | 5.1 |
| 8 | $m=3$ | 3.8 |
| 12 | $m=2$ | 2.5 |

**Differenza fondamentale rispetto alla serie di Rydberg/Balmer.**
La serie di Rydberg per l'atomo di idrogeno ha $E_n = -E_R/n^2$ (esponente 2 al
denominatore), che origina dal potenziale coulombiano $V\sim 1/r$ in 3 dimensioni.
Il nostro kink VQT ha $E_{\mathrm{kink}}(w)\sim 1/w$ (esponente 1): e' una
**serie armonica**, non una serie di Rydberg. La differenza viene dalla geometria:
il kink vive su un ring 1D, dove l'energia del gradiente scala come
$(2\chi_0/w)^2 \times w \propto w^{-1}$, non come $w^{-2}$.

Per ottenere $E\sim 1/w^2$ sarebbe necessario un termine di curvatura aggiuntivo
nell'Hamiltoniana del kink (analogo del termine centrifugo $\ell(\ell+1)/r^2$ in
meccanica quantistica 3D). Cio' potrebbe emergere a livelli gerarchici alti, dove
la struttura del reticolo acquista carattere 2D/3D effettivo, ma non e' nel modello
corrente e non puo' essere affermato senza derivazione esplicita. [CNG]

**[OSS] Dato osservato a L2** ($\chi_{\mathrm{mean}}=68$, massima localizzazione):
il kink occupa $n_{\mathrm{eff,block}} = 1.0\text{--}1.1$ blocchi L1 — consistente
con la predizione per il modo fondamentale $w=1$ di $\mathcal{D}_2=\{1\}$.
$M_{\mathrm{tot}}^{\mathrm{oss}} = 30\text{--}475$ (banda larga; lo spettro
osservato non e' ancora abbastanza raffinato da distinguere i livelli di $w$
intra-blocco).

### 4.5 Interpretazione verbale

Il "Muratore di Planck" non sceglie una larghezza arbitraria per i suoi difetti:
la geometria discreta del reticolo $Z_{24}$ gli impone un menu ristretto di
configurazioni coerenti. E' lo stesso principio che governa gli orbitali atomici —
non tutte le orbite sono permesse, solo quelle che "stanno" coerentemente nella
simmetria del sistema. A ogni livello della gerarchia si sblocca un nuovo modo
(un nuovo divisore), esattamente come a ogni shell atomica ($n=1,2,3,\ldots$)
si aggiungono nuovi tipi di orbitale ($s$, poi $p$, poi $d$, ...).

Il kink di larghezza 1 (stato fondamentale) e' il piu' energetico e il piu'
localizzato: la particella "minima". I kink piu' larghi (stati eccitati) hanno
piu' estensione spaziale e meno energia: potrebbero corrispondere a stati
eccitati della materia VQT.

### 4.6 Stato della verifica

**Verificato [OSS]:**
- L2, $\chi_{\mathrm{mean}}=68$: $n_{\mathrm{eff,block}} = 1.0\pm0.1$ per i seed
  con difetto reale ($M_{\mathrm{tot}}>10$). Consistente con $\mathcal{D}_2=\{1\}$.

**In verifica (run overnight 2026-06-03):**
- L3, $\chi_{\mathrm{mean}}=68$, 10 seed: misura di $n_{\mathrm{eff,block\_L2}}$.
  Predizione: $n_{\mathrm{eff}}\in\mathcal{D}_3=\{1,2\}$, mai $\ge3$.
  Script: `experiments/exp3/test_quantizzazione_gerarchica.py`

**Da fare (Task domani):**
- Termodinamica delle pareti (legge KZ: $n_{\mathrm{kink}}\sim|\varepsilon|^\nu$).
- Verifica a L4 e L5 per testare lo sblocco progressivo dei modi.

---

## 5. Sintesi e limiti

**Risultati [OSS] solidi (L1–L2):**
1. Soglia geometrica $\sqrt2$ e massa $E_{\Psi}^{\mathrm{anc}}$ sono osservabili
   distinti (il ginocchio non e' a $\sqrt2$ e migra con la scala).
2. La massa quenchata e' irriducibile e bimodale.
3. La struttura a due tempi ha un ritardo $\Delta t_{\mathrm{relax}}\approx50$
   quasi-invariante di scala L1$\to$L2.

**Aperti [CNG] / da verificare:**
- Scalabilita' a L3 del ritardo e della bimodalita'.
- Legge di scala dei valori assoluti ($t_{\mathrm{cross}},t_{\mathrm{freeze}}$) con $L$.
- Verifica quantitativa della legge KZ ($n_{\mathrm{def}}$ vs tasso di attraversamento).
- Quantizzazione del valore di massa nel ramo massivo (ora banda larga, CV $\approx0.3$).
- Ipotesi di quantizzazione gerarchica (§4): $n_{\mathrm{eff,block}}\in\mathcal{D}_L$,
  verificata a L2, da verificare a L3 (run in corso) e livelli superiori.

**Strumenti di riferimento (codice):**
`compute_geometric_E_psi`, `freeze_and_measure_mass` in `wqt_oop/energy_metrics.py`;
esperimenti in `experiments/exp3/test_quench_mass.py`,
`test_soglia_formazione.py`.
