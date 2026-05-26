"""
================================================================================
FUSION LOGIC - Termodinamica delle Transizioni di Fase
================================================================================

Implementa la logica di fusione inelastica con radiazione torsionale.

FISICA:
-------
Quando 24 solitoni raggiungono soglia energetica e coerenza spaziale/temporale,
si fondono in un MacroSolitone di livello superiore.

BILANCIO ENERGETICO:
-------------------
H_total^(N) = H_macro^(N+1) + E_rad + ΔE_metrica

Dove:
- E_rad = η · H_total^(N)  (energia radiata, 1-5%)
- E_rad = E_waves + E_metric
  - E_waves (70%): Onde torsionali libere (disperse)
  - E_metric (30%): Espansione metrica locale (assorbita)

CONSEGUENZE:
-----------
- Freccia del tempo (irreversibilità)
- Entropia cresce a ogni fusione
- Spazio-tempo si espande assorbendo radiazione
"""

import numpy as np
from typing import List, Dict, Tuple
import logging

# Importazioni locali (da implementare)
# from .abstract_soliton import AbstractSoliton
# from .physics_context import PhysicsContext


class FusionLogic:
    """
    Gestisce transizioni di fase tra livelli gerarchici.
    
    PATTERN: Strategy Pattern
    Diverse strategie di fusione possono essere implementate
    ereditando da questa classe base.
    """
    
    def __init__(self, physics_context):
        """
        Args:
            physics_context: PhysicsContext con parametri fusione
        """
        self.ctx = physics_context
        self.logger = logging.getLogger(__name__)
    
    def check_fusion_criteria(self, solitons: List) -> bool:
        """
        Verifica se N solitoni soddisfano criteri di fusione.
        
        CRITERI NECESSARI:
        1. Numero: len(solitons) == 24 (simmetria Leech)
        2. Energia: sum(H_i) > E_fusion_threshold
        3. Coerenza spaziale: max(|r_i - r_j|) < λ_coherence
        4. Chiusura topologica: |sum(τ_i) - 4π| < ε_topology
        
        Args:
            solitons: Lista di AbstractSoliton da verificare
        
        Returns:
            True se fusione può avvenire
        """
        # Criterio 1: Numero (simmetria Leech)
        if len(solitons) != 24:
            return False
        
        # Criterio 2: Energia totale
        H_total = sum(s.compute_hamiltonian() for s in solitons)
        if H_total < self.ctx.E_fusion_threshold:
            self.logger.debug(
                f"Energia insufficiente: H={H_total:.3e} < "
                f"H_thresh={self.ctx.E_fusion_threshold:.3e}"
            )
            return False
        
        # Criterio 3: Coerenza spaziale
        positions = np.array([s.get_position() for s in solitons])
        centroid = np.mean(positions, axis=0)
        distances = np.linalg.norm(positions - centroid, axis=1)
        max_distance = np.max(distances)
        
        if max_distance > self.ctx.lambda_coherence:
            self.logger.debug(
                f"Coerenza spaziale insufficiente: r_max={max_distance:.3e} > "
                f"λ={self.ctx.lambda_coherence:.3e}"
            )
            return False
        
        # Criterio 4: Chiusura topologica spinoriale
        tau_sum = sum(s.tau_proprio for s in solitons)
        tau_error = abs(tau_sum - 4 * np.pi)
        
        if tau_error > self.ctx.eps_topology:
            self.logger.debug(
                f"Chiusura topologica violata: |Στ - 4π| = {tau_error:.6f} > "
                f"ε={self.ctx.eps_topology:.6f}"
            )
            return False
        
        # Tutti i criteri soddisfatti
        self.logger.info(
            f"✅ FUSIONE AUTORIZZATA: 24 solitoni, H={H_total:.3e}J, "
            f"r_max={max_distance:.3e}m, |Στ-4π|={tau_error:.6f}"
        )
        return True
    
    def compute_radiation_energy(self, solitons: List) -> Dict[str, float]:
        """
        Calcola energia radiata durante fusione.
        
        FORMULA:
        η_eff = η_base · (1 + Var(τ)/τ_coherence²)
        E_rad = η_eff · H_total
        E_waves = (1 - ε_local) · E_rad  (70% dispersa)
        E_metric = ε_local · E_rad        (30% assorbita)
        
        Args:
            solitons: Lista di solitoni da fondere
        
        Returns:
            {
                'H_total': Energia totale pre-fusione,
                'eta_effective': Efficienza radiativa,
                'E_radiated': Energia totale radiata,
                'E_waves': Onde torsionali libere,
                'E_metric_expansion': Espansione metrica locale,
                'tau_variance': Varianza tempi locali,
                'tau_mean': Tempo medio cluster
            }
        """
        # Energia totale
        H_total = sum(s.compute_hamiltonian() for s in solitons)
        
        # Disomogeneità temporale
        tau_vals = np.array([s.tau_proprio for s in solitons])
        tau_mean = np.mean(tau_vals)
        tau_variance = np.var(tau_vals)
        
        # Efficienza radiativa (aumenta con disomogeneità)
        eta_eff = self.ctx.compute_radiation_efficiency(tau_variance)
        
        # Energia radiata
        E_rad_total = eta_eff * H_total
        
        # Frazione assorbita localmente vs dispersa
        E_metric = E_rad_total * self.ctx.epsilon_local_absorption
        E_waves = E_rad_total * (1 - self.ctx.epsilon_local_absorption)
        
        result = {
            'H_total': H_total,
            'eta_effective': eta_eff,
            'E_radiated': E_rad_total,
            'E_waves': E_waves,
            'E_metric_expansion': E_metric,
            'tau_variance': tau_variance,
            'tau_mean': tau_mean
        }
        
        self.logger.info(
            f"📡 RADIAZIONE: η={eta_eff:.4f}, E_rad={E_rad_total:.3e}J "
            f"(Onde={E_waves:.3e}J, Metrica={E_metric:.3e}J)"
        )
        
        return result
    
    def fuse_solitons(self, solitons: List, radiation_data: Dict) -> 'SolitoneComposito':
        """
        Esegue fusione fisica di 24 solitoni in MacroSolitone.
        
        CONSERVAZIONE:
        - Energia: H_macro = (1-η) · H_total
        - Momento: P_macro = sum(P_i)
        - Carica topologica: Q_macro = sum(χ_i)
        - Torsione: K²_macro (rinormalizzata)
        
        Args:
            solitons: Lista di 24 AbstractSoliton
            radiation_data: Output di compute_radiation_energy()
        
        Returns:
            SolitoneComposito di livello superiore
        """
        # Energia conservata (sottratta radiazione)
        H_macro = radiation_data['H_total'] - radiation_data['E_radiated']
        
        # Stato composito (concatenazione stati figli)
        state_vectors = [s.get_state_vector() for s in solitons]
        composite_state = np.concatenate(state_vectors)
        
        # Tempo proprio medio (pesato su energia)
        energies = np.array([s.compute_hamiltonian() for s in solitons])
        tau_weighted = np.average(
            [s.tau_proprio for s in solitons],
            weights=energies
        )
        
        # Posizione centroide
        positions = np.array([s.get_position() for s in solitons])
        centroid = np.mean(positions, axis=0)
        
        # Contesto fisico scala superiore
        next_ctx = self.ctx.for_level(self.ctx.level + 1)
        
        # Crea MacroSolitone
        from .solitone_composito import SolitoneComposito
        
        macro = SolitoneComposito(
            children=solitons,
            state=composite_state,
            tau_proprio=tau_weighted,
            position=centroid,
            energia_iniziale=H_macro,
            physics_context=next_ctx
        )
        
        self.logger.info(
            f"🔗 FUSIONE COMPLETATA: Livello {self.ctx.level} → {next_ctx.level}, "
            f"H={H_macro:.3e}J, DOF={len(composite_state)}"
        )
        
        return macro
    
    def apply_metric_expansion(
        self,
        E_metric: float,
        ambiente_solitons: List
    ) -> float:
        """
        Applica espansione metrica al livello superiore.
        
        FISICA: 
        L'energia radiata aumenta χ_ambiente (chiralità DX)
        → f_dx = e^χ cresce → metrica si espande
        
        Args:
            E_metric: Energia da convertire in espansione
            ambiente_solitons: Solitoni del livello ambiente
        
        Returns:
            Δχ_DX: Incremento campo di espansione
        """
        # Volume efficace del livello
        if len(ambiente_solitons) == 0:
            # Nessun ambiente → radiazione dispersa
            self.logger.warning("Nessun ambiente: radiazione dispersa")
            return 0.0
        
        positions = np.array([s.get_position() for s in ambiente_solitons])
        V_eff = self.estimate_volume(positions)
        
        # Incremento campo DX (espansione)
        # ΔE = ½ · Δχ² · V → Δχ = sqrt(2·ΔE/V)
        delta_chi = np.sqrt(2 * E_metric / max(V_eff, 1e-10))
        
        # Applica a tutti i solitoni ambiente
        for soliton in ambiente_solitons:
            soliton.apply_chi_shift(delta_chi)
        
        # Calcola nuovo raggio medio
        new_positions = np.array([s.get_position() for s in ambiente_solitons])
        centroid = np.mean(new_positions, axis=0)
        radii = np.linalg.norm(new_positions - centroid, axis=1)
        r_mean = np.mean(radii)
        
        self.logger.info(
            f"🌌 ESPANSIONE METRICA: Δχ_DX={delta_chi:.6f}, V_eff={V_eff:.3e}m³, "
            f"r_mean={r_mean:.4f}m"
        )
        
        return delta_chi
    
    @staticmethod
    def estimate_volume(positions: np.ndarray) -> float:
        """
        Stima volume efficace da posizioni solitoni.
        
        Usa convex hull per dimensione spaziale reale.
        """
        if positions.ndim == 1:
            # 1D: lunghezza
            return np.ptp(positions)
        elif positions.shape[1] == 2:
            # 2D: area (approssimazione rettangolare)
            return np.ptp(positions[:, 0]) * np.ptp(positions[:, 1])
        else:
            # 3D: volume (approssimazione parallelepipedo)
            return (np.ptp(positions[:, 0]) * 
                    np.ptp(positions[:, 1]) * 
                    np.ptp(positions[:, 2]))


# ============================================================
# TEST UNITARI (da spostare in test/test_fusion_logic.py)
# ============================================================

def _test_radiation_scaling():
    """Verifica che η cresca con Var(τ)."""
    from .physics_context import PhysicsContext
    
    ctx = PhysicsContext.for_level(0)
    fusion = FusionLogic(ctx)
    
    # Caso 1: τ uniforme (Var→0)
    tau_variance_low = 0.001
    eta_low = ctx.compute_radiation_efficiency(tau_variance_low)
    
    # Caso 2: τ disomogeneo (Var>>0)
    tau_variance_high = 100.0
    eta_high = ctx.compute_radiation_efficiency(tau_variance_high)
    
    assert eta_low < eta_high, "η deve crescere con Var(τ)"
    assert 0.01 <= eta_low <= 0.05, "η fuori range fisico"
    assert 0.01 <= eta_high <= 0.05, "η fuori range fisico"
    
    print(f"✅ TEST SCALING: η(Var=0.001)={eta_low:.4f}, η(Var=100)={eta_high:.4f}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    _test_radiation_scaling()
