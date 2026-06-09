"""
================================================================================
MURATORE DI PLANCK: espansione dello spazio sorgentata dalla torsione (EC)
================================================================================

LA FISICA (Einstein-Cartan cosmologico, lato espansione):
La stessa pressione di degenerazione di spin che localmente SATURA la densita'
(bounce, vedi einstein_cartan.py) globalmente SPINGE lo spazio a crescere: dove la
torsione eccede rho*, il manifold crea volume nuovo (voxel) per rilassare la densita'.

    densita' > rho*  ->  pressione repulsiva  ->  espansione (a cresce)
                     ->  densita' fisica scende verso rho*  ->  pressione cala (feedback)

E' AUTO-REGOLANTE (feedback negativo): il tasso NON e' una manopola, lo fissa di
quanto la densita' eccede rho*. A equilibrio (densita' fisica = rho*) H = a'/a = 0.

ZERO PARAMETRI NUOVI: riusa beta_sat e k2_ref (= (2*chi0)^2, topologico) dell'EC.
  - frequenza di Planck = il CLOCK (un tentativo per step = dt ~ t_Planck);
  - tasso NETTO di creazione = beta_sat * (K2_fisica - rho*)+ : quasi sempre ~0,
    positivo solo sull'eccesso di torsione. (Cosi' "espansione << Planck" senza
    tarare nulla: il feedback sopprime il ritmo di Planck nudo -> Hubble lento.)

FATTORE DI SCALA come metrica: ogni blocco ha a (default 1). La torsione FISICA
(per volume fisico) e' K2_coord / a^2: quando a cresce, i gradienti si diluiscono.
Il numero di voxel ~ volume ~ a^d_f (diagnostico). Il campo (materia/kink) NON viene
diluito: cresce il volume-per-nodo, cala la DENSITA' di difetti.

ADDITIVO: non tocca evolve() ne' evolve_with_ec() legacy. SolitoneComposito lo usa
solo con flag muratore_enabled (default OFF). Funzioni pure e testabili.
================================================================================
"""

import numpy as np
from .einstein_cartan import torsion_density_K2, default_k2_ref_chi


def physical_torsion(chi, W, a):
    """Densita' di torsione FISICA (per volume fisico): K2_coord / a^2.
    a>1 (spazio espanso) -> gradienti diluiti -> torsione fisica minore."""
    return torsion_density_K2(chi, W) / (a * a)


def hubble_rate(chi, W, a, k2_ref, beta_sat, K2=None):
    """H = a'/a sorgentato dall'ECCESSO di torsione fisica sopra rho*.

    H = beta_sat * < (K2_fisica_i - rho*)+ >   (eccesso LOCALE per-nodo, poi media).
    LOCALE (non (<K2>-rho*)+): cosi' nodi localizzati ad alta torsione (pareti, difetti)
    sorgentano espansione anche se la MEDIA del blocco e' sotto rho* -> espansione segue
    la materia DOVE sta (gravita' locale). Auto-regolante e KNOB-FREE: riusa beta_sat e
    k2_ref dell'EC. H=0 quando OGNI nodo e' sotto rho* (densita' fisica <= rho*).

    K2: se fornito (torsione gia' calcolata, es. SORGENTATA DALLO SPIN), usa quella invece
    del gradiente scalare -> Einstein-Cartan: lo spin sorgenta la torsione che espande."""
    K2coord = K2 if K2 is not None else torsion_density_K2(chi, W)
    K2_phys = K2coord / (a * a)
    excess = float(np.mean(np.maximum(K2_phys - k2_ref, 0.0)))   # per-nodo poi media
    return beta_sat * excess


def expand(a, H, dt):
    """Un tick di Planck: a <- a*(1 + H*dt). Creazione netta = a^d_f cresce."""
    return a * (1.0 + H * dt)


def voxel_count(a, d_f=3.0):
    """Numero di voxel ~ volume ~ a^d_f (DIAGNOSTICO, d_f interpretativo)."""
    return a ** d_f


def equilibrium_a(chi, W, k2_ref):
    """Punto fisso analitico del muratore LOCALE: a* tale che H=0, cioe' OGNI nodo sotto
    rho* (K2_i/a^2 <= rho*). Lo fissa il nodo a torsione MASSIMA (il piu' frustrato):
        a* = sqrt(max_i K2_i / rho*)  se max K2 > rho*, altrimenti 1 (non espande).
    Coerente con hubble_rate locale (l'eccesso si annulla quando anche il max scende a rho*)."""
    m = float(np.max(torsion_density_K2(chi, W)))
    return np.sqrt(m / k2_ref) if m > k2_ref else 1.0


# ---------------------------------------------------------------------------
# SELF-TEST: il feedback si auto-regola (a converge, H->0) SENZA manopole
# ---------------------------------------------------------------------------
def _self_test():
    rng = np.random.default_rng(1)
    N = 24
    chi0 = 50.0
    # blocco CON eccesso: vuoto a +chi0 con un kink (difetto) -> torsione concentrata
    chi = chi0 + 2.0 * rng.standard_normal(N)
    chi[10:14] = -chi0          # difetto: salto pieno tra pozzi opposti -> K2 alta
    W = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if i != j:
                d = min(abs(i - j), N - abs(i - j))
                W[i, j] = 0.716 ** d
    beta_sat = 1e-8
    k2ref = default_k2_ref_chi(chi0)
    a_eq = equilibrium_a(chi, W, k2ref)

    print("=" * 64)
    print("  MURATORE DI PLANCK self-test (auto-regolazione knob-free)")
    print("=" * 64)
    K2 = torsion_density_K2(chi, W)
    K2m = float(K2.mean()); K2max = float(K2.max())
    print(f"  <K2_coord>={K2m:.3e}  max K2={K2max:.3e}  rho*={k2ref:.3e}  "
          f"eccede={'SI' if K2max>k2ref else 'NO'}")
    print(f"  a* atteso (punto fisso LOCALE) = sqrt(maxK2/rho*) = {a_eq:.4f}")

    # integra il feedback: a parte da 1, H sorgentato dall'eccesso, dt grande per
    # arrivare a convergenza in pochi passi (qui contano i NUMERI, non il tempo reale)
    a = 1.0
    dt = 1.0e3            # piccolo -> convergenza liscia al punto fisso (no overshoot)
    H0 = hubble_rate(chi, W, a, k2ref, beta_sat)
    for step in range(4000):
        H = hubble_rate(chi, W, a, k2ref, beta_sat)
        a = expand(a, H, dt)
    Hf = hubble_rate(chi, W, a, k2ref, beta_sat)
    print(f"  H iniziale = {H0:.3e}  (>0: il blocco DEVE espandere)")
    print(f"  dopo feedback: a={a:.4f}  H_finale={Hf:.3e}  voxel~a^3={voxel_count(a):.2f}")
    print(f"  K2_fisica MAX finale = maxK2/a^2 = {K2max/(a*a):.3e}  (target rho*={k2ref:.3e})")

    conv = abs(a - a_eq) / a_eq < 1e-2           # a converge al punto fisso analitico
    relaxed = Hf < 1e-3 * (H0 + 1e-30)           # H crolla -> auto-regolato
    monotone = a >= 1.0                           # lo spazio non si contrae
    print(f"  CONVERGE al punto fisso {'OK' if conv else 'NO'}; "
          f"H->0 (auto-regolato) {'OK' if relaxed else 'NO'}; "
          f"a>=1 {'OK' if monotone else 'NO'}")
    return conv and relaxed and monotone


if __name__ == "__main__":
    _self_test()
