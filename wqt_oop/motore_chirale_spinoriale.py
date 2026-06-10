"""
================================================================================
MOTORE CHIRALE SPINORIALE (completo, additivo): spinore + chiralita' + 180/720
================================================================================

Da' al voxel il grado di liberta' SPINORIALE che mancava (il campo era ridotto a
scalare reale chi). Ogni voxel porta uno spinore/qubit

    psi_i = alpha_i |0> + beta_i |1> ,  alpha_i = cos(theta_i/2), beta_i = sin(theta_i/2) e^{i phi_i}

GRADI DI LIBERTA' per voxel:
  - theta_i (latitudine di Bloch): tan(theta_i/2) = |beta/alpha| = PENDENZA DEL KINK
    (la richiesta storica: beta/alpha nel campo complesso E' la pendenza del kink);
  - dphi_i (TWIST del legame i->i+1): la fase spinoriale avanza di dphi_i su ogni legame.
    La fase assoluta phi_i = cumsum(dphi) (puo' avvolgere): il WINDING = Sum dphi_i.

CHIUSURA 720 + TWIST 180 ALTERNATO (vincoli geometrici):
  twist preferito per legame  tau_i = (4pi/N) + HALF_TWIST*(-1)^i  (half-twist 180 a
  chiralita' alternata; parte alternata a somma nulla -> Sum tau_i = 4pi). Il winding
  Sum dphi_i e' guidato a 4pi (720 deg, doppio rivestimento spin-1/2). Nota: e^{i*4pi}=1
  -> lo spinore RITORNA a se' dopo 720 (e NON dopo 360): e' lo spin-1/2.

DENSITA' CHIRALI derivate dallo spinore (non campi separati):
  rho_DX = |alpha|^2 = cos^2(theta/2) ("spazio"),  rho_SX = |beta|^2 = sin^2(theta/2)
  ("materia"). Sum = 1 per voxel. La materia (SX) emerge dove la pendenza (theta) e' alta.

DINAMICA (stabile, NON esplode):
  - FASE/CHIUSURA (dphi, 180/720): TOPOLOGICA, NON rilassata -> dphi_i = tau_i (twist
    180 alternato), winding = Sum tau_i = 4pi ESATTO sempre. ZERO parametri.
  - LATITUDINE (theta, beta/alpha=pendenza): rilassa verso |s_i| (pendenza del kink) in
    bilancio col BOUNCE EC (vedi sotto). s_i = gradiente locale di chi / chi0.

ADDITIVO: lo spinore vive ACCANTO a (chi, v). Default OFF -> non tocca la dinamica di
campo. [DA CONFERMARE con Luca] l'aritmetica esatta 180->720 (qui: parte alternata +-pi
a somma nulla, media 4pi/N): scelta documentata.
================================================================================
"""

import numpy as np

HALF_TWIST = np.pi            # twist 180 deg per legame (half-twist). TOPOLOGICO.
CLOSURE_4PI = 4.0 * np.pi     # chiusura spinoriale 720 deg (spin-1/2). TOPOLOGICO.
J_SLOPE = 1.0                 # accoppiamento beta/alpha -> pendenza del kink
RELAX_THETA = 0.10            # tasso di rilassamento di theta (stabile)
RELAX_SAT = 0.50             # tasso del bounce EC sullo spin (allineamento gated)
# La chiusura 720 NON ha parametri: dphi = tau (twist topologico), winding = 4pi esatto.
# RIMOSSI K_CLOSURE, RELAX_DPHI, J_TWIST (la fase e' topologica, non rilassata).
# NB: la scala della pendenza e' chi0 = physics.chi_stable, PASSATA (non hardcoded).
# Le costanti J_*, RELAX_*, K_CLOSURE sono coefficienti NUMERICI del rilassamento
# (come dt), non valori fisici. Le costanti topologiche pi/4pi (180/720) sono derivate.


def bond_twist_target(N):
    """Twist preferito per legame: tau_i = 4pi/N + HALF_TWIST*(-1)^i. Parte alternata
    (+-pi) a somma nulla -> Sum tau_i = 4pi (chiusura 720 consistente). Realizza
    'ogni legame 180 deg, chiralita' alternata, chiude a 720'."""
    i = np.arange(N)
    return CLOSURE_4PI / N + HALF_TWIST * np.where(i % 2 == 0, 1.0, -1.0)


def kink_slope(chi, chi0):
    """Pendenza locale del kink = gradiente centrato di chi (anello), normalizzato per
    chi0 (= physics.chi_stable, NON hardcoded): s_i = (chi_{i+1}-chi_{i-1})/(2 chi0)."""
    return (np.roll(chi, -1) - np.roll(chi, 1)) / (2.0 * chi0)


def abs_phase(dphi):
    """Fase assoluta phi_i = somma dei twist dei legami precedenti (cumsum, phi_0=0)."""
    return np.concatenate([[0.0], np.cumsum(dphi)[:-1]])


def spinor_components(theta, dphi):
    """(alpha, beta) del qubit. beta/alpha = tan(theta/2) e^{i phi}, phi=cumsum(dphi)."""
    phi = abs_phase(dphi)
    return np.cos(theta / 2.0), np.sin(theta / 2.0) * np.exp(1j * phi)


def chirality_densities(theta):
    """rho_DX=cos^2(theta/2) (spazio), rho_SX=sin^2(theta/2) (materia). Sum=1 per voxel."""
    return np.sin(theta / 2.0) ** 2, np.cos(theta / 2.0) ** 2


def bloch_vectors(theta, dphi):
    """Vettore di Bloch (densita' di spin) per voxel: n = <psi|sigma|psi> =
    (sin theta cos phi, sin theta sin phi, cos theta), phi = cumsum(dphi). |n|=1."""
    phi = abs_phase(dphi)
    return np.stack([np.sin(theta) * np.cos(phi),
                     np.sin(theta) * np.sin(phi),
                     np.cos(theta)], axis=1)               # (N, 3)


def spin_torsion_K2(theta, dphi, W, chi0):
    """TORSIONE SORGENTATA DALLO SPIN (Einstein-Cartan vero): la torsione viene dal
    GRADIENTE della densita' di spin (vettore di Bloch), NON dal gradiente scalare di chi.
        K2_spin_i = chi0^2 * sum_j W_ij |n_i - n_j|^2 ,   |n_i-n_j|^2 = 2 - 2 n_i.n_j
    Scalata per chi0^2 -> STESSE unita' della torsione scalare (una parete spinoriale, n
    quasi antipodali, da' ~2 chi0^2 = rho*). Include la fase (twist 180/720): lo spin
    (incluso il suo avvolgimento) genera la torsione che guida saturazione/espansione."""
    return spin_torsion_K2_bloch(bloch_vectors(theta, dphi), W, chi0)


def spin_torsion_K2_bloch(n, W, chi0):
    """Torsione dallo spin per vettori di Bloch ARBITRARI (anche |n| < 1):
        K2_i = chi0^2 * sum_j W_ij |n_i - n_j|^2,  |n_i-n_j|^2 = |n_i|^2+|n_j|^2-2 n_i.n_j.
    Per |n|=1 (foglie) coincide con spin_torsion_K2 (2 - 2 n.n). Per gli AGGREGATI
    GERARCHICI (bloch_aggregate: media dei Bloch dei figli) |n| < 1 codifica la
    DEPOLARIZZAZIONE (disordine interno del blocco): anche la differenza di purezza
    tra blocchi e' torsione coarse. E' l'operatore che porta EC a TUTTI i livelli."""
    n = np.asarray(n, dtype=float)
    sq = np.sum(n * n, axis=1)                             # |n_i|^2
    diff2 = sq[:, None] + sq[None, :] - 2.0 * (n @ n.T)    # |n_i - n_j|^2 (N,N)
    return chi0 ** 2 * np.sum(W * diff2, axis=1)


def relax_step(theta, dphi, chi, dt, W=None, chi0=50.0, beta_sat=1e-8, rho_star=None):
    """Un passo di rilassamento STABILE dello spinore:
      - theta -> tan(theta/2)=|pendenza kink|  (beta/alpha = pendenza);
      - dphi  -> twist 180 di legame + winding 4pi (chiusura 720);
      - SATURAZIONE EC sullo spin (se W, rho_star dati): dove la torsione FISICA sorgentata
        dallo spin K2_spin eccede rho*, gli spin si ALLINEANO (bounce) -> riduce la torsione.
        E' Einstein-Cartan vero: lo spin genera la torsione e la torsione in eccesso e'
        respinta agendo sullo spin stesso.
    Ritorna (theta_new, dphi_new, diag)."""
    N = len(chi)
    s = np.abs(kink_slope(chi, chi0))

    th = np.clip(theta, 1e-6, np.pi - 1e-6)
    t_half = np.tan(th / 2.0)
    dtheta = J_SLOPE * (t_half - s) * (0.5 / np.cos(th / 2.0) ** 2)
    theta_new = np.clip(th - RELAX_THETA * dt * dtheta, 1e-6, np.pi - 1e-6)

    # CHIUSURA 720 ESATTA E TOPOLOGICA (non rilassata): il twist per legame E' il pattern
    # geometrico tau_i = 4pi/N + pi(-1)^i (180 alternato). Sum tau_i = 4pi per costruzione
    # -> winding = 4pi ESATTO, sempre. Nessun parametro (rimossi K_CLOSURE/RELAX_DPHI/J_TWIST).
    dphi_new = bond_twist_target(N)
    winding = float(np.sum(dphi_new))

    # --- SATURAZIONE / BOUNCE EC SULLO SPIN ---
    if W is not None and rho_star is not None:
        K2 = spin_torsion_K2(theta_new, dphi_new, W, chi0)
        gate = np.maximum(K2 - rho_star, 0.0)
        gate = gate / (rho_star + gate + 1e-30)          # [0,1): peso dell'eccesso
        theta_bar = W @ theta_new                        # media pesata vicini (W riga=1)
        theta_new = np.clip(theta_new - RELAX_SAT * dt * gate * (theta_new - theta_bar),
                            1e-6, np.pi - 1e-6)

    diag = {"winding": winding, "closure_err": float(winding - CLOSURE_4PI),
            "slope_err": float(np.mean(np.abs(t_half - s)))}
    return theta_new, dphi_new, diag


def init_from_field(chi, chi0):
    """Inizializza: theta da |pendenza kink| (beta/alpha=pendenza), dphi = tau (twist
    topologico 180/720 -> winding 4pi ESATTO da subito). chi0 = physics.chi_stable."""
    s = np.abs(kink_slope(chi, chi0))
    theta = np.clip(2.0 * np.arctan(s), 1e-6, np.pi - 1e-6)
    dphi = bond_twist_target(len(chi))
    return theta, dphi


# ---------------------------------------------------------------------------
# DIMOSTRAZIONE COMPLETA: stabile, chiude a 720, beta/alpha=pendenza, densita' chirali.
# ---------------------------------------------------------------------------
def _self_test():
    rng = np.random.default_rng(4)
    N = 24
    chi0 = 50.0
    chi = chi0 + 5.0 * rng.standard_normal(N)
    chi[10:15] = -chi0
    theta, dphi = init_from_field(chi, chi0)
    print("=" * 70)
    print("  MOTORE CHIRALE SPINORIALE self-test (completo)")
    print("=" * 70)
    print(f"  winding iniziale = {np.sum(dphi):.3f}  target 4pi = {CLOSURE_4PI:.3f}")
    for k in range(2000):
        theta, dphi, diag = relax_step(theta, dphi, chi, dt=1.0)
    a, b = spinor_components(theta, dphi)
    rho_sx, rho_dx = chirality_densities(theta)
    s = np.abs(kink_slope(chi, chi0))
    ratio = np.abs(b) / (np.abs(a) + 1e-12)
    norm = np.abs(a) ** 2 + np.abs(b) ** 2
    print(f"  dopo rilassamento (2000 step):")
    print(f"    winding finale = {np.sum(dphi):.4f}  closure_err = {diag['closure_err']:+.2e} (->0)")
    print(f"    |beta/alpha| vs |pendenza kink|: err medio = {np.mean(np.abs(ratio - s)):.2e}")
    print(f"    rho_SX(materia) max={rho_sx.max():.3f} (sul kink)  rho_DX(spazio) max={rho_dx.max():.3f}")
    print(f"    norma spinore |psi|^2: [{norm.min():.6f}, {norm.max():.6f}]")
    norm_ok = np.allclose(norm, 1.0, atol=1e-9)
    closes = abs(np.sum(dphi) - CLOSURE_4PI) < 0.2
    slope_ok = np.mean(np.abs(ratio - s)) < 0.05
    finite = np.all(np.isfinite(theta)) and np.all(np.isfinite(dphi))
    print(f"  NORMA=1 {'OK' if norm_ok else 'NO'}; CHIUDE a 720 {'OK' if closes else 'NO'}; "
          f"beta/alpha=PENDENZA {'OK' if slope_ok else 'NO'}; STABILE {'OK' if finite else 'NO'}")
    return norm_ok and closes and slope_ok and finite


if __name__ == "__main__":
    _self_test()
