"""
================================================================================
ZERO-POINT MOTOR — Modo di Nyquist (lambda = 2 l_P) come anti-congelamento
================================================================================

Principio fondativo VQT (scala di Planck):
  Il modo di lunghezza d'onda minima del reticolo (lambda = 2 l_P), ovvero il
  modo "staggered" u_i = (-1)^i, deve portare SEMPRE un quanto di punto-zero
  E_zp > 0. Cosi' il manifold non puo' mai congelarsi: e' lo zero-point geometrico
  intrinseco, indipendente dalla temperatura.

Meccanismo (one-sided floor):
  1. Proietta la velocita' sul modo staggered:  A = (1/sqrt(N)) * sum_i (-1)^i v_i
  2. Energia cinetica del modo:                 E_stag = 0.5 * A^2
  3. Se E_stag < E_zp: riporta |A| al floor sqrt(2 E_zp), iniettando il minimo.
     (mai sottrae energia -> i modi piu' bassi e la fisica Ramo B restano intatti)

Interpretazione fisica:
  La dissipazione FDT cerca di drenare il modo; lo zero-point lo ricarica al floor.
  Il bilancio stazionario e' un modo di Nyquist sempre attivo = "vuoto vivo"
  (sigma_inf > 0) come FATTO STRUTTURALE, non come artefatto termico.

================================================================================
"""

from __future__ import annotations
import numpy as np
from typing import Tuple


def staggered_basis(n: int) -> np.ndarray:
    """Vettore di Nyquist normalizzato: u_i = (-1)^i / sqrt(n)."""
    u = np.empty(n)
    u[0::2] = 1.0
    u[1::2] = -1.0
    return u / np.sqrt(n)


def staggered_amplitude(values: np.ndarray) -> float:
    """Ampiezza della componente staggered (proiezione su u)."""
    u = staggered_basis(len(values))
    return float(np.dot(values, u))


def enforce_nyquist_zero_point(
    velocities: np.ndarray,
    E_zp: float,
) -> Tuple[np.ndarray, float]:
    """
    Applica il floor di punto-zero al modo staggered delle velocita'.

    Parameters
    ----------
    velocities : ndarray (N,)
        Velocita' dei segmenti (mass = 1 in unita' naturali).
    E_zp : float
        Energia di punto-zero del modo di Nyquist (> 0).

    Returns
    -------
    v_new : ndarray (N,)
        Velocita' con il modo staggered riportato almeno al floor.
    E_injected : float
        Energia cinetica iniettata in questo step (>= 0).
    """
    v = np.asarray(velocities, dtype=float)
    n = len(v)
    if n < 2 or E_zp <= 0.0:
        return v.copy(), 0.0

    u = staggered_basis(n)
    A = float(np.dot(v, u))              # ampiezza staggered corrente
    E_stag = 0.5 * A * A                 # energia cinetica del modo (mass=1)

    if E_stag >= E_zp:
        return v.copy(), 0.0             # gia' sopra il floor: non tocca nulla

    # Riporta |A| al floor, preservando il segno (o + se A==0)
    A_floor = np.sqrt(2.0 * E_zp)
    A_new = A_floor if A >= 0.0 else -A_floor
    v_new = v + (A_new - A) * u          # corregge SOLO la componente staggered
    E_injected = 0.5 * A_new * A_new - E_stag
    return v_new, float(E_injected)


def E_zp_from_amplitude(epsilon_v: float, n: int) -> float:
    """
    Converte un'ampiezza di velocita' staggered per-segmento (epsilon_v)
    nell'energia di punto-zero corrispondente.

    Se ogni segmento oscilla con |v_stag_i| = epsilon_v nel modo (-1)^i, allora
    A = epsilon_v * sqrt(n)  e  E_zp = 0.5 * epsilon_v^2 * n.
    """
    return 0.5 * epsilon_v * epsilon_v * n


# ============================================================================
# Applicazione a un SolitoneComposito L1 (24 SegmentoQuantistico)
# ============================================================================

def apply_to_l1_soliton(soliton, E_zp: float) -> float:
    """
    Applica il floor di punto-zero alle velocita' dei segmenti figli di un
    SolitoneComposito L1. Ritorna l'energia iniettata.

    Richiede che i figli espongano l'attributo `.vel` (SegmentoQuantistico).
    """
    children = soliton.children
    vels = np.array([c.vel for c in children], dtype=float)
    v_new, E_inj = enforce_nyquist_zero_point(vels, E_zp)
    for c, vv in zip(children, v_new):
        c.vel = float(vv)
    return E_inj
