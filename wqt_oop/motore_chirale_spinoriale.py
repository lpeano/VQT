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

DINAMICA STABILE (rilassamento, gradiente di energia, NON esplode):
    E = J_SLOPE  * sum (tan(theta_i/2) - |s_i|)^2          [beta/alpha -> pendenza kink]
      + J_TWIST  * sum (1 - cos(dphi_i - tau_i))            [twist 180 per legame]
      + K_CLOSURE* (sum dphi_i - 4pi)^2                     [chiusura 720]
  s_i = pendenza locale del kink (gradiente di chi). (theta, dphi) <- discesa di gradiente.

ADDITIVO: lo spinore vive ACCANTO a (chi, v). Default OFF -> non tocca la dinamica di
campo. [DA CONFERMARE con Luca] l'aritmetica esatta 180->720 (qui: parte alternata +-pi
a somma nulla, media 4pi/N): scelta documentata.
================================================================================
"""

import numpy as np

HALF_TWIST = np.pi            # twist 180 deg per legame (half-twist)
CLOSURE_4PI = 4.0 * np.pi     # chiusura spinoriale 720 deg (spin-1/2)
J_SLOPE = 1.0                 # accoppiamento beta/alpha -> pendenza del kink
J_TWIST = 1.0                 # rigidita' del twist 180 per legame
K_CLOSURE = 0.05              # rigidita' della chiusura 720
RELAX_THETA = 0.10            # tasso di rilassamento di theta (stabile)
RELAX_DPHI = 0.10            # tasso di rilassamento dei twist di legame
SLOPE_SCALE = 50.0           # scala della pendenza (chi0): s = dchi / SLOPE_SCALE


def bond_twist_target(N):
    """Twist preferito per legame: tau_i = 4pi/N + HALF_TWIST*(-1)^i. Parte alternata
    (+-pi) a somma nulla -> Sum tau_i = 4pi (chiusura 720 consistente). Realizza
    'ogni legame 180 deg, chiralita' alternata, chiude a 720'."""
    i = np.arange(N)
    return CLOSURE_4PI / N + HALF_TWIST * np.where(i % 2 == 0, 1.0, -1.0)


def kink_slope(chi):
    """Pendenza locale del kink = gradiente centrato di chi (anello), normalizzato."""
    return (np.roll(chi, -1) - np.roll(chi, 1)) / (2.0 * SLOPE_SCALE)


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


def relax_step(theta, dphi, chi, dt):
    """Un passo di rilassamento STABILE: theta -> tan(theta/2)=|pendenza|; dphi -> twist
    180 di legame + winding 4pi. Ritorna (theta_new, dphi_new, diag)."""
    N = len(chi)
    tau = bond_twist_target(N)
    s = np.abs(kink_slope(chi))

    # settore theta: tan(theta/2) -> |s| (beta/alpha = pendenza del kink)
    th = np.clip(theta, 1e-6, np.pi - 1e-6)
    t_half = np.tan(th / 2.0)
    dtheta = J_SLOPE * (t_half - s) * (0.5 / np.cos(th / 2.0) ** 2)
    theta_new = np.clip(th - RELAX_THETA * dt * dtheta, 1e-6, np.pi - 1e-6)

    # settore dphi: twist 180 per legame + chiusura 720 (winding = Sum dphi -> 4pi)
    winding = float(np.sum(dphi))
    closure = winding - CLOSURE_4PI
    g = J_TWIST * np.sin(dphi - tau) + 2.0 * K_CLOSURE * closure
    dphi_new = dphi - RELAX_DPHI * dt * g

    diag = {"winding": winding, "closure_err": float(closure),
            "slope_err": float(np.mean(np.abs(t_half - s)))}
    return theta_new, dphi_new, diag


def init_from_field(chi):
    """Inizializza: theta da |pendenza kink| (beta/alpha=pendenza), dphi=0 (winding 0):
    il rilassamento porta dphi->tau e il winding a 4pi."""
    s = np.abs(kink_slope(chi))
    theta = np.clip(2.0 * np.arctan(s), 1e-6, np.pi - 1e-6)
    dphi = np.zeros_like(chi)
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
    theta, dphi = init_from_field(chi)
    print("=" * 70)
    print("  MOTORE CHIRALE SPINORIALE self-test (completo)")
    print("=" * 70)
    print(f"  winding iniziale = {np.sum(dphi):.3f}  target 4pi = {CLOSURE_4PI:.3f}")
    for k in range(2000):
        theta, dphi, diag = relax_step(theta, dphi, chi, dt=1.0)
    a, b = spinor_components(theta, dphi)
    rho_sx, rho_dx = chirality_densities(theta)
    s = np.abs(kink_slope(chi))
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
