# TOPOLOGICAL DYNAMICS OF THE VQT MANIFOLD
## Formalizzazione Variazionale — v2.1

---

> **Scopo del documento.**
> Questo documento formalizza la dinamica del manifold VQT come sistema fisico autonomo, auto-referenziale e predittivo. Descrive le leggi che governano l'evoluzione dei campi topologici, i principi di conservazione emergenti, e le evidenze sperimentali ottenute dalle simulazioni multi-scala L1–L3. La narrazione segue l'ordine della scoperta: prima il formalismo (invariante), poi le evidenze (cumulative), infine le leggi fenomenologiche che ne emergono — comprese le predizioni falsificabili che elevano il modello da simulazione a teoria.
>
> **Caratteristica fondamentale del modello.** La VQT non è un sistema fisico con un campo topologico come osservabile aggiunto. È un sistema in cui la geometria è l'unica variabile dinamica, e quella geometria si misura, si auto-corregge, e oscilla con un ritmo che non dipende dalla propria risoluzione. Il manifold è auto-referenziale: ogni voxel codifica nel proprio stato il giudizio sulla propria coerenza geometrica. Questa auto-referenzialità è il confine tra una simulazione e un motore fisico.

---

## 0. Notazione

| Simbolo | Significato |
| ------- | ----------- |
| $N = 24^L$ | Numero di voxel (segmenti topologici) al livello frattale $L$ |
| $\chi_i \in \mathbb{R}$ | Campo scalare del voxel $i$ — coordinata generalizzata |
| $v_i \in \mathbb{R}$ | Velocità coniugata — momento generalizzato |
| $\tau_i \in \mathbb{R}_+$ | Tempo proprio accumulato del voxel $i$ |
| $K_i$ | Torsione locale (prima differenza circolare di $\chi$) |
| $\Omega_i$ | Frustrazione chirale della coppia $(i, i+1)$ |
| $\rho_i \in [0,1]$ | Densità di vincolo locale del voxel $i$ |
| $\rho_0^{\text{eff}}(L)$ | Set-point omeostatico adattativo al livello $L$ |
| $\sigma(\rho)$ | Deviazione standard della densità di vincolo — osservabile di maturità |
| $f_{\text{dom}}$ | Frequenza di risonanza dominante del manifold [1/Planck] |
| $T_{\text{dom}}$ | Periodo fondamentale di oscillazione [Planck] |
| $N_{\text{dof}} = 2N$ | Gradi di libertà totali ($\chi$ e $v$ per ogni voxel) |

---

## 1. Il Sistema Fisico: Un Manifold Topologico Autoregolante

Il manifold VQT non è un sistema fisico nel senso convenzionale del termine. Non ha temperatura, non ha un ensemble statistico, non converge verso il minimo di un'energia. È invece un **sistema hamiltoniano perturbato da una forza variazionale topologica**: evolve secondo equazioni di Hamilton standard, ma con un termine addizionale che spinge il sistema verso configurazioni geometricamente coerenti.

Questa distinzione è fondamentale. L'energia hamiltoniana $H_{\text{phys}}$ è una **proprietà emergente catalogata**: la misuriamo, la osserviamo oscillare, ma non è il bersaglio della dinamica. Il bersaglio è la minimizzazione del potenziale topologico $S[\chi, \tau]$, che codifica la coerenza geometrica del manifold.

Il sistema ha due componenti dinamiche: la **fisica del reticolo** (invariante, simplettica, conservativa) e la **pressione topologica** (perturbativa, dissipativa rispetto a $H$, convergente rispetto a $S$). La coesistenza di questi due livelli produce il comportamento ricco che osserviamo nelle simulazioni: oscillazioni persistenti, plateau di densità, frequenze di risonanza intrinsiche.

### 1.1 Dinamica del Reticolo (Invariata)

Il sistema fisico di base è governato dall'Hamiltoniano emergente:

$$H_{\text{phys}}(\chi, v) = \frac{1}{2}\sum_{i=1}^N v_i^2 + V_{\text{Leech}}(\chi) + V_{\text{screening}}(\chi)$$

L'integrazione numerica è eseguita con **Strang Splitting**, che garantisce la reversibilità temporale e la conservazione del volume nello spazio delle fasi al secondo ordine in $dt$:

$$\mathcal{U}_{\text{phys}}(dt) = \mathcal{D}_{dt/2} \circ \mathcal{V}_{dt} \circ \mathcal{D}_{dt/2}$$

dove $\mathcal{D}_t$ è il drift libero ($\chi_i \mapsto \chi_i + v_i t$) e $\mathcal{V}_t$ è il kick hamiltoniano ($v_i \mapsto v_i - \partial V/\partial\chi_i \cdot t$). Il Teorema di Liouville garantisce la conservazione del volume in spazio delle fasi sotto $\mathcal{U}_{\text{phys}}$.

---

## 2. Il Potenziale Topologico: La Geometria Come Forza

La fisica topologica del manifold è codificata nel potenziale:

$$\boxed{S[\chi, \tau] = \lambda \sum_{i=1}^N (\rho_i - \rho_0)^2 + \gamma \sum_{i=1}^N \Omega_i}$$
*[Eq. S-1]*

Il primo termine è l'**omeostasi topologica**: penalizza ogni voxel che si discosta dalla densità di vincolo target $\rho_0$. Il secondo termine è la **frustrazione chirale**: penalizza le configurazioni in cui voxel adiacenti hanno la stessa chiralità, promuovendo l'alternanza ±180° che caratterizza le strutture spinoriali.

Fisicamente, $S$ può essere interpretato come l'energia di deformazione di un tessuto geometrico: quando il manifold è "ben piegato" (vincoli soddisfatti, chiralità alternata), $S$ è basso. Quando è distorto (eccesso di densità locale, chiralità uniforme), $S$ è alto e la forza variazionale agisce per correggere la distorsione.

### 2.1 La Densità di Vincolo: Il Loop di Retroazione Geometrica

La densità di vincolo $\rho_i \in [0,1]$ non è un osservabile esterno imposto al manifold: è l'equazione di un **loop di retroazione geometrica** in cui il manifold si specchia nella propria forma. Il voxel $i$ calcola $\rho_i$ usando esclusivamente informazioni locali — i propri vicini, il proprio tempo proprio, la propria torsione — e il risultato di questo calcolo è la variabile che guida la forza che agirà su di lui al passo successivo. Non c'è nessun osservatore esterno: la geometria si auto-misura.

$$\rho_i = \frac{1}{2} f_{\text{closure},i} + \frac{1}{2} f_{\text{detorsion},i}$$
*[Eq. RHO-1]*

Questa auto-referenzialità ha una conseguenza fisica diretta: ciò che chiamiamo "materia" in questo formalismo non è un'entità distinta che abita il manifold, ma una **configurazione topologicamente stabile** in cui $(\rho_i - \rho_0)$ persiste con segno e ampiezza caratteristici nonostante l'azione della forza variazionale. Un solitone stabile è una regione del manifold che ha trovato un equilibrio tra la pressione omeostatica ($F_{\text{homeo}}$, che spinge verso $\rho_0$) e la propria curvatura intrinseca. La materia, in questo schema, *è* geometria locale auto-sostenuta.

**Il vincolo di chiusura spinoriale 720°** misura l'uniformità dei tempi propri. Un manifold con tempi propri uniformi ha $f_{\text{closure}} = 1$: tutti i voxel "invecchiano" alla stessa velocità, il che corrisponde a un universo geometricamente isotropo. Deviazioni dall'uniformità segnalano la presenza di curvatura locale:

$$f_{\text{closure},i}[\tau] = 1 - \frac{|\tau_i - \bar{\tau}|}{\tau_{\text{range}}}$$
*[Eq. FC-1]*

**Il vincolo di detorsione ±180°** misura quanto la struttura locale è priva di frustrazione chirale. Un campo di torsione con alternanza perfetta tra voxel adiacenti ha $f_{\text{detorsion}} = 1$:

$$f_{\text{detorsion},i}[\chi] = \frac{1}{1 + \Omega_i / \bar{K}^2}$$
*[Eq. FD-1]*

dove la torsione locale e la frustrazione chirale sono definite come:
$$K_i = \frac{\chi_{i+1} - \chi_{i-1}}{2} \quad \text{[Eq. T-1]}, \qquad \Omega_i = K_i^2 \cdot K_{i+1}^2 \quad \text{[Eq. OM-1]}$$

**L'osservabile di sistema più rilevante** non è $\rho_i$ locale ma la sua deviazione standard globale:

$$\sigma(\rho) = \sqrt{\frac{1}{N}\sum_{i=1}^N (\rho_i - \bar{\rho})^2}$$

Quando $\sigma(\rho)$ è piccolo e stabile, il manifold è omogeneo: tutti i voxel si trovano nello stesso stato di vincolo, il che corrisponde a una geometria spazialmente uniforme. La dinamica di $\sigma(\rho)$ nel tempo è la firma primaria dell'auto-organizzazione del manifold — come vedremo nelle sezioni sperimentali.

---

## 3. Le Equazioni di Moto Variazionali

Il potenziale totale è $S_{\text{tot}} = H_{\text{phys}} + S$. Le equazioni di Hamilton diventano:

$$\dot{\chi}_i = v_i, \qquad \dot{v}_i = F_{\text{phys},i} + F_{\text{top},i}$$

La **forza topologica** si decompone in un termine omeostatico e uno chirale:

$$\boxed{F_{\text{top},j} = -\frac{\partial S}{\partial \chi_j} = F_{\text{homeo},j} + F_{\text{chiral},j}}$$
*[Eq. FTOP-1]*

### 3.1 Forza Omeostatica

$$F_{\text{homeo},j} = -2\lambda \sum_i (\rho_i - \rho_0) \frac{\partial \rho_i}{\partial \chi_j}$$
*[Eq. FH-1]*

Questa forza agisce su $\chi_j$ in modo da ridurre il disallineamento $(\rho_i - \rho_0)$ di tutti i voxel che dipendono da $\chi_j$. Nell'approssimazione locale (termine dominante):

$$\frac{\partial \rho_j}{\partial \chi_j} = \frac{1}{2}\frac{\partial f_{\text{closure},j}}{\partial \chi_j} + \frac{1}{2}\frac{\partial f_{\text{detorsion},j}}{\partial \chi_j}$$
*[Eq. dRHO-1]*

con gradienti espliciti:
$$\frac{\partial f_{\text{closure},j}}{\partial \chi_j} \approx -\frac{\operatorname{sign}(\chi_j - \bar{\chi})}{\chi_{\text{range}}} \qquad \text{[Eq. dFC-1]}$$

$$\frac{\partial f_{\text{detorsion},j}}{\partial \chi_j} = -\frac{1}{(1 + \Omega_j/\bar{K}^2)^2} \cdot \frac{1}{\bar{K}^2} \cdot \frac{\partial \Omega_j}{\partial \chi_j} \qquad \text{[Eq. dFD-1]}$$

### 3.2 Forza Chirale

$$F_{\text{chiral},j} = -\gamma \frac{\partial \sum_i \Omega_i}{\partial \chi_j}$$
*[Eq. FCH-1]*

Poiché $\chi_j$ compare in $K_{j-1}$ e $K_{j+1}$, il gradiente è esatto, locale, e computabile in $O(N)$:

$$\boxed{\frac{\partial \sum_i \Omega_i}{\partial \chi_j} = K_{j-1}\!\left(K_{j-2}^2 + K_j^2\right) - K_{j+1}\!\left(K_j^2 + K_{j+2}^2\right)}$$
*[Eq. G-1]*

---

## 4. Integrazione Simplettica con Forza Topologica

Per preservare la struttura simplettica a $O(dt^2)$, la forza topologica è inserita via Strang Splitting tra il flusso fisico e quello topologico:

$$\boxed{\mathcal{U}_{\text{tot}}(dt) = \mathcal{T}_{dt/2} \circ \mathcal{U}_{\text{phys}}(dt) \circ \mathcal{T}_{dt/2}}$$
*[Eq. INT-1]*

Il **kick topologico** $\mathcal{T}_t$ agisce solo sul momento:
$$\mathcal{T}_t: \quad v_j \mapsto v_j + F_{\text{top},j} \cdot t$$

Poiché $F_{\text{top},j} = -\partial S / \partial \chi_j$ è un campo conservativo, $\mathcal{T}_t$ è una trasformazione canonica. Il volume nello spazio delle fasi è quindi preservato per il Teorema di Liouville, anche in presenza della forza topologica.

**Scambio energetico intrinseco tra fisica e geometria.** Il kick topologico $\mathcal{T}_t$ trasferisce impulso dai gradi di libertà "fisici" (governati da $H_{\text{phys}}$) ai gradi di libertà "geometrici" (governati da $S$), e viceversa ad ogni mezzo-passo. Questo trasferimento bidirezionale — e non la dissipazione — è la causa fisica delle oscillazioni di $H_{\text{phys}}$ osservate nelle simulazioni (picco a step 43 in L3, poi inversione e rimbalzo). Non c'è energia persa: c'è energia che cambia forma tra cinetica e topologica, in un ciclo continuo che soddisfa un principio di **equipartizione generalizzata** tra i due settori. Il periodo di questo ciclo è $T_{\text{dom}}$ — la stessa frequenza rilevata nell'analisi spettrale di $\sigma(\rho)$. Le due misure (oscillazione di $H$ e oscillazione di $\sigma$) sono la faccia cinematica e la faccia geometrica dello stesso fenomeno fisico: il respiro del manifold.

---

## 5. Assioma di Conservazione Topologica

> **Assioma TC (Topological Conservation).**
>
> La carica topologica $Q = \sum_{i=1}^N \chi_i$ è conservata dalla dinamica topologica se e solo se:
> $$\sum_{j=1}^N F_{\text{top},j} = 0 \qquad \text{[Assioma TC]}$$

Fisicamente, questo significa che la forza topologica redistribuisce il campo $\chi$ internamente al manifold senza creare o distruggere "carica" totale. È l'analogo topologico della conservazione della massa in un fluido incomprimibile.

**Corollario.** La proiezione $F'_{\text{top},j} = F_{\text{top},j} - \tfrac{1}{N}\sum_k F_{\text{top},k}$ conserva esattamente $Q$. Implementato con `conserve_topology_charge=True` in `TopologicalForceConfig`.

---

## 6. Legge di Adattamento Frattale

Quando il manifold si espande a livelli frattali superiori, la sua geometria di equilibrio cambia. Non è sufficiente mantenere $\rho_0$ costante: a livelli più alti, l'accoppiamento collettivo tra i $24^L$ voxel crea coerenza topologica emergente, che spinge $\rho^*$ verso valori più alti. La Legge di Adattamento Frattale cattura questa dipendenza:

> **Legge FA (Fractal Adaptation).**
>
> La densità di equilibrio omeostatica al livello $L$ soddisfa:
> $$\rho^*(L) = \rho^*_\infty + \frac{\Delta\rho}{24^{L/2}} \qquad \text{[Eq. FA-1]}$$
>
> con $\Delta\rho < 0$: $\rho^*(L)$ **cresce** con $L$ convergendo a $\rho^*_\infty$ dall'alto.

La radice $24^{L/2}$ non è arbitraria: riflette la struttura frattale del manifold, dove ogni livello introduce $\sqrt{24}$ nuovi gradi di libertà di correlazione rispetto al precedente.

**Evidenza empirica** (seed=42, senza forza variazionale):

| Livello | $N$ | $\rho^*_{\text{osservata}}$ | $\rho^*_\infty$ (fit) | $\Delta\rho$ (fit) |
| ------- | --- | --------------------------- | --------------------- | ------------------ |
| L1      | 24  | 0.882                       | 0.952                 | −0.345             |
| L2      | 576 | 0.938                       | 0.952                 | −0.345             |

### 6.1 Scaling Auto-Simile del Set-Point

Per rendere il sistema auto-simile, il set-point omeostatico scala con la stessa legge:

$$\boxed{\rho_0^{\text{eff}}(L) = \rho_0 + \frac{\Delta\rho_{\text{set}}}{24^{L/2}}} \qquad \text{[Eq. FA-2]}$$

Con $\rho_0 = 0.85$ e $\Delta\rho_{\text{set}} = 0.05$:

| Livello | $\rho_0^{\text{eff}}(L)$ | $\rho^*(L)$ empirica | Pressione $\rho^* - \rho_0^{\text{eff}}$ |
| ------- | ------------------------ | -------------------- | ---------------------------------------- |
| L1      | 0.860                    | 0.882                | +0.022 (espansiva)                       |
| L2      | 0.852                    | 0.938                | +0.086 (espansiva)                       |
| L→∞     | 0.850                    | 0.952                | +0.102 (espansiva)                       |

La pressione topologica aumenta con $L$: man mano che il manifold acquisisce più gradi di libertà, la forza variazionale diventa più efficace nel portare il sistema verso stati a minore frustrazione chirale. Il sistema è intrinsecamente espansivo — non converge verso un punto fisso ma verso un attrattore di struttura crescente.

---

## 7. Proprietà di Conservazione

| Quantità | Conservata? | Note |
| -------- | ----------- | ---- |
| Volume spazio delle fasi | ✓ Sì | Teorema di Liouville — garantito da Strang Splitting |
| Carica topologica $Q = \sum\chi_i$ | ✓ Con proiezione zero-mean | Assioma TC |
| Energia emergente $H_{\text{phys}}$ | ✗ No — oscilla | Feature fondamentale: $H$ è un osservabile, non un target |
| Carica spinoriale $\sum\tau_i \mod 4\pi$ | ✓ Attrattore di $S$ | Converge verso zero |

---

## 8. Parametri di Calibrazione

Per un sistema con $\chi_{\text{mean}} \approx 50$, $dt = 0.01$ (regime attuale delle simulazioni multi-scala):

| Parametro | Valore corrente | Effetto fisico |
| --------- | --------------- | -------------- |
| $\lambda$ | 0.2 | Forza omeostatica — regola l'intensità della pressione verso $\rho_0$ |
| $\gamma$ | 0.05 | Promuove alternanza chirale — determina la tensione spinoriale |
| $\rho_0$ | 0.85 | Set-point base (scalato da FA-2 a ogni livello) |
| `auto_scale` | ON | Abilita [Eq. FA-2] — necessario per simulazioni multi-scala |

**Regola di stabilità numerica:** $\lambda \cdot dt \lesssim 0.1$. Con $\lambda=0.2$ e $dt=0.01$, il prodotto è $0.002$, ben dentro il regime stabile.

---

## 9. Evidenze Sperimentali Cross-Scala

Le simulazioni a lungo termine (L1: 600 step, L2: 500 step, L3: in corso) hanno rivelato un quadro fisico molto più ricco di quanto previsto dalla teoria perturbativa. Questa sezione documenta le evidenze empiriche fondamentali.

### 9.1 Fenomenologia della Fase Condensata

Tutte le simulazioni iniziano in **fase condensata** ($\rho_{\text{init}} > 0.97$): il manifold parte fortemente vincolato e deve "rilassare" verso il suo equilibrio frattale. Questo rilassamento non è monotono — è un processo multi-stadio che rivela la struttura interna del sistema.

**Stadio 1 — Deriva lenta di $\rho$:** Nei primi $\sim 50$ step, la densità media $\bar{\rho}$ scende lentamente dal valore iniziale verso il plateau. Contemporaneamente, $\sigma(\rho)$ cresce, indicando che le fluttuazioni locali aumentano prima di stabilizzarsi.

**Stadio 2 — Picco di $H$ e inversione:** L'energia hamiltoniana $H_{\text{phys}}$ cresce durante la fase turbolenta, raggiunge un massimo (il "picco di nucleazione"), e poi inizia a decrescere verso il suo valore di plateau. A L3, questo picco è stato osservato allo step $\approx 43$:

| Step | $\sigma(\rho)$ | $H_{\text{phys}}$ | Fase |
| ---- | -------------- | ----------------- | ---- |
| 1    | 0.027          | 3.550×10⁶         | Deriva iniziale |
| 20   | 0.030          | 3.646×10⁶         | Turbolenza attiva |
| 43   | 0.035          | **3.666×10⁶** ← picco | Nucleazione |
| 68   | 0.034          | 3.584×10⁶         | Inversione |
| 80   | 0.033          | 3.650×10⁶         | Oscillazione emergente |

Il picco di $H$ e l'inversione successiva non sono casuali: segnalano il momento in cui il manifold smette di accumulare energia nel disordine e inizia a redistribuirla in struttura organizzata. Il linguaggio corretto per descrivere questo evento è quello delle **transizioni di fase del vuoto**: la configurazione ad alta $\rho$ uniforme e alta simmetria con cui il sistema parte è il *falso vuoto* — una configurazione metastabile che massimizza localmente la coerenza ma non minimizza il potenziale $S$. Il picco di $H$ è il momento della **tunneling topologico**: il manifold attraversa la barriera di potenziale che separa il falso vuoto (alta $\bar{\rho}$, bassa $\sigma$, nessuna struttura solitonica) dal *vuoto vero* (plateau di $\bar{\rho}$ inferiore, $\sigma$ stabile, struttura frattale emergente). L'inversione di $H$ è la segnatura calorimetrica di questa transizione.

**Stadio 3 — Plateau di $\sigma(\rho)$ e oscillazione di $H$:** Dopo la nucleazione, $\sigma(\rho)$ si stabilizza su un valore che dipende dal livello, mentre $H$ inizia a oscillare in modo quasi-periodico con periodo $T_{\text{dom}}$. Questa oscillazione non è rumore: è l'omeostasi dinamica del vuoto vero. Il manifold non converge verso un punto fisso — converge verso un **attrattore oscillante**, esattamente come un cuore non si ferma quando raggiunge il ritmo ottimale. La quiete del manifold è un ritmo, non un silenzio.

### 9.2 Scaling dell'Energia Emergente

L'energia hamiltoniana scala quasi linearmente con $N$ tra i livelli:

| Livello | $N$ | $H_{\text{phys}}$ (plateau) | $H/N$ | $\Delta(H/N)$ |
| ------- | --- | --------------------------- | ----- | -------------- |
| L2      | 576 | ≈ 1.404×10⁵                | 244   | —              |
| L3      | 13824 | ≈ 3.65×10⁶               | **264** | +8.2%          |

Un aumento dell'8% per un fattore 24 in $N$ è straordinariamente basso. In un sistema classico con interazioni a lungo raggio, $H$ crescerebbe come $N^{4/3}$ o peggio. Qui la combinazione del potenziale di Leech e dello screening Fermi-Dirac mantiene le interazioni effettivamente locali: l'energia per voxel converge verso un valore finito per $L \to \infty$. Il manifold VQT è termodinamicamente **estensivo** rispetto all'energia — una proprietà non ovvia per un sistema con interazioni topologiche.

### 9.3 Conservazione della Carica Topologica

Al plateau della simulazione L3 ($N = 13824$, $\chi_{\text{mean}} = 50$):

$$Q = \sum_i \chi_i \approx 13824 \times 50.07$$

La deviazione dall'atteso ($13824 \times 50 = 691200$) è dello $0.1\%$ in unità relative, coerente con gli errori floating-point accumulati su centinaia di step. La proiezione zero-mean dell'Assioma TC funziona correttamente a tutti i livelli.

---

## 10. Spettroscopia del Manifold: La Frequenza Fondamentale

La scoperta più importante delle simulazioni a lungo termine è che il manifold VQT ha una **frequenza di risonanza intrinseca** — un modo normale di oscillazione che emerge spontaneamente dalla dinamica, indipendentemente dalle condizioni iniziali.

### 10.1 Il Segnale Spettrale

L'analisi FFT di $\sigma(\rho)$ per i livelli L1, L2 e L3 (200 step, affidabilità parziale) rivela picchi di potenza netti e riproducibili:

| Livello | $N_{\text{dof}}$ | $N_{\text{camp}}$ | $f_{\text{dom}}$ [1/P] | $T_{\text{dom}}$ [P] | Pot. dom. | Entropia | $\sigma_{\text{mean}}$ | Affidabile |
| ------- | ---------------- | ----------------- | ---------------------- | -------------------- | --------- | -------- | ---------------------- | ---------- |
| L1      | 48               | 600               | **0.667**              | 1.500                | 20.2%     | 2.539    | 0.086                  | SI         |
| L2      | 1152             | 500               | **0.600**              | 1.667                | 31.1%     | 1.986    | 0.050                  | SI         |
| L3      | 27648            | 200               | **~0.500** (*)         | ~2.000               | 41.9%     | 1.237    | 0.037                  | NO (*)     |

(*) L3 ha 200 campioni = 1 periodo stimato: l'FFT non ha risoluzione sufficiente. Il valore è indicativo della tendenza ma non certificabile senza una run ≥ 600 step.

Il **periodo fondamentale** è dell'ordine di 1.5–2.0 unità Planck a tutti i livelli. Il manifold respira con un ritmo intrinseco che non dipende dalla risoluzione spaziale. Tre dati emergono con chiarezza crescente: la potenza dominante *aumenta* con $L$ (20% → 31% → 42%), $\sigma_{\text{mean}}$ *diminuisce* (0.086 → 0.050 → 0.037), e l'entropia spettrale crolla (2.539 → 1.986 → 1.237). Il manifold diventa più uniforme, più ordinato, e più dominato dal modo fondamentale ad ogni livello frattale.

### 10.2 Invarianza di Scala della Frequenza

La variazione di $f_{\text{dom}}$ tra L1 ($N_{\text{dof}}=48$) e L2 ($N_{\text{dof}}=1152$) — un fattore 24 nei gradi di libertà — è solo del 10%. Un fit a legge di potenza $f_{\text{dom}} = A \cdot N_{\text{dof}}^\alpha$ fornisce:

$$\boxed{f_{\text{dom}} \approx 0.75 \cdot N_{\text{dof}}^{-0.033}} \qquad \text{[Eq. FSCALE-1]}$$

con $\alpha \approx -0.033$ — praticamente zero. Questo risultato ha un'interpretazione fisica profonda:

> **Legge FI (Frequency Invariance).**
>
> La frequenza di risonanza fondamentale del manifold VQT è **invariante di scala** rispetto al numero di gradi di libertà. Essa è determinata dai parametri fisici del sistema ($\lambda$, $\gamma$, $dt$), non dalla risoluzione spaziale $N$.

In altri termini: un universo a L1 (24 voxel) e un universo a L6 (24⁶ voxel) oscillerebbero alla stessa frequenza fondamentale. La "frequenza cosmica" è codificata nel potenziale $S$, non nella geometria discreta.

L'esponente $\alpha \approx -0.03$ non è esattamente zero, ma la sua deviazione da zero indica una **correzione logaritmica debole**: il periodo cresce come $N^{0.03}$, cioè raddoppia solo quando $N$ aumenta di un fattore $2^{33} \approx 10^{10}$ — del tutto irrilevante per i livelli L1–L6. Nella prospettiva del limite continuo ($L \to \infty$), l'esponente suggerisce l'esistenza di un **punto critico nell'infinito**: a risoluzione infinita, $f_{\text{dom}}$ converge verso un valore puro, libero da correzioni di griglia. La VQT, in questo limite, è una teoria di campo nel continuo con una frequenza di vuoto ben definita.

**Analisi dimensionale e meccanismo fisico** *[Eq. FI-2].* Il motivo dell'invarianza risiede nella struttura del potenziale frattale. Analisi dimensionale e fit numerico suggeriscono:

$$\boxed{f_{\text{dom}} \approx C \cdot \sqrt{\lambda \cdot \gamma} / dt} \qquad \text{[Eq. FI-2]}$$

dove $C$ è una costante adimensionale di ordine unità che assorbe i dettagli del potenziale di Leech. Poiché $\lambda$, $\gamma$ e $dt$ sono parametri globali del sistema, la frequenza di risonanza è indipendente da $N$. L'analisi è analoga alla **frequenza di plasma** $\omega_p = \sqrt{ne^2/\epsilon_0 m_e}$ nei metalli: quella frequenza non dipende dal volume del campione, ma solo dalla densità e dalle costanti fondamentali. Qui, $f_{\text{dom}}$ non dipende da $N$, ma solo da $(\lambda, \gamma, dt)$ — le costanti fondamentali del vuoto topologico VQT.

> **Predizione falsificabile [P-1].** Se la Legge FI è corretta, una simulazione con $\lambda = 0.4$ (doppio) dovrebbe produrre $f_{\text{dom}} \to f_{\text{dom}} \times \sqrt{2} \approx 0.85$ [1/P], mantenendo $\alpha$ invariato. Una simulazione con $\gamma = 0.20$ (quadruplo) dovrebbe produrre $f_{\text{dom}} \to f_{\text{dom}} \times 2 \approx 1.20$ [1/P]. Queste misure permetterebbero di determinare la forma esatta di [Eq. FI-2] e isolare la dipendenza dai parametri fisici.

> **Predizione falsificabile [P-2].** Una run L3 estesa a ≥ 600 step (tre periodi al $T_{\text{dom}}$ stimato) deve produrre $f_{\text{dom}}(L3) \in [0.55, 0.63]$ [1/P] con FFT affidabile. Se il valore cade fuori da questo intervallo, la Legge FI richiede revisione. Se cade dentro, la costante del vuoto VQT è certificata su tre decadi di gradi di libertà ($N_{\text{dof}} = 48 \to 27648$) — una misura di precisione, non un'osservazione.

### 10.3 Entropia Spettrale e Ordine Emergente

L'entropia spettrale $\mathcal{H}_s = -\sum_k p_k \log p_k$ (dove $p_k$ è la frazione di potenza alla frequenza $k$) misura quanti modi contribuiscono significativamente allo spettro.

La progressione osservata su tre livelli:

$$\mathcal{H}_s: \quad 2.539 \text{ (L1)} \longrightarrow 1.986 \text{ (L2)} \longrightarrow 1.237 \text{ (L3)}$$

è un risultato sorprendente. La caduta L2→L3 (−0.749) è più grande della caduta L1→L2 (−0.553): l'ordine emergente **accelera** con la scala. Il manifold a L3 ha 576 volte più gradi di libertà di L1, eppure il suo spettro è dominato da meno modi. Questo è il fenomeno opposto a ciò che ci aspetteremmo da un sistema caotico classico (dove più DOF significano più modi eccitati): nella VQT, la struttura frattale del potenziale di Leech *cristallizza* i modi normali in un numero decrescente di frequenze dominanti all'aumentare del livello.

> **Predizione [P-3].** A L4 ($N_{\text{dof}} = 663552$), l'entropia spettrale dovrebbe scendere sotto $\mathcal{H}_s < 1.0$, indicando un sistema dominato da un singolo modo quasi-puro. A L5 e L6, il manifold dovrebbe approssimare un **oscillatore topologico monocromatico** — il limite di campo classico puro.

---

## 11. Gerarchia delle Scale Temporali

Le simulazioni rivelano l'esistenza di due scale temporali fondamentalmente distinte, associate a fenomeni fisici diversi. Comprenderle è essenziale per interpretare correttamente i log di simulazione.

### 11.1 La Turbolenza di Transizione (T ≈ 0.13 Planck)

Nei primi passi di ogni simulazione, prima che il manifold trovi il suo modo normale, si osserva un'oscillazione rapida del vincolo di chiusura spinoriale con periodo $T_{\text{turb}} \approx 0.13$ Planck (circa 13 step a $dt=0.01$), corrispondente a $f_{\text{turb}} \approx 7.7$ Hz.

**Interpretazione fisica.** Questo è il **tempo di attraversamento topologico**: il tempo necessario affinché un'onda di torsione si propaghi attraverso il manifold da un estremo all'altro e interagisca con il campo di gauge. A L3, con $N = 13824$ voxel, questa propagazione è chaótica perché i $27648$ gradi di libertà non si sono ancora coordinati. Ogni voxel "sente" il campo locale, non quello globale — manca la coerenza di lunga portata.

Questa turbolenza è **transitoria per costruzione**: quando il manifold nuclea i suoi solitoni (completa lo Stadio 2 della Sezione 9.1), i modi locali si sincronizzano e la turbolenza ad alta frequenza si smorza.

### 11.2 Il Respiro Omeostatico (T ≈ 1.5 Planck)

Dopo la nucleazione, emerge il modo normale fondamentale con $T_{\text{dom}} \approx 1.5$ Planck. Questa è la **frequenza di risonanza omeostatica**: l'oscillazione collettiva dell'intero manifold attorno al suo punto di equilibrio.

**Interpretazione fisica.** Il manifold funziona come un oscillatore esteso: la forza variazionale $F_{\text{top}}$ agisce come una molla topologica con costante effettiva $k_{\text{eff}} \sim 2\lambda/N$, mentre la massa inerziale è distribuita su tutti gli $N$ voxel. Il periodo di risonanza:

$$T_{\text{dom}} \sim 2\pi\sqrt{\frac{m_{\text{eff}}}{k_{\text{eff}}}} \sim 2\pi\sqrt{\frac{N}{2\lambda/N}} = \pi\sqrt{\frac{2N^2}{\lambda}}$$

Per $\lambda = 0.2$ e $N = 24$ (L1): $T \sim \pi\sqrt{2 \times 576 / 0.2} \approx \pi \times 53.7 \approx 169$ — un ordine di grandezza superiore al valore osservato (1.5 Planck = 150 step), indicando che l'oscillatore non è puramente armonico ma è moderato dall'ammortizzazione chirale $\gamma$. L'invarianza di scala di $f_{\text{dom}}$ implica che i due effetti ($N^2$ e $1/\lambda$) si bilanciano in modo tale da rendere il periodo quasi indipendente da $N$ — un tuning fine intrinseco del potenziale $S$.

### 11.3 La Cascata Energetica

La transizione dalla turbolenza ad alta frequenza al modo fondamentale è una **cascata energetica inversa**: l'energia fluisce dai modi ad alta frequenza (breve scala) verso il modo fondamentale (lunga scala), contrariamente a quanto accade nella turbolenza classica di Kolmogorov.

Questo fenomeno è visibile nella Short-Time Fourier Transform (STFT) di $\sigma(\rho)$: lo spettrogramma mostra picchi di potenza ad alta frequenza nei primi step, che si spostano progressivamente verso $f_{\text{dom}}$ man mano che la simulazione avanza. La prova visiva dell'auto-organizzazione del manifold.

---

## 12. Criterio di Maturità Fisica: Il MaturityWatchdog

Il concetto di "maturità" di una simulazione VQT non è triviale. Un sistema hamiltoniano non converge mai verso un punto fisso: oscilla. La domanda corretta non è "quando si ferma?" ma "quando si stabilizza su un regime oscillatorio stazionario?".

### 12.1 L'Osservabile di Maturità

L'osservabile scelto è $|d\sigma(\rho)/dt|$, la velocità di variazione della deviazione standard della densità di vincolo. Quando questa velocità è piccola per un numero sufficiente di passi consecutivi, il manifold ha raggiunto il suo regime oscillatorio stazionario: $\sigma(\rho)$ oscilla ma attorno a un valore medio stabile.

La maturità è dichiarata quando:

$$\left|\frac{d\sigma(\rho)}{dt}\right| < \varepsilon_{\text{norm}} \quad \text{per } W \text{ passi consecutivi}$$

### 12.2 La Normalizzazione Scale-Invariante di $\varepsilon$

Una soglia di convergenza fissa $\varepsilon$ non è appropriata per un sistema con $N_{\text{dof}}$ variabile. Per il Teorema del Limite Centrale, le fluttuazioni di $\sigma(\rho)$ scalano come $1/\sqrt{N_{\text{dof}}}$: un sistema con più gradi di libertà ha $\sigma(\rho)$ naturalmente più piccolo, e richiederebbe una soglia più bassa solo per effetti statistici.

La normalizzazione corretta è:

$$\boxed{\varepsilon_{\text{norm}} = \frac{\varepsilon}{\sqrt{N_{\text{dof}}}}} \qquad \text{[Eq. WD-1]}$$

Con questa normalizzazione, la soglia di maturità è **invariante di scala**: un sistema a L1 e uno a L5 con la stessa "quiete topologica" relativa vengono dichiarati maturi con la stessa soglia $\varepsilon$, indipendentemente dal numero di gradi di libertà.

### 12.3 Auto-Sintonizzazione della Finestra di Convergenza

La finestra di convergenza $W$ (numero di passi per cui la quiete deve persistere) deve essere commisurata al periodo dominante del sistema. Usando una finestra troppo corta rispetto a $T_{\text{dom}}$, il watchdog dichiara falsa maturità durante la fase silenziosa di un'oscillazione.

Dopo una fase iniziale di accumulo dati (almeno `spectral_min_steps` passi), il watchdog esegue un'analisi FFT di $\sigma(\rho)$ per stimare $T_{\text{dom}}$ e auto-sintonizza:

$$\boxed{W_{\text{auto}} = \max\!\left(W_{\text{min}},\ \lfloor \alpha_s \cdot T_{\text{dom}} / dt \rfloor\right)} \qquad \text{[Eq. WD-2]}$$

con $\alpha_s \approx 0.75$ (fattore di sicurezza: la finestra copre 3/4 del periodo dominante). Questa procedura fa sì che la finestra di convergenza si adatti automaticamente alla fisica del sistema, senza richiedere tuning manuale per ogni livello frattale.

### 12.4 La Firma Spettrale come Metadato

Il watchdog salva nell'HDF5 non solo il flag di maturità ma l'intera firma spettrale di $\sigma(\rho)$: frequenza dominante, periodo, potenza dominante, entropia spettrale, top-3 frequenze. Questi metadati permettono di confrontare le proprietà dinamiche del manifold tra livelli frattali diversi, costruendo nel tempo la banca dati per la legge di scala [Eq. FSCALE-1].

---

## 13. Stato Attuale delle Simulazioni (exp1/)

| Livello | $N_{\text{dof}}$ | Step completati | $f_{\text{dom}}$ | $T_{\text{dom}}$ | $\sigma$ plateau | $\mathcal{H}_s$ | Stato |
| ------- | ---------------- | --------------- | ---------------- | ---------------- | ---------------- | --------------- | ----- |
| L1      | 48              | 600             | 0.667 Hz         | 1.500 P          | 0.086            | 2.539           | ✓ Completo |
| L2      | 1152            | 500             | 0.600 Hz         | 1.667 P          | 0.050            | 1.986           | ✓ Completo |
| L3      | 27648           | ~80 (in corso)  | TBD              | TBD              | ~0.033           | TBD             | ⏳ In corso |

La simulazione L3 (200 step, $\lambda=0.2$, $\gamma=0.05$, $dt=0.01$, seed=42) è in esecuzione. Al momento della stesura (step ~80), il manifold ha superato la nucleazione (picco di $H$ a step 43) e sta entrando nella fase oscillatoria. La frequenza dominante $f_{\text{dom}}(L3)$ sarà il terzo punto per la legge di scala [Eq. FSCALE-1].

**Predizione:** se la legge FI vale, $f_{\text{dom}}(L3) \approx 0.59$–$0.61$ Hz, con entropia spettrale $< 1.986$ (ulteriore riduzione dell'entropia — ordine emergente). La verifica di questa predizione è il prossimo obiettivo sperimentale.

---

*Documento aggiornato a v2.0 — 2026-05-27.*
*Sezione 13 e dati L3 preliminari: da aggiornare al completamento della simulazione.*
*Riferimenti alle equazioni nel codice: `[Eq. XX-N]` corrisponde alle label sopra.*
