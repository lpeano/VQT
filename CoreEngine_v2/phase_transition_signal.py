"""
PhaseTransitionSignal — Active saturation agent wrapping MaturityWatchdog.

Unlike MaturityWatchdog (passive observer → bool), PhaseTransitionSignal is an
active agent that emits structured SaturationSignal objects driving autonomous
level transitions in RecursiveManifoldManager.

Decision logic
--------------
1. Watchdog mature AND f_dom certified (power ≥ threshold) → 'advance_level'
2. Watchdog mature BUT f_dom not certified                 → 'extend_run'
3. max_steps reached (hard cap)                            → 'steps_limit'
   → 'advance_level' if mature, else 'extend_run'
4. None of the above                                       → 'hold'
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SaturationSignal:
    """
    Structured signal emitted when a level reaches topological saturation.

    Attributes
    ----------
    fired : bool
        True when the signal has fired (mature or steps_limit).
    level : int
        Simulation level that emitted this signal.
    step : int
        Step index at evaluation time.
    trigger_reason : str
        'mature' | 'steps_limit' | 'not_ready'
    sigma_plateau : float
        Estimated σ_∞ (mean of recent σ(ρ) window).
    f_dom : float
        Dominant frequency [1/Planck] from spectral analysis.
    spectral_entropy : float
        Spectral entropy H_s.
    dom_power_fraction : float
        Fraction of spectral power in dominant peak [0–1].
    watchdog_metadata : dict
        Full metadata dict from MaturityWatchdog.get_metadata_dict().
    recommended_action : str
        'advance_level' | 'extend_run' | 'hold'
    message : str
        Human-readable decision summary.
    """

    fired: bool
    level: int
    step: int
    trigger_reason: str
    sigma_plateau: float
    f_dom: float
    spectral_entropy: float
    dom_power_fraction: float = 0.0
    watchdog_metadata: dict = field(default_factory=dict)
    recommended_action: str = "hold"
    message: str = ""

    @property
    def should_advance(self) -> bool:
        return self.fired and self.recommended_action == "advance_level"

    @property
    def should_extend(self) -> bool:
        return self.fired and self.recommended_action == "extend_run"

    def __str__(self) -> str:
        return (
            f"SaturationSignal(L{self.level} step={self.step} fired={self.fired} "
            f"action={self.recommended_action} reason={self.trigger_reason})"
        )


class PhaseTransitionSignal:
    """
    Active saturation agent for a single simulation level.

    Wraps a MaturityWatchdog instance without modifying it.
    Exposes check_saturation() → SaturationSignal instead of a plain bool.

    Parameters
    ----------
    watchdog : MaturityWatchdog
        The underlying watchdog (passed by reference, not owned).
    level : int
        Current simulation level.
    max_steps : int
        Hard cap. Fires 'steps_limit' when reached regardless of maturity.
    f_dom_cert_threshold : float
        Minimum dominant power fraction to certify f_dom (default 0.15).
    """

    def __init__(
        self,
        watchdog,
        level: int,
        max_steps: int = 600,
        f_dom_cert_threshold: float = 0.15,
    ):
        self._wd = watchdog
        self.level = level
        self.max_steps = max_steps
        self._cert_threshold = f_dom_cert_threshold
        self._step = 0
        self._last_signal: Optional[SaturationSignal] = None

    # ------------------------------------------------------------------
    # Feed interface — drop-in replacement for watchdog.update() in the loop
    # ------------------------------------------------------------------

    def feed(self, topo_state, step_idx: int) -> SaturationSignal:
        """Forward one step to the watchdog, then evaluate saturation."""
        self._step = step_idx
        self._wd.update(topo_state, step_idx)
        return self.check_saturation()

    # ------------------------------------------------------------------
    # Core method
    # ------------------------------------------------------------------

    def check_saturation(self) -> SaturationSignal:
        """
        Evaluate current saturation state; return a structured SaturationSignal.

        Can be called independently from a monitoring thread without feeding
        a new step — always reflects the watchdog's current internal state.
        """
        wd = self._wd
        meta = wd.get_metadata_dict() if hasattr(wd, "get_metadata_dict") else {}

        sigma_plateau = self._extract_sigma_plateau(wd, meta)
        f_dom = float(meta.get("spectral_dominant_frequency", math.nan))
        spectral_entropy = float(meta.get("spectral_spectral_entropy", math.nan))
        dom_power = float(meta.get("spectral_dominant_power_fraction", 0.0))

        f_dom_certified = (
            wd.is_spectral_done()
            and not math.isnan(f_dom)
            and f_dom > 0.0
            and dom_power >= self._cert_threshold
        )

        # --- Case: hard step limit ---
        if self._step >= self.max_steps - 1:
            action = "advance_level" if wd.is_mature() else "extend_run"
            msg = (
                f"L{self.level} reached max_steps={self.max_steps}. "
                f"mature={wd.is_mature()}, f_dom_cert={f_dom_certified}. → {action}."
            )
            sig = SaturationSignal(
                fired=True, level=self.level, step=self._step,
                trigger_reason="steps_limit",
                sigma_plateau=sigma_plateau, f_dom=f_dom,
                spectral_entropy=spectral_entropy, dom_power_fraction=dom_power,
                watchdog_metadata=meta, recommended_action=action, message=msg,
            )
            logger.info("[PTS] %s", msg)
            self._last_signal = sig
            return sig

        # --- Case: not yet mature ---
        if not wd.is_mature():
            status = wd.get_status_line() if hasattr(wd, "get_status_line") else ""
            return SaturationSignal(
                fired=False, level=self.level, step=self._step,
                trigger_reason="not_ready",
                sigma_plateau=sigma_plateau, f_dom=f_dom,
                spectral_entropy=spectral_entropy, dom_power_fraction=dom_power,
                watchdog_metadata=meta, recommended_action="hold",
                message=f"L{self.level} step={self._step+1} — {status}",
            )

        # --- Case: mature — check f_dom certification ---
        if f_dom_certified:
            action = "advance_level"
            msg = (
                f"L{self.level} SATURATED at step {self._step+1}: "
                f"σ_∞={sigma_plateau:.4f}, f_dom={f_dom:.4f} [1/P] "
                f"({dom_power*100:.1f}% ≥ {self._cert_threshold*100:.0f}%). "
                f"→ ADVANCE to L{self.level+1}."
            )
        else:
            action = "extend_run"
            msg = (
                f"L{self.level} mature (step {self._step+1}) but f_dom not certified "
                f"(power={dom_power*100:.1f}% < {self._cert_threshold*100:.0f}%). "
                f"Recommend extending run."
            )

        sig = SaturationSignal(
            fired=True, level=self.level, step=self._step,
            trigger_reason="mature",
            sigma_plateau=sigma_plateau, f_dom=f_dom,
            spectral_entropy=spectral_entropy, dom_power_fraction=dom_power,
            watchdog_metadata=meta, recommended_action=action, message=msg,
        )
        logger.info("[PTS] %s", msg)
        self._last_signal = sig
        return sig

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_sigma_plateau(wd, meta: dict) -> float:
        if hasattr(wd, "_sigma_window") and wd._sigma_window:
            return float(np.mean(list(wd._sigma_window)))
        return float(meta.get("watchdog_epsilon_norm", math.nan))

    def last_signal(self) -> Optional[SaturationSignal]:
        return self._last_signal

    def maturity_percentage(self) -> float:
        return (
            self._wd.maturity_percentage()
            if hasattr(self._wd, "maturity_percentage")
            else 0.0
        )

    def status_line(self) -> str:
        sig = self._last_signal
        if sig is None:
            return f"L{self.level} — no signal yet (step {self._step})"
        return (
            f"L{self.level} step={self._step} "
            f"maturity={self.maturity_percentage():.1f}% "
            f"action={sig.recommended_action} "
            f"σ={sig.sigma_plateau:.4f} f_dom={sig.f_dom:.4f}"
        )

    def __repr__(self) -> str:
        return (
            f"PhaseTransitionSignal(level={self.level}, "
            f"max_steps={self.max_steps}, step={self._step})"
        )
