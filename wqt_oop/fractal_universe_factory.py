"""
================================================================================
FRACTAL UNIVERSE FACTORY - Generazione Dinamica Livelli Gerarchici
================================================================================

Factory pattern per istanziare livelli frattali (L0 → L1 → L2 → ... → Ln)
in modo ricorsivo, caricando parametri da PhysicsContext.

GERARCHIA FRATTALE:
- Livello 0: 1 SegmentoQuantistico (2 DOF)
- Livello 1: 24 Segmenti → SolitoneComposito (48 DOF)
- Livello 2: 24 Solitoni(24) → MacroSolitone (1152 DOF)
- Livello n: 24^n segmenti atomici

SCALING LAW:
- N_segments(n) = 24^n
- DOF(n) = 2 * 24^n
- Memory(n) ~ O(24^n) con spatial caching

================================================================================
"""

import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging

from .physics_context import PhysicsContext
from .segmento_quantistico import SegmentoQuantistico
from .solitone_composito import SolitoneComposito
from .abstract_soliton import AbstractSoliton


logger = logging.getLogger(__name__)


@dataclass
class UniverseConfig:
    """
    Configurazione universo frattale.
    
    Attributes:
    -----------
    target_level : int
        Livello gerarchico target (0 = segmenti, 1 = solitoni, ...)
    
    chi_mean : float
        Valore medio campo χ iniziale
    
    chi_std : float
        Deviazione standard χ
    
    vel_std : float
        Deviazione standard velocità
    
    spatial_extent : float
        Dimensione box spaziale [m]
    
    seed : int
        Random seed per riproducibilità
    
    enable_fermi_screening : bool
        Abilita screening Fermi-Dirac
    
    enable_spatial_cache : bool
        Abilita caching spaziale per performance
    """
    target_level: int = 2
    chi_mean: float = 50.0
    chi_std: float = 5.0
    vel_std: float = 1.0
    spatial_extent: float = 100.0
    seed: int = 42
    enable_fermi_screening: bool = True
    enable_spatial_cache: bool = True


class FractalUniverseFactory:
    """
    Factory per generazione ricorsiva universo frattale.
    
    Genera la gerarchia completa da L0 (segmenti atomici) fino a
    Ln (target_level) costruendo ricorsivamente i livelli intermedi.
    
    Methods:
    --------
    create_universe(config) -> AbstractSoliton
        Genera universo al livello target
    
    create_level(level, N_units) -> List[AbstractSoliton]
        Crea N unità al livello specificato
    
    create_segment(chi, vel, pos) -> SegmentoQuantistico
        Crea singolo segmento L0
    """
    
    def __init__(self, base_physics: Optional[PhysicsContext] = None):
        """
        Inizializza factory.
        
        Parameters:
        -----------
        base_physics : PhysicsContext, optional
            Contesto fisico base (livello 0)
            Se None, usa parametri default Planck-scale
        """
        self.base_physics = base_physics or PhysicsContext.for_level(0)
        
        # Cache physics contexts per livello
        self._physics_cache = {0: self.base_physics}
        
        logger.info(f"FractalUniverseFactory initialized: base_level=0")
    
    def get_physics_for_level(self, level: int) -> PhysicsContext:
        """
        Ottiene PhysicsContext per livello (con caching).
        
        Parameters:
        -----------
        level : int
            Livello gerarchico
        
        Returns:
        --------
        ctx : PhysicsContext
            Contesto fisico scalato
        """
        if level not in self._physics_cache:
            self._physics_cache[level] = PhysicsContext.for_level(
                level,
                base_context=self.base_physics
            )
        return self._physics_cache[level]

    def get_physics_for_level_with_chi(self, level: int, chi_mean_init: float) -> PhysicsContext:
        """
        PhysicsContext scalato con chi_stable = chi_mean_init.

        Garantisce che la soglia Jitterbug (chi_max/chi_stable = sqrt(2))
        sia calibrata sulle condizioni iniziali reali del run.
        Calibrazione sperimentale: chi_max_peak/chi_mean_init = sqrt(2)
        confermato su 5/8 file L2/L3/L4 (errore < 5%).
        """
        cache_key = (level, round(chi_mean_init, 4))
        if cache_key not in self._physics_cache:
            self._physics_cache[cache_key] = PhysicsContext.for_level(
                level,
                base_context=self.base_physics,
                chi_mean_init=chi_mean_init,
            )
        return self._physics_cache[cache_key]
    
    def create_universe(self, config: UniverseConfig) -> AbstractSoliton:
        """
        Genera universo frattale completo.
        
        Costruisce ricorsivamente la gerarchia:
        1. Crea 24^n segmenti atomici (L0)
        2. Raggruppa in solitoni compositi (L1)
        3. Itera fino a target_level
        
        Parameters:
        -----------
        config : UniverseConfig
            Configurazione universo
        
        Returns:
        --------
        universe : AbstractSoliton
            Root del frattale (livello target)
        """
        np.random.seed(config.seed)
        
        logger.info(f"Creating fractal universe: target_level={config.target_level}")
        logger.info(f"  Total segments: 24^{config.target_level} = {24**config.target_level}")
        
        if config.target_level == 0:
            # Caso base: singolo segmento
            return self._create_segment(
                chi=config.chi_mean,
                vel=0.0,
                pos=np.zeros(3)
            )
        
        # Costruzione ricorsiva bottom-up
        current_units = self._create_level_0_segments(config)
        logger.info(f"  L0: Created {len(current_units)} segments")
        
        # Iterazione livelli 1 → target_level
        for level in range(1, config.target_level + 1):
            current_units = self._build_next_level(
                children=current_units,
                target_level=level,
                config=config
            )
            logger.info(f"  L{level}: Created {len(current_units)} composites "
                       f"({len(current_units) * 24**(level)} total segments)")
        
        # Se target_level > 0, current_units contiene N compositi
        # Per semplicità, restituiamo il primo (o possiamo wrappare in un super-composito)
        if len(current_units) == 1:
            universe = current_units[0]
        else:
            # Wrap in super-composito
            ctx_super = self.get_physics_for_level(config.target_level + 1)
            universe = SolitoneComposito(
                current_units, 
                ctx_super,
                screening_enabled=config.enable_fermi_screening
            )
        
        logger.info(f"Universe created: type={type(universe).__name__}, "
                   f"total_DOF={24**(config.target_level) * 2}")
        
        return universe
    
    def _create_level_0_segments(self, config: UniverseConfig) -> List[SegmentoQuantistico]:
        """
        Crea pool di segmenti atomici (L0).
        
        Numero segmenti = 24^target_level (pool completo)
        """
        N_segments = 24 ** config.target_level
        
        segments = []
        ctx_0 = self.get_physics_for_level(0)
        
        # Distribuzione spaziale: griglia uniforme con jitter
        grid_size = int(np.ceil(N_segments ** (1/3)))
        spacing = config.spatial_extent / grid_size
        
        idx = 0
        for i in range(grid_size):
            for j in range(grid_size):
                for k in range(grid_size):
                    if idx >= N_segments:
                        break
                    
                    # Posizione griglia + jitter
                    pos = np.array([
                        i * spacing + np.random.uniform(-spacing/4, spacing/4),
                        j * spacing + np.random.uniform(-spacing/4, spacing/4),
                        k * spacing + np.random.uniform(-spacing/4, spacing/4)
                    ])
                    
                    # Campo χ distribuito normalmente
                    chi = np.random.normal(config.chi_mean, config.chi_std)
                    vel = np.random.normal(0.0, config.vel_std)
                    
                    segments.append(self._create_segment(chi, vel, pos))
                    idx += 1
                
                if idx >= N_segments:
                    break
            if idx >= N_segments:
                break
        
        return segments[:N_segments]
    
    def _create_segment(
        self, 
        chi: float, 
        vel: float, 
        pos: np.ndarray
    ) -> SegmentoQuantistico:
        """Crea singolo segmento atomico."""
        ctx_0 = self.get_physics_for_level(0)
        return SegmentoQuantistico(chi, vel, ctx_0, position=pos)
    
    def _build_next_level(
        self,
        children: List[AbstractSoliton],
        target_level: int,
        config: UniverseConfig
    ) -> List[SolitoneComposito]:
        """
        Costruisce livello (n+1) raggruppando 24 unità di livello n.
        
        Parameters:
        -----------
        children : List[AbstractSoliton]
            Unità del livello precedente
        
        target_level : int
            Livello target da costruire
        
        config : UniverseConfig
            Configurazione universo
        
        Returns:
        --------
        composites : List[SolitoneComposito]
            Solitoni compositi al livello target
        """
        assert len(children) % 24 == 0, \
            f"Children count must be multiple of 24, got {len(children)}"
        
        ctx = self.get_physics_for_level_with_chi(target_level, config.chi_mean)
        composites = []
        
        # Raggruppa in blocchi da 24
        N_composites = len(children) // 24
        
        for i in range(N_composites):
            start_idx = i * 24
            end_idx = start_idx + 24
            
            composite_children = children[start_idx:end_idx]
            
            composite = SolitoneComposito(
                composite_children,
                ctx,
                screening_enabled=config.enable_fermi_screening
            )
            
            composites.append(composite)
        
        return composites
    
    def estimate_memory(self, target_level: int) -> dict:
        """
        Stima memoria richiesta per universo al livello target.
        
        Returns:
        --------
        memory_info : dict
            Informazioni memoria
        """
        N_segments = 24 ** target_level
        
        # Stima conservativa
        bytes_per_segment = 200  # SegmentoQuantistico base
        bytes_per_composite = 500  # SolitoneComposito overhead
        
        # Livello 0: solo segmenti
        L0_memory = N_segments * bytes_per_segment
        
        # Livelli superiori: compositi + children references
        composite_memory = 0
        for level in range(1, target_level + 1):
            N_composites = N_segments // (24 ** level)
            composite_memory += N_composites * bytes_per_composite
        
        total_bytes = L0_memory + composite_memory
        
        return {
            'target_level': target_level,
            'N_segments': N_segments,
            'N_composites': sum(24**(target_level - i) for i in range(1, target_level + 1)),
            'L0_memory_MB': L0_memory / 1e6,
            'composite_memory_MB': composite_memory / 1e6,
            'total_memory_MB': total_bytes / 1e6,
            'total_memory_GB': total_bytes / 1e9
        }


# ========================================================================
# UTILITY FUNCTIONS
# ========================================================================

def print_universe_info(universe: AbstractSoliton, config: UniverseConfig):
    """Stampa informazioni universo generato."""
    print("=" * 70)
    print(" FRACTAL UNIVERSE INFO")
    print("=" * 70)
    print(f"Target Level:     {config.target_level}")
    print(f"Root Type:        {type(universe).__name__}")
    print(f"Total DOF:        {24**config.target_level * 2}")
    print(f"Total Segments:   {24**config.target_level}")
    
    if isinstance(universe, SolitoneComposito):
        print(f"Direct Children:  {len(universe.children)}")
        print(f"Screening:        {'ENABLED (Fermi-Dirac)' if universe.screening_enabled else 'DISABLED'}")
        print(f"T_eff:            {universe.fermi_screener.T_eff:.3e}")
        print(f"mu_fermi:         {universe.fermi_screener.mu:.3f}")
    
    print(f"Spatial Extent:   {config.spatial_extent} m")
    print("=" * 70)


# ========================================================================
# TEST
# ========================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print(" TEST: FRACTAL UNIVERSE FACTORY")
    print("="*70 + "\n")
    
    factory = FractalUniverseFactory()
    
    # Test livello 1 (24 segmenti)
    config_L1 = UniverseConfig(
        target_level=1,
        chi_mean=50.0,
        chi_std=3.0,
        vel_std=0.5,
        spatial_extent=50.0
    )
    
    print("Test 1: Livello 1 (24 segmenti)")
    print("-" * 70)
    universe_L1 = factory.create_universe(config_L1)
    print_universe_info(universe_L1, config_L1)
    
    mem_L1 = factory.estimate_memory(1)
    print(f"\nMemory L1: {mem_L1['total_memory_MB']:.2f} MB\n")
    
    # Test livello 2 (576 segmenti)
    config_L2 = UniverseConfig(
        target_level=2,
        chi_mean=50.0,
        chi_std=5.0,
        spatial_extent=100.0
    )
    
    print("\nTest 2: Livello 2 (576 segmenti)")
    print("-" * 70)
    universe_L2 = factory.create_universe(config_L2)
    print_universe_info(universe_L2, config_L2)
    
    mem_L2 = factory.estimate_memory(2)
    print(f"\nMemory L2: {mem_L2['total_memory_MB']:.2f} MB\n")
    
    # Test occupazione stati
    if isinstance(universe_L2, SolitoneComposito):
        stats = universe_L2.get_occupazione_stati()
        print("Occupazione Stati L2:")
        print(f"  Destrorsi:     {stats['N_destro']}")
        print(f"  Sinistrorsi:   {stats['N_sinistro']}")
        print(f"  Polarizzazione: {stats['polarizzazione']:.3f}")
    
    print("\n" + "="*70)
    print(" FACTORY TEST COMPLETATO")
    print("="*70 + "\n")
