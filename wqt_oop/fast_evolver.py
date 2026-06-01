"""
================================================================================
FAST EVOLVER — Evoluzione Accelerata con Metodi Spettrali e Simplettici
================================================================================

MOTIVAZIONE
-----------
Questo modulo implementa FastEvolver: un wrapper che usa SpectralBasis +
integratori simplettici per evolvere un SolitoneComposito L1 in modo piu'
veloce del metodo Eulero standard.

GARANZIA DI NON-ALTERAZIONE
-----------------------------
FastEvolver NON modifica SolitoneComposito o i suoi metodi.
E' un wrapper ESTERNO che:
  1. Legge lo stato del solitone (chi, vel dei 24 figli)
  2. Lo evolve con il metodo piu' veloce
  3. Riscrive lo stato aggiornato

I test esistenti continuano a passare identicamente.

CONFRONTO CON EVOLUZIONE STANDARD
-----------------------------------
Standard (Eulero, dt=0.01 per L4):
    Per ogni dei 331.776 segmenti: chi += v*dt, v += F*dt
    Errore: O(dt) per step -> deriva energetica
    dt_max: ~0.01 (stabilita' numerica)
    Tempo L4: ~8 min/step

FastEvolver (Verlet + spettrale, dt=0.1 per L1):
    Spettrale: 24 equazioni indipendenti invece di 24*24 accoppiate
    Verlet: O(dt^2) errore -> dt 10x piu' grande
    Errore energetico: O(dt^2) vs O(dt) -> 100x meno deriva
    Speedup atteso: 10-100x per livello L1

SCHEMA COMBINATO: STRANG SPLITTING
------------------------------------
    propagate_linear(dt/2)   [SpectralBasis: soluzione ANALITICA esatta]
    verlet_nonlinear(dt)      [doppio pozzo: unica parte da integrare]
    propagate_linear(dt/2)   [SpectralBasis: soluzione ANALITICA esatta]

Accuratezza: O(dt^3) per passo (O(dt^2) globale).
L'errore TOTALE e' dominato dalla parte non-lineare.

UTILIZZO
--------
    from wqt_oop.fast_evolver import FastEvolver

    # Crea il fast evolver per un SolitoneComposito L1
    fe = FastEvolver.from_solitone(solitone_l1, dt=0.1)

    # Evolve N passi (equivalente a solitone_l1.evolve(dt=0.01) x10 passi)
    for step in range(N):
        fe.step()

    # I valori chi/vel dei segmenti sono aggiornati in solitone_l1.children
================================================================================
"""

from __future__ import annotations

import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FastEvolver:
    """
    Evoluzione accelerata di un SolitoneComposito L1 con metodi analitici.

    Usa decomposizione spettrale (SpectralBasis) per la parte lineare e
    integratore simplettico (Verlet/Forest-Ruth) per la parte non-lineare.

    Parametri
    ---------
    solitone : SolitoneComposito
        Il solitone L1 da evolvere (DEVE avere N=24 figli SegmentoQuantistico).
    dt : float
        Passo temporale. Puo' essere 10-100x piu' grande di Eulero.
    method : str
        'verlet' (default) o 'forest_ruth' per l'integrazione non-lineare.
    use_spectral_linear : bool
        Se True, risolve la parte lineare analiticamente (SpectralBasis).
        Se False, usa solo Verlet per tutto (piu' semplice, meno veloce).
    """

    def __init__(
        self,
        solitone,
        dt: float = 0.1,
        method: str = "verlet",
        use_spectral_linear: bool = True,
    ):
        from .spectral_coupling import SpectralBasis
        from .symplectic_step import verlet_step, forest_ruth_step
        from .segmento_quantistico import SegmentoQuantistico

        self._solitone = solitone
        self._dt = dt
        self._method = method
        self._use_spectral = use_spectral_linear

        N = solitone.N_children
        physics = solitone.physics

        # Verifica che i figli siano tutti SegmentoQuantistico (L1)
        if not all(isinstance(c, SegmentoQuantistico) for c in solitone.children):
            raise ValueError("FastEvolver richiede un SolitoneComposito L1 "
                             "(tutti i figli devono essere SegmentoQuantistico).")

        # Costruisce la base spettrale dalla matrice di accoppiamento
        W_dense = (solitone.coupling_matrix.toarray()
                   if hasattr(solitone.coupling_matrix, 'toarray')
                   else solitone.coupling_matrix)
        self._basis = SpectralBasis.from_coupling_matrix(W_dense)

        # Parametri fisici
        self._alpha_K = physics.alpha_K
        self._gamma = 0.0  # sara' aggiornato dinamicamente da solitone
        self._mass = solitone.children[0].mass
        self._chi_0 = 4.5  # doppio pozzo: V = beta*(chi^2 - chi_0^2)^2
        self._beta = physics.beta_potential

        # Stima dt ottimale e avverte se troppo grande
        from .symplectic_step import estimate_optimal_dt
        omega_max = float(np.sqrt(physics.alpha_K * np.max(self._basis.eigenvalues_L)
                                   / self._mass + 1e-12))
        dt_safe = estimate_optimal_dt(omega_max, method=method)
        if dt > dt_safe * 2:
            logger.warning(
                "[FastEvolver] dt=%.3f supera il limite sicuro %.3f "
                "(omega_max=%.3f). Considera dt piu' piccolo.",
                dt, dt_safe, omega_max
            )

        self._step_count = 0
        logger.info(
            "[FastEvolver] Inizializzato: N=%d, dt=%.3f, method=%s, "
            "spectral=%s, omega_max=%.3f",
            N, dt, method, use_spectral_linear, omega_max
        )

    @classmethod
    def from_solitone(
        cls,
        solitone,
        dt: float = 0.1,
        method: str = "verlet",
    ) -> "FastEvolver":
        """Factory method con parametri di default ragionevoli."""
        return cls(solitone, dt=dt, method=method, use_spectral_linear=True)

    # ------------------------------------------------------------------
    # Forze fisiche
    # ------------------------------------------------------------------

    def _force_potential(self, chi: np.ndarray) -> np.ndarray:
        """
        Forza del potenziale doppio pozzo (non-lineare):

            V(chi) = beta * (chi^2 - chi_0^2)^2

        Forza: F = -dV/dchi = -4*beta*chi*(chi^2 - chi_0^2)
               = 4*beta*chi*(chi_0^2 - chi^2)

        Fisica: forza attrattiva verso i minimi +/-chi_0 (vuoti del campo).
        """
        return 4.0 * self._beta * chi * (self._chi_0 ** 2 - chi ** 2)

    def _force_coupling_nodal(self, chi: np.ndarray) -> np.ndarray:
        """
        Forza di accoppiamento nel dominio nodale:

            F_coupling_i = -alpha_K * sum_j W_ij * (chi_i - chi_j)
                         = -alpha_K * (L_graph @ chi)_i

        Fisica: forza coesiva che tende ad allineare i campi vicini.
        Per il reticolo cubottaedrico: 12 vicini con pesi esponenziali.
        """
        W = (self._solitone.coupling_matrix.toarray()
             if hasattr(self._solitone.coupling_matrix, 'toarray')
             else self._solitone.coupling_matrix)
        # L_graph @ chi = (D - W) @ chi
        degree = np.sum(W, axis=1)
        L_chi = degree * chi - W @ chi
        return -self._alpha_K * L_chi

    # ------------------------------------------------------------------
    # Passo di evoluzione principale
    # ------------------------------------------------------------------

    def step(self) -> None:
        """
        Esegue un passo di evoluzione con il metodo scelto.

        Schema Strang splitting (se use_spectral_linear=True):
            1. propagate_linear(dt/2)   <- analitico, zero errore
            2. verlet_nonlinear(dt)     <- doppio pozzo
            3. propagate_linear(dt/2)   <- analitico, zero errore

        Schema Verlet puro (se use_spectral_linear=False):
            verlet_step(F_total, dt)

        In entrambi i casi:
          - Aggiorna chi e vel in solitone.children[i]
          - NON chiama SolitoneComposito.evolve() (metodo esistente invariato)
          - Aggiorna il passo corrente per il guard Peano-VQT
        """
        from .symplectic_step import verlet_step, forest_ruth_step

        # Legge stato corrente dai figli (SegmentoQuantistico)
        chi = np.array([c.chi for c in self._solitone.children])
        vel = np.array([c.vel for c in self._solitone.children])

        # Legge gamma corrente dal solitone (puo' cambiare dinamicamente)
        gamma = getattr(self._solitone, '_last_gamma', 0.0)

        dt = self._dt

        if self._use_spectral:
            # Schema Strang: L(dt/2) -> N(dt) -> L(dt/2)
            chi_k = self._basis.to_spectral(chi)
            vel_k = self._basis.to_spectral(vel)

            # Passo 1: propagazione lineare per dt/2 (analitica)
            chi_k, vel_k = self._basis.propagate_linear(
                chi_k, vel_k,
                self._alpha_K, gamma, self._mass, dt / 2
            )
            chi_half = self._basis.from_spectral(chi_k)
            vel_half = self._basis.from_spectral(vel_k)

            # Passo 2: passo non-lineare per dt (doppio pozzo)
            if self._method == "forest_ruth":
                chi_mid, vel_mid = forest_ruth_step(
                    chi_half, vel_half, self._force_potential,
                    dt, gamma=gamma, mass=self._mass
                )
            else:
                chi_mid, vel_mid = verlet_step(
                    chi_half, vel_half, self._force_potential,
                    dt, gamma=gamma, mass=self._mass
                )

            # Passo 3: propagazione lineare per dt/2 (analitica)
            chi_k2 = self._basis.to_spectral(chi_mid)
            vel_k2 = self._basis.to_spectral(vel_mid)
            chi_k2, vel_k2 = self._basis.propagate_linear(
                chi_k2, vel_k2,
                self._alpha_K, gamma, self._mass, dt / 2
            )
            chi_new = self._basis.from_spectral(chi_k2)
            vel_new = self._basis.from_spectral(vel_k2)

        else:
            # Schema Verlet puro: F_total = F_potential + F_coupling
            def force_total(c):
                return self._force_potential(c) + self._force_coupling_nodal(c)

            if self._method == "forest_ruth":
                chi_new, vel_new = forest_ruth_step(
                    chi, vel, force_total, dt, gamma=gamma, mass=self._mass
                )
            else:
                chi_new, vel_new = verlet_step(
                    chi, vel, force_total, dt, gamma=gamma, mass=self._mass
                )

        # Scrive lo stato aggiornato nei figli
        for i, child in enumerate(self._solitone.children):
            child.chi = float(chi_new[i])
            child.vel = float(vel_new[i])

        self._step_count += 1

        # Aggiorna il contatore step del solitone (necessario per guard Peano-VQT)
        self._solitone._current_simulation_step += 1

    # ------------------------------------------------------------------
    # Diagnostica
    # ------------------------------------------------------------------

    def energy_check(self) -> dict:
        """
        Calcola l'energia del solitone e verifica la conservazione.

        Hamiltoniana totale: H = T + V + E_coupling
            T = sum_i 1/2 * m * v_i^2
            V = sum_i beta * (chi_i^2 - chi_0^2)^2
            E_coupling = 1/2 * alpha_K * chi^T L chi
        """
        chi = np.array([c.chi for c in self._solitone.children])
        vel = np.array([c.vel for c in self._solitone.children])

        T = 0.5 * self._mass * np.sum(vel ** 2)
        V = self._beta * np.sum((chi ** 2 - self._chi_0 ** 2) ** 2)
        W = (self._solitone.coupling_matrix.toarray()
             if hasattr(self._solitone.coupling_matrix, 'toarray')
             else self._solitone.coupling_matrix)
        degree = np.sum(W, axis=1)
        L_chi = degree * chi - W @ chi
        E_coupling = 0.5 * self._alpha_K * float(chi @ L_chi)

        return {
            "T": float(T),
            "V": float(V),
            "E_coupling": float(E_coupling),
            "H": float(T + V + E_coupling),
            "step": self._step_count,
        }
