"""
RecursiveManifoldManager — Autonomous orchestrator for VQT frattale hierarchy L1→LN.

Responsibilities
----------------
1. Maintain GlobalState (persistent seeds per completed level).
2. When a level completes, register its seed and determine next-level args.
3. Build and optionally launch generate_topological_dataset.py for L+1.
4. Import external results (e.g. L4 finished in a separate process) via
   register_from_hdf5() or register_completed_level().

Zero-impact guarantee
---------------------
- Does NOT import from wqt_oop directly.
- Does NOT modify generate_topological_dataset.py or sparse_coupling.py.
- Communicates with the existing simulation via subprocess CLI + HDF5 only.
- The running L4 process is completely unaffected.
"""

from __future__ import annotations

import logging
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_GENERATOR_SCRIPT = Path(__file__).parent.parent / "generate_topological_dataset.py"


class RecursiveManifoldManager:
    """
    Autonomous orchestrator for the VQT frattale hierarchy L1 → LN.

    Quick-start (import L4 results after it finishes and launch L5):
    ----------------------------------------------------------------
        from CoreEngine_v2 import RecursiveManifoldManager

        mgr = RecursiveManifoldManager(output_dir="experiments/exp1")
        mgr.register_from_hdf5(level=4, hdf5_path="experiments/exp1/cosmo_L4.h5")
        mgr.run_next_level(4)          # launches L5 as subprocess, log → cosmo_L5.log
        print(mgr.status_report())

    Parameters
    ----------
    global_state : GlobalState | None
        Persistent registry. If None, a fresh one is created.
    output_dir : str
        Directory where HDF5 outputs and logs are written.
    generator_script : Path | None
        Absolute path to generate_topological_dataset.py (auto-detected if None).
    default_dt : float
        Default time step for all levels.
    default_inherit_percentile : int
        Percentile threshold for soliton seed inheritance.
    watchdog : bool
        Whether to pass --watchdog to the generator.
    """

    # Per-level step budgets.
    # L3 needs t_max ≥ 12 P (1200 steps) for f_dom certification per REPORT_2026-05-28.
    _STEP_BUDGET: Dict[int, int] = {
        1: 600,
        2: 600,
        3: 1200,
        4: 600,
        5: 600,
    }
    _DEFAULT_STEPS = 600

    def __init__(
        self,
        global_state=None,
        output_dir: str = "experiments/exp1",
        generator_script: Optional[Path] = None,
        default_dt: float = 0.01,
        default_inherit_percentile: int = 75,
        watchdog: bool = True,
    ):
        from .global_state import GlobalState
        self._state = global_state if global_state is not None else GlobalState()
        self._output_dir = Path(output_dir)
        self._generator = Path(generator_script) if generator_script else _GENERATOR_SCRIPT
        self._default_dt = default_dt
        self._default_percentile = default_inherit_percentile
        self._watchdog = watchdog

        logger.info(
            "[RMM] Initialized — output=%s generator=%s",
            self._output_dir, self._generator.name,
        )
        logger.info("[RMM] %s", self._state.summary())

    # ------------------------------------------------------------------
    # Registration — importing external results
    # ------------------------------------------------------------------

    def register_completed_level(
        self,
        level: int,
        hdf5_path: str,
        n_segments: int,
        steps_completed: int,
        sigma_plateau: float = math.nan,
        f_dom: float = math.nan,
        H_emergent: float = math.nan,
        spectral_entropy: float = math.nan,
        chi_mean: float = 50.0,
        chi_std: float = 5.0,
        inherit_percentile: Optional[int] = None,
    ) -> None:
        """
        Manually register a completed simulation level in GlobalState.

        Call this after an external run finishes (e.g. the L4 currently running).
        The registered seed is used to initialise the next level.
        """
        from .global_state import LevelSeed
        seed = LevelSeed(
            level=level,
            hdf5_path=str(Path(hdf5_path).resolve()),
            n_segments=n_segments,
            steps_completed=steps_completed,
            completed_at=time.time(),
            inherit_percentile=inherit_percentile or self._default_percentile,
            sigma_plateau=sigma_plateau,
            f_dom=f_dom,
            H_emergent=H_emergent,
            spectral_entropy=spectral_entropy,
            chi_mean=chi_mean,
            chi_std=chi_std,
        )
        self._state.register_completion(seed)

    def register_from_hdf5(
        self,
        level: int,
        hdf5_path: str,
        **overrides,
    ) -> None:
        """
        Read seed metadata directly from a completed HDF5 file and register it.

        Reads n_segments, chi_mean, chi_std, steps from /metadata attrs.
        Estimates sigma_plateau from /topological_validation/constraint_density_std
        (last 50 samples).

        Extra kwargs override any auto-read value.
        """
        n_segments = 0
        n_frames = 0
        chi_mean = 50.0
        chi_std = 5.0
        sigma_plateau = math.nan

        try:
            import h5py
            import numpy as np

            with h5py.File(hdf5_path, "r") as hf:
                meta = hf.get("metadata")
                if meta is not None:
                    n_segments = int(meta.attrs.get("N_segments", 0))
                    chi_mean = float(meta.attrs.get("chi_mean", 50.0))
                    chi_std = float(meta.attrs.get("chi_std", 5.0))

                frames = hf.get("frames", {})
                n_frames = len(frames)

                tv = hf.get("topological_validation")
                if tv is not None and "constraint_density_std" in tv:
                    arr = tv["constraint_density_std"][()]
                    if len(arr) > 0:
                        sigma_plateau = float(np.mean(arr[-min(50, len(arr)):]))

        except Exception as exc:
            logger.warning("[RMM] Could not read HDF5 metadata from %s: %s", hdf5_path, exc)

        kw = dict(
            n_segments=n_segments,
            steps_completed=n_frames,
            sigma_plateau=sigma_plateau,
            chi_mean=chi_mean,
            chi_std=chi_std,
        )
        kw.update(overrides)
        self.register_completed_level(level=level, hdf5_path=hdf5_path, **kw)

    # ------------------------------------------------------------------
    # Readiness check
    # ------------------------------------------------------------------

    def check_readiness_for_next(self, current_level: int) -> bool:
        """True if current_level is registered and next-level HDF5 does not yet exist."""
        if not self._state.is_level_complete(current_level):
            logger.info("[RMM] L%d not registered — cannot advance.", current_level)
            return False
        next_hdf5 = self._output_dir / f"cosmo_L{current_level + 1}.h5"
        if next_hdf5.exists():
            logger.info("[RMM] L%d already exists at %s — skip.", current_level + 1, next_hdf5)
            return False
        return True

    # ------------------------------------------------------------------
    # Command building
    # ------------------------------------------------------------------

    def build_next_level_command(self, current_level: int) -> List[str]:
        """
        Build the argv for generate_topological_dataset.py to run level+1.

        Returns a list suitable for subprocess.run() or manual inspection/logging.
        Raises KeyError if current_level is not registered in GlobalState.
        """
        next_level = current_level + 1
        inherit_args = self._state.next_level_inherit_args(current_level)
        steps = self._STEP_BUDGET.get(next_level, self._DEFAULT_STEPS)
        output_path = self._output_dir / f"cosmo_L{next_level}.h5"

        cmd = [
            sys.executable,
            str(self._generator),
            "--level",              str(next_level),
            "--steps",              str(steps),
            "--dt",                 str(self._default_dt),
            "--inherit",            inherit_args["inherit"],
            "--inherit-percentile", str(inherit_args["inherit_percentile"]),
            "--output",             str(output_path),
            "--log-interval",       "10",
            "--save-interval",      "1",
            "--gc-interval",        "5",
        ]
        if self._watchdog:
            cmd += ["--watchdog", "--watchdog-window", "50"]

        logger.info("[RMM] Built command for L%d: %s", next_level, " ".join(cmd))
        return cmd

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    def run_next_level(
        self,
        current_level: int,
        blocking: bool = False,
        extra_args: Optional[List[str]] = None,
    ) -> Optional[subprocess.Popen]:
        """
        Launch generate_topological_dataset.py for level current_level+1.

        Output (stdout + stderr) is written to cosmo_L{N}.log in output_dir,
        so the terminal log problem encountered with L4 does not repeat.

        Parameters
        ----------
        blocking : bool
            If True, wait for completion (for scripted pipelines).
            If False, return the Popen object immediately (default).
        extra_args : list[str] | None
            Additional argv appended to the command.

        Returns
        -------
        subprocess.Popen if not blocking, None if blocking.
        """
        if not self.check_readiness_for_next(current_level):
            return None

        cmd = self.build_next_level_command(current_level)
        if extra_args:
            cmd.extend(extra_args)

        next_level = current_level + 1
        log_path = self._output_dir / f"cosmo_L{next_level}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("[RMM] Launching L%d → log: %s", next_level, log_path)

        log_file = open(log_path, "w", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(self._generator.parent),
        )
        logger.info("[RMM] L%d started — PID=%d", next_level, proc.pid)

        if blocking:
            proc.wait()
            log_file.close()
            rc = proc.returncode
            logger.info("[RMM] L%d completed — exit code %d", next_level, rc)
            return None

        return proc

    # ------------------------------------------------------------------
    # PhaseTransitionSignal integration hook
    # ------------------------------------------------------------------

    def handle_saturation_signal(self, signal, hdf5_path: str) -> None:
        """
        Callback to wire PhaseTransitionSignal directly into the manager.

        Usage inside a simulation loop:
        --------------------------------
            pts = PhaseTransitionSignal(watchdog, level=3, max_steps=600)
            # … in the step loop:
            sig = pts.feed(topo_state, step_idx)
            if sig.fired:
                mgr.handle_saturation_signal(sig, hdf5_path="experiments/exp1/cosmo_L3.h5")
        """
        if not signal.fired:
            return

        logger.info("[RMM] SaturationSignal received: %s", signal.message)

        self.register_from_hdf5(
            level=signal.level,
            hdf5_path=hdf5_path,
            sigma_plateau=signal.sigma_plateau,
            f_dom=signal.f_dom,
            spectral_entropy=signal.spectral_entropy,
        )

        if signal.should_advance:
            logger.info("[RMM] Auto-advancing to L%d.", signal.level + 1)
            self.run_next_level(signal.level, blocking=False)
        elif signal.should_extend:
            logger.warning(
                "[RMM] L%d needs extension for f_dom certification. "
                "Increase --steps and re-run.",
                signal.level,
            )

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------

    def status_report(self) -> str:
        lines = [
            "=" * 64,
            "RecursiveManifoldManager — Status Report",
            "=" * 64,
            self._state.summary(),
            "",
        ]
        highest = self._state.highest_completed_level()
        if highest is not None:
            next_l = highest + 1
            ready = self.check_readiness_for_next(highest)
            lines.append(
                f"Next action: L{next_l} — "
                f"{'READY to launch' if ready else 'already exists or blocked'}"
            )
            if ready:
                cmd = self.build_next_level_command(highest)
                lines.append("Command:")
                lines.append("  " + " \\\n    ".join(cmd))
        else:
            lines.append("No completed levels registered yet.")
        lines.append("=" * 64)
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"RecursiveManifoldManager("
            f"levels={self._state.completed_levels()}, "
            f"output={self._output_dir})"
        )
