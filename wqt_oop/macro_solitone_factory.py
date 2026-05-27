"""
================================================================================
MACRO SOLITONE FACTORY - Costruttore Gerarchico Frattale
================================================================================

Questo modulo implementa la fusione gerarchica dei solitoni seguendo il pattern:
- Livello 0: SegmentoQuantistico (2 DOF: χ, v)
- Livello 1: SolitoneComposito (24 × Livello 0 = 48 DOF)
- Livello 2: MacroSolitone (24 × Livello 1 = 1152 DOF = 576 segmenti)
- Livello N: Ricorsione (24^N segmenti atomici)

SCALING FISICO:
    α_K^(n) = α_K^(0) · (24²)^n
    λ_exchange^(n) = λ_base · α_K^(n) / α_K^(0)  (rapporto costante)
    L_eff mantiene significato locale (sempre ~3.0)

INVARIANTI:
    H_total^(n) = Σᵢ H_child[i] + E_coupling^(n) + E_torsion^(n) + E_exchange^(n)
    Conservazione: dH/dt = -E_radiated (termodinamica aperta)
================================================================================
"""

import numpy as np
from typing import List, Optional
import sys
sys.path.insert(0, r"c:\Users\lpeano\plank\VQT")

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


class MacroSolitoneFactory:
    """Factory per costruzione gerarchica di solitoni frattali."""
    
    @staticmethod
    def build_level_0_cluster(
        physics_ctx: PhysicsContext,
        n_matter: int = 9,
        n_space: int = 15,
        v_range: tuple = (-0.1, 0.1),
        seed: Optional[int] = None
    ) -> List[SegmentoQuantistico]:
        """
        Crea cluster di segmenti atomici (Livello 0).
        
        Parameters:
        -----------
        physics_ctx : PhysicsContext
            Contesto fisico Livello 0
        n_matter : int
            Numero segmenti "materia" (χ > 0)
        n_space : int
            Numero segmenti "spazio" (χ ≤ 0)
        v_range : tuple
            Range velocità iniziali (cold start)
        seed : int, optional
            Seed per riproducibilità
        
        Returns:
        --------
        segments : List[SegmentoQuantistico]
            24 segmenti atomici shuffled
        """
        if seed is not None:
            np.random.seed(seed)
        
        assert n_matter + n_space == 24, "Totale deve essere 24"
        
        segments = []
        
        # Materia
        for i in range(n_matter):
            chi_init = np.random.uniform(3.5, 5.5)  # ~+4.5
            v_init = np.random.uniform(*v_range)
            seg = SegmentoQuantistico(chi_init, v_init, physics_ctx)
            segments.append(seg)
        
        # Spazio
        for i in range(n_space):
            chi_init = np.random.uniform(-5.5, -3.5)  # ~-4.5
            v_init = np.random.uniform(*v_range)
            seg = SegmentoQuantistico(chi_init, v_init, physics_ctx)
            segments.append(seg)
        
        # Shuffle per evitare clustering artificiale
        np.random.shuffle(segments)
        
        return segments
    
    @staticmethod
    def build_level_1_soliton(
        physics_ctx_level_1: PhysicsContext,
        n_matter: int = 9,
        n_space: int = 15,
        v_range: tuple = (-0.1, 0.1),
        seed: Optional[int] = None
    ) -> SolitoneComposito:
        """
        Crea SolitoneComposito (Livello 1) da 24 segmenti atomici.
        
        Parameters:
        -----------
        physics_ctx_level_1 : PhysicsContext
            Contesto fisico Livello 1
        n_matter, n_space : int
            Configurazione materia/spazio
        v_range : tuple
            Range velocità (cold start)
        seed : int, optional
            Seed RNG
        
        Returns:
        --------
        soliton : SolitoneComposito
            Solitone Livello 1 (24 children)
        """
        # Crea contesto Livello 0 con stessi parametri base
        ctx_0 = PhysicsContext(
            level=0,
            length_scale=physics_ctx_level_1.length_scale / np.sqrt(24),
            alpha_K=physics_ctx_level_1.alpha_K / (24**2),
            beta_potential=physics_ctx_level_1.beta_potential,
            kappa_coupling=physics_ctx_level_1.kappa_coupling,
            lambda_exchange=physics_ctx_level_1.lambda_exchange / (24**2),
            sigma_chi=physics_ctx_level_1.sigma_chi / np.sqrt(24),
            sigma_velocity=physics_ctx_level_1.sigma_velocity,
            sigma_torsion=physics_ctx_level_1.sigma_torsion / np.sqrt(24),
            sigma_tau=physics_ctx_level_1.sigma_tau
        )
        
        # Crea 24 segmenti atomici
        segments = MacroSolitoneFactory.build_level_0_cluster(
            ctx_0, n_matter, n_space, v_range, seed
        )
        
        # Componi in Livello 1
        soliton = SolitoneComposito(
            segments,
            physics_ctx_level_1,
            screening_enabled=True  # Screening adattivo
        )
        
        return soliton
    
    @staticmethod
    def build_level_2_macro(
        physics_ctx_level_2: PhysicsContext,
        n_composites: int = 24,
        matter_fraction: float = 0.375,
        v_range: tuple = (-0.1, 0.1),
        seed: Optional[int] = None
    ) -> SolitoneComposito:
        """
        Crea MacroSolitone (Livello 2) da 24 SolitoneComposito (Livello 1).
        
        TOTALE: 24 × 24 = 576 segmenti atomici
        
        Parameters:
        -----------
        physics_ctx_level_2 : PhysicsContext
            Contesto fisico Livello 2
        n_composites : int
            Numero di solitoni Livello 1 (deve essere 24)
        matter_fraction : float
            Frazione media materia (0.375 = 9/24)
        v_range : tuple
            Range velocità iniziali
        seed : int, optional
            Seed RNG
        
        Returns:
        --------
        macro : SolitoneComposito
            MacroSolitone Livello 2 (24 children compositi)
        """
        assert n_composites == 24, "MacroSolitone richiede 24 compositi"
        
        if seed is not None:
            np.random.seed(seed)
        
        # Crea contesto Livello 1 (de-scaling da Livello 2)
        ctx_1 = PhysicsContext(
            level=1,
            length_scale=physics_ctx_level_2.length_scale / np.sqrt(24),
            alpha_K=physics_ctx_level_2.alpha_K / (24**2),
            beta_potential=physics_ctx_level_2.beta_potential,
            kappa_coupling=physics_ctx_level_2.kappa_coupling,
            lambda_exchange=physics_ctx_level_2.lambda_exchange / (24**2),
            sigma_chi=physics_ctx_level_2.sigma_chi / np.sqrt(24),
            sigma_velocity=physics_ctx_level_2.sigma_velocity,
            sigma_torsion=physics_ctx_level_2.sigma_torsion / np.sqrt(24),
            sigma_tau=physics_ctx_level_2.sigma_tau
        )
        
        # Crea 24 SolitoneComposito (Livello 1)
        composites = []
        for i in range(n_composites):
            # Varia configurazione M/S tra compositi
            n_matter = int(24 * matter_fraction)
            # Aggiungi variabilità ±2 segmenti
            n_matter += np.random.randint(-2, 3)
            n_matter = np.clip(n_matter, 3, 21)  # Vincolo fisico
            n_space = 24 - n_matter
            
            composite = MacroSolitoneFactory.build_level_1_soliton(
                ctx_1,
                n_matter=n_matter,
                n_space=n_space,
                v_range=v_range,
                seed=seed + i if seed is not None else None
            )
            composites.append(composite)
        
        # Componi in MacroSolitone (Livello 2)
        # NOTA: SolitoneComposito supporta ricorsione automatica
        macro = SolitoneComposito(
            composites,
            physics_ctx_level_2,
            screening_enabled=True
        )
        
        return macro
    
    @staticmethod
    def build_hierarchy(
        target_level: int,
        lambda_exchange_base: float = 5.0,
        v_range: tuple = (-0.1, 0.1),
        seed: Optional[int] = None
    ) -> SolitoneComposito:
        """
        Costruisce gerarchia completa fino a target_level.
        
        Parameters:
        -----------
        target_level : int
            Livello target (0=segmenti, 1=24seg, 2=576seg, 3=13824seg, ...)
        lambda_exchange_base : float
            Intensità scambio topologico base (tipicamente 5.0)
        v_range : tuple
            Range velocità cold start
        seed : int, optional
            Seed riproducibilità
        
        Returns:
        --------
        soliton : SolitoneComposito o SegmentoQuantistico
            Solitone al livello richiesto
        """
        if target_level == 0:
            # Livello atomico: singolo segmento
            ctx_0 = PhysicsContext.for_level(0)
            chi_init = np.random.uniform(3.5, 5.5)
            v_init = np.random.uniform(*v_range)
            return SegmentoQuantistico(chi_init, v_init, ctx_0)
        
        # Crea contesto al livello target con scaling corretto
        base_ctx = PhysicsContext(
            level=0,
            length_scale=1.616255e-35,
            alpha_K=1.0,
            beta_potential=0.001,
            kappa_coupling=0.25,
            lambda_exchange=lambda_exchange_base,
            sigma_chi=3.0,
            sigma_velocity=2.0,
            sigma_torsion=2.0 * np.pi,
            sigma_tau=5.0
        )
        
        ctx_target = PhysicsContext.for_level(target_level, base_context=base_ctx)
        
        if target_level == 1:
            return MacroSolitoneFactory.build_level_1_soliton(
                ctx_target,
                n_matter=9,
                n_space=15,
                v_range=v_range,
                seed=seed
            )
        elif target_level == 2:
            return MacroSolitoneFactory.build_level_2_macro(
                ctx_target,
                n_composites=24,
                matter_fraction=0.375,
                v_range=v_range,
                seed=seed
            )
        else:
            raise NotImplementedError(f"Livello {target_level} non implementato (max 2)")
    
    @staticmethod
    def print_hierarchy_info(soliton, level: int = 0, indent: int = 0) -> None:
        """
        Stampa struttura gerarchica ricorsivamente.
        
        Parameters:
        -----------
        soliton : AbstractSoliton
            Solitone da ispezionare
        level : int
            Livello corrente
        indent : int
            Indentazione visuale
        """
        prefix = "  " * indent
        
        if isinstance(soliton, SegmentoQuantistico):
            print(f"{prefix}L{level} Segmento: chi={soliton.chi:.2f}, v={soliton.vel:.2f}")
        elif isinstance(soliton, SolitoneComposito):
            N = soliton.N_children
            H = soliton.energia_totale
            print(f"{prefix}L{level} Composito: {N} children, H={H:.2e}, alpha_K={soliton.physics.alpha_K:.1f}")
            
            # Ricorsione sui primi 3 figli (per evitare output eccessivo)
            for i, child in enumerate(soliton.children[:3]):
                MacroSolitoneFactory.print_hierarchy_info(child, level - 1, indent + 1)
            if N > 3:
                print(f"{prefix}  ... ({N - 3} children omessi)")


if __name__ == "__main__":
    print("=" * 80)
    print(" TEST MACRO SOLITONE FACTORY")
    print("=" * 80)
    
    # Test Livello 1
    print("\n1. Costruzione Livello 1 (24 segmenti):")
    ctx_1 = PhysicsContext.for_level(1)
    soliton_l1 = MacroSolitoneFactory.build_level_1_soliton(
        ctx_1,
        n_matter=9,
        n_space=15,
        v_range=(-0.1, 0.1),
        seed=42
    )
    print(f"   N_children = {soliton_l1.N_children}")
    print(f"   N_DOF      = {soliton_l1.get_num_dof()}")
    print(f"   H_total    = {soliton_l1.energia_totale:.6e}")
    print(f"   alpha_K    = {soliton_l1.physics.alpha_K}")
    print(f"   lambda_ex  = {soliton_l1.physics.lambda_exchange}")
    
    # Test Livello 2
    print("\n2. Costruzione Livello 2 (576 segmenti):")
    ctx_2 = PhysicsContext.for_level(2)
    macro_l2 = MacroSolitoneFactory.build_level_2_macro(
        ctx_2,
        n_composites=24,
        matter_fraction=0.375,
        v_range=(-0.1, 0.1),
        seed=42
    )
    print(f"   N_children (L1)       = {macro_l2.N_children}")
    print(f"   N_segments (L0) total = {macro_l2.N_children * 24}")
    print(f"   N_DOF total           = {macro_l2.get_num_dof()}")
    print(f"   H_total               = {macro_l2.energia_totale:.6e}")
    print(f"   alpha_K (L2)          = {macro_l2.physics.alpha_K}")
    print(f"   lambda_ex (L2)        = {macro_l2.physics.lambda_exchange}")
    
    # Gerarchia
    print("\n3. Struttura Gerarchica (primi 2 compositi):")
    MacroSolitoneFactory.print_hierarchy_info(macro_l2, level=2, indent=0)
    
    print("\n" + "=" * 80)
