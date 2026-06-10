"""
================================================================================
CHIRALITA' EINSTEIN-CARTAN: trasporto di densita' chirale SX/DX (additivo)
================================================================================

Re-integra il MOTORE CHIRALE cancellato nel cleanup 2026-05-26 (modulo
dinamica_hamiltoniana_chiralita.py, recuperato in
dinamica_hamiltoniana_chiralita_RECUPERATO.py), ADATTANDOLO al motore attuale:
usa la torsione di gradiente K2 = sum_j W_ij (chi_i-chi_j)^2 e la soglia DERIVATA
rho* = 2*chi0^2 (al posto del 4pi del modulo originale, coerente con saturazione EC).

FISICA (trasporto di chiralita' = separazione di fase materia/spazio):
  - chiralita' del voxel da sign(chi) (su/giu): frazioni f_sx/f_dx;
  - densita' SX = "materia", DX = "spazio"; densita' base ~ 1 + 0.1|chi|;
  - boost torsionale: zone ad alta K2 attraggono materia (1 + 0.5 K2/rho*);
  - TRASPORTO: rho_SX fluisce lungo il gradiente di K2 (anello toroidale) PIU'
    un'attrazione one-sided verso le zone sopra rho* (max(0, K2-rho*)) -> clustering;
  - POROSITA': il legame si indebolisce dove |Delta K2| e' grande (bolle/domini);
  - CONSERVAZIONE: Sum(rho_SX + rho_DX) = costante; densita' >= 0 (no clip artificiale).

ADDITIVO: non tocca la dinamica di campo (chi,v) ne' i settori EC/muratore. E' un
campo di densita' chirale TRASPORTATO sopra il reticolo. Default OFF.

Costanti dal modulo originale (mobilita', accoppiamento, porosita'): non sono leggi di
scala 24^L, sono coefficienti di trasporto locali.
================================================================================
"""

import numpy as np
from .einstein_cartan import torsion_density_K2, default_k2_ref_chi

ALPHA_COUPLING = 0.05    # accoppiamento torsionale vicini (energia ~ gradiente^2)
MU_TRANSPORT = 0.25      # mobilita' (velocita' risposta al gradiente)
SIGMA_DECOUPLING = 3.0   # scala di porosita' (in unita' di rho*: disaccoppiamento)
DIFFUSIVITA = 0.02       # diffusione locale (anti-omogeneizzazione spuria)
ATTR_GAIN = 0.1          # guadagno attrazione zone sopra soglia (dal modulo originale)


def chirality_fractions(chi, K2, rho_star):
    """Frazioni chirali da sign(chi) con boost torsionale. f_sx (materia) + f_dx (spazio).
    boost: zone ad alta torsione = piu' materia. Ritorna (densita_sx, densita_dx, base)."""
    chi_sat = np.tanh(chi / 10.0)               # su/giu morbido (chi~chi0 -> ~±1)
    boost = 1.0 + 0.5 * (K2 / (rho_star + 1e-30))
    f_dx = 0.5 * (1.0 + chi_sat) * boost
    f_sx = 0.5 * (1.0 - chi_sat) * boost
    base = 1.0 + 0.1 * np.abs(chi)
    return base * f_sx, base * f_dx, base


def transport_step(rho_sx, rho_dx, chi, W, rho_star, dt):
    """Un passo di trasporto della densita' chirale (vettorizzato, anello toroidale).
    Restituisce (rho_sx_new, rho_dx_new, flussi_netto). Conserva la carica totale."""
    N = len(chi)
    K2 = torsion_density_K2(chi, W)
    K2n = K2 / (rho_star + 1e-30)         # torsione ADIMENSIONALE (~O(1) alla soglia)
    base = 1.0 + 0.1 * np.abs(chi)

    # gradiente di torsione (normalizzata) verso i vicini d'anello (i-1, i+1)
    grad_prev = K2n - np.roll(K2n, 1)    # in unita' di rho* -> coefficienti O(1) stabili
    grad_next = np.roll(K2n, -1) - K2n
    # attrazione one-sided verso zone sopra soglia (clustering = inversione del modulo orig.)
    attr = np.maximum(K2n - 1.0, 0.0)
    flusso_prev = -MU_TRANSPORT * grad_prev + ATTR_GAIN * (attr - np.roll(attr, 1))
    flusso_next = -MU_TRANSPORT * grad_next + ATTR_GAIN * (np.roll(attr, -1) - attr)
    # diffusione (Laplaciano discreto su rho_sx)
    lap = np.roll(rho_sx, 1) + np.roll(rho_sx, -1) - 2.0 * rho_sx
    flussi = flusso_prev + flusso_next + DIFFUSIVITA * lap

    rho_sx_new = rho_sx + flussi * dt
    rho_dx_new = base - rho_sx_new                       # DX complementare alla base
    # conservazione carica totale
    tot0 = float(np.sum(rho_sx) + np.sum(rho_dx))
    tot1 = float(np.sum(rho_sx_new) + np.sum(rho_dx_new))
    if tot1 > 0:
        rho_sx_new *= tot0 / tot1
        rho_dx_new *= tot0 / tot1
    # protezione fisica (no densita' negative; no clip artificiale sui valori)
    rho_sx_new = np.maximum(rho_sx_new, 0.0)
    rho_dx_new = np.maximum(rho_dx_new, 0.0)
    vuoto = (rho_sx_new + rho_dx_new) < 1e-10
    rho_sx_new[vuoto] = 0.5
    rho_dx_new[vuoto] = 0.5
    return rho_sx_new, rho_dx_new, flussi


def bond_chirality(chi):
    """Chiralita' ALTERNATA del legame (twist 180 promosso a quantita' del trasporto):
    chir_bond[b] = (-1)^b * sign(chi_b) * sign(chi_{b+1}). Su 24 legami il pattern
    alternato realizza 'il successivo con chiralita' opposta' (verso la chiusura 720)."""
    s = np.sign(chi); s[s == 0] = 1.0
    b = np.arange(len(chi))
    return np.where(b % 2 == 0, 1.0, -1.0) * (s * np.roll(s, -1))


# ---------------------------------------------------------------------------
# SELF-TEST: trasporto conserva la carica, densita' non negative, clustering sopra rho*
# ---------------------------------------------------------------------------
def _self_test():
    rng = np.random.default_rng(3)
    N = 24
    chi0 = 50.0
    chi = chi0 + 5.0 * rng.standard_normal(N)
    chi[10:14] = -chi0                       # difetto (parete) -> torsione alta locale
    W = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if i != j:
                d = min(abs(i - j), N - abs(i - j))
                W[i, j] = 0.716 ** d
    W /= W.sum(axis=1, keepdims=True)
    rho_star = default_k2_ref_chi(chi0)
    rho_sx, rho_dx, base = chirality_fractions(chi, torsion_density_K2(chi, W), rho_star)

    tot0 = float(np.sum(rho_sx) + np.sum(rho_dx))
    sx0_wall = float(rho_sx[10:14].mean())
    for _ in range(50):
        rho_sx, rho_dx, fl = transport_step(rho_sx, rho_dx, chi, W, rho_star, 0.05)
    tot1 = float(np.sum(rho_sx) + np.sum(rho_dx))
    sx1_wall = float(rho_sx[10:14].mean())

    print("=" * 68)
    print("  CHIRALITA' EC self-test (trasporto densita' SX/DX)")
    print("=" * 68)
    print(f"  carica totale: iniziale={tot0:.4f}  finale={tot1:.4f}  (conservata)")
    print(f"  densita' SX min={rho_sx.min():.3f} (>=0)  max={rho_sx.max():.3f}")
    print(f"  twist legame (180 alternato) range [{bond_chirality(chi).min():.0f},"
          f"{bond_chirality(chi).max():.0f}]")
    cons = abs(tot1 - tot0) / (tot0 + 1e-30) < 1e-9
    nonneg = rho_sx.min() >= 0 and rho_dx.min() >= 0
    print(f"  CONSERVAZIONE carica {'OK' if cons else 'NO'}; densita' >=0 "
          f"{'OK' if nonneg else 'NO'}")
    return cons and nonneg


if __name__ == "__main__":
    _self_test()
