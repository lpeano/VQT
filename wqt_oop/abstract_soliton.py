"""
================================================================================
ABSTRACT SOLITON - Classe Base Astratta
================================================================================

Pattern: Template Method + Composite
Definisce l'interfaccia comune per tutti i livelli gerarchici del manifold.

Ogni solitone (segmento, base, macro) implementa:
- get_state_vector(): stato completo (posizioni, velocità, torsione, tau)
- compute_hamiltonian(): energia totale (interna + accoppiamento + inter)
- evolve(dt): integrazione temporale
- check_fusion_threshold(): criterio transizione di fase
================================================================================
"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple, Dict, Any
from .physics_context import PhysicsContext


class AbstractSoliton(ABC):
    """
    Classe base astratta per tutti i livelli gerarchici.
    
    INVARIANTI FISICHE (da preservare):
    1. Energia totale H (drift < 10⁻⁸)
    2. Carica topologica Σχᵢ (esatta)
    3. Chiusura spinoriale Στᵢ ≡ 0 (mod 4π)
    4. Momento totale P (se sistema isolato)
    """
    
    def __init__(self, physics: PhysicsContext):
        """
        Inizializza solitone con contesto fisico.
        
        Parameters:
        -----------
        physics : PhysicsContext
            Costanti fisiche appropriate per questo livello
        """
        self.physics = physics
        self._energia_cache: float = 0.0  # Cache hamiltoniana
        self._cache_valid: bool = False
    
    @abstractmethod
    def get_state_vector(self) -> np.ndarray:
        """
        Restituisce vettore di stato completo.
        
        Returns:
        --------
        state : ndarray, shape (N_dof,)
            [χ₀, v₀, χ₁, v₁, ..., χₙ, vₙ] per N segmenti
            
        Note:
        -----
        Per SegmentoQuantistico: N_dof = 2 (χ, v)
        Per SolitoneComposito(24): N_dof = 48 (24 coppie)
        Per SolitoneComposito(24×24): N_dof = 1152
        """
        pass
    
    @abstractmethod
    def set_state_vector(self, state: np.ndarray) -> None:
        """
        Imposta stato completo e invalida cache.
        
        Parameters:
        -----------
        state : ndarray
            Nuovo vettore di stato
        """
        self._cache_valid = False
    
    @abstractmethod
    def get_auxiliary_state(self) -> Dict[str, np.ndarray]:
        """
        Restituisce variabili ausiliarie (torsione, tau, chiusura).
        
        Returns:
        --------
        aux : dict
            {
                'tau_locale': ndarray,
                'contorsione': ndarray (K²),
                'chiusura_spinore': ndarray
            }
        """
        pass
    
    @abstractmethod
    def compute_hamiltonian_internal(self) -> float:
        """
        Hamiltoniana interna (energia segmenti costituenti).
        
        H_internal = Σᵢ [T_i + V(χᵢ) + α_K·K²ᵢ]
        
        Returns:
        --------
        H_int : float
            Energia interna
        """
        pass
    
    @abstractmethod
    def compute_hamiltonian_coupling(self) -> float:
        """
        Hamiltoniana di accoppiamento (interazione tra segmenti).
        
        H_coupling = (1/2) Σᵢⱼ w_ij · A(Δχ,Δv,ΔK²,Δτ) · (χᵢ-χⱼ)²
        
        Returns:
        --------
        H_coup : float
            Energia di accoppiamento
        """
        pass
    
    def compute_hamiltonian(self) -> float:
        """
        Hamiltoniana totale (template method).
        
        Returns:
        --------
        H_total : float
            H_internal + H_coupling (+ H_inter per compositi)
        """
        if self._cache_valid:
            return self._energia_cache
        
        H_int = self.compute_hamiltonian_internal()
        H_coup = self.compute_hamiltonian_coupling()
        
        self._energia_cache = H_int + H_coup
        self._cache_valid = True
        
        return self._energia_cache
    
    @property
    def energia_totale(self) -> float:
        """Property: energia totale con cache."""
        return self.compute_hamiltonian()
    
    @abstractmethod
    def get_position(self) -> np.ndarray:
        """
        Posizione del centroide del solitone.
        
        Returns:
        --------
        r : ndarray, shape (3,)
            Coordinate spaziali (x, y, z)
        """
        pass
    
    @abstractmethod
    def get_topology_charge(self) -> float:
        """
        Carica topologica conservata (Σχᵢ).
        
        Returns:
        --------
        Q : float
            Carica topologica
        """
        pass
    
    @abstractmethod
    def get_spinor_closure(self) -> float:
        """
        Chiusura spinoriale (Στᵢ mod 4π).
        
        Returns:
        --------
        closure : float
            Στᵢ (dovrebbe essere ≡ 0 mod 4π)
        """
        pass
    
    def check_fusion_threshold(self) -> bool:
        """
        Verifica se il solitone ha raggiunto soglia fusione.
        
        CRITERI:
        1. Energia > E_fusion_threshold
        2. Coerenza temporale |Δτ| < ε
        
        Returns:
        --------
        should_fuse : bool
            True se deve fondersi con altri
        """
        if self.energia_totale < self.physics.E_fusion_threshold:
            return False
        
        # Verifica coerenza interna τ
        aux = self.get_auxiliary_state()
        tau = aux['tau_locale']
        tau_std = np.std(tau)
        
        # Se τ diverge troppo internamente, il solitone è instabile
        return tau_std < self.physics.sigma_tau
    
    @abstractmethod
    def evolve(self, dt: float, external_force: np.ndarray = None) -> None:
        """
        Evoluzione temporale (integratore simplettico).
        
        Parameters:
        -----------
        dt : float
            Passo temporale
        
        external_force : ndarray, optional
            Forze esterne (da altri solitoni)
        """
        pass
    
    def get_num_dof(self) -> int:
        """
        Numero di gradi di libertà.
        
        Returns:
        --------
        N_dof : int
            Dimensione vettore di stato
        """
        return len(self.get_state_vector())
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Diagnostica completa per logging/debugging.
        
        Returns:
        --------
        diag : dict
            {
                'energia': float,
                'carica_topologica': float,
                'chiusura_spinore': float,
                'tau_mean': float,
                'tau_std': float,
                'livello': int
            }
        """
        aux = self.get_auxiliary_state()
        
        return {
            'energia': self.energia_totale,
            'carica_topologica': self.get_topology_charge(),
            'chiusura_spinore': self.get_spinor_closure(),
            'tau_mean': np.mean(aux['tau_locale']),
            'tau_std': np.std(aux['tau_locale']),
            'livello': self.physics.level
        }
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"livello={self.physics.level}, "
            f"DOF={self.get_num_dof()}, "
            f"H={self.energia_totale:.3e})"
        )
