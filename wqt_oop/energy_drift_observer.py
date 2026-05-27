"""
================================================================================
ENERGY DRIFT OBSERVER - Pattern Observer per Monitoring Real-Time
================================================================================

Implementa Observer pattern per monitoraggio drift energetico durante
simulazioni lunghe.

PATTERN:
- Subject: UniverseSimulation (observable)
- Observers: EnergyMonitor, StatisticsLogger, AlertSystem
- Eventi: step_complete, energy_drift_detected, phase_transition

ALERTS:
- drift > 1e-3: WARNING
- drift > 1e-2: CRITICAL
- drift > 0.1:  EMERGENCY STOP

================================================================================
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import time
from collections import deque

from .abstract_soliton import AbstractSoliton


logger = logging.getLogger(__name__)


@dataclass
class SimulationState:
    """
    Snapshot stato simulazione.
    
    Attributes:
    -----------
    step : int
        Step corrente
    
    time : float
        Tempo fisico [s]
    
    H_total : float
        Energia totale
    
    drift : float
        Drift cumulativo |dH/H|
    
    N_solitons : int
        Numero solitoni attivi
    
    T_eff : float
        Temperatura effettiva media
    
    wall_time : float
        Wall-clock time [s]
    """
    step: int
    time: float
    H_total: float
    drift: float
    N_solitons: int
    T_eff: float
    wall_time: float


class Observer(ABC):
    """
    Interfaccia Observer.
    
    Subclassi implementano update() per rispondere a eventi.
    """
    
    @abstractmethod
    def update(self, state: SimulationState):
        """
        Callback su evento simulazione.
        
        Parameters:
        -----------
        state : SimulationState
            Stato corrente simulazione
        """
        pass
    
    def on_simulation_start(self):
        """Hook: simulazione iniziata."""
        pass
    
    def on_simulation_end(self):
        """Hook: simulazione terminata."""
        pass


class EnergyDriftMonitor(Observer):
    """
    Monitor drift energetico con alert system.
    
    Traccia drift cumulativo e trigger alert se supera soglie.
    """
    
    def __init__(
        self,
        warning_threshold: float = 1e-3,
        critical_threshold: float = 1e-2,
        emergency_threshold: float = 0.1
    ):
        """
        Inizializza monitor.
        
        Parameters:
        -----------
        warning_threshold : float
            Soglia WARNING
        
        critical_threshold : float
            Soglia CRITICAL
        
        emergency_threshold : float
            Soglia EMERGENCY (stop simulazione)
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.emergency_threshold = emergency_threshold
        
        # Storia drift (sliding window)
        self.drift_history = deque(maxlen=100)
        
        # Flags alert
        self.alert_triggered = {
            'WARNING': False,
            'CRITICAL': False,
            'EMERGENCY': False
        }
        
        # Energia iniziale
        self.H_initial = None
    
    def on_simulation_start(self):
        """Reset monitor."""
        self.drift_history.clear()
        self.alert_triggered = {k: False for k in self.alert_triggered}
        self.H_initial = None
        logger.info("EnergyDriftMonitor initialized")
    
    def update(self, state: SimulationState):
        """
        Controlla drift e trigger alert se necessario.
        """
        if self.H_initial is None:
            self.H_initial = state.H_total
        
        # Calcola drift
        drift = abs(state.H_total - self.H_initial) / (abs(self.H_initial) + 1e-30)
        self.drift_history.append(drift)
        
        # Check thresholds
        if drift > self.emergency_threshold and not self.alert_triggered['EMERGENCY']:
            logger.critical(
                f"EMERGENCY: Energy drift {drift:.3e} > {self.emergency_threshold:.3e} "
                f"at step {state.step}"
            )
            self.alert_triggered['EMERGENCY'] = True
            raise RuntimeError(f"EMERGENCY STOP: Excessive energy drift {drift:.3e}")
        
        elif drift > self.critical_threshold and not self.alert_triggered['CRITICAL']:
            logger.error(
                f"CRITICAL: Energy drift {drift:.3e} > {self.critical_threshold:.3e} "
                f"at step {state.step}"
            )
            self.alert_triggered['CRITICAL'] = True
        
        elif drift > self.warning_threshold and not self.alert_triggered['WARNING']:
            logger.warning(
                f"WARNING: Energy drift {drift:.3e} > {self.warning_threshold:.3e} "
                f"at step {state.step}"
            )
            self.alert_triggered['WARNING'] = True
    
    def get_drift_statistics(self) -> dict:
        """Restituisce statistiche drift."""
        if not self.drift_history:
            return {}
        
        return {
            'drift_current': self.drift_history[-1],
            'drift_mean': np.mean(self.drift_history),
            'drift_max': np.max(self.drift_history),
            'drift_std': np.std(self.drift_history)
        }


class StatisticsLogger(Observer):
    """
    Logger statistiche simulazione.
    
    Stampa report periodici su console.
    """
    
    def __init__(self, log_interval: int = 100):
        """
        Inizializza logger.
        
        Parameters:
        -----------
        log_interval : int
            Stampa ogni N steps
        """
        self.log_interval = log_interval
        self.start_time = None
    
    def on_simulation_start(self):
        """Marca inizio simulazione."""
        self.start_time = time.time()
        logger.info("=" * 70)
        logger.info(" SIMULATION STARTED")
        logger.info("=" * 70)
    
    def update(self, state: SimulationState):
        """Stampa report se step % log_interval == 0."""
        if state.step % self.log_interval == 0:
            elapsed = time.time() - self.start_time
            steps_per_sec = state.step / elapsed if elapsed > 0 else 0
            
            logger.info(
                f"Step {state.step:6d} | "
                f"t={state.time:8.2f}s | "
                f"H={state.H_total:.6e} | "
                f"drift={state.drift:.3e} | "
                f"T_eff={state.T_eff:.2e} | "
                f"{steps_per_sec:.1f} steps/s"
            )
    
    def on_simulation_end(self):
        """Stampa summary finale."""
        elapsed = time.time() - self.start_time
        logger.info("=" * 70)
        logger.info(f" SIMULATION COMPLETED (wall time: {elapsed:.2f}s)")
        logger.info("=" * 70)


class ProgressTracker(Observer):
    """
    Tracker progresso con ETA.
    """
    
    def __init__(self, total_steps: int):
        """
        Inizializza tracker.
        
        Parameters:
        -----------
        total_steps : int
            Numero totale steps target
        """
        self.total_steps = total_steps
        self.start_time = None
    
    def on_simulation_start(self):
        """Marca inizio."""
        self.start_time = time.time()
    
    def update(self, state: SimulationState):
        """Calcola ETA."""
        if state.step % 100 == 0 and state.step > 0:
            elapsed = time.time() - self.start_time
            progress = state.step / self.total_steps
            eta = elapsed / progress - elapsed if progress > 0 else 0
            
            logger.info(
                f"Progress: {progress*100:.1f}% | "
                f"ETA: {eta:.1f}s"
            )


# ========================================================================
# OBSERVABLE SUBJECT
# ========================================================================

class Observable:
    """
    Subject nel pattern Observer.
    
    Mantiene lista observers e notifica su eventi.
    """
    
    def __init__(self):
        """Inizializza lista observers."""
        self._observers: List[Observer] = []
    
    def attach(self, observer: Observer):
        """
        Attacca observer.
        
        Parameters:
        -----------
        observer : Observer
            Observer da registrare
        """
        if observer not in self._observers:
            self._observers.append(observer)
            logger.debug(f"Observer attached: {type(observer).__name__}")
    
    def detach(self, observer: Observer):
        """Rimuove observer."""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify(self, state: SimulationState):
        """
        Notifica tutti observers.
        
        Parameters:
        -----------
        state : SimulationState
            Stato corrente
        """
        for observer in self._observers:
            observer.update(state)
    
    def notify_start(self):
        """Notifica inizio simulazione."""
        for observer in self._observers:
            observer.on_simulation_start()
    
    def notify_end(self):
        """Notifica fine simulazione."""
        for observer in self._observers:
            observer.on_simulation_end()


# ========================================================================
# TEST
# ========================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print(" TEST: OBSERVER PATTERN")
    print("="*70 + "\n")
    
    # Crea observable
    subject = Observable()
    
    # Crea observers
    drift_monitor = EnergyDriftMonitor(
        warning_threshold=1e-4,
        critical_threshold=1e-3
    )
    
    stats_logger = StatisticsLogger(log_interval=10)
    progress_tracker = ProgressTracker(total_steps=100)
    
    # Attach observers
    subject.attach(drift_monitor)
    subject.attach(stats_logger)
    subject.attach(progress_tracker)
    
    # Simula evoluzione
    subject.notify_start()
    
    H_initial = 1e6
    dt = 0.1
    
    print("Simulazione con drift graduale...")
    print("-" * 70)
    
    for step in range(100):
        # Simula drift graduale
        drift = step * 1e-5
        H_current = H_initial * (1 + drift)
        
        state = SimulationState(
            step=step,
            time=step * dt,
            H_total=H_current,
            drift=drift,
            N_solitons=24,
            T_eff=5.0,
            wall_time=time.time()
        )
        
        try:
            subject.notify(state)
        except RuntimeError as e:
            print(f"\nEMERGENCY STOP: {e}")
            break
    
    subject.notify_end()
    
    # Print drift statistics
    drift_stats = drift_monitor.get_drift_statistics()
    print("\nDrift Statistics:")
    print(f"  Current: {drift_stats['drift_current']:.3e}")
    print(f"  Mean:    {drift_stats['drift_mean']:.3e}")
    print(f"  Max:     {drift_stats['drift_max']:.3e}")
    
    print("\n" + "="*70)
    print(" OBSERVER TEST COMPLETATO")
    print("="*70 + "\n")
