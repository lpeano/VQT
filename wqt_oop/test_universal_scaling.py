"""
================================================================================
TEST UNIVERSAL SCALING - Validazione Dissipazione Frattale Auto-Consistente
================================================================================

Test suite per validare il modello di dissipazione universale con:
- Legge di scala frattale: \u03b3_n = \u03b3_0 \u00b7 (24^n)^k
- Feedback termodinamico: modulazione per T_eff
- Trasferimento energetico gerarchico (serbatoio energetico)

OBIETTIVO:
Verificare che L3 (13,824 segmenti) si stabilizzi senza interventi manuali,
mantenendo drift energetico < 10% grazie al damping adattivo.

ESECUZIONE:
-----------
python -m wqt_oop.test_universal_scaling

================================================================================
"""

import numpy as np
import logging
from typing import Dict
import time

from .physics_context import PhysicsContext
from .fractal_universe_factory import FractalUniverseFactory, UniverseConfig
from .energy_drift_observer import EnergyDriftMonitor, Observable, SimulationState


logger = logging.getLogger(__name__)


class SimpleSimulation(Observable):
    """
    Simulazione minima per test damping.
    
    Observable per integration con EnergyDriftMonitor.
    """
    
    def __init__(self, universe, dt: float):
        super().__init__()
        self.universe = universe
        self.dt = dt
        self.H_initial = universe.energia_totale
        self.current_step = 0
        self.time = 0.0
    
    def step(self) -> SimulationState:
        """Esegui un step temporale."""
        self.universe.evolve(self.dt)
        
        self.current_step += 1
        self.time += self.dt
        
        # Calcola drift
        H_current = self.universe.energia_totale
        drift = abs(H_current - self.H_initial) / (abs(self.H_initial) + 1e-30)
        
        # Stato per observers
        state = SimulationState(
            step=self.current_step,
            time=self.time,
            H_total=H_current,
            drift=drift,
            N_solitons=self.universe.N_children if hasattr(self.universe, 'N_children') else 1,
            T_eff=self.universe.physics.T_fermi,
            wall_time=0.0  # Non usato in test
        )
        
        # Notifica observers
        self.notify(state)
        
        return state


def test_damping_scaling_law():
    """
    Test 1: Verifica legge di scala frattale \u03b3_n = \u03b3_0 \u00b7 (24^n)^k.
    """
    print("\\n" + "="*70)
    print(" TEST 1: Legge di Scala Frattale Damping")
    print("="*70)
    
    gamma_0 = 0.0005  # RIDOTTO per stabilità L3
    k = 0.2  # Scaling molto conservativo
    
    results = []
    
    for level in range(4):
        physics = PhysicsContext.for_level(
            level=level,
            base_context=PhysicsContext(
                level=0,
                length_scale=1.0,
                gamma_damping_base=gamma_0,
                damping_scaling_exponent=k
            )
        )
        
        # Verifica scaling
        expected_gamma_base = gamma_0 * (24 ** level) ** k
        actual_gamma_base = physics.gamma_damping_base
        
        ratio = actual_gamma_base / expected_gamma_base if expected_gamma_base > 0 else 1.0
        
        print(f"  L{level}: gamma_base = {actual_gamma_base:.6f} (expected {expected_gamma_base:.6f}, ratio={ratio:.3f})")
        
        results.append(abs(ratio - 1.0) < 0.01)  # Tolleranza 1%
    
    success = all(results)
    print(f"\\n  Result: {'PASS' if success else 'FAIL'}")
    
    return success


def test_thermal_modulation():
    """
    Test 2: Verifica modulazione termica del damping.
    """
    print("\\n" + "="*70)
    print(" TEST 2: Modulazione Termica Damping")
    print("="*70)
    
    physics = PhysicsContext(
        level=1,
        length_scale=1.0,
        gamma_damping_base=0.001,
        damping_scaling_exponent=0.5,
        thermal_feedback_strength=0.1,
        T_fermi=10.0
    )
    
    T_ref = physics.T_fermi
    tau_variance = 0.1  # Fisso per isolare effetto termico
    
    test_cases = [
        (T_ref * 0.5, "freddo"),  # Sistema freddo \u2192 damping ridotto
        (T_ref * 1.0, "nominale"),  # Temperatura nominale
        (T_ref * 2.0, "caldo")  # Sistema caldo \u2192 damping aumentato
    ]
    
    results = []
    gamma_prev = 0.0
    
    for T_eff, label in test_cases:
        gamma = physics.get_adaptive_damping(T_eff=T_eff, tau_variance=tau_variance)
        
        # Verifica monotonicita: gamma aumenta con T_eff
        if gamma_prev > 0:
            is_increasing = gamma > gamma_prev
            results.append(is_increasing)
        
        print(f"  T_eff/{T_ref}={T_eff/T_ref:.1f} ({label:8s}): gamma = {gamma:.6f}")
        gamma_prev = gamma
    
    success = all(results)
    print(f"\\n  Result: {'PASS' if success else 'FAIL'} (damping increases with temperature)")
    
    return success


def test_energy_transfer():
    """
    Test 3: Verifica trasferimento energetico gerarchico (serbatoio).
    """
    print("\\n" + "="*70)
    print(" TEST 3: Trasferimento Energetico Gerarchico")
    print("="*70)
    
    # Crea universo L1 con damping abilitato
    base_physics = PhysicsContext(
        level=0,
        length_scale=1.0,
        gamma_damping_base=0.01,  # Damping significativo per test
        damping_scaling_exponent=0.5,
        mu_fermi=50.0,
        T_fermi=5.0
    )
    
    config = UniverseConfig(
        target_level=1,
        chi_mean=50.0,
        chi_std=5.0,
        spatial_extent=100.0,
        seed=42
    )
    
    factory = FractalUniverseFactory(base_physics=base_physics)
    universe = factory.create_universe(config)
    
    # Misura energetica iniziale
    budget_before = universe.get_energy_budget()
    H_before = budget_before['H_total']
    
    # Evolvi con damping
    universe.evolve(dt=0.01)
    
    # Misura energetica finale
    budget_after = universe.get_energy_budget()
    E_radiated = budget_after['E_radiated']
    E_transferred = budget_after['E_transferred']
    E_net_dissipated = budget_after['E_net_dissipated']
    
    # Verifica conservazione con trasferimento
    H_conserved_before = budget_before['H_conserved']
    H_conserved_after = budget_after['H_conserved']
    conservation_drift = abs(H_conserved_after - H_conserved_before) / (abs(H_conserved_before) + 1e-30)
    
    print(f"  E_radiated:        {E_radiated:+.3e} J")
    print(f"  E_transferred:     {E_transferred:+.3e} J")
    print(f"  E_net_dissipated:  {E_net_dissipated:+.3e} J")
    print(f"  H_conserved drift: {conservation_drift:.3e}")
    
    # Criteri successo
    has_transfer = E_transferred > 0
    transfer_fraction = E_transferred / E_radiated if E_radiated > 0 else 0
    is_reasonable_fraction = 0.5 < transfer_fraction < 0.9  # 50-90% trasferito
    
    success = has_transfer and is_reasonable_fraction
    
    print(f"\\n  Transfer fraction: {transfer_fraction:.1%} (expected 70%)")
    print(f"  Result: {'PASS' if success else 'FAIL'}")
    
    return success


def test_l3_stability():
    """
    Test 4: VALIDAZIONE FINALE - L3 stabile senza interventi manuali.
    """
    print("\\n" + "="*70)
    print(" TEST 4: L3 Stability (13,824 segments)")
    print("="*70)
    
    # Crea universo L3 con damping universale
    base_physics = PhysicsContext(
        level=0,
        length_scale=1.0,
        gamma_damping_base=0.0005,  # RIDOTTO drasticamente
        damping_scaling_exponent=0.2,  # k=0.2 (scaling molto conservativo)
        thermal_feedback_strength=0.05,  # Feedback termico ridotto a 5%
        mu_fermi=50.0,
        T_fermi=5.0,
        alpha_K=0.005,  # Coupling ULTERIORMENTE ridotto
        kappa_coupling=0.005
    )
    
    config = UniverseConfig(
        target_level=3,
        chi_mean=50.0,
        chi_std=5.0,
        spatial_extent=100.0,
        seed=42
    )
    
    print("\\nGenerating L3 universe (13,824 segments)...")
    t0 = time.time()
    factory = FractalUniverseFactory(base_physics=base_physics)
    universe = factory.create_universe(config)
    t_create = time.time() - t0
    
    print(f"  Created in {t_create:.2f}s")
    print(f"  N_segments: {universe.N_children if hasattr(universe, 'N_children') else '?'}")
    print(f"  Gamma_base(L3): {universe.physics.gamma_damping_base:.6f}")
    
    # Setup simulazione
    sim = SimpleSimulation(universe, dt=0.01)
    monitor = EnergyDriftMonitor(
        warning_threshold=1e-2,  # 1% warning
        critical_threshold=5e-2,  # 5% critical
        emergency_threshold=0.1  # 10% emergency (più permissivo)
    )
    sim.attach(monitor)
    
    print("\\nRunning 10 steps...")
    
    t0 = time.time()
    max_drift = 0.0
    final_drift = 0.0
    
    for step in range(10):
        state = sim.step()
        max_drift = max(max_drift, state.drift)
        final_drift = state.drift
        
        if step % 2 == 0:
            print(f"  Step {step:2d}: drift={state.drift:.4f}, H={state.H_total:.3e}")
    
    t_sim = time.time() - t0
    
    print(f"\\nSimulation completed in {t_sim:.2f}s ({10/t_sim:.2f} steps/s)")
    print(f"  Final drift:  {final_drift:.4f}")
    print(f"  Max drift:    {max_drift:.4f}")
        # Diagnostica dettagliata energia
    budget = universe.get_energy_budget()
    print(f"\n  Energy Budget:")
    print(f"    E_radiated:     {budget['E_radiated']:+.3e}")
    print(f"    E_transferred:  {budget['E_transferred']:+.3e}")
    print(f"    E_net_dissip:   {budget['E_net_dissipated']:+.3e}")
    print(f"    Transfer frac:  {budget['E_transferred']/budget['E_radiated']*100 if budget['E_radiated'] > 0 else 0:.1f}%")
        # Criteri successo: drift < 10% (no emergency stop)
    success = max_drift < 0.1
    
    print(f"\\n  Result: {'PASS' if success else 'FAIL'} (max drift < 10%)")
    
    return success


def run_all_tests() -> int:
    """Esegui tutti i test."""
    logging.basicConfig(level=logging.WARNING)
    
    print("\\n" + "="*70)
    print(" UNIVERSAL SCALING TEST SUITE")
    print("="*70)
    
    tests = [
        ("Damping Scaling Law", test_damping_scaling_law),
        ("Thermal Modulation", test_thermal_modulation),
        ("Energy Transfer", test_energy_transfer),
        ("L3 Stability", test_l3_stability)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\\n  ERROR: {e}")
            results.append((name, False))
    
    # Summary
    print("\\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    
    N_passed = sum(1 for _, r in results if r)
    N_total = len(results)
    
    print(f"\\nTotal: {N_passed}/{N_total} tests passed")
    print("="*70 + "\\n")
    
    return 0 if N_passed == N_total else 1


if __name__ == "__main__":
    import sys
    sys.exit(run_all_tests())
