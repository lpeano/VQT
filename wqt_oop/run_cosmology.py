"""
================================================================================
RUN COSMOLOGY - Entry Point Unificato per Simulazioni WQT
================================================================================

Entry point principale per eseguire simulazioni cosmologiche multi-livello.

USAGE:
------
python -m wqt_oop.run_cosmology --level 2 --steps 1000 --dt 0.01 --output sim_L2.h5

FEATURES:
- Factory automatica universo frattale
- Spatial hashing per performance O(N log N)
- Observer pattern per monitoring real-time
- Salvataggio HDF5 incrementale
- Configurazione via CLI o file YAML

================================================================================
"""

import numpy as np
import argparse
import logging
import time
import sys
from pathlib import Path
from typing import Optional

# Import framework
from .fractal_universe_factory import FractalUniverseFactory, UniverseConfig, print_universe_info
from .spatial_hash_grid import SpatialHashGrid, SpatialHashConfig
from .energy_drift_observer import (
    Observable, EnergyDriftMonitor, StatisticsLogger, 
    ProgressTracker, SimulationState
)
from .hdf5_logger import HDF5Logger, HDF5LoggerConfig
from .abstract_soliton import AbstractSoliton
from .solitone_composito import SolitoneComposito
from .physics_context import PhysicsContext


logger = logging.getLogger(__name__)


class CosmologySimulation(Observable):
    """
    Simulazione cosmologica completa con monitoring.
    
    Combina:
    - FractalUniverseFactory per generazione
    - SpatialHashGrid per performance
    - Observer pattern per monitoring
    - HDF5 I/O per persistenza
    """
    
    def __init__(
        self,
        universe: AbstractSoliton,
        dt: float = 0.01,
        enable_spatial_hash: bool = True,
        spatial_hash_config: Optional[SpatialHashConfig] = None
    ):
        """
        Inizializza simulazione.
        
        Parameters:
        -----------
        universe : AbstractSoliton
            Universo frattale (root)
        
        dt : float
            Timestep integrazione
        
        enable_spatial_hash : bool
            Abilita spatial hashing
        
        spatial_hash_config : SpatialHashConfig, optional
            Config spatial hash
        """
        super().__init__()
        
        self.universe = universe
        self.dt = dt
        self.current_step = 0
        self.current_time = 0.0
        
        # Spatial hashing (opzionale)
        self.enable_spatial_hash = enable_spatial_hash
        self.spatial_hash = None
        
        if enable_spatial_hash:
            if spatial_hash_config is None:
                # Auto-config
                spatial_hash_config = SpatialHashConfig(
                    cell_size=10.0,
                    grid_bounds=(
                        np.array([-100.0, -100.0, -100.0]),
                        np.array([100.0, 100.0, 100.0])
                    )
                )
            
            self.spatial_hash = SpatialHashGrid(spatial_hash_config)
            logger.info("Spatial hashing ENABLED")
        
        # Energia iniziale
        self.H_initial = self.universe.energia_totale
        
        logger.info(f"CosmologySimulation initialized: dt={dt}, H_init={self.H_initial:.6e}")
    
    def run(self, total_steps: int):
        """
        Execute full cosmological simulation for N timesteps.
        
        **Physics Principle**: Time Evolution of Hierarchical Hamiltonian System
        **Reference**: PHYSICS_MANIFESTO.md § 4 "Dynamics & Evolution"
        
        **Algorithm**:
        ```
        for step in 1..N:
            1. Evolve universe → universe.evolve(dt)  [Symplectic integration cascade]
            2. Extract state → H_total, drift, T_eff  [Observables]
            3. Notify observers → Log, HDF5, Monitoring [Observer pattern]
        ```
        
        **Physical Interpretation**:
        - Each step propagates ALL segments via recursive evolve() cascade
        - Energy drift |ΔH/H| monitors conservation (should be < 0.1%)
        - T_eff tracks effective temperature (thermal homeostasis)
        - Observer pattern decouples physics from I/O (separation of concerns)
        
        Parameters:
        -----------
        total_steps : int
            Total number of timesteps (physical time = total_steps × dt)
        """
        logger.info(f"Starting simulation: {total_steps} steps")
        
        # [PHYSICS_TRACE] Notify observers: Simulation START
        # Purpose: Initialize HDF5 file, reset energy baseline, start wall-clock timer
        self.notify_start()
        
        try:
            # [PHYSICS_TRACE] Main evolution loop
            # Physical process: Time evolution via recursive Hamiltonian cascade
            # Each iteration advances physical time by dt (Planck time units)
            for step in range(total_steps):
                # [PHYSICS_TRACE] Evolve universe by one timestep
                # Cascade: Root.evolve() → Children.evolve() → ... → Segments.evolve()
                # Algorithm: Symplectic Verlet at each level (see PHYSICS_MANIFESTO.md § 4.1)
                self.step()
                
                # [PHYSICS_TRACE] Create state snapshot for monitoring
                # Observables: H_total (Hamiltonian), drift (|ΔH/H|), T_eff (temperature)
                # Physical meaning: Macroscopic quantities derived from microscopic state
                state = self._create_state_snapshot()
                
                # [PHYSICS_TRACE] Notify all observers (logging, HDF5, monitoring)
                # Pattern: Observer pattern decouples physics engine from I/O
                # Observers can: Log to console, save HDF5 frame, check drift warnings
                self.notify(state)
        
        except Exception as e:
            logger.error(f"Simulation error at step {self.current_step}: {e}")
            raise
        
        finally:
            # [PHYSICS_TRACE] Notify observers: Simulation END
            # Purpose: Finalize HDF5, compute statistics, close resources
            self.notify_end()
    
    def step(self):
        """
        Single timestep evolution.
        
        **Physics Principle**: Recursive Hamiltonian Time Propagation
        **Reference**: PHYSICS_MANIFESTO.md § 3 "Hierarchical Structure"
        
        **Algorithm**:
        ```
        universe.evolve(dt) triggers recursive cascade:
          SolitoneComposito(L3).evolve(dt)
            → for each child in L2:
                SolitoneComposito(L2).evolve(dt)
                  → for each child in L1:
                      ... → SegmentoQuantistico(L0).evolve(dt) [Verlet]
        ```
        
        **Physical Interpretation**:
        - Each level evolves its children via parent-mediated coupling
        - Inter-level energy transfer via hierarchical damping γ_h
        - Symplectic property preserved at ALL levels (phase-space volume conservation)
        - Time propagates "top-down" but forces computed "bottom-up"
        """
        # [PHYSICS_TRACE] Evolve universe (recursive cascade to all segments)
        # Physical meaning: Advance system state by dt in phase space
        self.universe.evolve(self.dt)
        
        # [PHYSICS_TRACE] Update global time counters
        # step: Discrete timestep index (integer)
        # time: Physical time = step × dt [Planck time units]
        self.current_step += 1
        self.current_time += self.dt
    
    def _create_state_snapshot(self) -> SimulationState:
        """
        Create state snapshot for observer monitoring.
        
        **Physics Principle**: Macroscopic Observables from Microscopic State
        **Reference**: PHYSICS_MANIFESTO.md § 5 "Conservation Laws"
        
        **Observables Extracted**:
        ```
        H_total:  Total Hamiltonian = Σ_i H_i(segment) + U_coupling
        drift:    |ΔH/H| = |H_current - H_initial| / H_initial  [Conservation check]
        T_eff:    Effective temperature from Fermi-Dirac screening
        ```
        
        **Physical Interpretation**:
        - H_total: Total energy (should be conserved, drift < 0.1%)
        - drift: Measure of symplectic integration quality
        - T_eff: Emergent temperature from RG flow (thermal homeostasis)
        
        Returns:
        --------
        state : SimulationState
            Snapshot with all observables
        """
        # [PHYSICS_TRACE] Compute total Hamiltonian
        # Physical meaning: Sum of all segment energies + inter-segment coupling
        H_current = self.universe.energia_totale
        
        # [PHYSICS_TRACE] Compute energy drift (conservation check)
        # Formula: drift = |ΔH/H| = |H_current - H_initial| / H_initial
        # Acceptable: < 0.1% (symplectic integration quality)
        drift = abs(H_current - self.H_initial) / (abs(self.H_initial) + 1e-30)
        
        # [PHYSICS_TRACE] Extract effective temperature (if composite)
        # Physical meaning: T_eff from Fermi-Dirac topological screening
        # See PHYSICS_MANIFESTO.md § 3.2 for T_eff derivation
        T_eff = 0.0
        N_solitons = 1
        
        if isinstance(self.universe, SolitoneComposito):
            T_eff = self.universe.fermi_screener.T_eff
            N_solitons = self.universe.N_children
        
        return SimulationState(
            step=self.current_step,
            time=self.current_time,
            H_total=H_current,
            drift=drift,
            N_solitons=N_solitons,
            T_eff=T_eff,
            wall_time=time.time()
        )


# ========================================================================
# CLI INTERFACE
# ========================================================================

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="WQT Cosmology Simulation - Fractal Universe Evolution",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Simulation parameters
    parser.add_argument(
        '--level', '-l',
        type=int,
        default=2,
        help='Target fractal level (0=segments, 1=solitons, 2=macro, ...)'
    )
    
    parser.add_argument(
        '--steps', '-n',
        type=int,
        default=1000,
        help='Total integration steps'
    )
    
    parser.add_argument(
        '--dt',
        type=float,
        default=0.01,
        help='Timestep [s]'
    )
    
    # Universe configuration
    parser.add_argument(
        '--chi-mean',
        type=float,
        default=50.0,
        help='Mean chi field value'
    )
    
    parser.add_argument(
        '--chi-std',
        type=float,
        default=5.0,
        help='Chi standard deviation'
    )
    
    parser.add_argument(
        '--spatial-extent',
        type=float,
        default=100.0,
        help='Spatial box size [m]'
    )
    
    # Performance
    parser.add_argument(
        '--enable-spatial-hash',
        action='store_true',
        default=True,
        help='Enable spatial hashing for O(N log N) performance'
    )
    
    # Monitoring
    parser.add_argument(
        '--log-interval',
        type=int,
        default=100,
        help='Log statistics every N steps'
    )
    
    parser.add_argument(
        '--drift-warning',
        type=float,
        default=1e-3,
        help='Warning threshold for energy drift'
    )
    
    parser.add_argument(
        '--drift-critical',
        type=float,
        default=1e-2,
        help='Critical threshold for energy drift'
    )
    
    # Output
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output HDF5 file (optional)'
    )
    
    parser.add_argument(
        '--save-interval',
        type=int,
        default=1,
        help='Save HDF5 frame every N steps (default: 1 = every step)'
    )
    
    parser.add_argument(
        '--hdf5-compression',
        type=str,
        default='gzip',
        choices=['gzip', 'lzf', 'none'],
        help='HDF5 compression type'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed'
    )
    
    # Logging
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose logging'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("="*70)
    logger.info(" WQT COSMOLOGY SIMULATION")
    logger.info("="*70)
    
    # Print configuration
    logger.info("\nConfiguration:")
    logger.info(f"  Target Level:    {args.level}")
    logger.info(f"  Total Steps:     {args.steps}")
    logger.info(f"  Timestep:        {args.dt} s")
    logger.info(f"  Chi Mean:        {args.chi_mean}")
    logger.info(f"  Spatial Extent:  {args.spatial_extent} m")
    logger.info(f"  Spatial Hash:    {'ENABLED' if args.enable_spatial_hash else 'DISABLED'}")
    logger.info(f"  Seed:            {args.seed}")
    
    # PHASE 1: Create Universe
    logger.info("\n" + "="*70)
    logger.info(" PHASE 1: Universe Generation")
    logger.info("="*70)
    
    config = UniverseConfig(
        target_level=args.level,
        chi_mean=args.chi_mean,
        chi_std=args.chi_std,
        spatial_extent=args.spatial_extent,
        seed=args.seed,
        enable_fermi_screening=True,
        enable_spatial_cache=True
    )
    
    # Create factory with WEAKER coupling for stability
    # NOTE: Default PhysicsContext scaling (24^2 per level) è troppo forte
    # per simulazioni generali. Usiamo coupling ridotto.
    from .physics_context import PhysicsContext
    
    base_physics = PhysicsContext(
        level=0,
        length_scale=1.0e-10,
        alpha_K=0.01,        # Reduced from 1.0
        kappa_coupling=0.01,  # Reduced from 0.25
        lambda_exchange=0.001,  # Reduced from 0.05
        mu_fermi=50.0,
        T_fermi=5.0,
        gamma_cooling=0.01
    )
    
    factory = FractalUniverseFactory(base_physics=base_physics)
    
    # Estimate memory
    mem_info = factory.estimate_memory(args.level)
    logger.info(f"\nMemory estimate:")
    logger.info(f"  Total segments: {mem_info['N_segments']}")
    logger.info(f"  Memory:         {mem_info['total_memory_MB']:.2f} MB")
    
    # Create universe
    t0 = time.time()
    universe = factory.create_universe(config)
    t_create = time.time() - t0
    
    logger.info(f"\nUniverse created in {t_create:.2f}s")
    print_universe_info(universe, config)
    
    # PHASE 2: Setup Simulation
    logger.info("\n" + "="*70)
    logger.info(" PHASE 2: Simulation Setup")
    logger.info("="*70)
    
    sim = CosmologySimulation(
        universe=universe,
        dt=args.dt,
        enable_spatial_hash=args.enable_spatial_hash
    )
    
    # Attach observers
    drift_monitor = EnergyDriftMonitor(
        warning_threshold=args.drift_warning,
        critical_threshold=args.drift_critical,
        emergency_threshold=0.1
    )
    
    stats_logger = StatisticsLogger(log_interval=args.log_interval)
    progress_tracker = ProgressTracker(total_steps=args.steps)
    
    sim.attach(drift_monitor)
    sim.attach(stats_logger)
    sim.attach(progress_tracker)
    
    # HDF5 Logger (se --output specificato)
    hdf5_logger = None
    if args.output is not None:
        from pathlib import Path
        
        compression = args.hdf5_compression if args.hdf5_compression != 'none' else None
        
        hdf5_config = HDF5LoggerConfig(
            filepath=Path(args.output),
            save_interval=args.save_interval,
            enable_swmr=True,  # SWMR per rendering real-time
            buffer_size=10,
            compression=compression
        )
        
        hdf5_metadata = {
            'target_level': args.level,
            'total_steps': args.steps,
            'dt': args.dt,
            'chi_mean': args.chi_mean,
            'chi_std': args.chi_std,
            'spatial_extent': args.spatial_extent,
            'seed': args.seed
        }
        
        hdf5_logger = HDF5Logger(
            config=hdf5_config,
            universe=universe,
            metadata=hdf5_metadata
        )
        
        sim.attach(hdf5_logger)
        logger.info("  - HDF5Logger (SWMR enabled)")
        logger.info(f"    Output: {args.output}")
        logger.info(f"    Save interval: {args.save_interval}")
        logger.info(f"    Compression: {compression or 'none'}")
    
    logger.info("Observers attached:")
    logger.info("  - EnergyDriftMonitor")
    logger.info("  - StatisticsLogger")
    logger.info("  - ProgressTracker")
    
    # PHASE 3: Run Simulation
    logger.info("\n" + "="*70)
    logger.info(" PHASE 3: Evolution")
    logger.info("="*70)
    
    t0 = time.time()
    
    try:
        sim.run(args.steps)
    except RuntimeError as e:
        logger.error(f"Simulation terminated: {e}")
        return 1
    
    t_sim = time.time() - t0
    
    # PHASE 4: Results
    logger.info("\n" + "="*70)
    logger.info(" RESULTS")
    logger.info("="*70)
    
    logger.info(f"\nTotal wall time:  {t_sim:.2f}s")
    logger.info(f"Steps/second:     {args.steps / t_sim:.2f}")
    logger.info(f"Time/step:        {t_sim / args.steps * 1000:.2f} ms")
    
    # Drift statistics
    drift_stats = drift_monitor.get_drift_statistics()
    logger.info(f"\nEnergy Drift:")
    logger.info(f"  Final:  {drift_stats['drift_current']:.3e}")
    logger.info(f"  Mean:   {drift_stats['drift_mean']:.3e}")
    logger.info(f"  Max:    {drift_stats['drift_max']:.3e}")
    
    # Final state
    if isinstance(universe, SolitoneComposito):
        stats = universe.get_occupazione_stati()
        logger.info(f"\nFinal State:")
        logger.info(f"  T_eff:          {stats['T_eff']:.3e}")
        logger.info(f"  Destrorsi:      {stats['N_destro']}")
        logger.info(f"  Sinistrorsi:    {stats['N_sinistro']}")
        logger.info(f"  Polarizzazione: {stats['polarizzazione']:+.3f}")
    
    logger.info("\n" + "="*70)
    logger.info(" SIMULATION COMPLETED SUCCESSFULLY")
    logger.info("="*70 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
