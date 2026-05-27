"""
================================================================================
SPATIAL HASH GRID - Ottimizzazione Interazioni O(N^2) → O(N log N)
================================================================================

Implementa spatial hashing (cell-linked list) per calcolo efficiente
delle interazioni a corto raggio tra solitoni.

COMPLESSITÀ:
- Naive: O(N²) per N solitoni
- Spatial Hash: O(N) costruzione + O(N·k) query, dove k ~ costante
- Speedup: ~100x per N=10000, ~1000x per N=100000

ALGORITMO:
1. Divide spazio 3D in celle (grid cubico)
2. Assegna ogni solitone alla cella corrispondente
3. Per ogni interazione, cerca solo nelle celle vicine (27 celle)

PARAMETRI:
- cell_size: Dimensione cella ~ R_interaction (raggio interazione)
- grid_size: Numero celle per dimensione

================================================================================
"""

import numpy as np
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
import logging

from .abstract_soliton import AbstractSoliton


logger = logging.getLogger(__name__)


@dataclass
class SpatialHashConfig:
    """
    Configurazione spatial hash grid.
    
    Attributes:
    -----------
    cell_size : float
        Dimensione cella [m] (~ raggio interazione)
    
    grid_bounds : tuple
        (min, max) coordinate spaziali [(xmin,ymin,zmin), (xmax,ymax,zmax)]
    
    enable_adaptive : bool
        Abilita ridimensionamento automatico celle
    """
    cell_size: float = 10.0
    grid_bounds: Tuple[np.ndarray, np.ndarray] = (
        np.array([-100.0, -100.0, -100.0]),
        np.array([100.0, 100.0, 100.0])
    )
    enable_adaptive: bool = True


class SpatialHashGrid:
    """
    Griglia hash spaziale per neighbor search efficiente.
    
    Usa hashing 3D per mappare posizioni → ID cella.
    
    Methods:
    --------
    build(solitons) : Costruisce hash grid
    get_neighbors(position, radius) : Query neighbor search
    get_cell_occupancy() : Statistiche occupazione celle
    """
    
    def __init__(self, config: SpatialHashConfig):
        """
        Inizializza spatial hash grid.
        
        Parameters:
        -----------
        config : SpatialHashConfig
            Configurazione grid
        """
        self.config = config
        
        # Grid parameters
        self.cell_size = config.cell_size
        self.grid_min = config.grid_bounds[0]
        self.grid_max = config.grid_bounds[1]
        
        # Calcola dimensioni grid
        grid_extent = self.grid_max - self.grid_min
        self.grid_dims = np.ceil(grid_extent / self.cell_size).astype(int)
        
        # Hash table: cell_id → list of (soliton, position)
        self.cells: Dict[Tuple[int, int, int], List[Tuple[AbstractSoliton, np.ndarray]]] = {}
        
        # Statistiche
        self.N_solitons = 0
        self.N_cells_occupied = 0
        
        logger.info(f"SpatialHashGrid initialized: "
                   f"cell_size={self.cell_size}, "
                   f"grid_dims={self.grid_dims}")
    
    def _position_to_cell(self, position: np.ndarray) -> Tuple[int, int, int]:
        """
        Converte posizione 3D → indice cella (ix, iy, iz).
        
        Parameters:
        -----------
        position : ndarray, shape (3,)
            Posizione spaziale
        
        Returns:
        --------
        cell_id : tuple
            (ix, iy, iz) indice cella
        """
        # Normalizza posizione rispetto a grid_min
        rel_pos = position - self.grid_min
        
        # Calcola indice cella
        cell_idx = np.floor(rel_pos / self.cell_size).astype(int)
        
        # Clamp a bounds
        cell_idx = np.clip(cell_idx, 0, self.grid_dims - 1)
        
        return tuple(cell_idx)
    
    def build(self, solitons: List[AbstractSoliton]):
        """
        Costruisce hash grid da lista solitoni.
        
        Complessità: O(N)
        
        Parameters:
        -----------
        solitons : List[AbstractSoliton]
            Lista solitoni da indicizzare
        """
        # Reset grid
        self.cells.clear()
        self.N_solitons = len(solitons)
        
        # Inserisci solitoni nelle celle
        for soliton in solitons:
            pos = soliton.get_position()
            cell_id = self._position_to_cell(pos)
            
            if cell_id not in self.cells:
                self.cells[cell_id] = []
            
            self.cells[cell_id].append((soliton, pos))
        
        self.N_cells_occupied = len(self.cells)
        
        logger.debug(f"SpatialHashGrid built: "
                    f"{self.N_solitons} solitons in {self.N_cells_occupied} cells")
    
    def get_neighbors(
        self, 
        position: np.ndarray, 
        radius: float
    ) -> List[Tuple[AbstractSoliton, np.ndarray, float]]:
        """
        Query neighbor search (sphere search).
        
        Restituisce solitoni entro raggio `radius` da `position`.
        
        Complessità: O(k) dove k ~ numero neighbors (tipicamente k << N)
        
        Parameters:
        -----------
        position : ndarray
            Posizione centro query
        
        radius : float
            Raggio ricerca
        
        Returns:
        --------
        neighbors : List[(soliton, pos, distance)]
            Lista (solitone, posizione, distanza)
        """
        # Calcola celle da visitare
        cells_to_check = self._get_neighbor_cells(position, radius)
        
        neighbors = []
        
        for cell_id in cells_to_check:
            if cell_id not in self.cells:
                continue
            
            # Controlla distanza per ogni solitone in cella
            for soliton, sol_pos in self.cells[cell_id]:
                dist = np.linalg.norm(sol_pos - position)
                
                if dist <= radius:
                    neighbors.append((soliton, sol_pos, dist))
        
        return neighbors
    
    def _get_neighbor_cells(
        self, 
        position: np.ndarray, 
        radius: float
    ) -> List[Tuple[int, int, int]]:
        """
        Restituisce celle che intersecano sfera di raggio `radius`.
        
        Usa approccio conservativo: visita tutte le celle in box 3D.
        """
        # Cella centrale
        center_cell = self._position_to_cell(position)
        
        # Calcola offset massimo in celle
        cell_offset = int(np.ceil(radius / self.cell_size))
        
        # Genera liste celle
        cells = []
        
        for dx in range(-cell_offset, cell_offset + 1):
            for dy in range(-cell_offset, cell_offset + 1):
                for dz in range(-cell_offset, cell_offset + 1):
                    ix = center_cell[0] + dx
                    iy = center_cell[1] + dy
                    iz = center_cell[2] + dz
                    
                    # Controlla bounds
                    if (0 <= ix < self.grid_dims[0] and
                        0 <= iy < self.grid_dims[1] and
                        0 <= iz < self.grid_dims[2]):
                        cells.append((ix, iy, iz))
        
        return cells
    
    def get_cell_occupancy(self) -> dict:
        """
        Calcola statistiche occupazione celle.
        
        Returns:
        --------
        stats : dict
            Statistiche distribuzione
        """
        if not self.cells:
            return {
                'N_solitons': 0,
                'N_cells_total': np.prod(self.grid_dims),
                'N_cells_occupied': 0,
                'occupancy_ratio': 0.0,
                'solitons_per_cell_mean': 0.0,
                'solitons_per_cell_max': 0
            }
        
        # Conta solitoni per cella
        counts = [len(occupants) for occupants in self.cells.values()]
        
        return {
            'N_solitons': self.N_solitons,
            'N_cells_total': int(np.prod(self.grid_dims)),
            'N_cells_occupied': self.N_cells_occupied,
            'occupancy_ratio': self.N_cells_occupied / np.prod(self.grid_dims),
            'solitons_per_cell_mean': np.mean(counts),
            'solitons_per_cell_max': np.max(counts),
            'solitons_per_cell_std': np.std(counts)
        }
    
    def optimize_cell_size(self, interaction_radius: float):
        """
        Ottimizza cell_size per massimizzare performance.
        
        Rule of thumb: cell_size ~ interaction_radius (1x-2x)
        
        Parameters:
        -----------
        interaction_radius : float
            Raggio tipico interazione
        """
        optimal_size = interaction_radius * 1.5
        
        if abs(self.cell_size - optimal_size) / optimal_size > 0.2:
            logger.info(f"Optimizing cell_size: {self.cell_size:.2f} → {optimal_size:.2f}")
            
            self.cell_size = optimal_size
            
            # Ricalcola grid dimensions
            grid_extent = self.grid_max - self.grid_min
            self.grid_dims = np.ceil(grid_extent / self.cell_size).astype(int)
            
            # Rebuild grid (se già popolato)
            if self.cells:
                logger.warning("Grid was populated - rebuilding required")


# ========================================================================
# INTEGRATION HELPERS
# ========================================================================

def compute_pairwise_forces_optimized(
    solitons: List[AbstractSoliton],
    spatial_hash: SpatialHashGrid,
    interaction_radius: float,
    force_kernel
) -> np.ndarray:
    """
    Calcola forze pairwise usando spatial hash.
    
    Riduce complessità da O(N²) a O(N·k) dove k ~ neighbors.
    
    Parameters:
    -----------
    solitons : List[AbstractSoliton]
        Lista solitoni
    
    spatial_hash : SpatialHashGrid
        Hash grid pre-costruito
    
    interaction_radius : float
        Raggio cut-off interazione
    
    force_kernel : callable
        Funzione F(soliton_i, soliton_j, distance) → force_ij
    
    Returns:
    --------
    forces : ndarray, shape (N,)
        Forze su ogni solitone
    """
    N = len(solitons)
    forces = np.zeros(N)
    
    for i, sol_i in enumerate(solitons):
        pos_i = sol_i.get_position()
        
        # Query neighbors (solo entro interaction_radius)
        neighbors = spatial_hash.get_neighbors(pos_i, interaction_radius)
        
        for sol_j, pos_j, dist in neighbors:
            # Skip self-interaction
            if sol_i is sol_j:
                continue
            
            # Calcola forza tramite kernel
            force_ij = force_kernel(sol_i, sol_j, dist)
            forces[i] += force_ij
    
    return forces


# ========================================================================
# TEST
# ========================================================================

if __name__ == "__main__":
    import time
    
    print("\n" + "="*70)
    print(" TEST: SPATIAL HASH GRID")
    print("="*70 + "\n")
    
    # Mock soliton per testing
    class MockSoliton:
        def __init__(self, pos):
            self.position = pos
        def get_position(self):
            return self.position
    
    # Test 1: Costruzione grid
    print("Test 1: Costruzione Grid")
    print("-" * 70)
    
    config = SpatialHashConfig(
        cell_size=10.0,
        grid_bounds=(
            np.array([-50.0, -50.0, -50.0]),
            np.array([50.0, 50.0, 50.0])
        )
    )
    
    grid = SpatialHashGrid(config)
    
    # Crea 1000 solitoni random
    N_test = 1000
    solitons = [
        MockSoliton(np.random.uniform(-50, 50, 3))
        for _ in range(N_test)
    ]
    
    t0 = time.time()
    grid.build(solitons)
    t_build = time.time() - t0
    
    stats = grid.get_cell_occupancy()
    
    print(f"N solitons:         {stats['N_solitons']}")
    print(f"Cells total:        {stats['N_cells_total']}")
    print(f"Cells occupied:     {stats['N_cells_occupied']}")
    print(f"Occupancy ratio:    {stats['occupancy_ratio']:.3f}")
    print(f"Solitons/cell mean: {stats['solitons_per_cell_mean']:.2f}")
    print(f"Solitons/cell max:  {stats['solitons_per_cell_max']}")
    print(f"Build time:         {t_build*1000:.2f} ms")
    
    # Test 2: Neighbor query
    print("\nTest 2: Neighbor Query")
    print("-" * 70)
    
    query_pos = np.array([0.0, 0.0, 0.0])
    search_radius = 20.0
    
    t0 = time.time()
    neighbors = grid.get_neighbors(query_pos, search_radius)
    t_query = time.time() - t0
    
    print(f"Query position:   {query_pos}")
    print(f"Search radius:    {search_radius}")
    print(f"Neighbors found:  {len(neighbors)}")
    print(f"Query time:       {t_query*1000:.3f} ms")
    
    # Test 3: Performance comparison (naive vs hash)
    print("\nTest 3: Performance Comparison")
    print("-" * 70)
    
    # Naive: O(N²)
    t0 = time.time()
    naive_count = 0
    for sol_i in solitons[:100]:  # Limita a 100 per velocità
        for sol_j in solitons:
            dist = np.linalg.norm(sol_i.position - sol_j.position)
            if dist < search_radius and sol_i is not sol_j:
                naive_count += 1
    t_naive = time.time() - t0
    
    # Hash: O(N·k)
    t0 = time.time()
    hash_count = 0
    for sol_i in solitons[:100]:
        neighbors = grid.get_neighbors(sol_i.position, search_radius)
        hash_count += len([n for n in neighbors if n[0] is not sol_i])
    t_hash = time.time() - t0
    
    speedup = t_naive / t_hash if t_hash > 0 else float('inf')
    
    print(f"Naive approach:   {t_naive*1000:.2f} ms")
    print(f"Hash approach:    {t_hash*1000:.2f} ms")
    print(f"Speedup:          {speedup:.1f}x")
    
    print("\n" + "="*70)
    print(" SPATIAL HASH TEST COMPLETATO")
    print("="*70 + "\n")
