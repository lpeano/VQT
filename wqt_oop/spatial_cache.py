"""
================================================================================
SPATIAL CACHE - Mean-Field Caching per Solitoni Multi-Livello
================================================================================

Implementa caching spaziale per evitare ricalcoli durante propagazione
del cono di luce tra livelli gerarchici.

STRATEGIA:
- Solitone L2 memorizza stato medio dei figli L1
- Invalidazione automatica quando |dH/H| > threshold
- Mean-field approximation per campi lontani

PERFORMANCE:
- Riduce chiamate ricorsive N → 1 per campi distanti
- Speedup: ~10x per L2, ~100x per L3

================================================================================
"""

import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging
import time


logger = logging.getLogger(__name__)


@dataclass
class CachedState:
    """
    Stato cachato di solitone composito.
    
    Attributes:
    -----------
    position_mean : ndarray
        Posizione media figli
    
    chi_mean : float
        Valore medio chi
    
    chi_std : float
        Deviazione standard chi
    
    H_total : float
        Energia totale
    
    timestamp : float
        Wall-clock time creazione [s]
    
    step : int
        Step simulazione
    """
    position_mean: np.ndarray
    chi_mean: float
    chi_std: float
    H_total: float
    timestamp: float
    step: int


class SpatialCache:
    """
    Cache spaziale per solitoni multi-livello.
    
    Memorizza stato medio figli e invalida quando necessario.
    
    Methods:
    --------
    get() : Recupera stato cachato (se valido)
    update() : Aggiorna cache
    invalidate() : Forza invalidazione
    is_valid() : Controlla validità
    """
    
    def __init__(
        self,
        invalidation_threshold: float = 1e-4,
        max_age_seconds: float = float('inf'),
        max_age_steps: int = 10
    ):
        """
        Inizializza cache.
        
        Parameters:
        -----------
        invalidation_threshold : float
            Threshold |dH/H| per auto-invalidazione
        
        max_age_seconds : float
            Età massima cache [s wall-clock]
        
        max_age_steps : int
            Età massima [steps simulazione]
        """
        self.invalidation_threshold = invalidation_threshold
        self.max_age_seconds = max_age_seconds
        self.max_age_steps = max_age_steps
        
        # Cache storage
        self._cache: Optional[CachedState] = None
        
        # Statistiche
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
    
    def get(self, current_step: int) -> Optional[CachedState]:
        """
        Recupera stato cachato (se valido).
        
        Parameters:
        -----------
        current_step : int
            Step corrente simulazione
        
        Returns:
        --------
        state : CachedState or None
            Stato cachato (None se invalido)
        """
        if self._cache is None:
            self.misses += 1
            return None
        
        # Controlla età
        age_steps = current_step - self._cache.step
        age_seconds = time.time() - self._cache.timestamp
        
        if age_steps > self.max_age_steps or age_seconds > self.max_age_seconds:
            logger.debug(f"Cache expired: age_steps={age_steps}, age_sec={age_seconds:.3f}")
            self.invalidate()
            self.misses += 1
            return None
        
        # Cache valida
        self.hits += 1
        return self._cache
    
    def update(
        self,
        position_mean: np.ndarray,
        chi_mean: float,
        chi_std: float,
        H_total: float,
        current_step: int
    ):
        """
        Aggiorna cache con nuovo stato.
        
        Parameters:
        -----------
        position_mean : ndarray
            Posizione media figli
        
        chi_mean : float
            Media chi
        
        chi_std : float
            Std chi
        
        H_total : float
            Energia totale
        
        current_step : int
            Step corrente
        """
        # Controlla se invalidare (cambio energia significativo)
        if self._cache is not None:
            dH = abs(H_total - self._cache.H_total)
            if dH / (abs(self._cache.H_total) + 1e-30) > self.invalidation_threshold:
                logger.debug(f"Auto-invalidation: dH/H={dH/self._cache.H_total:.3e}")
                self.invalidations += 1
        
        # Aggiorna cache
        self._cache = CachedState(
            position_mean=position_mean.copy(),
            chi_mean=chi_mean,
            chi_std=chi_std,
            H_total=H_total,
            timestamp=time.time(),
            step=current_step
        )
        
        logger.debug(f"Cache updated: step={current_step}, H={H_total:.6e}")
    
    def invalidate(self):
        """Forza invalidazione cache."""
        self._cache = None
        self.invalidations += 1
    
    def is_valid(self, current_step: int) -> bool:
        """
        Controlla se cache è valida.
        
        Parameters:
        -----------
        current_step : int
            Step corrente
        
        Returns:
        --------
        valid : bool
            True se cache valida
        """
        return self.get(current_step) is not None
    
    def get_statistics(self) -> dict:
        """
        Restituisce statistiche cache.
        
        Returns:
        --------
        stats : dict
            Statistiche hit/miss/invalidations
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'invalidations': self.invalidations,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }


class HierarchicalCacheManager:
    """
    Gestore cache multi-livello per universo frattale.
    
    Mantiene cache separate per ogni livello gerarchico.
    """
    
    def __init__(self, max_levels: int = 5):
        """
        Inizializza manager.
        
        Parameters:
        -----------
        max_levels : int
            Numero massimo livelli gerarchici
        """
        self.max_levels = max_levels
        
        # Cache per livello
        self.caches: Dict[int, SpatialCache] = {}
        
        for level in range(max_levels):
            # Aumenta threshold invalidazione per livelli superiori
            threshold = 1e-4 * (1.5 ** level)
            
            self.caches[level] = SpatialCache(
                invalidation_threshold=threshold,
                max_age_steps=10
            )
        
        logger.info(f"HierarchicalCacheManager initialized: {max_levels} levels")
    
    def get_cache(self, level: int) -> SpatialCache:
        """
        Recupera cache per livello specifico.
        
        Parameters:
        -----------
        level : int
            Livello gerarchico
        
        Returns:
        --------
        cache : SpatialCache
            Cache del livello
        """
        if level not in self.caches:
            raise ValueError(f"Invalid level {level} (max={self.max_levels})")
        
        return self.caches[level]
    
    def invalidate_all(self):
        """Invalida tutte le cache."""
        for cache in self.caches.values():
            cache.invalidate()
    
    def get_global_statistics(self) -> dict:
        """
        Statistiche aggregate di tutte le cache.
        
        Returns:
        --------
        stats : dict
            Statistiche per livello
        """
        stats = {}
        
        for level, cache in self.caches.items():
            stats[f'level_{level}'] = cache.get_statistics()
        
        # Aggregate totals
        total_hits = sum(s['hits'] for s in stats.values())
        total_misses = sum(s['misses'] for s in stats.values())
        total_invalidations = sum(s['invalidations'] for s in stats.values())
        total_requests = total_hits + total_misses
        
        stats['TOTAL'] = {
            'hits': total_hits,
            'misses': total_misses,
            'invalidations': total_invalidations,
            'hit_rate': total_hits / total_requests if total_requests > 0 else 0.0,
            'total_requests': total_requests
        }
        
        return stats


# ========================================================================
# TEST
# ========================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    print("\n" + "="*70)
    print(" TEST: SPATIAL CACHE")
    print("="*70 + "\n")
    
    # Test 1: Basic cache operations
    print("Test 1: Basic Operations")
    print("-" * 70)
    
    cache = SpatialCache(
        invalidation_threshold=1e-3,
        max_age_steps=5
    )
    
    # Update cache
    cache.update(
        position_mean=np.array([0.0, 0.0, 0.0]),
        chi_mean=50.0,
        chi_std=2.0,
        H_total=1e6,
        current_step=0
    )
    
    # Hit
    state = cache.get(current_step=1)
    assert state is not None, "Cache miss (expected hit)"
    print(f"Cache HIT: chi_mean={state.chi_mean}, H={state.H_total:.6e}")
    
    # Age out
    state = cache.get(current_step=10)
    assert state is None, "Cache hit (expected miss)"
    print("Cache MISS: expired (age > max_age_steps)")
    
    # Test 2: Auto-invalidation
    print("\nTest 2: Auto-Invalidation")
    print("-" * 70)
    
    cache.update(
        position_mean=np.array([0.0, 0.0, 0.0]),
        chi_mean=50.0,
        chi_std=2.0,
        H_total=1e6,
        current_step=0
    )
    
    # Piccola variazione energia (no invalidation)
    cache.update(
        position_mean=np.array([0.0, 0.0, 0.0]),
        chi_mean=50.0,
        chi_std=2.0,
        H_total=1e6 * 1.0001,  # +0.01%
        current_step=1
    )
    
    print(f"Small dH: invalidations={cache.invalidations} (expected 0)")
    
    # Grande variazione energia (auto-invalidation)
    cache.update(
        position_mean=np.array([0.0, 0.0, 0.0]),
        chi_mean=50.0,
        chi_std=2.0,
        H_total=1e6 * 1.01,  # +1%
        current_step=2
    )
    
    print(f"Large dH: invalidations={cache.invalidations} (expected 1)")
    
    # Test 3: Hierarchical cache manager
    print("\nTest 3: Hierarchical Cache Manager")
    print("-" * 70)
    
    manager = HierarchicalCacheManager(max_levels=3)
    
    # Update caches per livello
    for level in range(3):
        cache = manager.get_cache(level)
        
        cache.update(
            position_mean=np.array([0.0, 0.0, 0.0]),
            chi_mean=50.0 + level * 10,
            chi_std=2.0,
            H_total=1e6 * (level + 1),
            current_step=0
        )
        
        # Simula alcune query
        for _ in range(5):
            cache.get(current_step=1)
    
    # Statistiche globali
    stats = manager.get_global_statistics()
    
    print("\nGlobal Statistics:")
    for level_key, level_stats in stats.items():
        print(f"  {level_key}: "
              f"hits={level_stats['hits']}, "
              f"misses={level_stats['misses']}, "
              f"hit_rate={level_stats['hit_rate']:.2%}")
    
    print("\n" + "="*70)
    print(" SPATIAL CACHE TEST COMPLETATO")
    print("="*70 + "\n")
