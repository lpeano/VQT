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

> **Status epistemico aggiornato 2026-06-04**: [CNG, in gran parte SUPERATA].
> La misura diretta del profilo $\chi$ (sez. 5.2) ha mostrato che il difetto e'
> PUNTUALE (un singolo nodo), non un kink esteso. Quindi NON esiste una "larghezza"
> da quantizzare sui divisori: l'ipotesi e' mal posta nel dominio della larghezza.
> Sopravvive SOLO come $n_{\mathrm{eff,block}}=1$ (il difetto sta in 1 blocco su 24),
> che e' localizzazione gerarchica, non quantizzazione di modi. La sezione sotto e'
> conservata come record del ragionamento; leggere prima la sez. 5.
> [La stesura originale 2026-06-03 ipotizzava un kink esteso, poi falsificato.]

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

### 4.6 Spettroscopia della frustrazione topologica

#### Interpretazione armonica

Lo spettro $E_{\mathrm{kink}}(w)=E_0/w$ e' la serie armonica della frustrazione:
$$E_0,\quad \frac{E_0}{2},\quad \frac{E_0}{3},\quad \frac{E_0}{4},\quad \frac{E_0}{6},\quad \ldots$$
(solo divisori di 24). Questa e' la **serie di risonanza del manifold VQT**: il
modo fondamentale ($w=1$) e' il "tono fondamentale", i modi superiori sono le
armoniche. Il fatto che i modi permessi siano solo i divisori di 24 — non tutti i
numeri interi — rende questa "orchestra" **molto piu' selettiva** di un oscillatore
armonico continuo.

#### Energia di attivazione tra modi

Per transitare dal modo $w_1$ al modo $w_2 > w_1$ (transizione eccitata) e'
necessaria un'energia di attivazione:
$$\Delta E(w_1 \to w_2) = E_0\left(\frac{1}{w_1} - \frac{1}{w_2}\right).$$
Esempi (con $E_0=30.4$):

| Transizione | $\Delta E$ |
|---|---|
| $1\to 2$ (fondamentale $\to$ primo eccitato) | 15.2 |
| $1\to 3$ | 20.2 |
| $2\to 4$ | 7.6 |
| $3\to 6$ | 5.1 |

**[CNG] Predizione:** in un sistema in cui il kink puo' transitare tra modi, si
dovrebbe osservare un rilascio discreto di energia $\Delta E$ durante il passaggio
$w\to w'<w$ (transizione verso il basso = emissione). Questo sarebbe l'analogo
dell'emissione di fotoni in un laser. Non e' stato ancora misurato — richiederebbe
osservare un kink "wide" che si restringe durante il quench rilasciando $\Delta E$
in forma di impulso di torsione. [Da misurare]

#### Legame con M_tot e predizione per l'istogramma

**[CNG] Predizione spettrale:** se il kink puo' essere in modo $w\in\mathcal{D}_L$
con probabilita' $p_w$, allora la distribuzione di $M_{\mathrm{tot}}$ su molti seed
dovrebbe mostrare picchi localizzati attorno a $E_{\mathrm{kink}}(w)$ per i
divisori permessi. L'istogramma sarebbe la "spettroscopia" del kink: ogni picco
e' una riga spettrale del modo $w$.

Questa predizione e' verificabile con 100+ seed a $\chi_{\mathrm{mean}}=68$
(dove i kink sono nel modo fondamentale $w=1$ con $M_{\mathrm{tot}}\approx E_0\sim30$).
Se a $\chi_{\mathrm{mean}}$ piu' alto si eccitano modi $w=2,3$, i picchi si
sposteranno verso valori piu' bassi di $M_{\mathrm{tot}}$.

#### Connessione con il costo informazionale (Landauer)

**[CNG — richiede derivazione]** Il principio di Landauer stabilisce che
cancellare 1 bit costa $k_B T \ln 2$ di energia. In un sistema a temperatura
finita, "scegliere" un modo (stabilizzare un kink in $w=1$ vs $w=2$) e'
equivalente a scrivere 1 bit di informazione geometrica nel manifold. L'energia
del modo $E_0/w$ potrebbe quindi essere interpretata come il "costo di Landauer"
per immagazzinare $\log_2(w)$ bit di struttura spaziale. Questa connessione e'
intuitiva ma non derivata formalmente: richiederebbe identificare esplicitamente
l'entropia di configurazione associata a ciascun modo. [Da formalizzare]

### 4.7 Stato della verifica

**Verificato [OSS]:**
- L2, $\chi_{\mathrm{mean}}=68$: $n_{\mathrm{eff,block}} = 1.0\pm0.1$ per i seed
  con difetto reale ($M_{\mathrm{tot}}>10$). Consistente con $\mathcal{D}_2=\{1\}$.

**[OSS] L3 — verdetto (2026-06-04):**
- L3, $\chi_{\mathrm{mean}}=68$, 10 seed: $n_{\mathrm{eff,block\_L2}} = 12.1\pm2.9$
  (range 7-18). Predizione $\{1,2\}$ FALSIFICATA nel regime $\chi_{\mathrm{mean}}=68$.

  **Motivo fisico**: a $\chi_{\mathrm{mean}}=68$ ciascuno dei 24 blocchi L2
  del sistema L3 nucleata un kink con probabilita' $\approx50\%$ (dalla misura
  di riproducibilita' a L2: 6/15 seed con $M_{\mathrm{tot}}>1$). Il risultato e'
  $24\times0.5\approx12$ kink indipendenti distribuiti nei blocchi L2 — non un
  super-kink coerente di L3. L'ipotesi descrive il **regime diluito** (1 solo
  kink per sistema), non il regime denso (kink multipli e indipendenti).

  **Come testare a L3 nel regime corretto**: usare $\chi_{\mathrm{mean}}\ll68$
  tale che la probabilita' di nucleazione per blocco L2 sia $\ll50\%$, in modo
  da osservare $0$ o $1$ kink sull'intero sistema L3. In quel regime la predizione
  $\mathcal{D}_3=\{1,2\}$ sarebbe ancora verificabile. [Da fare]
  Predizione: $n_{\mathrm{eff}}\in\mathcal{D}_3=\{1,2\}$, mai $\ge3$.
  Script: `experiments/exp3/test_quantizzazione_gerarchica.py`

**Da fare (Task domani):**
- Termodinamica delle pareti (legge KZ: $n_{\mathrm{kink}}\sim|\varepsilon|^\nu$).
- Verifica a L4 e L5 per testare lo sblocco progressivo dei modi.

---

## 5. Risultati 2026-06-04: scala finita, difetto puntuale, densita' di difetti

Sessione di verifica rigorosa. Tre risultati solidi e diverse falsificazioni.

### 5.1 Scaling della soglia critica con N (effetto di scala finita) — [OSS, 2 livelli]

La soglia di nucleazione della materia (frazione di sistemi che congelano un
difetto con $M_{\mathrm{tot}}>1$) e' una curva sigmoide in $\chi_{\mathrm{mean}}$.
Fit logistico $P=\bigl(1+e^{-(\chi-\chi_c)/w}\bigr)^{-1}$:
$$\frac{\chi_c^{L2}}{\chi_0}=1.338\pm0.004,\qquad \frac{\chi_c^{L3}}{\chi_0}=1.240\pm0.008.$$
La soglia **scende del 7.4%** da L2 (576 nodi) a L3 (13824 nodi): differenza
$\sim10\times$ le barre d'errore. **$\chi_c$ NON e' invariante di scala**: il sistema
piu' grande nuclea a soglia piu' bassa (piu' modi disponibili per il difetto). E'
un effetto di scala finita standard, senza contenuto esotico.
La FORMA (larghezza normalizzata $w/\chi_c$) e' COMPATIBILE tra L2 e L3
($0.0202\pm0.0025$ vs $0.0176\pm0.0063$) ma con incertezza alta: l'universalita'
di forma e' [CNG], non certificata (servono $\sim$50 seed/punto).

### 5.2 Il difetto e' PUNTUALE (single-site) — [OSS]

Misura diretta del profilo $\chi$ sui blocchi congelati ($\chi_{\mathrm{mean}}=68$,
max localizzazione, L2, 20 seed): in ogni kink **un solo nodo** (mediana 1, range
0–1 su 576) si e' deviato dal pozzo dominante; gli altri restano a $+\chi_0$.
Profili tipici: $[+\chi_0\times23,\ \text{un nodo a }-48]$ oppure
$[\text{un nodo depresso},\ +\chi_0\times23]$.

**La materia VQT alla soglia di nucleazione e' un singolo voxel** ribaltato (nel
pozzo opposto) o depresso (sulla barriera) — la perturbazione minima del reticolo.

**Correzione** dell'interpretazione "kink $\phi^4$ esteso" (biopsia 2026-06-03):
i "$\sim$6 nodi" non erano la larghezza del difetto ma la ZONA DI TORSIONE
($\rho_{\mathrm{tors}}$ alto sui $\sim$5 vicini del nodo deviato, per il salto
$-48\to+50$). $\langle\chi\rangle_{\mathrm{hot}}\approx34$ era la media
[nodo deviato + vicini a $+\chi_0$]. Il difetto vero e' 1 nodo, non 6.
Conseguenza: la quantizzazione della larghezza sui divisori (sez. 4) e' mal posta
— non c'e' larghezza ne' pacchetto di modi (1 nodo $\Rightarrow$ spettro piatto).

### 5.3 La materia come densita' di difetti puntuali — [OSS forma, CNG esponente]

Conteggio $n_{\mathrm{def}}(\chi_{\mathrm{mean}})$ = nodi deviati dal pozzo
($|\chi-\chi_{\mathrm{pozzo}}|>0.6\,\chi_0$), L2, 10 seed/punto:
$$n_{\mathrm{def}}:\ 0\ (\chi/\chi_0<1.34)\ \to\ 0.4\ \to\ 2.4\ \to\ 9.2\ \to\ 33\ \to\ 80\ \to\ 131\ \to\ 175\ (\chi=90).$$
Crescita **super-lineare** dal vuoto al plasma ($175/576\approx30\%$ dei nodi).
Tre regimi: vuoto $\to$ nucleazione diluita di difetti puntuali $\to$ crescita
verso plasma.

**Esponente NON determinato** [CNG]. Il fit $n_{\mathrm{def}}\sim(\chi-\chi_c)^p$
e' degenere: $p$ e $\chi_c$ anti-correlati ($\mathrm{corr}=-0.94$). Con $\chi_c$
fisso a 66.92: $p=2.23$; con $\chi_c$ libero: $\chi_c=71.68,\ p=1.46$. Escludendo
i punti plasma (che saturano per taglia finita) e fissando $\chi_c$ dalla nucleazione
binaria, $p$ scende verso $\sim1.6$–$1.7$ ma con soli 3 punti critici. La legge di
potenza critica vale solo per $\varepsilon\to0$ (vicino soglia); i punti plasma
gonfiano la pendenza. Per misurare $p$ serve sweep fitto solo-critico + $\sim$30-50
seed (in corso al momento della stesura).

**NB: nessuna "doppia soglia"** — il $\chi_c\approx72$ del fit libero e' non-fisico
(predirebbe 0 difetti dove ce ne sono gia'). Una sola soglia ($\sim67$), poi crescita.

### 5.4 Falsificazioni della sessione (risultati negativi di valore)

- **SOC** (criticalita' auto-organizzata): la "legge di potenza" di $\rho_{\mathrm{tors}}$
  era un artefatto di pooling di seed eterogenei. Falsificata.
- **Doppia transizione geometrica/energetica** (V5): la "soglia geometrica" e' un
  fondo di fluttuazioni fredde ($M_{\mathrm{tot}}\sim10^{-7}$). Una sola transizione.
- **Quantizzazione della larghezza** (V4): il difetto e' puntuale, no larghezza.
- **Esponente di densita' $\sim2.2$**: artefatto del $\chi_c$ fissato; degenere.

### 5.5 Nota metodologica: non-determinismo del motore

Il motore usa `np.random` globale non seedato in `_transfer_heat_to_children`
(riscaldamento gerarchico) $\Rightarrow$ il sistema e' stocastico run-to-run.
Le conclusioni aggregate (medie d'ensemble) restano valide — il rumore termico e'
parte del modello — ma il singolo seed non identifica una realizzazione e le barre
d'errore sono leggermente piu' larghe del nominale. Fix: seeding deterministico
per-task (rende i run riproducibili e il parallelo identico al seriale, GATE PASS).

---

## 6. Sintesi e limiti

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

---

## 7. [CNG] Parametro d'ordine complesso a livello di cluster — la massa come difetto topologico di psi

> **Status**: congettura strutturale, TEST FONDAMENTALE DA ESEGUIRE *DOPO* L4
> (serve il flusso RG calibrato su L2/L3/L4 e i campi congelati con difetti reali).
> Origine: discussione 2026-06-05 "il voxel e' un qubit alpha|0>+beta|1>?".

### 7.1 Dal voxel al cluster: cosa cambia

**[OSS/DEF] Singolo voxel = pseudo-spin classica REALE.** Lo stato del voxel L0 e'
$(\chi, v)\in\mathbb{R}^2$ (classico: niente spazio di Hilbert, niente sovrapposizione,
niente unitarieta'). I due pozzi $\pm\chi_0$ danno una struttura a due livelli con
ampiezza $s=\tanh(\chi/\chi_0)\in[-1,+1]$ (gia' nel coupling del motore). NON e' un
qubit quantistico; $\alpha,\beta$ complessi NON sono nel modello. E $\beta/\alpha$ NON
e' "la pendenza del kink": la pendenza e' una grandezza INTER-voxel (la torsione sugli
spigoli $\rho^{\mathrm{tors}}_i=\sum_j W_{ij}(\chi_i-\chi_j)^2$), non intra-voxel.
Confermato dal difetto PUNTUALE misurato (sez. 5.2): dentro un voxel non c'e' pendenza
da codificare.

**[CNG] Cluster = parametro d'ordine COMPLESSO (Ginzburg-Landau).** A livello di
blocco la visione a due livelli regge MEGLIO, ma si trasforma. L'oggetto fedele e':
$$\psi_B = m_B\,e^{i\phi_B},\qquad
  m_B=\langle\tanh(\chi/\chi_0)\rangle_{\text{blocco}},\quad
  \phi_B=\text{fase del modo collettivo }(f_{\mathrm{dom}}).$$
E' un campo CLASSICO complesso (il potenziale del motore E' Landau-Ginzburg,
$V=\beta(\chi^2-\chi_0^2)^2$), NON un qubit: $\alpha,\beta$ come ampiezza d'ORDINE, non
di probabilita'. Il modo collettivo coerente $m_B$ coincide con la media di blocco
$\bar\chi_B$ = la variabile RG del block-spin (TEO 2 in
`basimatematiche/teorema_peano_vqt.md`).

### 7.2 Perche' la massa NON sta nella macro-spin (di nuovo il TEO 2)

La macro-spin $\bar\chi_B$ cattura il modo collettivo "quale pozzo" e BUTTA VIA la
struttura interna. Ma la massa vive proprio nella struttura interna (il voxel girato,
la torsione). E' il contenuto del TEO 2: $\bar\chi_B$ si chiude sotto il coupling, ma
il termine non lineare $\Delta_B\sim\mathrm{Var}_B(\chi)$ (le fluttuazioni interne =
i difetti) NON si chiude. Quindi:

> La visione a due livelli sul cluster regge per la parte SENZA massa (modo collettivo
> coerente) e fallisce per la parte CON massa (i difetti interni).

Il linguaggio GL recupera la massa nel modo giusto: in un parametro d'ordine complesso
i difetti sono DIFETTI TOPOLOGICI di $\psi$ — un avvolgimento della fase (winding
number) e un crollo del modulo $|\psi|$ nel core, dove si concentra l'energia. Cioe'
la massa riappare come difetto topologico del campo d'ordine = la tesi centrale di
questo documento ("massa come difetto topologico congelato"). Il difetto puntuale
misurato (sez. 5.2) sarebbe il core di questo difetto.

### 7.3 IL TEST FONDAMENTALE (da eseguire DOPO L4)

**Ipotesi falsificabile**: attorno a un difetto, la fase $\phi_B$ del parametro
d'ordine fa un avvolgimento INTERO $2\pi n$ (winding number $n$ quantizzato), e il
modulo $|\psi|$ crolla nel core.

**Protocollo** (sul campo CONGELATO di un quench con difetto reale, $M_{\mathrm{tot}}>1$):
1. Costruire $\psi_B$ per ogni blocco L1: $m_B=\langle\tanh(\chi/\chi_0)\rangle$, e
   $\phi_B$ dalla fase del modo collettivo. NB: la definizione operativa di $\phi_B$
   (fase dell'oscillazione dominante, o angolo in $(\bar\chi,\dot{\bar\chi})$, o
   componente spettrale $f_{\mathrm{dom}}$) e' essa stessa da fissare e verificare —
   e' il primo sotto-task.
2. Calcolare il winding di $\phi_B$ lungo un cammino chiuso attorno al blocco
   difettoso: $n=\frac{1}{2\pi}\oint \Delta\phi_B$.
3. Verificare: $|\psi|$ crolla nel core? $n$ e' intero e stabile su piu' seed?

**Predizioni e conseguenze**:
- Se $n$ e' intero quantizzato $\to$ la massa e' una CARICA TOPOLOGICA quantizzata.
  Qui SI' che la "legge dei divisori di 24" potrebbe avere senso, ma nel DOMINIO
  GIUSTO: un CONTEGGIO (il winding / il numero di difetti), non sulle energie (che
  sono continue ed estensive $\sim N$: cercarci i divisori e' numerologia, vedi gotcha
  in CLAUDE.md).
- Se non c'e' winding (solo dip di $|\psi|$ senza avvolgimento di fase) $\to$ il
  difetto e' uno "scalare" (vacancy/instanton), non un vortice. Anche questo e' un
  risultato.

**Cosa abbiamo gia' e cosa manca**:
- [OSS] Misurato: difetti PUNTUALI e torsione sugli spigoli (sez. 5).
- [manca] Mai misurato un winding di fase. "Difetto = vortice di $\psi$" e'
  interpretazione, NON fatto. Questo test lo decide.

**Perche' DOPO L4**: (a) serve la mappa RG calibrata (L2/L3/L4 con P1) per sapere se la
struttura del cluster e' scale-stabile prima di attribuirle una carica topologica;
(b) servono campi congelati a L3/L4 con difetti ben localizzati per avere un "loop"
attorno al core con abbastanza blocchi. Si aggancia al punto P5 di
`METODO_SCALING_RG.md` (RG-covarianza della triade + c-function): il winding sarebbe un
invariante topologico candidato a sopravvivere al coarse-graining.
