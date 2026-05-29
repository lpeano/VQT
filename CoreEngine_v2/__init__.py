"""
CoreEngine_v2 — Autonomous Orchestration Engine for the VQT Frattale Hierarchy.

Modules
-------
GlobalState           : Persistent seed cache (one LevelSeed per completed level).
                        Persists to CoreEngine_v2/state/global_state.json.

PhaseTransitionSignal : Active saturation agent wrapping MaturityWatchdog.
                        Emits SaturationSignal objects instead of a plain bool.
                        Decides: advance_level | extend_run | hold.

RecursiveManifoldManager : Autonomous L1→LN orchestrator.
                        Builds and launches generate_topological_dataset.py
                        for each successive level. Writes stdout to cosmo_L{N}.log.

Zero-impact guarantee
---------------------
Does NOT import wqt_oop directly.
Does NOT touch generate_topological_dataset.py, sparse_coupling.py, or any
file used by the running L4 simulation (PID 37732).
Communicates via subprocess CLI + HDF5 files only.

Quick-start (after L4 finishes)
--------------------------------
    from CoreEngine_v2 import RecursiveManifoldManager

    mgr = RecursiveManifoldManager(output_dir="experiments/exp1")
    mgr.register_from_hdf5(level=4, hdf5_path="experiments/exp1/cosmo_L4.h5")
    print(mgr.status_report())
    mgr.run_next_level(4)          # launches L5; log → experiments/exp1/cosmo_L5.log

Wiring PhaseTransitionSignal into the simulation loop (future runs)
---------------------------------------------------------------------
    from CoreEngine_v2 import RecursiveManifoldManager, PhaseTransitionSignal
    from wqt_oop.maturity_watchdog import MaturityWatchdog

    watchdog = MaturityWatchdog(window_size=50, n_dof=n_dof, dt=dt)
    pts = PhaseTransitionSignal(watchdog, level=5, max_steps=600)
    mgr = RecursiveManifoldManager(output_dir="experiments/exp1")

    for step_idx in range(max_steps):
        # ... evolve manifold ...
        sig = pts.feed(topo_state, step_idx)
        if sig.fired:
            mgr.handle_saturation_signal(sig, hdf5_path=output_path)
            if sig.should_advance:
                break
"""

from .global_state import GlobalState, LevelSeed
from .phase_transition_signal import PhaseTransitionSignal, SaturationSignal
from .recursive_manifold_manager import RecursiveManifoldManager

__all__ = [
    "GlobalState",
    "LevelSeed",
    "PhaseTransitionSignal",
    "SaturationSignal",
    "RecursiveManifoldManager",
]

__version__ = "2.0.0"
