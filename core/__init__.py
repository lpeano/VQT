"""
core — API pulita del motore VQT / Peano-VQT.
Re-esporta i moduli fondamentali da wqt_oop.
"""
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.energy_metrics import (
    PeanoVQTAnalyzer,
    EnergyTriad,
    PhaseTransitionEvent,
    classify_geometric_phase,
    load_h5_and_validate,
)

__all__ = [
    'SolitoneComposito', 'SegmentoQuantistico', 'PhysicsContext',
    'PeanoVQTAnalyzer', 'EnergyTriad', 'PhaseTransitionEvent',
    'classify_geometric_phase', 'load_h5_and_validate',
]
