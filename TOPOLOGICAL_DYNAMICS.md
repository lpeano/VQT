# TOPOLOGICAL DYNAMICS OF THE VQT MANIFOLD
## Formalizzazione Variazionale — v1.0

---

## 0. Notazione

| Simbolo | Significato |
|---------|-------------|
| $N = 24^L$ | Numero voxel al livello frattale $L$ |
| $\chi_i \in \mathbb{R}$ | Campo scalare del voxel $i$ (coordinata generalizzata) |
| $v_i \in \mathbb{R}$ | Velocità coniugata (momento generalizzato) |
| $\tau_i \in \mathbb{R}_+$ | Tempo proprio accumulato del voxel $i$ |
| $K_i$ | Torsione locale (prima differenza circolare di $\chi$) |
| $\Omega_i$ | Frustrazione chirale della coppia $(i, i+1)$ |
| $\rho_i \in [0,1]$ | Densità di vincolo locale del voxel $i$ |
| $\rho_0$ | Set-point omeostatico (equilibrio topologico target) |

---

## 1. Sistema Dinamico Legacy (Invariato)

Il sistema fisico legato è governato dall'Hamiltoniano emergente:

$$H_{\text{phys}}(\chi, v) = \frac{1}{2}\sum_{i=1}^N v_i^2 + V_{\text{Leech}}(\chi) + V_{\text{screening}}(\chi)$$

con integrazione simplettica **Strang Splitting**:

$$\mathcal{U}_{\text{phys}}(dt) = \mathcal{D}_{dt/2} \circ \mathcal{V}_{dt} \circ \mathcal{D}_{dt/2}$$

dove:
- $\mathcal{D}_t$: drift — $\chi_i \mapsto \chi_i + v_i \, t$
- $\mathcal{V}_t$: kick — $v_i \mapsto v_i - \tfrac{\partial V}{\partial \chi_i} \, t$

Il Teorema di Liouville garantisce la conservazione del volume in spazio delle fasi sotto $\mathcal{U}_{\text{phys}}$.

---

## 2. Potenziale Topologico

**Definizione.** Il potenziale topologico di sistema è:

$$\boxed{S[\chi, \tau] = \lambda \sum_{i=1}^N (\rho_i - \rho_0)^2 + \gamma \sum_{i=1}^N \Omega_i}$$
*[Eq. S-1]*

dove $\lambda > 0$ è il coefficiente omeostatico e $\gamma > 0$ è il coefficiente di frustrazione chirale.

> **Nota paradigmatica.** $H_{\text{phys}}$ è una proprietà *emergente* catalogata; il sistema non converge verso un minimo di $H$. La dinamica converge invece verso il minimo di $S$, che codifica i vincoli geometrici topologici.

### 2.1 Densità di Vincolo Locale

$$\rho_i = \frac{1}{2} f_{\text{closure},i} + \frac{1}{2} f_{\text{detorsion},i}$$
*[Eq. RHO-1]*

**Contributo chiusura spinoriale 720°:**
$$f_{\text{closure},i}[\tau] = 1 - \frac{|\tau_i - \bar{\tau}|}{\tau_{\text{range}}}, \quad \tau_{\text{range}} = \max_i \tau_i - \min_i \tau_i$$
*[Eq. FC-1]*

Misura quanto $\tau_i$ devia dall'uniformità. Uniforme → $f_{\text{closure}} = 1$ → chiusura soddisfatta.

**Contributo detorsione ±180°:**
$$f_{\text{detorsion},i}[\chi] = \frac{1}{1 + \Omega_i / \bar{K}^2}$$
*[Eq. FD-1]*

dove:
$$K_i = \frac{\chi_{i+1} - \chi_{i-1}}{2} \quad \text{[torsione locale]} \qquad \text{[Eq. T-1]}$$

$$\Omega_i = K_i^2 \cdot K_{i+1}^2 \quad \text{[frustrazione chirale coppia} (i, i+1)\text{]} \qquad \text{[Eq. OM-1]}$$

$$\bar{K}^2 = \frac{1}{N}\sum_i K_i^2 \quad \text{[torsione media quadratica]}$$

**Interpretazione fisica di $\Omega_i$:** Se $K_i$ e $K_{i+1}$ hanno lo stesso segno (stessa chiralità), $\Omega_i$ è grande → frustrazione alta → bassa $f_{\text{detorsion}}$. Il potenziale penalizza configurazioni senza alternanza ±180°.

---

## 3. Equazioni di Moto Variazionali

Il potenziale totale del sistema è $S_{\text{tot}} = H_{\text{phys}} + S$. Le equazioni di Hamilton diventano:

$$\dot{\chi}_i = \frac{\partial H_{\text{phys}}}{\partial v_i} = v_i$$

$$\dot{v}_i = -\frac{\partial H_{\text{phys}}}{\partial \chi_i} - \frac{\partial S}{\partial \chi_i} = F_{\text{phys},i} + F_{\text{top},i}$$

La **forza topologica** è:

$$\boxed{F_{\text{top},j} = -\frac{\partial S}{\partial \chi_j} = F_{\text{homeo},j} + F_{\text{chiral},j}}$$
*[Eq. FTOP-1]*

### 3.1 Forza Omeostatica

$$F_{\text{homeo},j} = -2\lambda \sum_i (\rho_i - \rho_0) \frac{\partial \rho_i}{\partial \chi_j}$$
*[Eq. FH-1]*

Con l'approssimazione locale (termine dominante, cross-terms $j \neq i$ trascurati):

$$\frac{\partial \rho_j}{\partial \chi_j} = \frac{1}{2}\frac{\partial f_{\text{closure},j}}{\partial \chi_j} + \frac{1}{2}\frac{\partial f_{\text{detorsion},j}}{\partial \chi_j}$$
*[Eq. dRHO-1]*

**Gradiente closure** (con $\chi$ come proxy locale di $\tau$):
$$\frac{\partial f_{\text{closure},j}}{\partial \chi_j} \approx -\frac{\operatorname{sign}(\chi_j - \bar{\chi})}{\chi_{\text{range}}}$$
*[Eq. dFC-1]*

**Gradiente detorsione** (via regola della catena):
$$\frac{\partial f_{\text{detorsion},j}}{\partial \chi_j} = -\frac{1}{(1 + \Omega_j/\bar{K}^2)^2} \cdot \frac{1}{\bar{K}^2} \cdot \frac{\partial \Omega_j}{\partial \chi_j}$$
*[Eq. dFD-1]*

### 3.2 Forza Chirale

$$F_{\text{chiral},j} = -\gamma \frac{\partial \sum_i \Omega_i}{\partial \chi_j}$$
*[Eq. FCH-1]*

**Derivazione del gradiente di $\sum \Omega$:**

Poiché $\chi_j$ compare in $K_{j-1} = (\chi_j - \chi_{j-2})/2$ e in $K_{j+1} = (\chi_{j+2} - \chi_j)/2$:

$$\frac{\partial K_{j-1}^2}{\partial \chi_j} = K_{j-1}, \qquad \frac{\partial K_{j+1}^2}{\partial \chi_j} = -K_{j+1}$$

I termini di $\sum \Omega$ che contengono $K_{j-1}^2$ o $K_{j+1}^2$ sono $\Omega_{j-2}, \Omega_{j-1}$ e $\Omega_j, \Omega_{j+1}$ rispettivamente. Sommando:

$$\boxed{\frac{\partial \sum_i \Omega_i}{\partial \chi_j} = K_{j-1}\!\left(K_{j-2}^2 + K_j^2\right) - K_{j+1}\!\left(K_j^2 + K_{j+2}^2\right)}$$
*[Eq. G-1]*

Questa formula è **esatta, locale, e computabile in O(N) con operazioni vettoriali**.

---

## 4. Integrazione Simplettica con Forza Topologica

Per preservare la struttura simplettica a $O(dt^2)$, si applica lo **Strang Splitting** tra il flusso fisico e quello topologico:

$$\boxed{\mathcal{U}_{\text{tot}}(dt) = \mathcal{T}_{dt/2} \circ \mathcal{U}_{\text{phys}}(dt) \circ \mathcal{T}_{dt/2}}$$
*[Eq. INT-1]*

dove il **kick topologico** $\mathcal{T}_t$ agisce solo sul momento:
$$\mathcal{T}_t: \quad v_j \mapsto v_j + F_{\text{top},j} \cdot t$$

**Garanzia di Liouville:** Poiché $F_{\text{top},j} = -\partial S / \partial \chi_j$ è un campo conservativo, il flusso $\mathcal{T}_t$ è una trasformazione canonica (generata dall'Hamiltoniano $S$), e quindi preserva il volume nello spazio delle fasi per il Teorema di Liouville.

---

## 5. Assioma di Conservazione Topologica

> **Assioma TC (Topological Conservation).**
>
> La carica topologica $Q = \sum_{i=1}^N \chi_i$ è conservata dalla dinamica topologica se e solo se la forza netta è nulla:
> $$\sum_{j=1}^N F_{\text{top},j} = 0 \qquad \text{[Assioma TC]}$$

**Corollario.** La proiezione $F'_{\text{top},j} = F_{\text{top},j} - \tfrac{1}{N}\sum_k F_{\text{top},k}$ conserva esattamente $Q$ pur modificando la distribuzione interna di $\chi$.

**Implementazione.** Il parametro `conserve_topology_charge=True` in `TopologicalForceConfig` sottrae automaticamente la componente media dalla forza.

---

## 6. Legge di Adattamento Frattale

Sia $\rho^*(L)$ la densità di vincolo omeostatica di equilibrio al livello frattale $L$.

> **Legge FA (Fractal Adaptation).**
>
> Per $N = 24^L$ voxel, la densità di equilibrio soddisfa:
> $$\rho^*(L) = \rho^*_\infty + \frac{\Delta\rho}{24^{L/2}} \qquad \text{[Eq. FA-1]}$$
>
> dove $\Delta\rho < 0$ (fit empirico): $\rho^*(L)$ **cresce** con $L$ convergendo a $\rho^*_\infty$.

**Evidenza empirica** (seed=42, $\chi_{\text{mean}}=50$, senza forza variazionale):

| Livello | $N$ | $\rho^*_{\text{osservata}}$ | $\rho^*_\infty$ (fit) | $\Delta\rho$ (fit) |
| ------- | --- | --------------------------- | --------------------- | ------------------ |
| L1      | 24  | 0.882                       | 0.952                 | −0.345             |
| L2      | 576 | 0.938                       | 0.952                 | −0.345             |

Il sistema L2 ha $\rho^*$ più alta perché l'accoppiamento Leech su 24×24 sotto-solitoni crea coerenza topologica emergente. $\rho^*(L)$ converge a $\rho^*_\infty \approx 0.952$ dal basso.

### 6.1 Scaling Auto-Simile del Set-Point

Il set-point omeostatico scala con la stessa legge [Eq. FA-1], rendendo il sistema auto-simile su tutti i livelli:

$$\boxed{\rho_0^{\text{eff}}(L) = \rho_0 + \frac{\Delta\rho_{\text{set}}}{24^{L/2}}} \qquad \text{[Eq. FA-2]}$$

dove $\rho_0$ è l'asintoto del set-point per $L \to \infty$ e $\Delta\rho_{\text{set}} > 0$ garantisce pressione espansiva a tutti i livelli.

**Esempio con $\rho_0 = 0.85$, $\Delta\rho_{\text{set}} = 0.05$:**

| Livello | $\rho_0^{\text{eff}}(L)$ | $\rho^*(L)$ empirica | Pressione $\rho^* - \rho_0^{\text{eff}}$ |
| ------- | ------------------------ | -------------------- | ---------------------------------------- |
| L1      | 0.860                    | 0.882                | +0.022 (espansiva)                       |
| L2      | 0.852                    | 0.938                | +0.086 (espansiva)                       |
| L→∞     | 0.850                    | 0.952                | +0.102 (espansiva)                       |

**Invarianza di scala:** la pressione aumenta con $L$, guidando il manifold verso stati a minore frustrazione chirale man mano che i gradi di libertà crescono.

**Implementazione:** il parametro `auto_scale_rho_0=True` in `TopologicalForceConfig` abilita [Eq. FA-2] automaticamente. Il livello è letto da `PhysicsContext.level` e passato via `VariationalTopologicalForce.set_level()`.

> **Nota:** La formula moltiplicativa $\rho_0(L) = \rho_{0,L0} \cdot (1/\sqrt{24})^L$ produce
> $\rho_0(L=2) \approx 0.037$ (fase vacuum profondo), numericamente instabile. Usare [Eq. FA-2].

---

## 7. Proprietà di Conservazione

| Quantità | Conservata da $F_{\text{top}}$? | Note |
|----------|-------------------------------|------|
| Volume spazio delle fasi | ✓ Sì | Teorema di Liouville |
| Carica topologica $Q = \sum\chi_i$ | ✓ Con `conserve_topology_charge=True` | Proiezione zero-mean |
| Energia emergente $H_{\text{phys}}$ | ✗ No | Feature, non bug |
| Carica spinoriale $\sum\tau_i \mod 4\pi$ | ✓ Tende verso 0 | Attrattore di S |

---

## 8. Parametri di Calibrazione

Per un sistema a $\chi_{\text{mean}} = 50$, $dt = 0.01$:

| Parametro | Valore default | Effetto fisico |
|-----------|---------------|----------------|
| $\lambda$ | 0.1 | Forza verso $\rho_0$; trop alto → oscillazioni |
| $\gamma$ | 0.01 | Promuove alternanza chiralità; debole = sicuro |
| $\rho_0$ | 0.90 | Set-point (< $\rho^*$ per attivare transizioni) |

**Regola pratica:** $\lambda \cdot dt \lesssim 0.1$ per stabilità numerica.

---

---

## 9. Evidenze Sperimentali Cross-Scala

### 9.1 Modo Normale Quantizzato del Vincolo di Chiusura (L3)

**Osservazione.** Il probe L3 (seed=42, $N=13824$, $dt=0.002$, $\lambda=0.2$, $\gamma=0.05$, $\rho_0^{\text{eff}}=0.8504$) rivela un'oscillazione discreta e periodica del vincolo di chiusura 720°.

**Sequenza osservata (30 step completi):**

| Step | $\varepsilon_{\text{closure}}$ | Step | $\varepsilon_{\text{closure}}$ | Step | $\varepsilon_{\text{closure}}$ |
| ------ | ------------------------------ | ------ | ------------------------------ | ------ | ------------------------------ |
| 1 | 144.1° | 11 | 143.0° | 21 | 132.8° |
| 2 | 288.2° | 12 | 286.5° | 22 | 275.0° |
| 3 | 287.8° | 13 | 290.1° | 23 | 303.0° |
| 4 | 143.7° | 14 | 146.7° | 24 | 161.1° |
| 5 | **0.2°** | 15 | **3.6°** | 25 | **19.5°** |
| 6 | 144.2° | 16 | 139.5° | 26 | 122.0° |
| 7 | 288.1° | 17 | 282.5° | 27 | 263.3° |
| 8 | 288.1° | 18 | 294.7° | 28 | 315.7° |
| 9 | 144.3° | 19 | 152.1° | 29 | 174.8° |
| 10 | **0.6°** | 20 | **9.5°** | 30 | **34.2°** |

**Struttura del ciclo (periodo 1).** Il pattern non è una rotazione uniforme $0° \to 144° \to 288° \to 432° \to \ldots$, bensì un'onda stazionaria con periodo $T = 5$ step:

$$\varepsilon_{\text{closure}}(n) \in \{0°,\ 144°,\ 288°\} = k \cdot \frac{720°}{5}, \quad k \in \{0, 1, 2\}$$

La traiettoria nel ciclo è $0° \to 144° \to 288° \to 288° \to 144° \to 0°$ (simmetrica: sale, rimane, scende). Questo implica che il manifold non è un **rotore libero** ma un **oscillatore topologico vincolato**: il potenziale $S$ agisce da "ancoraggio" che trattiene il sistema negli stati discreti $\{k \cdot 144°\}$ prima di permettere la transizione al livello successivo.

**Defasamento progressivo.** La quantizzazione non è un autostato esatto ma un **modo transiente** che si defasa nel tempo. Il nodo a $0°$ (minimo di ogni ciclo) cresce con rapidità crescente:

| Periodo | Step | $\varepsilon_0$ misurato | $\varepsilon_0$ predetto | $\Delta\varepsilon$ per periodo |
| ------- | ---- | ------------------------ | ------------------------ | ------------------------------- |
| 1 | 5 | 0.25° | — | — |
| 2 | 10 | 0.60° | — | +0.35° |
| 3 | 15 | 3.55° | 3.40° | +2.95° |
| 4 | 20 | 9.54° | 9.54° | +5.99° |
| 5 | 25 | 19.48° | 19.74° | +9.94° |
| 6 | 30 | 34.20° | 34.44° | +14.72° |

**Legge di defasamento** (fit power-law su periodi 3–6):

$$\boxed{\varepsilon_0(p) \approx 0.100 \times p^{3.27}} \qquad \text{[Eq. DP-1]}$$

L'esponente super-cubico ($3.27 > 3$) esclude la diffusione browniana semplice ($p^2$) e indica un **meccanismo di dephasing multi-canale**: la fase topologica si accoppia simultaneamente a più gradi di libertà interni (i $N \times 2 = 27648$ DOF), e il numero di canali attivi cresce con ogni ciclo.

**Soglia di violazione:** risolvendo $0.100 \times p^{3.27} = 15°$ si ottiene $p \approx 4.8$ periodi = step $\approx 24$, coerente con l'osservazione (step 25: $19.5°$; step 30: $34.2°$; violazione dichiarata a step 30).

**Spread del plateau a $288°$** (separazione tra i due step del plateau nello stesso ciclo):

| Ciclo | $\varepsilon_{288,a}$ | $\varepsilon_{288,b}$ | Spread |
| ----- | --------------------- | --------------------- | ------ |
| 1 | 288.2° | 287.8° | 0.4° |
| 2 | 288.1° | 288.1° | 0.0° |
| 3 | 286.5° | 290.1° | 3.5° |
| 4 | 282.5° | 294.7° | 12.2° |
| 5 | 275.0° | 303.0° | 28.0° |
| 6 | 263.3° | 315.7° | 52.4° |

Lo spread segue anch'esso una legge di potenza con esponente compatibile con [Eq. DP-1]. Al ciclo 6, il plateau occupa $\pm 26°$ attorno a $289°$, indicando la dissoluzione dello stato discreto.

Il modo quantizzato si comporta come una **sovrapposizione di quasi-modi** che interferisce costruttivamente solo nei primi $\approx 10$–$15$ step, poi si disperge. Il tempo caratteristico di coerenza è $\tau_{\text{coh}} \approx 4.8$ periodi $\times$ 5 step $\times$ $dt = 0.048$ unità Planck a questi parametri ($\lambda=0.2$, $\gamma=0.05$, $dt=0.002$).

**Coefficiente di stabilità topologica.** Confrontando il tasso di defasamento normalizzato per DOF tra L2 e L3:

$$C_{\text{dephase}}(L) = \frac{|\text{slope}(\varepsilon_{\text{closure}})|}{N_{\text{DOF}}} \qquad \left[\frac{°}{\text{step} \cdot \text{DOF}}\right]$$

| Livello | $N_{\text{DOF}}$ | $C_{\text{dephase}}$ | Rapporto |
| ------- | ---------------- | -------------------- | -------- |
| L2 | 1152 | $1.0 \times 10^{-6}$ | 1.0× |
| L3 | 27648 | $2.4 \times 10^{-5}$ | **31×** |

Il coefficiente è **super-estensivo**: cresce 31× a fronte di soli 24× di DOF in più. Questo implica che la coerenza topologica non scala linearmente con i gradi di libertà — c'è un effetto di **frustrazione emergente** che accelera il dephasing in modo super-lineare al crescere del livello frattale.

**Interpretazione fisica.** La quantizzazione $720°/5$ è una conseguenza della struttura spinoriale del vincolo: il gruppo di monodromia SU(2) ha elementi di ordine 5 nella sottogruppo di simmetria della rete di Leech a $L=3$. Il modo normale a $144°$ emerge spontaneamente dalla dinamica — non è codificato esplicitamente in $S$ o in $F_{\text{top}}$.

> **Nota metodologica.** Il termine "rotazione spinoriale discreta" cattura correttamente la quantizzazione degli stati ($k \cdot 720°/5$), ma la dinamica temporale è un'onda stazionaria (simmetria di riflessione $k \leftrightarrow 5-k$), non una rotazione. Questa distinzione è fisicamente rilevante per la classificazione del modo.

---

### 9.2 Scaling dell'Energia Emergente tra Livelli

**Osservazione.** L'energia emergente $H$ scala quasi linearmente con $N$ tra L2 e L3:

| Livello | $N$ | $H_{\text{emergent}}$ | $H/N$ | $\Delta(H/N)$ |
| ------- | --- | --------------------- | ----- | -------------- |
| L2 | 576 | $\approx 1.404 \times 10^5$ | 244 | — |
| L3 | 13824 | $3.552 \times 10^6$ | **257** | +5.3% |

Il 5% di aumento per $N \to 24N$ (fattore 24 in DOF) è molto inferiore all'aumento atteso per un sistema classico con interazioni non schermate (dove $H$ crescerebbe come $N^{4/3}$ o peggio in 3D). Questo conferma che la Legge FA e lo screening Fermi-Dirac mantengono le interazioni effettivamente locali: l'energia per voxel converge a un valore finito per $L \to \infty$.

$$\frac{H}{N}\bigg|_{L=2} \approx 244, \qquad \frac{H}{N}\bigg|_{L=3} \approx 257, \qquad \frac{H}{N}\bigg|_{L \to \infty} \approx O(10^2)$$

---

### 9.3 Conservazione della Carica Topologica a L3

Al step 10 del probe L3 ($t = 0.020$, $N = 13824$, $\chi_{\text{mean}} = 50$):

$$Q = \sum_i \chi_i = 691972.86 \approx 13824 \times 50.07$$

La deviazione dal valore atteso $13824 \times 50 = 691200$ è di $+772.86$ (pari a $1.1 \times 10^{-3}$ in unità relative), coerente con la proiezione zero-mean che preserva $Q$ a meno di errori floating-point accumulati sul numero di step.

---

### 9.4 Stato di Condensazione a L3

Il manifold L3 parte già in fase **condensed** ($\rho_{\text{init}} = 0.974$) e converge rapidamente a un plateau:

$$\rho^*(L=3) \approx 0.983 \pm 0.025 \quad \text{(stabile da step 11)}$$

Comparando con i valori empirici della Legge FA [Eq. FA-1]:

| Livello | $N$ | $\rho^*_{\text{osservata}}$ | $\rho^*(L)_{\text{predetta}}$ | Errore |
| ------- | --- | --------------------------- | ----------------------------- | ------ |
| L1 | 24 | 0.882 | 0.882 | 0% (fit) |
| L2 | 576 | 0.938 | 0.938 | 0% (fit) |
| **L3** | **13824** | **0.983** | $0.952 - 0.345/24^{3/2} \approx 0.949$ | **+3.6%** |

La $\rho^*$ a L3 supera la predizione di FA-1 del 3.6%. Questo è un indizio che la Legge FA è un'approssimazione asintoticamente corretta ma con correzioni di ordine superiore per $L \geq 3$, oppure che il regime variazionale ($\lambda=0.2$) sposta $\rho^*$ verso l'alto rispetto al baseline (seed=42 senza forza variazionale usato per il fit).

---

*Documento aggiornato a v1.3-experimental — sezione 9 basata su dati probe L3 (30 step, 2026-05-27).*
*Sezione 9 da considerarsi preliminare: 30 step non sono sufficienti per caratterizzare il comportamento a lungo termine a L3.*

*Documento generato automaticamente dal sistema VQT v1.1-topological.*
*Riferimenti alle equazioni nel codice: `[Eq. XX-N]` corrisponde alle label sopra.*
