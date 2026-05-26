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

__version__ = "1.0.0-alpha"

# Core classes
from .physics_context import PhysicsContext
from .abstract_soliton import AbstractSoliton
from .segmento_quantistico import SegmentoQuantistico
from .solitone_composito import SolitoneComposito

# Visualization (native module)
from .visualizer import ManifoldVisualizer, VisualizationConfig

__all__ = [
    "PhysicsContext",
    "AbstractSoliton",
    "SegmentoQuantistico",
    "SolitoneComposito",
    "ManifoldVisualizer",
    "VisualizationConfig",
]
