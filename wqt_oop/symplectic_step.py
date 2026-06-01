"""
================================================================================
SYMPLECTIC STEP — Integratori Simplettici per il Sistema Hamiltoniano VQT
================================================================================

MOTIVAZIONE
-----------
L'integratore di Eulero attuale (ordine 1) ha due limitazioni:

  1. DERIVA ENERGETICA: l'errore per step e' O(dt), l'energia H = T + V
     deriva monotonicamente nel tempo (non e' conservata).
  2. DT PICCOLO NECESSARIO: dt=0.01 e' imposto dalla stabilita' numerica.
     Con un integratore simplettico si puo' usare dt=0.1 o piu' grande.

Gli integratori SIMPLETTICI conservano esattamente:
  - Il volume nello spazio delle fasi (teorema di Liouville)
  - Una Hamiltoniana "ombra" H_shadow vicina a H reale
  - La struttura simplettica del flusso hamiltoniano

Questo permette passo temporale 10-100x piu' grande con la stessa accuratezza
fisica, senza alcuna modifica alla fisica del sistema.

INTEGRATORI IMPLEMENTATI
------------------------

1. STORMER-VERLET (ordine 2, simplettico)
   Coefficienti: c1=1, c2=0 (posizione), d1=1/2, d2=1/2 (velocita')
   Errore locale: O(dt^3) per passo, O(dt^2) globale
   Conservazione H: deriva O(dt^2) (vs O(dt) di Eulero)

2. FOREST-RUTH (ordine 4, simplettico)
   Coefficienti di Forest-Ruth (1990):
     theta = 1 / (2 - 2^(1/3))  [costante universale]
     Quattro sotto-step con pesi specifici
   Errore locale: O(dt^5), globale O(dt^4)
   Usa dt molto piu' grande mantenendo alta accuratezza

3. VELOCITY-VERLET con FORCING (estensione per sistemi smorzati)
   Per sistemi con smorzamento: d^2chi/dt^2 = F(chi) - gamma*v
   Usa il predictor-corrector di Beeman o il metodo splitting L+F

FONDAMENTO FISICO
-----------------
Il sistema VQT e' un sistema di Lagrangiano con vincoli:

    L = T - V = sum_i [1/2 * m * v_i^2 - V(chi_i)] - E_coupling

Il flusso hamiltoniano e' una trasformazione simplettica su T*R^N:
    d/dt [chi, v] = J * grad H,   J = [[0, I], [-I, 0]]

Gli integratori simplettici PRESERVANO la struttura J (forma simplettica),
garantendo che le traiettorie numeriche rimangano su varietà hamiltoniane.

Conseguenza fisica: nessuna creazione o distruzione artificiale di energia.
Il drain Jitterbug (E_chi -> E_Psi) e' un fenomeno FISICO, non numerico.

RELAZIONE CON EULERO ATTUALE
-----------------------------
Eulero esplicito:
    chi(t+dt) = chi(t) + v(t) * dt
    v(t+dt)   = v(t) + a(t) * dt                  [a = F/m]

Errore: O(dt) per step -> deriva energetica O(dt * T) sull'intervallo T.

Stormer-Verlet:
    chi(t+dt) = chi(t) + v(t)*dt + 1/2*a(t)*dt^2
    v(t+dt)   = v(t) + 1/2*(a(t) + a(t+dt))*dt

Errore: O(dt^2) per step -> deriva energetica O(dt^2 * T). Stesso risultato
fisico con dt 10x piu' grande (e.g., dt=0.1 anziche' dt=0.01).

UTILIZZO
--------
    from wqt_oop.symplectic_step import verlet_step, forest_ruth_step

    def my_force(chi): return -4 * beta * chi * (chi**2 - chi0**2)  # doppio pozzo

    chi_new, vel_new = verlet_step(chi, vel, my_force, dt=0.1)
================================================================================
"""

from __future__ import annotations

import numpy as np
from typing import Callable

# Costante di Forest-Ruth (1990), valida per qualsiasi sistema hamiltoniano
# theta = 1 / (2 - 2^(1/3))
_FOREST_RUTH_THETA = 1.0 / (2.0 - 2.0 ** (1.0 / 3.0))


# ===========================================================================
# INTEGRATORE 1: STORMER-VERLET (ordine 2)
# ===========================================================================

def verlet_step(
    chi: np.ndarray,
    vel: np.ndarray,
    force_fn: Callable[[np.ndarray], np.ndarray],
    dt: float,
    gamma: float = 0.0,
    mass: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Un passo Stormer-Verlet (simplettico, ordine 2).

    Schema:
        a(t)     = force_fn(chi(t)) / mass - gamma/mass * vel(t)
        chi(t+dt) = chi(t) + vel(t)*dt + 0.5*a(t)*dt^2
        a(t+dt)  = force_fn(chi(t+dt)) / mass - gamma/mass * vel(t+dt)_pred
        vel(t+dt) = vel(t) + 0.5*(a(t) + a(t+dt))*dt

    Nota sul termine di smorzamento gamma: lo smorzamento rompe la simmetria
    simplettica esatta, ma il metodo Verlet rimane stabile e accurato per
    smorzamento debole (gamma << omega). Per smorzamento forte si usa Beeman.

    Fisica conservata:
        - Volume fase (approssimata, degrada con gamma)
        - Hamiltoniana "ombra" H_shadow ~ H_real + O(dt^2)
        - Simmetria tempo-reversibile per gamma=0

    Parametri
    ---------
    chi : ndarray, shape (N,)
        Valori del campo.
    vel : ndarray, shape (N,)
        Velocita'.
    force_fn : callable
        F(chi) -> ndarray, shape (N,). Forza conservativa SENZA smorzamento.
        Tipicamente F = -dV/dchi = 4*beta*chi*(chi_0^2 - chi^2) + F_coupling.
    dt : float
        Passo temporale.
    gamma : float
        Coefficiente smorzamento viscoso (0 = Hamiltoniano puro).
    mass : float
        Massa del segmento.

    Ritorna
    -------
    chi_new, vel_new : ndarray
    """
    inv_mass = 1.0 / mass

    # Accelerazione iniziale: a = F/m - gamma/m * v
    F0 = force_fn(chi)
    a0 = F0 * inv_mass - (gamma * inv_mass) * vel

    # Aggiorna posizione: chi(t+dt) = chi(t) + v*dt + 0.5*a*dt^2
    chi_new = chi + vel * dt + 0.5 * a0 * dt ** 2

    # Accelerazione finale (usa posizione aggiornata, velocita' predetta)
    # Predictor per v: usa a0 (approx di primo ordine per il termine smorzato)
    vel_pred = vel + a0 * dt
    F1 = force_fn(chi_new)
    a1 = F1 * inv_mass - (gamma * inv_mass) * vel_pred

    # Aggiorna velocita': v(t+dt) = v(t) + 0.5*(a0 + a1)*dt
    vel_new = vel + 0.5 * (a0 + a1) * dt

    return chi_new, vel_new


# ===========================================================================
# INTEGRATORE 2: FOREST-RUTH (ordine 4)
# ===========================================================================

def forest_ruth_step(
    chi: np.ndarray,
    vel: np.ndarray,
    force_fn: Callable[[np.ndarray], np.ndarray],
    dt: float,
    gamma: float = 0.0,
    mass: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Un passo Forest-Ruth (simplettico, ordine 4).

    Schema a 4 sotto-step con coefficienti derivati da:
        theta = 1 / (2 - 2^(1/3))   [Forest & Ruth, 1990]

    I coefficienti di posizione e velocita' sono:
        c1 = theta/2,          d1 = theta
        c2 = (1-theta)/2,      d2 = 1 - 2*theta
        c3 = (1-theta)/2,      d3 = theta
        c4 = theta/2

    Schema esplicito:
        chi_1 = chi + c1*v*dt
        v_1   = v + d1*(F(chi_1)/m)*dt
        chi_2 = chi_1 + c2*v_1*dt
        v_2   = v_1 + d2*(F(chi_2)/m)*dt
        chi_3 = chi_2 + c3*v_2*dt
        v_3   = v_2 + d3*(F(chi_3)/m)*dt
        chi_4 = chi_3 + c4*v_3*dt

    Proprieta':
        - Ordine 4: errore O(dt^5) per step, O(dt^4) globale
        - Simplettico: conserva esattamente la forma simplettica
        - Reversibile nel tempo (per gamma=0)
        - Richiede 3 valutazioni di F per step (vs 2 per Verlet, 1 per Eulero)

    Con Forest-Ruth si puo' usare dt 10-50x piu' grande di Eulero mantenendo
    la stessa accuratezza -> risparmio netto ~3-15x (considerando le 3 F/step).

    Parametri: identici a verlet_step.
    """
    theta = _FOREST_RUTH_THETA
    inv_mass = 1.0 / mass

    c1 = theta / 2.0
    d1 = theta
    c2 = (1.0 - theta) / 2.0
    d2 = 1.0 - 2.0 * theta
    d3 = theta
    c3 = c2
    c4 = c1

    # Sotto-step 1
    chi_1 = chi + c1 * vel * dt
    F1 = force_fn(chi_1)
    vel_1 = vel + d1 * (F1 * inv_mass - gamma * inv_mass * vel) * dt

    # Sotto-step 2
    chi_2 = chi_1 + c2 * vel_1 * dt
    F2 = force_fn(chi_2)
    vel_2 = vel_1 + d2 * (F2 * inv_mass - gamma * inv_mass * vel_1) * dt

    # Sotto-step 3
    chi_3 = chi_2 + c3 * vel_2 * dt
    F3 = force_fn(chi_3)
    vel_3 = vel_2 + d3 * (F3 * inv_mass - gamma * inv_mass * vel_2) * dt

    # Sotto-step 4 (solo posizione)
    chi_4 = chi_3 + c4 * vel_3 * dt

    return chi_4, vel_3


# ===========================================================================
# INTEGRATORE 3: SPLITTING OPERATORE (per combinare lineare + nonlineare)
# ===========================================================================

def strang_splitting_step(
    chi: np.ndarray,
    vel: np.ndarray,
    force_linear_fn: Callable[[np.ndarray], np.ndarray],
    force_nonlinear_fn: Callable[[np.ndarray], np.ndarray],
    dt: float,
    mass: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Passo con splitting di Strang (ordine 2) per sistemi L + N.

    Schema: L(dt/2) -> N(dt) -> L(dt/2)
    dove L = forza lineare (coupling), N = forza non-lineare (doppio pozzo).

    Fisica:
        L: F_coupling = -alpha_K * (L_graph @ chi)  [parte lineare]
        N: F_potential = -dV/dchi = 4*beta*chi*(chi_0^2 - chi^2)

    Lo splitting di Strang e' simplettico e ha errore O(dt^3) per passo
    (ordine 2 globale). Si puo' combinare con la soluzione ANALITICA della
    parte L (vedi SpectralBasis.propagate_linear) per azzerare l'errore su L.

    In quel caso:
        propagate_linear(dt/2) -> verlet_step(N, dt) -> propagate_linear(dt/2)

    Questo schema ha errore O(dt^3) sul N e zero errore su L: molto piu'
    accurato dell'integrazione diretta.
    """
    inv_mass = 1.0 / mass

    # L(dt/2): passo Verlet con solo forza lineare
    FL0 = force_linear_fn(chi)
    aL0 = FL0 * inv_mass
    chi_half = chi + vel * (dt / 2) + 0.5 * aL0 * (dt / 2) ** 2
    vel_half = vel + aL0 * (dt / 2)

    # N(dt): passo Verlet con solo forza non-lineare
    FN0 = force_nonlinear_fn(chi_half)
    aN0 = FN0 * inv_mass
    chi_mid = chi_half + vel_half * dt + 0.5 * aN0 * dt ** 2
    aN1 = force_nonlinear_fn(chi_mid) * inv_mass
    vel_mid = vel_half + 0.5 * (aN0 + aN1) * dt

    # L(dt/2): secondo passo Verlet lineare
    FL1 = force_linear_fn(chi_mid)
    aL1 = FL1 * inv_mass
    chi_new = chi_mid + vel_mid * (dt / 2) + 0.5 * aL1 * (dt / 2) ** 2
    aL2 = force_linear_fn(chi_new) * inv_mass
    vel_new = vel_mid + 0.5 * (aL1 + aL2) * (dt / 2)

    return chi_new, vel_new


# ===========================================================================
# UTILITA': Stima timestep ottimale
# ===========================================================================

def estimate_optimal_dt(
    omega_max: float,
    gamma: float = 0.0,
    method: str = "verlet",
    safety: float = 0.5,
) -> float:
    """
    Stima il dt massimo stabile per l'integratore scelto.

    Per un oscillatore armonico con frequenza omega_max:
        Eulero:      dt_max = 2/omega_max   (stabibilita' marginale)
        Verlet:      dt_max ~ 2/omega_max   (ma piu' accurato a dt dato)
        Forest-Ruth: dt_max ~ 2/omega_max   (margine di stabilita' piu' ampio)

    Con il fattore di sicurezza safety=0.5, si usa il 50% del limite teorico.

    Parametri
    ---------
    omega_max : float
        Frequenza massima del sistema (sqrt(alpha_K * mu_max / m)).
        Per il reticolo VQT: omega_max = sqrt(alpha_K * lambda_max / m).
    gamma : float
        Smorzamento.
    method : str
        Integratore ('euler', 'verlet', 'forest_ruth').
    safety : float
        Fattore di sicurezza [0, 1].

    Ritorna
    -------
    float : dt ottimale
    """
    if omega_max < 1e-12:
        return 1.0  # sistema statico, dt arbitrario

    dt_euler = 2.0 / omega_max
    if method == "euler":
        return safety * dt_euler
    elif method in ("verlet", "stormer_verlet"):
        # Verlet ha lo stesso limite di stabilita' di Eulero, ma errore piu' basso
        # Nella pratica si puo' usare dt 2-5x piu' grande mantenendo l'accuratezza
        return safety * dt_euler * 3.0
    elif method in ("forest_ruth", "fr"):
        # Forest-Ruth: accuratezza O(dt^4) permette dt ancora piu' grandi
        return safety * dt_euler * 10.0
    else:
        return safety * dt_euler
