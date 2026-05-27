"""
================================================================================
TOPOLOGICAL INTEGRATION LAYER - Connessione Validator ↔ Evolve
================================================================================

Layer di integrazione NON-DISTRUTTIVO che connette il nuovo sistema di
validazione topologica al metodo `evolve` esistente.

ARCHITETTURA:
┌──────────────────────────────────────────────────────────┐
│              LEGACY SYSTEM (invariato)                    │
│                                                           │
│   SegmentoQuantistico.evolve()                           │
│     └── Strang Splitting D_{dt/2} ∘ V_dt ∘ D_{dt/2}    │
│   SolitoneComposito.evolve()                             │
│     └── Accoppiamento Leech + screening Fermi-Dirac      │
│                                                           │
└──────────────────────┬───────────────────────────────────┘
                       │  LETTURA PASSIVA (get_auxiliary_state)
                       ▼
┌──────────────────────────────────────────────────────────┐
│              NEW LAYER (addittivo)                        │
│                                                           │
│   TopologicalEvolutionWrapper                            │
│     └── evolve_step(dt)                                  │
│           0. T_{dt/2} kick variazionale [Eq. INT-1]     │
│           1. universe.evolve(dt)   <- legacy intatto      │
│           2. T_{dt/2} kick variazionale [Eq. INT-1]     │
│           3. validator.compute_constraint_state()  <- NUOVO│
│           4. observer.update()     <- log rho_constraint  │
│                                                           │
│   Strang Splitting topologico [Eq. INT-1]:               │
│     U_tot(dt) = T_{dt/2} o U_phys(dt) o T_{dt/2}        │
│                                                           │
│   Risultato: TopologicalState per ogni step              │
│     - constraint_density[i]: rho per rendering clustering │
│     - phase_label: "vacuum" / "transition" / "condensed" │
│     - H_total_emergent: energia catalogata (non vincolo) │
└──────────────────────────────────────────────────────────┘

GARANZIE:
  Zero modifiche ai moduli esistenti
  Proprieta' simplettiche Strang Splitting intatte
  Opt-in: attivato solo se enable_validation=True
  Forza variazionale opt-in via force_config (default None = disabilitata)
  I test legacy continuano a passare invariati

================================================================================
"""

import numpy as np
from typing import Dict, List, Optional
import logging

from .abstract_soliton import AbstractSoliton
from .physics_context import PhysicsContext
from .topological_constraint_validator import (
    TopologicalConstraintValidator,
    TopologicalConstraintObserver,
    TopologicalState,
)
from .energy_drift_observer import SimulationState
from .variational_topological_force import (
    VariationalTopologicalForce,
    TopologicalForceConfig,
)


logger = logging.getLogger(__name__)


# ============================================================================
# WRAPPER NON-INVASIVO
# ============================================================================

class TopologicalEvolutionWrapper:
    """
    Wrapper NON-INVASIVO per evoluzione con validazione topologica.

    Sostituisce il loop di simulazione energetico con uno topologico,
    senza mai modificare l'implementazione di `evolve`.

    Usage
    -----
    >>> wrapper = TopologicalEvolutionWrapper(universe, physics)
    >>> for step in range(N_steps):
    ...     topo_state = wrapper.evolve_step(dt)
    ...     rho_map = topo_state.constraint_density  # per rendering
    ...     print(topo_state.phase_label)
    >>> wrapper.finalize()
    >>> data = wrapper.export_topological_history()  # per HDF5
    """

    def __init__(
        self,
        universe: AbstractSoliton,
        physics: PhysicsContext,
        enable_validation: bool = True,
        enable_legacy_energy_logging: bool = False,
        closure_tolerance_deg: float = 10.0,
        detorsion_tolerance_deg: float = 30.0,
        log_interval: int = 10,
        verbose_interval: int = 100,
        force_config: Optional[TopologicalForceConfig] = None,
    ):
        """
        Parameters
        ----------
        universe : AbstractSoliton
            Universo frattale (SolitoneComposito o SegmentoQuantistico).
        physics : PhysicsContext
            Contesto fisico per parametri di scala.
        enable_validation : bool
            Se False, il wrapper esegue solo `universe.evolve()` (legacy puro).
        enable_legacy_energy_logging : bool
            Se True, salva anche H_total a ogni step (compatibilità).
        closure_tolerance_deg : float
            Tolleranza vincolo chiusura 720° [gradi].
        detorsion_tolerance_deg : float
            Tolleranza vincolo detorsione ±180° [gradi].
        log_interval : int
            Frequenza log compatto (ogni N steps).
        verbose_interval : int
            Frequenza log verboso/summary (ogni N steps).
        force_config : TopologicalForceConfig, optional
            Configurazione forza variazionale [Eq. S-1].
            None (default) = forza disabilitata (legacy puro).
            Se fornita, attiva lo Strang Splitting topologico [Eq. INT-1]:
                U_tot(dt) = T_{dt/2} o U_phys(dt) o T_{dt/2}
        """
        self.universe = universe
        self.physics = physics
        self.enable_validation = enable_validation
        self.enable_legacy_energy_logging = enable_legacy_energy_logging

        self.current_step: int = 0
        self.current_time: float = 0.0

        # Forza variazionale [Eq. S-1, INT-1] — opt-in
        if force_config is not None:
            self.force_calc: Optional[VariationalTopologicalForce] = (
                VariationalTopologicalForce(force_config)
            )
            # Informa il calcolatore del livello frattale per rho_0_eff [Eq. FA-2]
            self.force_calc.set_level(physics.level)
        else:
            self.force_calc = None

        if enable_validation:
            self.validator = TopologicalConstraintValidator(
                universe=universe,
                physics=physics,
                closure_tolerance_deg=closure_tolerance_deg,
                detorsion_tolerance_deg=detorsion_tolerance_deg,
            )
            self.topo_observer = TopologicalConstraintObserver(
                validator=self.validator,
                log_interval=log_interval,
                verbose_interval=verbose_interval,
            )
            self.topo_observer.on_simulation_start()
        else:
            self.validator = None
            self.topo_observer = None

        if enable_legacy_energy_logging:
            self.energy_history: List[Dict] = []

        logger.info(
            f"TopologicalEvolutionWrapper initialized "
            f"(validation={'ON' if enable_validation else 'OFF'}, "
            f"legacy_energy={'ON' if enable_legacy_energy_logging else 'OFF'}, "
            f"variational_force={'ON' if self.force_calc else 'OFF'})"
        )

    # ------------------------------------------------------------------
    # Step evolutivo principale
    # ------------------------------------------------------------------

    def evolve_step(
        self,
        dt: float,
        external_force: Optional[np.ndarray] = None,
    ) -> Optional[TopologicalState]:
        """
        Esegue un singolo step di evoluzione + validazione topologica.

        Workflow
        --------
        0. ``force_calc.apply_symplectic_kick(dt/2)`` — pre-kick T_{dt/2}  [Eq. INT-1]
        1. ``universe.evolve(dt)``       — LEGACY INVARIATO (Strang Splitting)
        1b.``force_calc.apply_symplectic_kick(dt/2)`` — post-kick T_{dt/2} [Eq. INT-1]
        2. ``validator.compute_constraint_state()``  — NUOVO, lettura passiva
        3. ``topo_observer.update()``    — log rho_constraint (non |DeltaH/H|)
        [4. ``energy_history.append()`` — OPZIONALE, deprecato]

        I passi 0 e 1b sono attivi solo se ``force_config`` e' stato fornito
        all'inizializzazione, realizzando lo Strang Splitting topologico O(dt^2):
            U_tot(dt) = T_{dt/2} o U_phys(dt) o T_{dt/2}  [Eq. INT-1]

        Parameters
        ----------
        dt : float
            Passo temporale [unità Planck].
        external_force : ndarray, optional
            Forza esterna (passata trasparentemente a `evolve`).

        Returns
        -------
        TopologicalState or None
            None se ``enable_validation=False``.
        """
        # STEP 0: pre-kick variazionale T_{dt/2}  [Eq. INT-1]
        if self.force_calc is not None:
            self.force_calc.apply_symplectic_kick(self.universe, dt * 0.5)

        # STEP 1: evoluzione fisica legacy (invariata) — U_phys(dt)
        self.universe.evolve(dt, external_force)
        self.current_step += 1
        self.current_time += dt

        # STEP 1b: post-kick variazionale T_{dt/2}  [Eq. INT-1]
        if self.force_calc is not None:
            self.force_calc.apply_symplectic_kick(self.universe, dt * 0.5)

        topo_state: Optional[TopologicalState] = None

        # STEP 2-3: validazione topologica (addittiva)
        if self.enable_validation:
            topo_state = self.validator.compute_constraint_state(
                step=self.current_step,
                time=self.current_time,
            )

            # Notifica observer: log ρ invece di |ΔH/H|
            sim_state = SimulationState(
                step=self.current_step,
                time=self.current_time,
                H_total=topo_state.H_total_emergent,  # energia come variabile emergente
                drift=0.0,                             # non più un vincolo
                N_solitons=topo_state.N_segments,
                T_eff=getattr(self.physics, 'T_fermi', 0.0),
                wall_time=0.0,
            )
            self.topo_observer.update(sim_state)

        # STEP 4: legacy energy logging (opzionale, deprecato)
        if self.enable_legacy_energy_logging:
            self.energy_history.append({
                'step': self.current_step,
                'time': self.current_time,
                'H_total': float(self.universe.energia_totale),
            })

        return topo_state

    # ------------------------------------------------------------------
    # Accesso allo stato topologico corrente
    # ------------------------------------------------------------------

    def get_current_topological_state(self) -> Optional[TopologicalState]:
        """Restituisce l'ultimo stato topologico calcolato."""
        if self.validator and self.validator.state_history:
            return self.validator.state_history[-1]
        return None

    def get_constraint_density_map(self) -> Optional[np.ndarray]:
        """
        Mappa spaziale ρ_constraint (metrica per rendering clustering materia).

        Questa è la metrica che SOSTITUISCE il potenziale energetico
        per visualizzare la distribuzione della materia nel playback.

        Returns
        -------
        ndarray, shape (N,) or None
            Densità vincolo per ogni segmento atomico.
        """
        state = self.get_current_topological_state()
        return state.constraint_density if state is not None else None

    def get_phase_label(self) -> str:
        """Fase topologica corrente ('vacuum'|'transition'|'condensed'|'unknown')."""
        state = self.get_current_topological_state()
        return state.phase_label if state is not None else "unknown"

    def get_dof(self) -> int:
        """DOF corrente = 2 × N_segments."""
        state = self.get_current_topological_state()
        return state.N_dof if state is not None else 0

    # ------------------------------------------------------------------
    # Export e finalizzazione
    # ------------------------------------------------------------------

    def export_variational_force_history(self) -> Dict:
        """
        Esporta la storia della forza variazionale (|F|_RMS e S).

        Returns
        -------
        dict
            {'force_rms': ndarray, 'potential_S': ndarray}
            Vuoto se force_config non era fornito.
        """
        if self.force_calc is not None:
            return self.force_calc.export_history_dict()
        return {}

    def export_topological_history(self) -> Dict:
        """
        Esporta la storia completa della validazione topologica.

        Formato compatibile con HDF5Logger (dizionario di ndarray).
        Usare con ``integrate_topological_validation_to_hdf5`` per
        aggiungere i dati a un file HDF5 esistente.

        Returns
        -------
        dict
            Chiavi: step, time, closure_error_deg, closure_satisfied,
            detorsion_quality, detorsion_satisfied,
            mean_constraint_density, constraint_density_std,
            N_dof, N_segments, H_total_emergent, H_torsion_emergent,
            topology_charge, phase_label, transition_detected.
        """
        if self.topo_observer:
            return self.topo_observer.export_to_dict()
        return {}

    def finalize(self):
        """
        Chiude la simulazione: logga il summary finale.

        Chiamare alla fine del loop di simulazione.
        """
        if self.topo_observer:
            self.topo_observer.on_simulation_end()

    def print_validation_summary(self):
        """Stampa su stdout il riassunto della validazione topologica corrente."""
        state = self.get_current_topological_state()
        if state and self.validator:
            print(self.validator.get_summary(state))
        else:
            print("Topological validation not enabled or no steps executed.")


# ============================================================================
# HELPER HDF5 (addizione non-invasiva)
# ============================================================================

def integrate_topological_validation_to_hdf5(
    hdf5_file_handle,
    topo_data: Dict,
    group_name: str = "topological_validation",
) -> None:
    """
    Aggiunge dati di validazione topologica a un file HDF5 esistente.

    Crea il gruppo ``/<group_name>`` senza modificare la struttura
    legacy del file (frames, metadata, ecc. restano invariati).

    Parameters
    ----------
    hdf5_file_handle : h5py.File
        File HDF5 aperto in modalità write/append.
    topo_data : dict
        Output di ``TopologicalEvolutionWrapper.export_topological_history()``.
    group_name : str
        Nome del gruppo HDF5 da creare.
    """
    if not topo_data:
        logger.warning("integrate_topological_validation_to_hdf5: empty data, skipping")
        return

    # Rimuovi gruppo precedente se esiste
    if group_name in hdf5_file_handle:
        del hdf5_file_handle[group_name]

    grp = hdf5_file_handle.create_group(group_name)

    for key, value in topo_data.items():
        if isinstance(value, np.ndarray):
            grp.create_dataset(key, data=value, compression='gzip')

    # Metadata del gruppo
    grp.attrs['description'] = (
        "Topological constraint validation data. "
        "Constraint density (rho_constraint) replaces energy drift as primary monitor. "
        "Energy is an emergent property catalogued here, not a convergence criterion."
    )
    grp.attrs['paradigm'] = "topological_validation_v1"
    grp.attrs['primary_metric'] = "mean_constraint_density"

    logger.info(f"Topological data saved to HDF5 group '{group_name}'")
