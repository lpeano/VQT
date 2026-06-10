"""
================================================================================
EINSTEIN-CARTAN: torsioni a chiralita' alternata (180 deg) + chiusura spinoriale 720 deg
================================================================================

Implementa la dinamica di Einstein-Cartan sul solitone di base / anello L1 (Z_24),
RECUPERANDO e formalizzando la fisica persa nel refactoring (commit a5b417e,
2026-05-26, "cleanup obsolete files": cancello' dinamica_hamiltoniana_chiralita.py
SENZA che wqt_oop l'avesse re-implementata -> perdita da cleanup prematuro, NON
instabilita').

SPEC (basimatematiche/TOPOLOGIA_FONDAMENTALE.md, dal disegno di Luca):
  - ogni voxel up/down si lega a un complementare con un HALF-TWIST di 180 deg lungo
    il senso di percorrenza;
  - il voxel successivo si lega con lo STESSO twist ma CHIRALITA' OPPOSTA (alternanza);
  - su 24 voxel la sinusoide chiude a 720 deg (4*pi) = chiusura spinoriale (spin-1/2).

DUE SETTORI (vedi diagnosi DIAGNOSI_SATURAZIONE_EC.md):
  1. SETTORE chi (campo / torsione di gradiente): la SATURAZIONE / pressione di
     degenerazione di spin Einstein-Cartan. Energia di torsione che oltre la soglia
     INVERTE (bounce) -> impedisce la singolarita'. E' il termine beta*rho^2 mancante.
  2. SETTORE tau (fase spinoriale): la CHIUSURA a 720 deg con chiralita' alternata.
     La fase deve avvolgere a 4*pi sull'anello chiuso; un'energia la guida.

PRINCIPIO: le forze EC sono GRADIENTI di energie ben definite -> conservative,
compatibili con l'integratore simplettico, stabili (coefficienti tarabili e limitati).

ADDITIVO: questo modulo NON tocca evolve() legacy. SolitoneComposito lo usa SOLO con
flag ec_dynamics_enabled (default OFF). Tutte le funzioni sono PURE e testabili.

[DA CONFERMARE con Luca] (segnati anche nella spec):
  - L'aritmetica esatta 180 deg/connessione -> 720 deg/globale su 24 (24*180 != 720):
    qui la chiusura e' imposta come VINCOLO globale (sum dei twist -> 4*pi), e
    l'alternanza di chiralita' come modulazione (-1)^i / sign(chi). La relazione
    geometrica precisa half-twist<->winding e' una scelta, documentata.
  - "complementare": qui = pozzo opposto del campo (sign(chi)) = up/down.
  - La sinusoide e' realizzata nella fase tau (spinoriale), il campo chi da' la
    chiralita' (up/down) che ne alterna il segno.
================================================================================
"""

import numpy as np

# ---------------------------------------------------------------------------
# COSTANTI FISICHE (NON fragili: topologiche/geometriche, non fit empirici)
# ---------------------------------------------------------------------------
TAU_CLOSURE_4PI = 4.0 * np.pi   # chiusura spinoriale 720 deg (spin-1/2). TOPOLOGICA.
HALF_TWIST_PI = np.pi           # half-twist di 180 deg per connessione.


def chirality_sign(chi):
    """Chiralita' (handedness) dal pozzo occupato: up (+) / down (-).
    'complementare' = pozzo opposto. Ritorna +-1 per ogni voxel."""
    s = np.sign(chi)
    s[s == 0] = 1.0
    return s


def bond_twist(tau, chi):
    """Twist per connessione sull'anello Z_N (toroidale), a CHIRALITA' ALTERNATA.

    bond b collega il voxel b al b+1. Il twist e' la differenza di fase spinoriale
    (tau) modulata dalla chiralita' del legame. La chiralita' del legame alterna:
    il segno e' dato dal prodotto delle chiralita' dei due voxel (up-down -> -1) e
    da un pattern alternato (-1)^b che realizza "il successivo con chiralita' opposta".

    Ritorna twist_bonds (N elementi), uno per connessione.
    """
    N = len(tau)
    s = chirality_sign(chi)
    dtau = np.roll(tau, -1) - tau                  # differenza di fase circolare (N bond)
    alt = np.where(np.arange(N) % 2 == 0, 1.0, -1.0)  # alternanza (-1)^b
    # chiralita' del legame: alternanza geometrica * complementarieta' dei voxel
    chir_bond = alt * (s * np.roll(s, -1))
    twist = chir_bond * (dtau + HALF_TWIST_PI)     # half-twist 180 deg per connessione
    return twist


def torsion_density_K2(chi, W):
    """Densita' di torsione di GRADIENTE per voxel (settore chi):
    K2_i = sum_j W_ij (chi_i - chi_j)^2.  (= E_tors del motore, qui esplicita)."""
    diff2 = (chi[:, None] - chi[None, :]) ** 2
    return np.sum(W * diff2, axis=1)


def ec_energy(chi, tau, W, chi0, beta_sat, kappa_closure, k2_ref_chi):
    """Energia totale di Einstein-Cartan (le forze ne sono il gradiente).

    E_EC = E_saturazione(settore chi) + E_chiusura(settore tau)

      E_sat = beta_sat * sum_i (K2_i - k2_ref_chi)^2   [pressione di spin / bounce]
      E_clo = kappa_closure * (sum_i tau_i - 4*pi)^2   [chiusura spinoriale 720 deg]

    NB chiusura: usa la fase spinoriale totale sum(tau) vs 4*pi, COERENTE col
    diagnostico gia' presente nel motore (compute_geometric_E_psi: closure_err =
    sum(tau) mod 4*pi). Il twist alternato a 180 deg (bond_twist) e' calcolato come
    DIAGNOSTICO della struttura, non come driver (la geometria esatta 180->720 e'
    [DA CONFERMARE] con Luca; non la forziamo nelle forze).

    Ritorna (E_tot, E_sat, E_clo) per diagnostica.
    """
    K2 = torsion_density_K2(chi, W)
    # SATURAZIONE A SOFFITTO (one-sided): penalizza SOLO l'eccesso sopra rho*.
    # Sotto rho* la forza e' nulla (vuoto/domini stabili); sopra -> bounce. La forma
    # simmetrica (K2-rho*)^2 spingerebbe la torsione VERSO rho* anche dal basso
    # (creando torsione nel vuoto): sbagliato. (K2-rho*)+ = solo ceiling.
    exc = np.maximum(K2 - k2_ref_chi, 0.0)
    E_sat = beta_sat * np.sum(exc ** 2)
    closure = np.sum(tau) - TAU_CLOSURE_4PI
    E_clo = kappa_closure * closure ** 2
    return float(E_sat + E_clo), float(E_sat), float(E_clo)


def ec_forces(chi, tau, W, chi0, beta_sat, kappa_closure, k2_ref_chi):
    """Forze EC ADDITIVE su (chi, tau), gradienti ANALITICI di ec_energy (conservative).

    F_chi_i = -dE_sat/dchi_i : pressione di degenerazione di spin (saturazione). Oltre
              k2_ref_chi il fattore (K2-ref) cambia segno -> INVERSIONE (bounce): la
              torsione in eccesso e' respinta -> la densita' SATURA. E' il beta*rho^2 EC.
    F_tau_i = -dE_clo/dtau_i = -2 kappa (sum(tau)-4pi) : guida la fase alla chiusura 720.

    Gradiente settore chi (verificato vs numerico nel self-test):
      K2_i = sum_j W_ij (chi_i-chi_j)^2 ; coef_i = 2 beta (K2_i - ref)
      dE/dchi_k = coef_k * [2 sum_j W_kj (chi_k-chi_j)]            (termine i=k)
                  - 2 sum_i coef_i W_ik (chi_i-chi_k)              (termini i!=k)
    """
    N = len(chi)
    K2 = torsion_density_K2(chi, W)
    # one-sided (ceiling): coef = 2 beta (K2-rho*)+ -> zero sotto soglia (vuoto stabile),
    # bounce solo sopra. Gradiente di E_sat = beta*sum((K2-rho*)+^2) (vedi ec_energy).
    coef = 2.0 * beta_sat * np.maximum(K2 - k2_ref_chi, 0.0)   # (N,)
    diff = chi[:, None] - chi[None, :]             # diff[i,j] = chi_i - chi_j

    dK2_self = 2.0 * np.sum(W * diff, axis=1)       # dK2_i/dchi_i
    grad = coef * dK2_self                           # termine i=k
    cross = -2.0 * np.sum((coef[:, None] * W) * diff, axis=0)  # termini i!=k (segno -)
    F_chi = -(grad + cross)

    closure = np.sum(tau) - TAU_CLOSURE_4PI
    F_tau = -2.0 * kappa_closure * closure * np.ones(N)
    return F_chi, F_tau


def default_k2_ref_chi(chi0):
    """Soglia di saturazione del settore chi (torsione di gradiente).

    DERIVATA (misurata, non fit) = la scala della PARETE di dominio / del disordine:
        rho* = (sqrt(2)*chi0)^2 = 2*chi0^2 .
    Misura su coupling Leech reale: una parete di dominio ha K2 ~ 2*chi0^2 (nodi di
    parete ~5018 per chi0=50); un campo disordinato ha <K2> ~ 2*chi0^2 (~5083). Il
    (2*chi0)^2 = 4*chi0^2 lo raggiunge SOLO un nodo isolato totalmente frustrato (max),
    mai una parete tipica -> con quella soglia la saturazione/espansione non scattava.
    rho* = 2*chi0^2 e' anche la costante sqrt(2) Jitterbug (Ottaedro->Cubottaedro):
    la torsione 'di materia' (kink/parete) e' la soglia naturale del bounce."""
    return 2.0 * chi0 ** 2


# ---------------------------------------------------------------------------
# SELF-TEST: stabilita' e conservativita' (eseguibile direttamente)
# ---------------------------------------------------------------------------
def _self_test():
    rng = np.random.default_rng(0)
    N = 24
    chi0 = 50.0
    # config CON DIFETTO (parete) -> K2 sopra rho* -> gradiente one-sided NON banale
    chi = chi0 + 8.0 * rng.standard_normal(N)
    chi[8:14] = -chi0           # dominio opposto: nodi di parete con K2 > rho*
    tau = 0.1 * rng.standard_normal(N)
    # coupling circolante decrescente (giocattolo, simil-Leech)
    W = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if i != j:
                d = min(abs(i - j), N - abs(i - j))
                W[i, j] = 0.716 ** d
    beta_sat = 1e-8
    kappa_closure = 1e-2
    k2ref = default_k2_ref_chi(chi0)

    E0, Es0, Ec0 = ec_energy(chi, tau, W, chi0, beta_sat, kappa_closure, k2ref)
    Fchi, Ftau = ec_forces(chi, tau, W, chi0, beta_sat, kappa_closure, k2ref)
    # verifica gradiente numerico settore chi: perturba il nodo a K2 MASSIMO
    # (sicuramente sopra rho* -> forza one-sided non nulla e differenziabile)
    eps = 1e-4
    k = int(np.argmax(torsion_density_K2(chi, W)))
    chi_p = chi.copy(); chi_p[k] += eps
    chi_m = chi.copy(); chi_m[k] -= eps
    Ep, _, _ = ec_energy(chi_p, tau, W, chi0, beta_sat, kappa_closure, k2ref)
    Em, _, _ = ec_energy(chi_m, tau, W, chi0, beta_sat, kappa_closure, k2ref)
    num = -(Ep - Em) / (2 * eps)
    print("=" * 64)
    print("  EINSTEIN-CARTAN self-test")
    print("=" * 64)
    print(f"  E_tot={E0:.4e}  E_sat={Es0:.4e}  E_clo={Ec0:.4e}")
    print(f"  F_chi[{k}] analitico={Fchi[k]:+.4e}  numerico={num:+.4e}  "
          f"err_rel={abs(Fchi[k]-num)/(abs(num)+1e-30):.2e}")
    print(f"  |F_chi| max={np.max(np.abs(Fchi)):.3e}  |F_tau| max={np.max(np.abs(Ftau)):.3e}")
    # chiusura spinoriale (settore tau)
    print(f"  chiusura: sum(tau)={np.sum(tau):+.3f}  target 4pi={4*np.pi:.3f}  "
          f"F_tau (uniforme)={Ftau[0]:+.3e}")
    # diagnostico struttura: twist alternato a 180 deg per bond
    tw = bond_twist(tau, chi)
    print(f"  [diagnostico] twist/bond range [{tw.min():+.3f},{tw.max():+.3f}] "
          f"(half-twist 180=pi={np.pi:.3f})")
    ok_chi = abs(Fchi[k] - num) / (abs(num) + 1e-30) < 1e-3
    ok_tau = abs(Ftau[0]) > 0
    print(f"  GRADIENTE settore chi {'OK (conservativo)' if ok_chi else 'ERRORE'}; "
          f"forza chiusura tau {'OK' if ok_tau else 'NULLA'}")
    return ok_chi and ok_tau


if __name__ == "__main__":
    _self_test()
