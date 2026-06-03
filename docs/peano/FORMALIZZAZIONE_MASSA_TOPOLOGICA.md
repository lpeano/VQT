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

## 4. Sintesi e limiti

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

**Strumenti di riferimento (codice):**
`compute_geometric_E_psi`, `freeze_and_measure_mass` in `wqt_oop/energy_metrics.py`;
esperimenti in `experiments/exp3/test_quench_mass.py`,
`test_soglia_formazione.py`.
