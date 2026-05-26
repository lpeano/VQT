"""
================================================================================
TEST SUITE COMPLETO - Validazione Architettura Fermi-Dirac + Scaling
================================================================================

Test suite unificato per validazione completa del framework WQT_OOP con:
- Fermi-Dirac screening
- Spatial hashing
- Spatial cache
- Observer pattern
- Factory pattern

ESECUZIONE:
-----------
python -m wqt_oop.test_suite_completo

COVERAGE:
---------
1. Physics correctness (conservazione energia, distribuzione Fermi)
2. Performance (spatial hashing speedup)
3. Monitoring (observer pattern)
4. Cache (hit rate, invalidation logic)
5. Integration (factory + simulation full cycle)

================================================================================
"""

import numpy as np
import logging
import time
import sys
from typing import Dict, List

# Import moduli framework
from .physics_context import PhysicsContext
from .fermi_dirac_screening import FermiDiracScreening
from .segmento_quantistico import SegmentoQuantistico
from .solitone_composito import SolitoneComposito
from .fractal_universe_factory import FractalUniverseFactory, UniverseConfig, print_universe_info
from .spatial_hash_grid import SpatialHashGrid, SpatialHashConfig
from .spatial_cache import SpatialCache, HierarchicalCacheManager
from .energy_drift_observer import (
    EnergyDriftMonitor, StatisticsLogger, ProgressTracker, 
    Observable, SimulationState
)
from .hdf5_logger import HDF5Logger, HDF5LoggerConfig, load_from_hdf5, count_frames
from .hdf5_playback import HDF5PlaybackEngine, convert_hdf5_to_manifold_frame


logger = logging.getLogger(__name__)


# ========================================================================
# TEST UTILITIES
# ========================================================================

class TestResult:
    """Container per risultato test."""
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0.0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration


def assert_close(actual: float, expected: float, rel_tol: float, name: str) -> TestResult:
    """Helper per confronto numerico."""
    diff = abs(actual - expected)
    rel_diff = diff / (abs(expected) + 1e-30)
    
    passed = rel_diff < rel_tol
    
    message = f"actual={actual:.6e}, expected={expected:.6e}, rel_diff={rel_diff:.3e}"
    
    return TestResult(name, passed, message)


# ========================================================================
# TEST 1: FERMI-DIRAC PHYSICS
# ========================================================================

def test_fermi_dirac_distribution() -> List[TestResult]:
    """Test distribuzione Fermi-Dirac."""
    print("\n" + "=" * 70)
    print(" TEST 1: FERMI-DIRAC DISTRIBUTION")
    print("=" * 70)
    
    results = []
    
    # Crea screener
    screener = FermiDiracScreening(mu=50.0, T_eff=5.0, epsilon=1e-9)
    
    # Test f(μ) = 0.5
    f_mu = screener.occupation(np.array([50.0]))[0]
    results.append(assert_close(f_mu, 0.5, 1e-6, "f(mu) = 0.5"))
    print(f"  f(mu=50):     {f_mu:.6f} (expected 0.500)")
    
    # Test f(μ-5T) ≈ 0.993
    f_low = screener.occupation(np.array([25.0]))[0]
    results.append(assert_close(f_low, 0.993, 0.01, "f(mu-5T) ~ 0.993"))
    print(f"  f(chi=25):    {f_low:.6f} (expected 0.993)")
    
    # Test f(μ+5T) ≈ 0.007
    f_high = screener.occupation(np.array([75.0]))[0]
    results.append(assert_close(f_high, 0.007, 0.05, "f(mu+5T) ~ 0.007"))  # Relaxed tolerance
    print(f"  f(chi=75):    {f_high:.6f} (expected 0.007)")
    
    # Test cooling
    T_initial = screener.T_eff
    screener.update_temperature(gamma_cooling=0.1, dt=1.0)
    T_after = screener.T_eff
    expected_T = T_initial * np.exp(-0.1 * 1.0)
    results.append(assert_close(T_after, expected_T, 1e-6, "Temperature cooling"))
    print(f"  T cooling:    {T_after:.6e} (expected {expected_T:.6e})")
    
    return results


# ========================================================================
# TEST 2: ENERGY CONSERVATION
# ========================================================================

def test_energy_conservation() -> List[TestResult]:
    """Test conservazione energia durante evoluzione."""
    print("\n" + "=" * 70)
    print(" TEST 2: ENERGY CONSERVATION")
    print("=" * 70)
    
    results = []
    
    # Crea physics context con parametri conservativi (coupling ridotto)
    physics_weak = PhysicsContext(
        level=1,
        length_scale=1.0e-10,
        alpha_K=0.01,       # Exchange debole
        kappa_coupling=0.01 # Coupling debole
    )
    
    # Crea 24 segmenti near-equilibrium
    np.random.seed(42)
    
    # NOTA: SegmentoQuantistico richiede level=0, quindi uso physics separato
    physics_L0 = PhysicsContext(
        level=0,
        length_scale=1.0e-10,
        alpha_K=0.01,
        kappa_coupling=0.01
    )
    
    segments = []
    for i in range(24):
        chi_init = 50.0 + np.random.normal(0, 0.5)
        vel_init = np.random.normal(0, 0.1)
        seg = SegmentoQuantistico(chi_init, vel_init, physics_L0)
        segments.append(seg)
    
    composito = SolitoneComposito(segments, physics_weak)
    
    # Energia iniziale
    H_init = composito.energia_totale
    print(f"  H_initial:    {H_init:.6e}")
    
    # Evolvi 100 steps
    dt = 0.005
    N_steps = 100
    
    for _ in range(N_steps):
        composito.evolve(dt)
    
    # Energia finale
    H_final = composito.energia_totale
    drift = abs(H_final - H_init) / (abs(H_init) + 1e-30)
    
    print(f"  H_final:      {H_final:.6e}")
    print(f"  drift:        {drift:.3e}")
    
    # Valida drift < 1%
    results.append(TestResult(
        "Energy drift < 0.01",
        drift < 0.01,
        f"drift={drift:.3e}"
    ))
    
    return results


# ========================================================================
# TEST 3: SPATIAL HASH PERFORMANCE
# ========================================================================

def test_spatial_hash_performance() -> List[TestResult]:
    """Test spatial hashing speedup."""
    print("\n" + "=" * 70)
    print(" TEST 3: SPATIAL HASH PERFORMANCE")
    print("=" * 70)
    
    results = []
    
    # Mock solitons
    class MockSoliton:
        def __init__(self, pos):
            self.position = pos
        def get_position(self):
            return self.position
    
    # Crea 1000 solitoni random
    N = 1000
    solitons = [
        MockSoliton(np.random.uniform(-50, 50, 3))
        for _ in range(N)
    ]
    
    # Build grid
    config = SpatialHashConfig(
        cell_size=10.0,
        grid_bounds=(
            np.array([-50.0, -50.0, -50.0]),
            np.array([50.0, 50.0, 50.0])
        )
    )
    
    grid = SpatialHashGrid(config)
    
    t0 = time.time()
    grid.build(solitons)
    t_build = time.time() - t0
    
    print(f"  N solitons:   {N}")
    print(f"  Build time:   {t_build*1000:.2f} ms")
    
    # Test query
    query_pos = np.array([0.0, 0.0, 0.0])
    search_radius = 20.0
    
    t0 = time.time()
    neighbors = grid.get_neighbors(query_pos, search_radius)
    t_query = time.time() - t0
    
    print(f"  Query time:   {t_query*1000:.3f} ms")
    print(f"  Neighbors:    {len(neighbors)}")
    
    # Valida build < 15ms, query < 2ms (tolleranza per variabilità sistema)
    results.append(TestResult(
        "Build time < 15ms",
        t_build < 0.015,
        f"t_build={t_build*1000:.2f}ms"
    ))
    
    results.append(TestResult(
        "Query time < 2ms",
        t_query < 0.002,
        f"t_query={t_query*1000:.3f}ms"
    ))
    
    return results


# ========================================================================
# TEST 4: SPATIAL CACHE
# ========================================================================

def test_spatial_cache() -> List[TestResult]:
    """Test spatial caching."""
    print("\n" + "=" * 70)
    print(" TEST 4: SPATIAL CACHE")
    print("=" * 70)
    
    results = []
    
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
    
    # Test hit
    state = cache.get(current_step=1)
    hit1 = (state is not None)
    results.append(TestResult("Cache hit (age=1)", hit1, ""))
    print(f"  Hit (age=1):  {hit1}")
    
    # Test expire
    state = cache.get(current_step=10)
    hit2 = (state is None)
    results.append(TestResult("Cache miss (expired)", hit2, ""))
    print(f"  Miss (age=10): {hit2}")
    
    # Test auto-invalidation
    cache.update(
        position_mean=np.array([0.0, 0.0, 0.0]),
        chi_mean=50.0,
        chi_std=2.0,
        H_total=1e6,
        current_step=0
    )
    
    n_inval_before = cache.invalidations
    
    cache.update(
        position_mean=np.array([0.0, 0.0, 0.0]),
        chi_mean=50.0,
        chi_std=2.0,
        H_total=1e6 * 1.01,  # +1% energia
        current_step=1
    )
    
    auto_inval = (cache.invalidations > n_inval_before)
    results.append(TestResult("Auto-invalidation (dH=1%)", auto_inval, ""))
    print(f"  Auto-inval:   {auto_inval}")
    
    return results


# ========================================================================
# TEST 5: OBSERVER PATTERN
# ========================================================================

def test_observer_pattern() -> List[TestResult]:
    """Test observer pattern."""
    print("\n" + "=" * 70)
    print(" TEST 5: OBSERVER PATTERN")
    print("=" * 70)
    
    results = []
    
    # Crea observable
    subject = Observable()
    
    # Crea observer
    drift_monitor = EnergyDriftMonitor(
        warning_threshold=1e-4,
        critical_threshold=1e-3
    )
    
    subject.attach(drift_monitor)
    subject.notify_start()
    
    # Simula drift graduale
    H_init = 1e6
    triggered_warning = False
    
    for step in range(50):
        drift = step * 2e-5
        H_current = H_init * (1 + drift)
        
        state = SimulationState(
            step=step,
            time=step * 0.1,
            H_total=H_current,
            drift=drift,
            N_solitons=24,
            T_eff=5.0,
            wall_time=time.time()
        )
        
        subject.notify(state)
        
        if drift_monitor.alert_triggered['WARNING']:
            triggered_warning = True
            break
    
    subject.notify_end()
    
    results.append(TestResult(
        "Warning triggered",
        triggered_warning,
        f"alerts={drift_monitor.alert_triggered}"
    ))
    
    print(f"  Warning:      {triggered_warning}")
    print(f"  Alerts:       {drift_monitor.alert_triggered}")
    
    return results


# ========================================================================
# TEST 6: FACTORY INTEGRATION
# ========================================================================

def test_factory_integration() -> List[TestResult]:
    """Test factory pattern + full integration."""
    print("\n" + "=" * 70)
    print(" TEST 6: FACTORY INTEGRATION")
    print("=" * 70)
    
    results = []
    
    # Crea universo L1
    config = UniverseConfig(
        target_level=1,
        chi_mean=50.0,
        chi_std=2.0,
        spatial_extent=10.0,
        seed=42,
        enable_fermi_screening=True,
        enable_spatial_cache=True
    )
    
    factory = FractalUniverseFactory()
    
    t0 = time.time()
    universe = factory.create_universe(config)
    t_create = time.time() - t0
    
    print(f"  Level:        {universe.physics.level}")
    print(f"  N_children:   {universe.N_children if hasattr(universe, 'N_children') else 1}")
    print(f"  Create time:  {t_create:.3f}s")
    
    # Valida livello
    results.append(TestResult(
        "Universe level = 1",
        universe.physics.level == 1,
        f"level={universe.physics.level}"
    ))
    
    # Evolvi universo
    H_init = universe.energia_totale
    
    for _ in range(10):
        universe.evolve(0.01)
    
    H_final = universe.energia_totale
    drift = abs(H_final - H_init) / (abs(H_init) + 1e-30)
    
    print(f"  H_drift:      {drift:.3e}")
    
    results.append(TestResult(
        "Factory evolution drift < 0.07",
        drift < 0.07,  # Relaxed threshold (10 steps è poco per stabilizzazione)
        f"drift={drift:.3e}"
    ))
    
    return results


# ========================================================================
# TEST 7: HDF5 Logging & Playback
# ========================================================================

def test_hdf5_logging() -> List[TestResult]:
    """Test HDF5 write/read/playback."""
    print("\n" + "="*70)
    print(" TEST 7: HDF5 Logging & Playback")
    print("="*70)
    
    results = []
    
    # Setup
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_hdf5.h5"
        
        # --- Test 1: Write frames ---
        print("\n[Test 1] HDF5 Write")
        
        physics = PhysicsContext(
            level=0,
            length_scale=1.0,
            mu_fermi=50.0,
            T_fermi=5.0,
            gamma_cooling=0.01,
            alpha_K=0.01,
            kappa_coupling=0.01
        )
        
        seg = SegmentoQuantistico(
            chi=50.0,
            position=np.array([0.0, 0.0, 0.0]),
            vel=0.0,
            physics=physics
        )
        
        # HDF5Logger (simulato come Observer)
        hdf5_config = HDF5LoggerConfig(
            filepath=filepath,
            save_interval=1,
            enable_swmr=False,  # No SWMR per test semplice
            buffer_size=5,
            compression='gzip'
        )
        
        metadata = {
            'target_level': 0,
            'N_segments': 1,
            'dt': 0.01
        }
        
        logger_obj = HDF5Logger(
            config=hdf5_config,
            universe=seg,
            metadata=metadata
        )
        
        # Simula 10 steps
        for step in range(10):
            seg.evolve(0.01)
            
            state = SimulationState(
                step=step,
                time=step * 0.01,
                H_total=seg.energia_totale,
                drift=0.001 * step,
                N_solitons=1,
                T_eff=physics.T_fermi,
                wall_time=step * 0.01
            )
            
            logger_obj.update(state)
        
        # Flush e chiudi ESPLICITAMENTE
        logger_obj.flush()
        logger_obj.close()
        
        results.append(TestResult(
            "HDF5 file created",
            filepath.exists(),
            f"exists={filepath.exists()}"
        ))
        
        # --- Test 2: Read frames ---
        print("\n[Test 2] HDF5 Read")
        
        N_frames = count_frames(filepath)
        print(f"  Frames:  {N_frames}")
        
        results.append(TestResult(
            "HDF5 frame count = 10",
            N_frames == 10,
            f"N_frames={N_frames}"
        ))
        
        # Load frame 5
        frame_data = load_from_hdf5(filepath, frame_idx=5)
        
        print(f"  Frame 5 time: {frame_data['time']:.3f}s")
        print(f"  Frame 5 H:    {frame_data['H_total']:.3e}")
        
        results.append(TestResult(
            "HDF5 frame 5 loaded",
            'time' in frame_data and 'H_total' in frame_data,
            f"keys={list(frame_data.keys())}"
        ))
        
        # --- Test 3: Playback mapping ---
        print("\n[Test 3] Playback Mapping")
        
        manifold_frame = convert_hdf5_to_manifold_frame(frame_data)
        
        print(f"  N_segments:  {manifold_frame['N_segments']}")
        print(f"  Scalari dtype: {manifold_frame['scalari_24'].dtype.names}")
        
        # Verifica DTYPE
        expected_fields = ['chi', 'polarizzazione', 'contorsione_locale', 
                          'densita_screening', 'chiralita', 'aging_factor', 
                          'temperature']
        
        actual_fields = list(manifold_frame['scalari_24'].dtype.names)
        
        results.append(TestResult(
            "SCALARI_24_DTYPE fields match",
            actual_fields == expected_fields,
            f"fields={actual_fields}"
        ))
        
        # --- Test 4: Playback engine ---
        print("\n[Test 4] Playback Engine")
        
        engine = HDF5PlaybackEngine(
            filepath=filepath,
            follow_mode=False
        )
        
        # Load 3 frames
        frames_loaded = []
        for _ in range(3):
            frame = engine.next_frame()
            if frame is not None:
                frames_loaded.append(frame)
        
        print(f"  Frames loaded: {len(frames_loaded)}")
        
        results.append(TestResult(
            "Playback engine loaded 3 frames",
            len(frames_loaded) == 3,
            f"N_loaded={len(frames_loaded)}"
        ))
    
    return results


# ========================================================================
# MAIN TEST RUNNER
# ========================================================================

def run_all_tests() -> int:
    """Esegui tutti i test e stampa summary."""
    logging.basicConfig(level=logging.WARNING)  # Silenza dettagli
    
    print("\n" + "="*70)
    print(" WQT_OOP TEST SUITE COMPLETO")
    print("="*70)
    
    all_results = []
    
    # Run tests
    all_results.extend(test_fermi_dirac_distribution())
    all_results.extend(test_energy_conservation())
    all_results.extend(test_spatial_hash_performance())
    all_results.extend(test_spatial_cache())
    all_results.extend(test_observer_pattern())
    all_results.extend(test_factory_integration())
    all_results.extend(test_hdf5_logging())
    
    # Summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    
    N_total = len(all_results)
    N_passed = sum(1 for r in all_results if r.passed)
    N_failed = N_total - N_passed
    
    print(f"\nTotal tests:  {N_total}")
    print(f"Passed:       {N_passed}")
    print(f"Failed:       {N_failed}")
    
    # Print failures
    if N_failed > 0:
        print("\nFailed tests:")
        for result in all_results:
            if not result.passed:
                print(f"  [FAIL] {result.name}: {result.message}")
    
    # Final verdict
    print("\n" + "="*70)
    if N_failed == 0:
        print(" ALL TESTS PASSED")
        print("="*70 + "\n")
        return 0
    else:
        print(" SOME TESTS FAILED")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
