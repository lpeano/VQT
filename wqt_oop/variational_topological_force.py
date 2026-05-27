"""
================================================================================
VARIATIONAL TOPOLOGICAL FORCE — Forze dal Potenziale Topologico VQT
================================================================================

Implementa il gradiente del potenziale topologico S [Eq. S-1]:

    S[χ, τ] = λ · Σᵢ (ρᵢ - ρ₀)² + γ · Σᵢ Ωᵢ

da cui si derivano le forze topologiche [Eq. FTOP-1]:

    F_top,j = -∂S/∂χⱼ = F_homeo,j + F_chiral,j

COMPONENTI:
    F_homeo,j  = -2λ (ρⱼ - ρ₀) ∂ρⱼ/∂χⱼ          [Eq. FH-1]
    F_chiral,j = -γ ∂(Σᵢ Ωᵢ)/∂χⱼ                  [Eq. FCH-1]

GRADIENTE CHIRALE (formula esatta, O(N) vettoriale):
    ∂(ΣΩ)/∂χⱼ = K_{j-1}(K²_{j-2} + K²ⱼ) - K_{j+1}(K²ⱼ + K²_{j+2})  [Eq. G-1]

INTEGRAZIONE SIMPLETTICA [Eq. INT-1]:
    U_tot(dt) = T_{dt/2} ∘ U_phys(dt) ∘ T_{dt/2}
    T_t: vⱼ ← vⱼ + F_top,j · t   (kick canonico)

Riferimento: TOPOLOGICAL_DYNAMICS.md
================================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from .abstract_soliton import AbstractSoliton

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

@dataclass
class TopologicalForceConfig:
    """
    Parametri del potenziale topologico S [Eq. S-1].

    Attributes
    ----------
    lambda_homeo : float
        Coefficiente omeostatico lambda. Governa la forza di ritorno verso rho_0.
        Regola: lambda * dt <= 0.1 per stabilita' numerica.
    gamma_chiral : float
        Coefficiente di frustrazione chirale gamma. Promuove alternanza K^2 ±180°.
        Tenere piccolo (0.001-0.05) per evitare instabilita'.
    rho_0 : float
        Set-point omeostatico base. Con auto_scale_rho_0=False e' il valore fisso.
        Con auto_scale_rho_0=True e' l'asintoto L→∞ di rho_0_eff(L).
    conserve_topology_charge : bool
        Se True, sottrae la media di F_top per garantire sum_j F_top,j = 0,
        preservando la carica topologica Q = sum(chi_i) [Assioma TC].
    auto_scale_rho_0 : bool
        Se True, il set-point si adatta automaticamente al livello frattale L
        usando la Legge FA [Eq. FA-2]:
            rho_0_eff(L) = rho_0 + delta_rho_fractal / 24^(L/2)
        Il sistema diventa auto-simile: nessun parametro da ricalcolare per
        ogni livello L.
        NOTA: la formula moltiplicativa rho_0_L0 * (1/sqrt(24))^L
        produce rho_0(L=2) ~ 0.037, in fase vacuum — numericamente instabile.
        Usare invece questa forma additiva, coerente con la Legge FA in
        TOPOLOGICAL_DYNAMICS.md.
    delta_rho_fractal : float
        Coefficiente di scaling per auto_scale_rho_0 [Eq. FA-2].
        Con rho_0=0.85 e delta_rho_fractal=0.05:
          L=1: rho_0_eff = 0.85 + 0.05/sqrt(24) ~ 0.860 (sotto rho*(L=1)~0.882)
          L=2: rho_0_eff = 0.85 + 0.05/24       ~ 0.852 (sotto rho*(L=2)~0.938)
        Il sistema esercita sempre pressione espansiva, indipendentemente da L.
    """
    lambda_homeo: float = 0.1
    gamma_chiral: float = 0.01
    rho_0: float = 0.90
    conserve_topology_charge: bool = True
    auto_scale_rho_0: bool = False
    delta_rho_fractal: float = 0.05

    def get_rho_0(self, level: int) -> float:
        """
        Restituisce il set-point effettivo per il livello frattale L.

        Se auto_scale_rho_0=False restituisce rho_0 (comportamento legacy).
        Se auto_scale_rho_0=True usa Legge FA [Eq. FA-2]:

            rho_0_eff(L) = rho_0 + delta_rho_fractal / 24^(L/2)

        rho_0 e' l'asintoto per L→∞.
        delta_rho_fractal > 0 → set-point piu' alto ai livelli bassi (L piccolo).
        delta_rho_fractal < 0 → set-point piu' basso ai livelli bassi.
        """
        if not self.auto_scale_rho_0:
            return self.rho_0
        n_voxels = 24 ** level
        correction = self.delta_rho_fractal / float(n_voxels ** 0.5)
        return float(np.clip(self.rho_0 + correction, 0.01, 0.99))


# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class VariationalTopologicalForce:
    """
    Calcola e applica le forze derivate dal potenziale topologico S [Eq. S-1].

    Approccio variazionale puro: nessuna logica if/else per il controllo.
    La dinamica emerge dai gradienti del potenziale.

    Usage
    -----
    >>> cfg = TopologicalForceConfig(lambda_homeo=0.1, rho_0=0.92)
    >>> force = VariationalTopologicalForce(cfg)
    >>> force.apply_symplectic_kick(universe, dt=0.005)  # mezzo-kick T_{dt/2}
    >>> universe.evolve(dt=0.01)                          # Strang Splitting fisico
    >>> force.apply_symplectic_kick(universe, dt=0.005)  # mezzo-kick T_{dt/2}
    """

    def __init__(self, config: TopologicalForceConfig):
        self.cfg = config
        self._level: int = 0          # Livello frattale corrente; impostare via set_level()
        self._force_rms_history: List[float] = []
        self._potential_history: List[float] = []

        logger.info(
            f"VariationalTopologicalForce initialized: "
            f"lambda={config.lambda_homeo}, gamma={config.gamma_chiral}, "
            f"rho_0={config.rho_0}, auto_scale={config.auto_scale_rho_0}"
        )

    def set_level(self, level: int) -> None:
        """
        Imposta il livello frattale L per il calcolo di rho_0_eff [Eq. FA-2].

        Chiamare prima di usare compute_forces / apply_symplectic_kick.
        TopologicalEvolutionWrapper lo chiama automaticamente da __init__.
        """
        self._level = level
        rho_0_eff = self.cfg.get_rho_0(level)
        logger.info(
            f"VariationalTopologicalForce: level={level}, "
            f"rho_0_eff={rho_0_eff:.4f} "
            f"(auto_scale={'ON' if self.cfg.auto_scale_rho_0 else 'OFF'})"
        )

    # ------------------------------------------------------------------
    # Raccolta foglie (struttura frattale)
    # ------------------------------------------------------------------

    def _collect_leaves(self, universe: AbstractSoliton) -> List:
        """
        Raccoglie ricorsivamente tutti i SegmentoQuantistico (foglie L0)
        dall'albero frattale. Supporta strutture L1, L2, LN.
        """
        from .segmento_quantistico import SegmentoQuantistico
        from .solitone_composito import SolitoneComposito

        if isinstance(universe, SegmentoQuantistico):
            return [universe]
        if isinstance(universe, SolitoneComposito):
            leaves: List = []
            for child in universe.children:
                leaves.extend(self._collect_leaves(child))
            return leaves
        return []

    # ------------------------------------------------------------------
    # Campi geometrici
    # ------------------------------------------------------------------

    @staticmethod
    def _torsion_field(chi: np.ndarray) -> np.ndarray:
        """
        K_i = (χ_{i+1} - χ_{i-1}) / 2     [Eq. T-1]

        Prima differenza circolare del campo χ.
        Misura la curvatura locale del manifold.
        """
        return (np.roll(chi, -1) - np.roll(chi, 1)) * 0.5

    def _constraint_fields(
        self,
        chi: np.ndarray,
        tau: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """
        Calcola ρᵢ, Kᵢ, Ωᵢ dallo stato corrente.

        Returns
        -------
        rho   : ndarray (N,) — densità vincolo [0,1]       [Eq. RHO-1]
        K     : ndarray (N,) — torsione locale              [Eq. T-1]
        Omega : ndarray (N,) — frustrazione chirale         [Eq. OM-1]
        K2_mean : float — torsione media quadratica
        """
        # --- Closure: f_closure,i = 1 - |τᵢ - τ̄| / τ_range  [Eq. FC-1] ---
        tau_mean  = float(np.mean(tau))
        tau_range = float(np.ptp(tau)) + 1e-12
        f_closure = 1.0 - np.abs(tau - tau_mean) / tau_range

        # --- Detorsione: torsione e frustrazione  [Eq. T-1, OM-1] ---
        K       = self._torsion_field(chi)
        K2      = K ** 2
        K2_mean = float(np.mean(K2)) + 1e-30

        # Ωᵢ = K²ᵢ · K²_{i+1}   [Eq. OM-1]
        Omega = K2 * np.roll(K2, -1)

        # f_detorsion,i = 1 / (1 + Ωᵢ/K̄²)  [Eq. FD-1]
        f_detorsion = 1.0 / (1.0 + Omega / K2_mean)

        # ρᵢ = ½ f_closure + ½ f_detorsion   [Eq. RHO-1]
        rho = np.clip(0.5 * f_closure + 0.5 * f_detorsion, 0.0, 1.0)

        return rho, K, Omega, K2_mean

    # ------------------------------------------------------------------
    # Gradiente del potenziale
    # ------------------------------------------------------------------

    def compute_forces(
        self,
        chi: np.ndarray,
        tau: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calcola F_top,j = -∂S/∂χⱼ  [Eq. FTOP-1].

        Parameters
        ----------
        chi : ndarray (N,) — valori campo χ dei voxel L0
        tau : ndarray (N,) — tempi propri τ dei voxel L0

        Returns
        -------
        F_top : ndarray (N,) — forza topologica per voxel
        rho   : ndarray (N,) — densità vincolo corrente
        Omega : ndarray (N,) — frustrazione chirale corrente
        """
        rho, K, Omega, K2_mean = self._constraint_fields(chi, tau)
        K2      = K ** 2
        rho_0_eff = self.cfg.get_rho_0(self._level)   # Legge FA [Eq. FA-2]
        delta_rho = rho - rho_0_eff

        # ================================================================
        # GRADIENTE CHIRALE ∂(ΣΩ)/∂χⱼ  [Eq. G-1]
        # Derivazione: χⱼ compare in K_{j-1} e K_{j+1} (non in Kⱼ).
        # ∂K²_{j-1}/∂χⱼ = K_{j-1},  ∂K²_{j+1}/∂χⱼ = −K_{j+1}
        # Termini di ΣΩ che dipendono da K²_{j-1}: Ω_{j-2}, Ω_{j-1}
        # Termini di ΣΩ che dipendono da K²_{j+1}: Ωⱼ,     Ω_{j+1}
        # ================================================================
        Km1  = np.roll(K,  1)    # K_{j-1}
        Kp1  = np.roll(K, -1)    # K_{j+1}
        K2m2 = np.roll(K2, 2)    # K²_{j-2}
        K2p2 = np.roll(K2, -2)   # K²_{j+2}

        # [Eq. G-1]
        dSigmaOmega_dchi = Km1 * (K2m2 + K2) - Kp1 * (K2 + K2p2)

        # ================================================================
        # GRADIENTE LOCALE ∂ρⱼ/∂χⱼ  [Eq. dRHO-1]
        # ================================================================

        # Contributo closure [Eq. dFC-1]: χ come proxy locale di τ
        chi_range = float(np.ptp(chi)) + 1e-12
        dF_closure_dchi = -np.sign(chi - np.mean(chi)) / chi_range

        # Contributo detorsione [Eq. dFD-1]: regola della catena su f_detorsion
        # f_detorsion = 1/(1 + Ω/K̄²)
        # ∂f_detorsion/∂χ = −1/(1+Ω/K̄²)² · (1/K̄²) · ∂Ω/∂χ
        inv_denom_sq    = 1.0 / (1.0 + Omega / K2_mean) ** 2
        dF_detorsion_dchi = -inv_denom_sq * dSigmaOmega_dchi / K2_mean

        # ∂ρ/∂χ = ½ ∂f_closure/∂χ + ½ ∂f_detorsion/∂χ   [Eq. dRHO-1]
        drho_dchi = 0.5 * dF_closure_dchi + 0.5 * dF_detorsion_dchi

        # ================================================================
        # FORZA OMEOSTATICA  F_homeo,j = -2λ(ρⱼ-ρ₀)∂ρⱼ/∂χⱼ  [Eq. FH-1]
        # ================================================================
        F_homeo = -2.0 * self.cfg.lambda_homeo * delta_rho * drho_dchi

        # ================================================================
        # FORZA CHIRALE  F_chiral,j = -γ ∂(ΣΩ)/∂χⱼ  [Eq. FCH-1]
        # ================================================================
        F_chiral = -self.cfg.gamma_chiral * dSigmaOmega_dchi

        F_top = F_homeo + F_chiral

        # Conservazione carica topologica Q = Σχᵢ  [Assioma TC]
        if self.cfg.conserve_topology_charge:
            F_top = F_top - float(np.mean(F_top))   # proiezione zero-sum

        return F_top, rho, Omega

    # ------------------------------------------------------------------
    # Kick simplettico
    # ------------------------------------------------------------------

    def apply_symplectic_kick(
        self,
        universe: AbstractSoliton,
        dt: float,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Applica il kick topologico T_t: vⱼ ← vⱼ + F_top,j · dt  [Eq. INT-1].

        Chiamare PRIMA e DOPO universe.evolve(dt) con dt/2 per ottenere
        lo Strang Splitting topologico O(dt²):

            U_tot(dt) = T_{dt/2} ∘ U_phys(dt) ∘ T_{dt/2}    [Eq. INT-1]

        Parameters
        ----------
        universe : AbstractSoliton
        dt : float
            Passo temporale del kick (usare dt/2 per Strang splitting).

        Returns
        -------
        F_top : ndarray (N,)
        rho   : ndarray (N,)
        Omega : ndarray (N,)
        """
        leaves = self._collect_leaves(universe)
        N = len(leaves)
        if N == 0:
            return np.zeros(0), np.zeros(0), np.zeros(0)

        chi = np.array([getattr(seg, 'chi',        0.0) for seg in leaves])
        tau = np.array([getattr(seg, 'tau_locale',  0.0) for seg in leaves])

        F_top, rho, Omega = self.compute_forces(chi, tau)

        # Kick canonico: vⱼ ← vⱼ + F_top,j · dt   [Eq. INT-1]
        for i, seg in enumerate(leaves):
            seg.vel = float(getattr(seg, 'vel', 0.0)) + float(F_top[i]) * dt

        # Diagnostica
        F_rms = float(np.sqrt(np.mean(F_top ** 2)))
        S_val = self.compute_potential_from_arrays(chi, tau)
        self._force_rms_history.append(F_rms)
        self._potential_history.append(S_val)

        logger.debug(
            f"Topo kick dt={dt:.4f}: "
            f"|F|_rms={F_rms:.3e}  S={S_val:.4e}  "
            f"ρ_mean={float(np.mean(rho)):.4f}"
        )

        return F_top, rho, Omega

    # ------------------------------------------------------------------
    # Potenziale scalare
    # ------------------------------------------------------------------

    def compute_potential_from_arrays(
        self,
        chi: np.ndarray,
        tau: np.ndarray,
    ) -> float:
        """
        S[chi, tau] = lambda*sum(rho_i - rho_0_eff)^2 + gamma*sum(Omega_i)  [Eq. S-1]

        rho_0_eff segue la Legge FA [Eq. FA-2] se auto_scale_rho_0=True.
        """
        rho, _, Omega, _ = self._constraint_fields(chi, tau)
        rho_0_eff = self.cfg.get_rho_0(self._level)
        S_homeo  = self.cfg.lambda_homeo * float(np.sum((rho - rho_0_eff) ** 2))
        S_chiral = self.cfg.gamma_chiral * float(np.sum(Omega))
        return S_homeo + S_chiral

    def compute_potential(self, universe: AbstractSoliton) -> float:
        """Calcola S dal universo corrente."""
        leaves = self._collect_leaves(universe)
        if not leaves:
            return 0.0
        chi = np.array([getattr(seg, 'chi',       0.0) for seg in leaves])
        tau = np.array([getattr(seg, 'tau_locale', 0.0) for seg in leaves])
        return self.compute_potential_from_arrays(chi, tau)

    # ------------------------------------------------------------------
    # Export storia
    # ------------------------------------------------------------------

    def get_force_history(self) -> np.ndarray:
        """Serie storica di |F_top|_RMS per ogni kick."""
        return np.array(self._force_rms_history)

    def get_potential_history(self) -> np.ndarray:
        """Serie storica del potenziale S per ogni kick."""
        return np.array(self._potential_history)

    def export_history_dict(self) -> dict:
        """Dizionario compatibile con HDF5Logger per salvare la storia variazionale."""
        return {
            'force_rms':   self.get_force_history(),
            'potential_S': self.get_potential_history(),
        }
