# Teorema di Induzione Peano-VQT — Rifattorizzazione rigorosa

**Rifattorizzato**: 2026-06-05 · **Versione originale (2026-05-28)**: Appendice A (conservata integralmente)

---

## Avvertenza epistemica (leggere prima)

La versione 2026-05-28 (Appendice A) aveva la *forma* di una dimostrazione (assiomi,
induzione, Q.E.D., limiti) ma non il *contenuto*: il passo induttivo era circolare,
la chiusura tautologica, il limite asintotico mal posto (su una funzione mai definita),
e c'era un'incoerenza tipologica ($\tau\in\mathbb{R}$ vs $\tau \bmod 2\pi$). Vedi la
tabella di riconciliazione in §6.

Questa rifattorizzazione **conserva i quattro temi** dell'originale (induzione sui
livelli, chiusura topologica, massa come torsione integrata, comportamento asintotico)
ma riclassifica ciascuno al suo posto logico. Ogni affermazione e' marcata:

- **[DEF]** Definizione (vera per costruzione).
- **[ASS]** Assunzione strutturale del modello (proprieta' verificabile nel codice/geometria).
- **[TEO]** Teorema (dimostrato qui, con dimostrazione esplicita).
- **[OSS]** Osservazione empirica (misurata, con dominio e incertezza).
- **[CNG]** Congettura falsificabile (non dimostrata; si propone il test).

Principio guida: **non si chiama "teorema" cio' che non e' dimostrato**. Cio' che e'
solido viene dimostrato; cio' che e' un'ipotesi viene enunciato come congettura
falsificabile con il suo protocollo di verifica.

---

## 0. Notazione (coerente con FORMALIZZAZIONE_MASSA_TOPOLOGICA.md)

| Simbolo | Significato |
|---|---|
| $\mathcal{K}$ | complesso cellulare gerarchico (il manifold) |
| $L\in\mathbb{N}$ | livello della gerarchia; $N=24^L$ nodi foglia |
| $\chi_i$ | campo scalare (parametro d'ordine) sul nodo $i$ |
| $\chi_0$ | valore di vuoto, $\chi_0=50$ |
| $v_i=\dot\chi_i$ | velocita' coniugata |
| $W_{ij}$ | accoppiamento, simmetrico, circolante su $\mathbb{Z}_{24}$, $W_{ij}\ge 0$ |
| $L_{\mathrm{graph}}=D-W$ | Laplaciano di grafo, $D_{ii}=\sum_j W_{ij}$ |
| $\alpha_K$ | costante di accoppiamento di torsione |
| $\beta$ | profondita' del doppio pozzo |

Potenziale e moto (sistema aperto, smorzamento $\gamma$, gia' nel repo):
$$V(\chi)=\beta(\chi^2-\chi_0^2)^2,\qquad
m\,\ddot\chi_i=\underbrace{-V'(\chi_i)}_{F_i^{V}}\;\underbrace{-\,\alpha_K(L_{\mathrm{graph}}\chi)_i}_{F_i^{\mathrm{cpl}}}\;\underbrace{-\,\gamma\dot\chi_i}_{F_i^{\mathrm{diss}}}.$$

---

## 1. Definizioni

**[DEF 1.1] Operatore di media di blocco (coarse-graining RG).** Per un blocco
$B\subset\mathcal{K}$ (es. i 24 figli di un nodo) si definisce la media
$$\bar\chi_B=\frac{1}{|B|}\sum_{i\in B}\chi_i .$$
Questa e' la variabile del livello superiore: la gerarchia VQT identifica il nodo
genitore con $\bar\chi_B$ del blocco dei figli (block-spin di Kadanoff).

**[DEF 1.2] Torsione orientata.** A ogni spigolo orientato $e=(a\!\to\! b)$ si
associa una torsione $\tau(e)\in\mathbb{R}$ **antisimmetrica**:
$$\tau(b\!\to\! a)=-\tau(a\!\to\! b).$$
(Questo risolve l'incoerenza dell'originale: $\tau$ e' un flusso reale orientato,
non un angolo mod $2\pi$. Una eventuale olonomia angolare e' un oggetto separato.)

**[DEF 1.3] Massa topologica (postulato del modello).** La massa associata a un
difetto e' la circolazione della torsione attorno al difetto,
$$m\ \propto\ \oint_{\partial S}\tau\,ds .$$
E' un **postulato interpretativo** (l'ipotesi centrale della VQT), non un teorema:
qui e' input, non output. Coerente con $M[\chi]=E_\Psi^{\mathrm{anc}}(\mathcal{Q}[\chi])$
di FORMALIZZAZIONE_MASSA_TOPOLOGICA.md §3.

**[DEF 1.4] Difetto di chiusura $\Psi_L$.** Si definisce $\Psi_L$ come l'energia di
frustrazione residua per grado di liberta' allo stato congelato del livello $L$:
$$\Psi_L=\frac{1}{N_{\mathrm{dof}}}\,E_\Psi^{\mathrm{anc}}\!\bigl(\mathcal{Q}[\chi^{(L)}]\bigr),
\qquad N_{\mathrm{dof}}=2\cdot 24^L .$$
("Chiusura perfetta" $\equiv \Psi_L=0$.) A differenza dell'originale, $\Psi_L$ e'
ora un numero misurabile, non un simbolo.

**[DEF 1.5] Densita' di vincoli.** $\displaystyle \Gamma_L=\frac{N_c(L)}{N_{\mathrm{dof}}(L)}$,
con $N_c(L)$ = numero di vincoli di chiusura indipendenti al livello $L$.

**[DEF 1.6] Potenziale di violazione asintotico.** $\displaystyle
U_L=\frac{1}{N_{\mathrm{dof}}}\sum_i \rho^{\mathrm{tors}}_i\Big|_{\text{stato congelato}}$
(densita' media di torsione residua per dof). Definisce in modo ben posto il limite
$L\to\infty$ che l'originale lasciava su una $U_L$ mai definita.

---

## 2. Assunzioni strutturali (verificabili)

**[ASS 2.1] Coupling Laplaciano.** $W$ e' simmetrica con $W_{ij}\ge0$, quindi
$L_{\mathrm{graph}}=D-W$ e' un Laplaciano di grafo: ha somme di riga nulle,
$$\sum_j (L_{\mathrm{graph}})_{ij}=0\quad\Rightarrow\quad L_{\mathrm{graph}}\mathbf{1}=0,\;\;\mathbf{1}^\top L_{\mathrm{graph}}=0.$$
(Verificabile direttamente nella matrice del codice.)

**[ASS 2.2] Dinamica simplettica + sink aperto.** La parte conservativa
($V+$coupling) e' Hamiltoniana; smorzamento $\gamma$ e drain $E_\chi\!\to\!E_\Psi$
rendono il sistema **aperto**.

**[ASS 2.3] Regola di drain.** A ogni drain, $(E_\chi,E_{RX},E_\Psi)\mapsto
(E_\chi-\delta,\,E_{RX},\,E_\Psi+\delta)$ con $0\le\delta\le\tfrac12|E_\chi|$.

**[ASS 2.4] Coupling inter-blocco mean-field (esatto).** Il coupling tra blocchi
dipende solo dalle medie $\bar\chi_B$ dei blocchi (nel codice, il figlio di un nodo
restituisce la media delle foglie). Quindi la chiusura della gerarchia al livello
del coupling e' esatta, non approssimata.

---

## 3. Teoremi (cio' che si dimostra davvero)

### [TEO 1] Il coupling e' una forza interna (terza legge di Newton)

$$\boxed{\ \sum_i F_i^{\mathrm{cpl}}=0\ }$$

**Dim.** $E_{\mathrm{cpl}}=\tfrac{\alpha_K}{2}\sum_{i,j}W_{ij}(\chi_i-\chi_j)^2$.
Per la simmetria di $W$,
$F_i^{\mathrm{cpl}}=-\partial_{\chi_i}E_{\mathrm{cpl}}=-\alpha_K\sum_j W_{ij}(\chi_i-\chi_j)=-\alpha_K(L_{\mathrm{graph}}\chi)_i$.
Sommando su $i$ e usando $\mathbf{1}^\top L_{\mathrm{graph}}=0$ (ASS 2.1):
$\sum_i F_i^{\mathrm{cpl}}=-\alpha_K\,\mathbf{1}^\top L_{\mathrm{graph}}\,\chi=0$.
Equivalentemente, $\sum_{i,j}W_{ij}(\chi_i-\chi_j)=0$ per antisimmetria del fattore
$(\chi_i-\chi_j)$ sotto scambio $i\leftrightarrow j$. $\blacksquare$

**Contenuto fisico.** Il momento totale del campo $P=m\sum_i v_i$ puo' cambiare solo
per il potenziale on-site e lo smorzamento: **il coupling, da solo, non puo' spostare
il baricentro del campo**. E' la conservazione esatta che l'originale §3 voleva, qui
dimostrata invece che assunta.

### [TEO 2] Chiusura della media di blocco — fondamento rigoroso della gerarchia/RG

> La media di blocco e' **insensibile** al coupling intra-blocco. La sua dinamica e'
> guidata solo dal potenziale on-site, dal coupling inter-blocco e dalla dissipazione.

**Dim.** Decomponi $F_i=F_i^{V}+F_i^{\mathrm{cpl,intra}}+F_i^{\mathrm{cpl,inter}}+F_i^{\mathrm{diss}}$.
Il coupling intra-blocco ristretto a $B$ e' governato dal sotto-Laplaciano $L_B$, che
ha anch'esso somme di riga nulle su $B$. Per TEO 1 applicato a $B$:
$\sum_{i\in B}F_i^{\mathrm{cpl,intra}}=-\alpha_K\sum_{i\in B}(L_B\chi)_i=0$. Quindi
$$|B|\,\ddot{\bar\chi}_B=\sum_{i\in B}F_i=\sum_{i\in B}F_i^{V}+\sum_{i\in B}F_i^{\mathrm{cpl,inter}}+\sum_{i\in B}F_i^{\mathrm{diss}}. \qquad\blacksquare$$

**Perche' e' importante (e dove vive l'emergenza).** TEO 2 e' la giustificazione
rigorosa del block-spin: il genitore $\bar\chi_B$ e' la variabile coarse-grained
corretta. **Ma la chiusura e' esatta solo per il termine lineare (coupling).** Il
termine on-site e' non-lineare e **non** si chiude:
$$\sum_{i\in B}V'(\chi_i)\ \ne\ |B|\,V'(\bar\chi_B)\quad\text{(salvo fluttuazioni nulle).}$$
Lo scarto e'
$$\Delta_B \;=\;\sum_{i\in B}V'(\chi_i)\;-\;|B|\,V'(\bar\chi_B)\;=\;|B|\cdot\tfrac12 V'''(\bar\chi_B)\,\mathrm{Var}_B(\chi)+\dots$$
cioe' dipende dalla **varianza (e momenti superiori) del campo dentro il blocco**.
**Questo termine e' esattamente cio' che la trasformazione RG deve tracciare livello
per livello**: il suo crescere o decrescere con $L$ E' la questione dell'emergenza
("more is different"). TEO 2 quindi non elimina l'emergenza: ne **isola con precisione
il luogo matematico** ($\Delta_B$, la feedback delle fluttuazioni intra-blocco).

### [TEO 3] Flusso di torsione orientato identicamente nullo (chiusura onesta)

$$\boxed{\ \Phi=\sum_{e\ \mathrm{orientati}}\tau(e)=0\ }$$

**Dim.** Per l'antisimmetria (DEF 1.2), raggruppando per spigolo non orientato:
$\Phi=\sum_{\{a,b\}}\bigl[\tau(a\!\to\!b)+\tau(b\!\to\!a)\bigr]=\sum_{\{a,b\}}0=0$. $\blacksquare$

**Contenuto fisico (vs originale).** La chiusura del flusso netto **non** richiede di
assumere "il Cosmo e' isolato": e' una conseguenza dell'antisimmetria, valida per
**ogni** configurazione. La domanda non banale — lo *sbilancio per regione* si annulla?
— e' il difetto di chiusura $\Psi_L$, trattato come congettura (CNG B), non come fatto.

### [TEO 4] Bilancio dell'energia aumentata e monotonia di $E_\Psi$

Sotto la regola di drain (ASS 2.3):
$$ (E_\chi+E_{RX}+E_\Psi)\ \text{invariante},\qquad E_\Psi\ \text{non-decrescente}. $$

**Dim.** $(E_\chi-\delta)+E_{RX}+(E_\Psi+\delta)=E_\chi+E_{RX}+E_\Psi$; e $\delta\ge0$
da' $\Delta E_\Psi\ge0$. $\blacksquare$ (Verificato: `test_peano_integration.py`,
$|\Delta|<10^{-10}$.)

**Framing onesto.** E' un **lemma sullo schema numerico**: certifica che la
contabilita' energetica del sistema **aperto** non perde nulla e che il sink e'
irreversibile *per costruzione*. **Non** e' una legge di conservazione di un sistema
chiuso, e **non** predice l'irreversibilita': l'irreversibilita' e' input (il vincolo
$\delta\ge0$). Distinzione cruciale rispetto all'originale, che la presentava come
scoperta.

### [TEO 5] Conservazione del volume di fase (parte conservativa)

Il flusso conservativo ($H=T+V+E_{\mathrm{cpl}}$, senza $\gamma$ e drain) integrato
con schema simplettico (Stormer-Verlet / Forest-Ruth) **preserva esattamente la
misura di Liouville**.

**Dim.** Standard (Hairer-Lubich-Wanner, *Geometric Numerical Integration*): una mappa
simplettica ha Jacobiano a determinante 1. $\blacksquare$ (Verifica empirica:
equivalenza a RK45 con $\mathrm{err}_{\mathrm{std}}=1.1\times10^{-7}$, repo
SPECTRAL_METHODS.md.) Conseguenza: la parte conservativa non introduce attrattori
spuri; ogni dissipazione e' quella fisica di $\gamma$ e del drain.

---

## 4. Congetture (falsificabili, con test)

Qui confluiscono i contenuti dell'originale che **non** sono teoremi ma ipotesi
legittime. Ciascuna e' resa precisa e misurabile.

### [CNG A] Invarianza della densita' di vincoli = punto fisso RG
*(era l'Assioma 3 originale)*

$$\Gamma_L\ \xrightarrow[L\to\infty]{}\ \Gamma^\star\quad(\text{o }\Gamma_L\ \text{costante}).$$
Equivale a dire che $\Gamma$ e' una coordinata **fissa** della mappa RG. **Test
diretto**: misurare $\Gamma_{L2},\Gamma_{L3},\Gamma_{L4}$. Costante entro le barre
$\Rightarrow$ invariante (supporto forte alla scale-invarianza); deriva
$\Rightarrow$ se ne misura il flusso. E' l'ipotesi piu' preziosa dell'originale.

### [CNG B] Stabilita' della chiusura $\Psi_L\to0$
*(sostituisce la finta induzione del §2 originale)*

$$\text{Congettura: sotto coarse-graining}\quad \Psi_{L+1}\le\Psi_L\ \Rightarrow\ \Psi_L\to\Psi^\star\ (\text{idealmente }0).$$

**Lemma di capacita' (cio' che chiuderebbe davvero l'induzione).** Definiti
$$\mathrm{gen}_L=\text{torsione in eccesso prodotta dalla proiezione } L\to L+1,\qquad
\mathrm{abs}_L=\text{torsione massima assorbibile (massa + scarico geometrico)},$$
**SE** $\mathrm{abs}_L\ge\mathrm{gen}_L\ \forall L$, **ALLORA** $\Psi_{L+1}\le\Psi_L$
e l'induzione si chiude. L'originale **assumeva** che il "Meccanismo di Reset" lo
garantisse (circolarita'); qui la garanzia e' isolata in una **disuguaglianza
esplicita e misurabile**. **Test**: stimare $\mathrm{gen}_L$ e $\mathrm{abs}_L$ a
L2, L3, L4 e verificare il segno di $\Psi_{L+1}-\Psi_L$. Finche' la disuguaglianza
non e' dimostrata o misurata, $\forall L\,\Psi_L=0$ resta **congettura, non teorema**.

### [CNG C] Saturazione asintotica e inversione di fase
*(era il §4 originale, "Phase Flip")*

Con $U_L$ ora ben definito (DEF 1.6): $\displaystyle\lim_{L\to\infty}U_L=U^\star$
(possibilmente $0$) e' una congettura **ben posta** (prima era su una funzione
inesistente). L'**inversione di fase / de-iterazione ciclica** ("ritorno alla fonte")
e' una **congettura cosmologica interpretativa**, esplicitamente **non derivabile**
dal modello corrente e **non testata**: si conserva come scenario, marcata come
speculazione, senza Q.E.D.

---

## 5. Connessione con il programma RG

Le congetture A, B, C non sono vicoli ciechi: sono esattamente i bersagli del piano
operativo in [../docs/peano/METODO_SCALING_RG.md](../docs/peano/METODO_SCALING_RG.md):
- **CNG A** $\to$ punto P2 (fit FSS di $\Gamma_L$) e P4 (predetto vs misurato).
- **CNG B** $\to$ punti P1 (misura $\Psi_L$ su L2-L4) e P3 (mappa RG + consistenza).
- **TEO 2** $\to$ fondamento del punto P5: la triade e' RG-covariante? Il termine
  $\Delta_B$ (feedback delle fluttuazioni) e' il candidato naturale a "c-function" di
  scala. L'emergenza, se c'e', si manifesta nel flusso di $\Delta_B$ con $L$.

Cioe': il teorema rifattorizzato **non chiude** la questione multi-livello per decreto
(come pretendeva l'originale), ma fornisce (a) i teoremi che reggono il ponte
gerarchico (TEO 1-2), (b) le congetture giuste, rese falsificabili, e (c) il luogo
matematico esatto dove l'estrapolazione puo' fallire ($\Delta_B$).

---

## 6. Riconciliazione con l'originale (cosa e' cambiato e perche')

| Claim originale (2026-05-28) | Difetto | Status corretto |
|---|---|---|
| Assioma 2: $\tau=0\bmod 2\pi$, $\tau\in\mathbb{R}$ | incoerenza tipologica | DEF 1.2: torsione reale antisimmetrica |
| Assioma 2: $m\propto\oint\tau\,ds$ | "dimostra" la massa, ma la assume | DEF 1.3: postulato del modello (input) |
| Assioma 3: curva di Peano governa $L\!\to\!L\!+\!1$ | mappa mai definita | CNG A: invarianza di $\Gamma$ (testabile) |
| §2 Induzione $\forall L\,\Psi_L=0$, Q.E.D. | circolare (Reset assume la tesi) | CNG B + lemma di capacita' esplicito |
| §3 Chiusura, Q.E.D. | tautologica (assume isolamento) | TEO 3: nullo per antisimmetria (onesto) |
| §4 $\lim U_L=0$, Q.E.D. | $U_L$ mai definita | DEF 1.6 + CNG C (ben posta, non provata) |
| §4 Phase Flip | narrazione cosmologica | CNG C: speculazione esplicita, no Q.E.D. |
| (assente) | — | TEO 1, TEO 2, TEO 4, TEO 5: i teoremi veri |

**In sintesi**: l'originale aveva 3 Q.E.D. non guadagnati e 0 teoremi reali. La
rifattorizzazione ha 5 teoremi dimostrati, 3 congetture falsificabili, 0 Q.E.D.
abusivi. I quattro temi sopravvivono tutti, ciascuno al proprio livello di rigore.

---
---

# Appendice A — Enunciato originale (2026-05-28), conservato integralmente

> Conservato come record storico del ragionamento. I difetti logici sono analizzati
> in §6. Non rappresenta lo stato corrente della formalizzazione.

## Documento: Teorema di Induzione Peano-VQT
### Dimostrazione Totale della Dinamica, Stabilita' e Chiusura Ciclica

### 1. Definizione Assiomatica
Sia $\mathcal{K}$ il complesso cellulare dinamico rappresentante il Cosmo come manifold vivente.
- **Assioma 1 (Operatore $\tau$):** Ad ogni cella $\mathcal{C}\in\mathcal{K}$ e' associata una torsione discreta $\tau\in\mathbb{R}$.
- **Assioma 2 (Invarianza Ciclica):** Il sistema e' in equilibrio dinamico se $\sum_{\mathcal{C}}\tau(\mathcal{C})=0\pmod{2\pi}$. La torsione eccedente viene convertita tramite intrecci topologici in massa ($m\propto\oint\tau\,ds$), fungendo da memoria del bilancio energetico.
- **Assioma 3 (Proiezione Frattale):** L'espansione $L\to L+1$ e' governata dalla curva di Peano, garantendo la conservazione della densita' di vincoli $\Gamma=\frac{N_c}{N_{dof}}$.

### 2. Dimostrazione per Induzione (Stabilita' e Autocompensazione)
**Enunciato:** $\forall L\in\mathbb{N},\ \Psi_L=0$.
- **Base ($L=1$):** Il cubottaedro fondamentale e' autochiudente ($\Psi_1=0$).
- **Passo Induttivo ($P(L)\implies P(L+1)$):** Assumiamo $\Psi_L=0$. La proiezione $\mathcal{K}_L\to\mathcal{K}_{L+1}$ introduce $N_{dof}$ gradi di liberta' aggiuntivi. Qualora la torsione locale superi la soglia di stabilita', il sistema attiva un **Meccanismo di Reset**: la torsione non chiusa viene "messa in sicurezza" tramite intrecci (massa) o scaricata geometricamente. Questo processo garantisce la continuita' della condizione $\sum\tau_{L+1}=0$.

> **Nota sull'Autocompensazione Attiva:** La soglia di stabilita' non e' un limite esterno, ma una proprieta' endogena: il manifold "monitora" la propria frustrazione energetica e riconfigura la sua connettivita' topologica per preservare l'induzione. **Q.E.D.**

### 3. Dimostrazione di Chiusura e Integrita' (Analisi del Flusso)
Essendo il Cosmo un manifold topologicamente isolato, la chiusura e' intrinseca e garantita dalla struttura stessa della rete.
- Ogni spigolo $e$ creato dall'iterazione funge da interfaccia tra flussi orientati opposti ($e_{ab},e_{ba}$), annullando ogni flusso netto: $\Phi_{\partial\mathcal{K}}=\sum\tau(e)=0$.
- **Integrazione della Massa:** Le anisotropie osservate (materia/galassie) non sono violazioni, ma "memorie topologiche" di torsioni che il manifold ha integrato come massa per mantenere la chiusura globale. Il sistema e' chiuso perche' ogni singola unita' di torsione e' contabilizzata nel bilancio energetico totale.

### 4. Limite Asintotico e Inversione di Fase ($L\to\infty$)
Il limite $L\to\infty$ non rappresenta la fine, ma la soglia critica di transizione del sistema.
- **Calcolo del Limite:** $\lim_{L\to\infty}U_L=0$.
- **Interpretazione (Phase Flip):** Raggiunto il limite di saturazione topologica, il manifold subisce un'**Inversione di Fase**: la dinamica si inverte, innescando una de-iterazione speculare ("ritorno alla fonte"). Il sistema ripercorre all'inverso la propria struttura, sciogliendo gli intrecci (rilascio di massa) per riportare $\tau$ al valore nullo iniziale.

> **Nota sulla Dinamica Ciclica:** Il limite infinito e' il punto di biforcazione: non vi e' inversione temporale, ma un riorientamento della fase topologica. Il sistema trasforma la frustrazione accumulata in un nuovo ordine, rendendo l'intero processo una sequenza ricorsiva infinita di crescita e de-iterazione. **Q.E.D.**
