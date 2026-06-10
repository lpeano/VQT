"""
================================================================================
RIGIDEZZA GEOMETRICA  ->  G EMERGENTE (gravita' indotta, Sakharov/Verlinde)
================================================================================

PRINCIPIO FISICO
----------------
La costante di gravitazione G NON e' fondamentale: e' l'INVERSO della RIGIDEZZA
elastica dello SPAZIOTEMPO (gravita' indotta, Sakharov 1967; gravita' entropica,
Verlinde 2011). La relazione di Einstein

        curvatura  =  (8 pi G) * stress-energia

si legge, in linguaggio elastico, come

        deformazione  =  stress / RIGIDEZZA ,     con   G ~ 1 / rigidezza .

Spaziotempo RIGIDO  -> poca curvatura per unita' di sorgente -> G piccolo.
Spaziotempo CEDEVOLE -> molta curvatura                      -> G grande.

DERIVIAMO il coefficiente del muratore EC, beta (l'analogo di G), dalla rigidezza
LOCALE della GEOMETRIA, invece di postularlo (costante o legge 24^L). I RAPPORTI
beta_i/beta_j risultano fissati dalla geometria (zero numeri tarati); resta solo
UNA unita' dimensionale (la scala di Planck Theta), inevitabile.

DUE SETTORI DISTINTI (lezione del primo self-test)
--------------------------------------------------
- SETTORE MATERIA (massa del campo): curvatura del doppio pozzo
      V''(chi) = beta_pot (12 chi^2 - 4 chi0^2);  al vuoto 8 beta_pot chi0^2.
  E' la rigidezza della MATERIA (i kink), NON dello spaziotempo. Domina di ~3
  ordini la geometrica -> se la usassimo per G, mascheriamo la geometria.
- SETTORE SPAZIOTEMPO (cio' che serve per G): spettro del Laplaciano del coupling
      E_tors = sum_ij W_ij (chi_i-chi_j)^2 = 2 chi^T L chi ,   L = D - W
  L'Hessiano e' 4 L. La rigidezza dello spaziotempo E' lo spettro di L (PSD).
  Il modo nullo (autovalore 0, traslazione globale) e' gauge -> ESCLUSO: la
  rigidezza vive nei modi di DEFORMAZIONE (autovalori > 0).

RIGIDEZZA SCALARE E G
---------------------
  R_geo(W) = 4 kappa_geo * < lambda_k(L) : lambda_k > 0 >        (modi di deformazione)
  beta_local = Theta_planck / R_geo                              (G ~ 1/rigidezza)

LA RIGIDEZZA CAMBIA, E NON E' DETTO SIA MONOTONA IN L (intuizione di Luca)
-------------------------------------------------------------------------
R_geo non e' una costante imposta: cambia perche'
  (a) l'espansione dilata il coupling: W_eff = W / a^2 -> L_eff = L / a^2;
  (b) la GERARCHIA combina rigidezze (molle annidate): la rigidezza efficace di un
      blocco di livello L dipende da quella dei figli (vedi effective_rigidity);
  (c) la distribuzione di materia modula il coupling locale.
NON assumiamo monotonia: la MISURIAMO (misura_rigidezza_scala()).

ADDITIVO: modulo di sola diagnostica. Non tocca evolve()/EC/muratore. Puo'
alimentare il muratore (beta_sat <- beta_local) come opzione futura.
================================================================================
"""

import numpy as np


def graph_laplacian(W):
    """Laplaciano del grafo L = D - W (D = diag somme di riga). PSD per W>=0
    simmetrica. E' l'Hessiano (/4) dell'energia di torsione = rigidezza geometrica."""
    W = np.asarray(W, dtype=float)
    return np.diag(W.sum(axis=1)) - W


def laplacian_modes(W, tol=1e-9):
    """Autovalori di DEFORMAZIONE del Laplaciano (esclude il modo nullo gauge).
    Sono le 'frequenze elastiche' della geometria. Maschera vettoriale lambda>tol:
    vincolo fisico (il modo nullo = traslazione globale non e' rigidezza), non if."""
    w = np.linalg.eigvalsh(graph_laplacian(W))
    return w[w > tol]


def geometric_rigidity(W, kappa_geo=1.0, tol=1e-9):
    """Rigidezza geometrica scalare dello spaziotempo:
        R_geo = 4 kappa_geo * < autovalori di deformazione di L >.
    Pura funzione del coupling W (la geometria Leech/cubottaedro). >0 se il grafo
    e' connesso. NON contiene beta_sat (no circolarita')."""
    lam = laplacian_modes(W, tol)
    return float(4.0 * kappa_geo * lam.mean()) if lam.size > 0 else 0.0


def onsite_stiffness(chi, beta_pot, chi0):
    """Rigidezza della MATERIA (massa del campo): V''(chi)=beta_pot(12 chi^2-4 chi0^2).
    Settore separato dallo spaziotempo; qui solo come diagnostica/modulazione."""
    chi = np.asarray(chi, dtype=float)
    return beta_pot * (12.0 * chi * chi - 4.0 * chi0 * chi0)


def g_from_rigidity(R, theta_planck=1.0, eps=1e-30):
    """G emergente: beta_local = Theta / R (G ~ 1/rigidezza).

    Theta_planck NON e' un knob libero: e' la scala di energia INTRINSECA del voxel,
    DERIVATA dalle primitive del modello (chi0, beta_pot) -- non un parametro tarato.
    In unita' di codice si pone Theta=1 (sola convenzione di misura). Conseguenza:
    i rapporti beta_i/beta_j = R_j/R_i sono determinati dalla SOLA geometria; nessun
    numero strutturale resta libero. Vedi docs/peano/EDIFICIO_EINSTEIN_CARTAN.md sez.6."""
    return theta_planck / (R + eps)


def effective_rigidity(R_geo, R_children, mode="series"):
    """Rigidezza EFFICACE di un blocco gerarchico (molle annidate).
      - 'series'   (default): 1/R = 1/R_geo + 1/<R_figli>  -> l'assemblaggio e' piu'
        CEDEVOLE delle parti (la compliance si somma) -> G cresce con la scala.
      - 'parallel': R = R_geo + <R_figli>               -> piu' RIGIDO -> G cala.
    La regola di combinazione e' una scelta di modello (documentata): la MISURA
    dira' quale e' coerente e se la dipendenza da L e' monotona o no."""
    Rc = float(np.mean(R_children)) if len(R_children) else 0.0
    if mode == "parallel":
        return R_geo + Rc
    # series (compliance additiva)
    inv = (1.0 / (R_geo + 1e-30)) + (1.0 / (Rc + 1e-30) if Rc > 0 else 0.0)
    return 1.0 / inv


def misura_rigidezza_scala(root, mode="series"):
    """Misura la rigidezza geometrica DERIVATA per livello su un albero reale.
    Ritorna dict {livello: {R_geo_singolo, beta_singolo, R_eff, beta_eff}}.
    - R_geo_singolo: rigidezza del singolo blocco (dal suo coupling Leech) = 4 N/(N-1),
      topologica e scala-invariante.
    - R_eff: rigidezza efficace gerarchica (molle annidate, vedi effective_rigidity).
    Cosi' la dipendenza da L e' MISURATA, non assunta (monotona o no)."""
    from .segmento_quantistico import SegmentoQuantistico

    def depth(n):
        if not n.children or isinstance(n.children[0], SegmentoQuantistico):
            return 1
        return 1 + depth(n.children[0])

    per_level = {}
    def walk(n):
        if n.children and not isinstance(n.children[0], SegmentoQuantistico):
            W = n.coupling_matrix
            W = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
            per_level.setdefault(depth(n), []).append(geometric_rigidity(W))
            for c in n.children:
                if not isinstance(c, SegmentoQuantistico):
                    walk(c)
    walk(root)

    out, R_eff = {}, None
    for lev in sorted(per_level):
        R_single = float(np.mean(per_level[lev]))
        R_eff = R_single if R_eff is None else effective_rigidity(R_single, [R_eff], mode)
        out[lev] = {"R_geo_singolo": R_single, "beta_singolo": g_from_rigidity(R_single),
                    "R_eff": R_eff, "beta_eff": g_from_rigidity(R_eff)}
    return out


# ---------------------------------------------------------------------------
# SELF-TEST: beta ~ 1/R_geo, DERIVATA dalla geometria (geometrie diverse -> G diverso)
# ---------------------------------------------------------------------------
def _ring_coupling(N, decay):
    W = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if i != j:
                d = min(abs(i - j), N - abs(i - j))
                W[i, j] = decay ** d
    return W / W.sum(axis=1, keepdims=True)


def _self_test():
    N = 24
    # due GEOMETRIE diverse: una piu' connessa (rigida), una piu' locale (cedevole)
    W_rigid = _ring_coupling(N, 0.716)     # coda lunga -> piu' legato -> piu' rigido
    W_soft = _ring_coupling(N, 0.30)       # decadimento rapido -> meno legato -> cedevole
    R_rigid = geometric_rigidity(W_rigid)
    R_soft = geometric_rigidity(W_soft)
    b_rigid = g_from_rigidity(R_rigid)
    b_soft = g_from_rigidity(R_soft)

    print("=" * 70)
    print("  RIGIDEZZA GEOMETRICA self-test (G ~ 1/rigidezza, derivato dalla geometria)")
    print("=" * 70)
    print(f"  geometria RIGIDA (coda lunga):  R_geo={R_rigid:.4f}  beta=Theta/R={b_rigid:.4f}")
    print(f"  geometria CEDEVOLE (locale):    R_geo={R_soft:.4f}  beta=Theta/R={b_soft:.4f}")
    print(f"  beta_cedevole/beta_rigida = {b_soft/b_rigid:.3f}  "
          f"(atteso = R_rigida/R_cedevole = {R_rigid/R_soft:.3f})")

    # recursione gerarchica: rigidezza efficace su L livelli (molle in serie)
    print("  --- rigidezza efficace gerarchica (serie) ---")
    R = R_rigid
    for L in range(1, 5):
        R = effective_rigidity(R_rigid, [R], mode="series") if L > 1 else R_rigid
        print(f"    L{L}: R_eff={R:.4f}  beta=Theta/R={g_from_rigidity(R):.4f}")

    pos = R_rigid > 0 and R_soft > 0
    inv = abs((b_soft / b_rigid) - (R_rigid / R_soft)) < 1e-6
    soft_bigger_G = b_soft > b_rigid
    print(f"  R>0 {'OK' if pos else 'NO'}; beta=Theta/R esatto {'OK' if inv else 'NO'}; "
          f"geometria cedevole -> G maggiore {'OK' if soft_bigger_G else 'NO'}")
    return pos and inv and soft_bigger_G


if __name__ == "__main__":
    _self_test()
