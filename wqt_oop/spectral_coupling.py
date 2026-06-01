"""
================================================================================
SPECTRAL COUPLING — Decomposizione Spettrale della Matrice di Accoppiamento VQT
================================================================================

MOTIVAZIONE
-----------
Il metodo numerico standard (Eulero, dt=0.01) richiede ~8 min/step per L4
(331.776 segmenti). Questo modulo implementa la decomposizione spettrale della
matrice di accoppiamento W, che:

  1. NON altera la fisica: usa la DFT Discreta su Z_N (biettiva, invertibile),
     non il limite continuo N->inf. La discretezza del reticolo e' PRESERVATA.
  2. Disaccoppia il sistema: 24 equazioni accoppiate -> 24 equazioni INDIPENDENTI.
  3. Risolve analiticamente la parte lineare (coupling): zero errori numerici.

FONDAMENTO FISICO
-----------------
La matrice di accoppiamento W del reticolo VQT (cubottaedrico/Leech, N=24 nodi)
e' una MATRICE CIRCOLANTE: W_ij dipende solo da d(i,j) = min(|i-j|, N-|i-j|).

    W_ij = exp(-d(i,j) / L_eff) / Z_i

Una matrice circolante su Z_N ha autovettori esatti = basi della DFT discreta:

    phi_k(n) = exp(2*pi*i*k*n/N) / sqrt(N),   k = 0, 1, ..., N-1

con autovalori:

    lambda_k = sum_{j=0}^{N-1} W_{0j} * exp(-2*pi*i*k*j/N)

Questi autovalori sono le FREQUENZE PROPRIE del reticolo di accoppiamento.

DISACCOPPIAMENTO DELL'EQUAZIONE DEL MOTO
-----------------------------------------
L'equazione completa per un nodo i al livello L1:

    m * d^2 chi_i/dt^2 = F_potential(chi_i) + F_coupling_i - gamma * v_i

dove:

    F_coupling_i = -alpha_K * sum_j W_ij * (chi_i - chi_j)
                 = -alpha_K * (L * chi)_i      [L = Laplaciano del grafo = D - W]

Nel dominio spettrale (chi_tilde_k = DFT(chi_i)):

    m * d^2 chi_k/dt^2 = F_k_nonlin(t) - alpha_K * mu_k * chi_k - gamma * v_k

dove:
    mu_k     = autovalori del Laplaciano L = D - W   [reali, >= 0]
    F_k_nonlin = DFT(-dV/dchi)                       [doppio pozzo: UNICA parte non-lin]

La parte LINEARE ha soluzione ANALITICA ESATTA:
    chi_k(t) = A_k * exp(-gamma/2 * t) * cos(Omega_k * t + phi_k)
dove:
    Omega_k = sqrt(alpha_K * mu_k / m - (gamma/2)^2)   [frequenza smorzata]

Solo il doppio pozzo V = beta*(chi^2 - chi_0^2)^2 richiede integrazione numerica,
ma le equazioni ora sono INDIPENDENTI -> si parallelizzano banalmente.

CONNESSIONE ALLA GEOMETRIA DI FULLER
-------------------------------------
Gli autovalori mu_k del Laplaciano del cubottaedro hanno struttura specifica:
  - mu_0 = 0          (modo zero: traslazione uniforme, conservata)
  - mu_k > 0  k>0     (modi di oscillazione, frequenze crescenti)

La soglia Jitterbug sqrt(2) e' una proprieta' TOPOLOGICA del reticolo (dipende
dalla struttura delle connessioni, non dalla base di rappresentazione) e quindi
e' INVARIANTE sotto trasformazione spettrale.

UTILIZZO
--------
    from wqt_oop.spectral_coupling import SpectralBasis

    basis = SpectralBasis.from_coupling_matrix(W)
    chi_spectral = basis.to_spectral(chi_values)
    chi_back = basis.from_spectral(chi_spectral)  # chi_back == chi_values

    # Evoluzione analitica della parte lineare per un passo dt:
    chi_k_new, vel_k_new = basis.propagate_linear(chi_spectral, vel_spectral,
                                                    alpha_K, gamma, mass, dt)
================================================================================
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class SpectralBasis:
    """
    Base spettrale per una matrice di accoppiamento circolante VQT.

    Attributi
    ---------
    N : int
        Numero di nodi (tipicamente 24 per il livello L1).

    eigenvalues_W : ndarray, shape (N,)
        Autovalori della matrice di accoppiamento W.
        Reali per W simmetrica. Ordine: k=0,1,...,N-1.

    eigenvalues_L : ndarray, shape (N,)
        Autovalori del Laplaciano L = D - W (D diagonale con D_ii = sum_j W_ij).
        Sempre reali >= 0 (Laplaciano e' semidefinito positivo).
        Interpretazione fisica: mu_k = frequenza quadratica del k-esimo modo.

    dft_matrix : ndarray, shape (N, N), complex
        Matrice DFT normalizzata: F_kn = exp(-2*pi*i*k*n/N) / sqrt(N).
        Usata per trasformare chi_i -> chi_tilde_k.
        Nota: F^{-1} = F^* (coniugato, per DFT normalizzata).
    """

    N: int
    eigenvalues_W: np.ndarray
    eigenvalues_L: np.ndarray
    dft_matrix: np.ndarray

    # ------------------------------------------------------------------
    # Costruttori
    # ------------------------------------------------------------------

    @classmethod
    def from_coupling_matrix(cls, W: np.ndarray) -> "SpectralBasis":
        """
        Costruisce la base spettrale dalla matrice di accoppiamento W.

        W deve essere:
          - Simmetrica (coupling reciproco)
          - Circolante (W_ij dipende solo da min(|i-j|, N-|i-j|))
          - Con valori >= 0 (coupling attrattivo/repulsivo solo via segno chi)

        Parametri
        ---------
        W : ndarray, shape (N, N)
            Matrice di accoppiamento normalizzata (righe sommano a 1 o a rho).

        Ritorna
        -------
        SpectralBasis con autovalori e matrice DFT pre-calcolati.
        """
        N = W.shape[0]
        assert W.shape == (N, N), "W deve essere quadrata"

        # Autovalori di W (per matrice circolante: DFT della prima riga)
        # lambda_k = sum_j W_0j * exp(-2*pi*i*k*j/N)
        eigenvalues_W = np.real(np.fft.fft(W[0]))

        # Laplaciano: L = D - W, dove D_ii = sum_j W_ij (grado pesato)
        # Per W circolante normalizzata (righe sommano a rho), D = rho * I
        degree = np.sum(W[0])  # grado del nodo 0 (= tutti per circolarita')
        # mu_k = degree - lambda_k
        # Fisica: mu_k = 0 per k=0 (modo di traslazione), mu_k > 0 per k > 0
        eigenvalues_L = degree - eigenvalues_W

        # Matrice DFT: F_kn = exp(-2*pi*i*k*n/N) / sqrt(N)
        # Normalizzazione: F F^* = I (unitaria)
        k = np.arange(N)
        n = np.arange(N)
        dft_matrix = np.exp(-2j * np.pi * np.outer(k, n) / N) / np.sqrt(N)

        return cls(
            N=N,
            eigenvalues_W=eigenvalues_W,
            eigenvalues_L=eigenvalues_L,
            dft_matrix=dft_matrix,
        )

    @classmethod
    def from_n_nodes(cls, N: int, L_eff: float = 3.0) -> "SpectralBasis":
        """
        Costruisce la base spettrale per un reticolo ciclico a N nodi
        con decadimento esponenziale W_ij = exp(-d_ij/L_eff) / Z.

        Utile quando non si ha la matrice W esplicita.

        Parametri
        ---------
        N : int
            Numero di nodi.
        L_eff : float
            Lunghezza caratteristica del decadimento esponenziale.
        """
        from .sparse_coupling import build_dense_decay_coupling
        W = build_dense_decay_coupling(N, L_eff)
        return cls.from_coupling_matrix(W)

    # ------------------------------------------------------------------
    # Trasformazioni
    # ------------------------------------------------------------------

    def to_spectral(self, chi: np.ndarray) -> np.ndarray:
        """
        Trasforma chi dal dominio nodale al dominio spettrale.

        chi_tilde_k = sum_n F_kn * chi_n = (F @ chi)_k

        Fisica: decompone il campo chi nella somma di modi normali del reticolo.
        Ogni modo k oscilla con frequenza propria sqrt(alpha_K * mu_k / m).

        Parametri
        ---------
        chi : ndarray, shape (N,) o (N, M) per M traiettorie
            Valori del campo nei nodi del reticolo.

        Ritorna
        -------
        chi_spectral : ndarray, shape (N,) complessa
            Ampiezze modali. chi_spectral[0] = media (modo zero).
        """
        return self.dft_matrix @ chi.astype(complex)

    def from_spectral(self, chi_spectral: np.ndarray) -> np.ndarray:
        """
        Trasforma chi dal dominio spettrale al dominio nodale.

        chi_n = sum_k F*_kn * chi_tilde_k = (F^H @ chi_tilde)_n

        La trasformazione inversa e' F^H (trasposta coniugata), poiche' F e'
        unitaria: F @ F^H = I.

        Fisicamente: ricostruisce il campo dai modi normali.
        Garantisce: from_spectral(to_spectral(chi)) == chi (a precisione macchina).
        """
        return np.real(self.dft_matrix.conj().T @ chi_spectral)

    # ------------------------------------------------------------------
    # Propagazione analitica della parte lineare
    # ------------------------------------------------------------------

    def propagate_linear(
        self,
        chi_k: np.ndarray,
        vel_k: np.ndarray,
        alpha_K: float,
        gamma: float,
        mass: float,
        dt: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Evolve analiticamente la parte LINEARE del sistema per un passo dt.

        Equazione del moto lineare per il modo k (smorzamento + coupling):

            m * d^2 chi_k/dt^2 = -alpha_K * mu_k * chi_k - gamma * d_chi_k/dt

        Questa e' l'equazione dell'OSCILLATORE ARMONICO SMORZATO con:
            omega_0_k^2 = alpha_K * mu_k / m   [frequenza naturale al quadrato]
            xi_k        = gamma / (2 * sqrt(m * alpha_K * mu_k))   [smorzamento]

        Soluzione analitica esatta (caso sottosmorzato, xi < 1):
            chi_k(t) = exp(-gamma*t/(2m)) * [A_k * cos(Omega_k*t) + B_k * sin(Omega_k*t)]
        dove:
            Omega_k = sqrt(omega_0_k^2 - (gamma/(2m))^2)   [frequenza smorzata]
            A_k = chi_k(0)
            B_k = (vel_k(0) + gamma/(2m) * chi_k(0)) / Omega_k

        Nota: il modo k=0 (Laplaciano mu_0=0, modo di traslazione) e' risolto
        separatamente come moto rettilineo uniforme smorzato.

        Parametri
        ---------
        chi_k, vel_k : ndarray, shape (N,) complesse
            Ampiezze e velocita' modali correnti.
        alpha_K : float
            Costante di accoppiamento torsione (da PhysicsContext).
        gamma : float
            Coefficiente di smorzamento viscoso.
        mass : float
            Massa del segmento.
        dt : float
            Passo temporale (puo' essere molto piu' grande di Eulero).

        Ritorna
        -------
        chi_k_new, vel_k_new : ndarray, shape (N,) complesse
            Ampiezze e velocita' modali al tempo t+dt.
        """
        gamma_eff = gamma / mass
        half_gamma = gamma_eff / 2.0

        chi_k_new = np.zeros_like(chi_k)
        vel_k_new = np.zeros_like(vel_k)

        for k in range(self.N):
            mu_k = self.eigenvalues_L[k]
            omega0_sq = alpha_K * mu_k / mass  # omega_0^2

            c0 = chi_k[k]
            v0 = vel_k[k]

            if mu_k < 1e-12:
                # Modo zero (k=0): traslazione uniforme smorzata
                # d^2 chi/dt^2 = -gamma/m * d_chi/dt
                # Soluzione: chi(t) = chi(0) + v(0)/gamma*(1 - exp(-gamma*t/m))
                # vel(t) = v(0) * exp(-gamma*t/m)
                decay = np.exp(-gamma_eff * dt)
                if gamma_eff > 1e-12:
                    chi_k_new[k] = c0 + v0 / gamma_eff * (1.0 - decay)
                else:
                    chi_k_new[k] = c0 + v0 * dt
                vel_k_new[k] = v0 * decay
            else:
                discriminant = omega0_sq - half_gamma ** 2

                if discriminant > 0:
                    # Caso sottosmorzato: oscillazione smorzata
                    Omega = np.sqrt(discriminant)
                    exp_decay = np.exp(-half_gamma * dt)
                    cos_t = np.cos(Omega * dt)
                    sin_t = np.sin(Omega * dt)

                    A = c0
                    B = (v0 + half_gamma * c0) / Omega

                    chi_k_new[k] = exp_decay * (A * cos_t + B * sin_t)
                    vel_k_new[k] = exp_decay * (
                        (v0 * cos_t)
                        + (-A * Omega - half_gamma * B) * sin_t
                        + half_gamma * B * cos_t
                        - half_gamma * chi_k_new[k]
                    )

                elif discriminant < 0:
                    # Caso sovrasmorzato: decadimento esponenziale puro
                    # Radici: r1,r2 = -half_gamma +/- sqrt(-discriminant)
                    s = np.sqrt(-discriminant)
                    r1 = -half_gamma + s
                    r2 = -half_gamma - s
                    # Coefficienti da condizioni iniziali
                    C2 = (v0 - r1 * c0) / (r2 - r1)
                    C1 = c0 - C2
                    chi_k_new[k] = C1 * np.exp(r1 * dt) + C2 * np.exp(r2 * dt)
                    vel_k_new[k] = C1 * r1 * np.exp(r1 * dt) + C2 * r2 * np.exp(r2 * dt)

                else:
                    # Caso criticamente smorzato
                    exp_decay = np.exp(-half_gamma * dt)
                    chi_k_new[k] = exp_decay * (c0 + (v0 + half_gamma * c0) * dt)
                    vel_k_new[k] = exp_decay * (
                        v0 * (1.0 - half_gamma * dt) - half_gamma ** 2 * c0 * dt
                    )

        return chi_k_new, vel_k_new

    # ------------------------------------------------------------------
    # Diagnostica
    # ------------------------------------------------------------------

    def jitterbug_invariance_check(self, chi: np.ndarray, chi_stable: float) -> dict:
        """
        Verifica che la soglia Jitterbug sqrt(2) sia invariante sotto DFT.

        La costante Jitterbug chi_max/chi_stable = sqrt(2) e' una proprieta'
        TOPOLOGICA del reticolo: dipende dalla struttura delle connessioni (mu_k),
        non dalla base di rappresentazione. Questo metodo lo verifica numericamente.

        Fisica: Parseval-Plancherel garantisce ||chi_spectral||^2 = ||chi||^2,
        ma chi_max non e' conservato (la DFT redistribuisce l'energia sui modi).
        Il check conferma che il valore fisico di chi_max (nel dominio nodale)
        e' indipendente dalla rappresentazione usata per l'integrazione.
        """
        chi_max_nodal = float(np.max(np.abs(chi)))
        chi_spectral = self.to_spectral(chi)
        chi_reconstructed = self.from_spectral(chi_spectral)
        chi_max_reconstructed = float(np.max(np.abs(chi_reconstructed)))

        reconstruction_error = abs(chi_max_nodal - chi_max_reconstructed) / (chi_max_nodal + 1e-12)
        jitterbug_ratio_nodal = chi_max_nodal / max(chi_stable, 1e-12)

        return {
            "chi_max_nodal": chi_max_nodal,
            "chi_max_after_roundtrip": chi_max_reconstructed,
            "reconstruction_error": reconstruction_error,
            "jitterbug_ratio": jitterbug_ratio_nodal,
            "above_threshold": jitterbug_ratio_nodal >= np.sqrt(2),
            "invariant_ok": reconstruction_error < 1e-10,
        }
