"""
================================================================================
WQT_OOP - Architecture Object-Oriented per Manifold Frattale
================================================================================

Package refactoring della geometrodinamica quantistica 24-field.

PATTERN ARCHITETTURALI:
- Composite: Gerarchia frattale solitoni (24, 576, 13824...)
- Template Method: AbstractSoliton.compute_hamiltonian()
- Strategy: Screening dinamico multi-scala
- Dependency Injection: PhysicsContext
- Factory: SolitonFactory (future)

GERARCHIA FISICA:
- Livello 0: SegmentoQuantistico (2 DOF: χ, v)
- Livello 1: SolitoneComposito(24 Segmenti) → 48 DOF
- Livello 2: SolitoneComposito(24 Solitoni) → 1152 DOF
- Livello N: 24^N segmenti atomici

INVARIANTI:
1. Energia H (drift < 10⁻⁸)
2. Carica topologica Σχᵢ (esatta)
3. Chiusura spinore Στᵢ ≡ 0 (mod 4π)

AUTHOR: Lorenzo Peano (CTO/Senior Software Architect)
DATE: 2024
================================================================================
"""

__version__ = "1.2.0-variational"

# Core classes (legacy, invariati)
from .physics_context import PhysicsContext
from .abstract_soliton import AbstractSoliton
from .segmento_quantistico import SegmentoQuantistico
from .solitone_composito import SolitoneComposito

# Visualization (native module, legacy)
from .visualizer import ManifoldVisualizer, VisualizationConfig

# === TOPOLOGICAL VALIDATION LAYER (v1.1) ===
# Passaggio da convergenza energetica a validazione geometrica.
# Energia = proprietà emergente (catalogata, non vincolo).
from .topological_constraint_validator import (
    TopologicalState,
    TopologicalConstraintValidator,
    TopologicalConstraintObserver,
)
from .topological_integration import (
    TopologicalEvolutionWrapper,
    integrate_topological_validation_to_hdf5,
)
# Playback esteso (ConstraintDensityPlaybackEngine)
from .hdf5_playback import (
    ConstraintDensityPlaybackEngine,
    load_topological_group,
    convert_hdf5_frame_with_constraint_density,
)

# === VARIATIONAL TOPOLOGICAL FORCE LAYER (v1.2) ===
# Forze dal gradiente del potenziale topologico S [Eq. S-1].
# Strang Splitting: U_tot(dt) = T_{dt/2} o U_phys(dt) o T_{dt/2}  [Eq. INT-1]
from .variational_topological_force import (
    VariationalTopologicalForce,
    TopologicalForceConfig,
)

__all__ = [
    # Legacy core
    "PhysicsContext",
    "AbstractSoliton",
    "SegmentoQuantistico",
    "SolitoneComposito",
    "ManifoldVisualizer",
    "VisualizationConfig",
    # Topological validation layer
    "TopologicalState",
    "TopologicalConstraintValidator",
    "TopologicalConstraintObserver",
    "TopologicalEvolutionWrapper",
    "integrate_topological_validation_to_hdf5",
    # Topological playback
    "ConstraintDensityPlaybackEngine",
    "load_topological_group",
    "convert_hdf5_frame_with_constraint_density",
    # Variational force layer
    "VariationalTopologicalForce",
    "TopologicalForceConfig",
]
