"""
GlobalState — Persistent seed cache for VQT topological levels.

Persists to CoreEngine_v2/state/global_state.json.
One LevelSeed per completed simulation level.

Key addition: S_residual = lambda_homeo * N_dof * sigma_inf^2
This is the irreducible topological frustration energy at the sigma_inf plateau —
the energy locked in sub-grid modes that cannot be minimized at level L.
It is the thermodynamic driving force for the transition to level L+1.
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_STATE_FILE = Path(__file__).parent / "state" / "global_state.json"

# Observed sigma reduction factor between consecutive levels (from exp1 L1->L2->L3).
# r(L) = sigma_inf(L+1) / sigma_inf(L).  Grows toward 1 as L increases.
_SIGMA_REDUCTION_FACTORS = {1: 0.583, 2: 0.778, 3: 0.865}
_DEFAULT_SIGMA_REDUCTION = 0.85  # conservative default for unknown levels


def compute_s_residual(
    sigma_plateau: float,
    n_segments: int,
    lambda_homeo: float,
) -> float:
    """
    Compute the irreducible topological frustration energy at the sigma_inf plateau.

    S_residual(L) = lambda_homeo * N_dof(L) * sigma_inf(L)^2

    This is the homeostatic potential that the current level CANNOT minimize
    further. It is strictly positive (sigma_inf > 0 at any finite L) and
    strictly decreasing across levels (S_residual(L+1) < S_residual(L)),
    making the L -> L+1 transition thermodynamically obligatory.

    Parameters
    ----------
    sigma_plateau : float
        Measured sigma_inf = constraint_density_std at the maturity plateau.
    n_segments : int
        Number of topological segments at level L.
    lambda_homeo : float
        Homeostatic coupling constant from TopologicalForceConfig.
        Default in the codebase: 0.1 (TopologicalForceConfig) or
        0.2 (exp1 runs with --lambda-homeo 0.2).

    Returns
    -------
    float : S_residual in the same energy units as the Hamiltonian.
            Returns nan if any input is nan.
    """
    if math.isnan(sigma_plateau) or math.isnan(lambda_homeo):
        return float("nan")
    n_dof = n_segments * 2
    return lambda_homeo * n_dof * sigma_plateau ** 2


def predict_s_per_dof_next(s_per_dof: float, level: int) -> float:
    """
    Predict S_residual_per_dof(L+1) using the observed sigma reduction law.

    S_per_dof(L) = lambda * sigma_inf(L)^2
    S_per_dof(L+1) = lambda * (r * sigma_inf(L))^2 = r^2 * S_per_dof(L)

    The PER-DOF density is strictly decreasing (r < 1 always).
    This is the correct thermodynamic driving force: S_per_dof(L) > S_per_dof(L+1).

    Note: the TOTAL S_residual grows (×24·r^2 per level) because N_dof grows faster
    than sigma^2 falls. The transition is driven by the density, not the total.

    Parameters
    ----------
    s_per_dof : float
        S_residual / N_dof of the current (completed) level.
    level : int
        Current level L.

    Returns
    -------
    float : predicted S_per_dof(L+1).
    """
    if math.isnan(s_per_dof):
        return float("nan")
    r = _SIGMA_REDUCTION_FACTORS.get(level, _DEFAULT_SIGMA_REDUCTION)
    return s_per_dof * r ** 2


# Keep old name as alias for backward compat
def predict_s_residual_next(s_residual: float, level: int) -> float:
    """
    Predict TOTAL S_residual(L+1).

    S_residual(L+1) = 24 * r^2 * S_residual(L)
    (24x more DOF, each with r^2 less frustration density)
    """
    if math.isnan(s_residual):
        return float("nan")
    r = _SIGMA_REDUCTION_FACTORS.get(level, _DEFAULT_SIGMA_REDUCTION)
    return s_residual * 24 * r ** 2


@dataclass
class LevelSeed:
    """
    Topological seed produced by a completed simulation level.

    Core thermodynamic quantities
    -----------------------------
    sigma_plateau : float
        sigma_inf = constraint_density_std at the maturity plateau.
        Measures residual geometric frustration [dimensionless].

    lambda_homeo : float
        Homeostatic coupling constant used in the simulation.
        Required to compute S_residual.

    S_residual : float
        Irreducible topological frustration energy:
            S_residual = lambda_homeo * N_dof * sigma_inf^2
        This is the energy driving the transition to level L+1.
        Positive, strictly decreasing across levels.
    """

    level: int
    hdf5_path: str
    n_segments: int
    steps_completed: int
    completed_at: float = field(default_factory=time.time)
    inherit_percentile: int = 75
    sigma_plateau: float = float("nan")
    f_dom: float = float("nan")
    H_emergent: float = float("nan")
    spectral_entropy: float = float("nan")
    chi_mean: float = 50.0
    chi_std: float = 5.0
    lambda_homeo: float = 0.1
    S_residual: float = float("nan")

    def __post_init__(self) -> None:
        # Auto-compute S_residual if not provided but inputs are available
        if math.isnan(self.S_residual) and not math.isnan(self.sigma_plateau):
            self.S_residual = compute_s_residual(
                self.sigma_plateau, self.n_segments, self.lambda_homeo
            )

    @property
    def n_dof(self) -> int:
        return self.n_segments * 2

    @property
    def s_residual_per_dof(self) -> float:
        """S_residual / N_dof — the thermodynamic density driving the transition."""
        if math.isnan(self.S_residual) or self.n_dof == 0:
            return float("nan")
        return self.S_residual / self.n_dof

    def transition_potential_to_next(self) -> float:
        """
        Predicted thermodynamic driving force for the L -> L+1 transition.

        Uses the per-DOF action density, which is strictly decreasing:
            dS_per_dof = S_per_dof(L) - S_per_dof_predicted(L+1) > 0

        The TOTAL S_residual grows (×24·r^2), but the DENSITY per DOF shrinks
        (×r^2). The transition is thermodynamically obligatory because the system
        at L+1 has lower energy PER DEGREE OF FREEDOM.

        Returns a positive float when the transition is favorable (always true
        when r < 1, which holds empirically for all observed levels).
        """
        s_per_dof_next = predict_s_per_dof_next(self.s_residual_per_dof, self.level)
        if math.isnan(s_per_dof_next):
            return float("nan")
        return self.s_residual_per_dof - s_per_dof_next


class GlobalState:
    """
    Persistent registry of completed simulation levels and their topological seeds.

    Seeds are the high-contorsion solitons (chi > inherit_percentile threshold)
    that survive from level L and initialise level L+1 via --inherit.

    Thread-safety: single-writer assumed (one active simulation at a time).
    """

    def __init__(self, state_file: Optional[Path] = None):
        self._path = Path(state_file) if state_file else _DEFAULT_STATE_FILE
        self._seeds: Dict[int, LevelSeed] = {}
        self._load()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_completion(self, seed: LevelSeed) -> None:
        """Record that level seed.level has completed and store its seed."""
        self._seeds[seed.level] = seed
        self._save()
        s_str = f"{seed.S_residual:.4e}" if not math.isnan(seed.S_residual) else "nan"
        logger.info(
            "[GlobalState] L%d registered — %d DOF, %d steps, "
            "sigma_inf=%.4f, S_residual=%s, f_dom=%.4f",
            seed.level, seed.n_dof, seed.steps_completed,
            seed.sigma_plateau, s_str, seed.f_dom,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_seed(self, level: int) -> Optional[LevelSeed]:
        return self._seeds.get(level)

    def is_level_complete(self, level: int) -> bool:
        return level in self._seeds

    def completed_levels(self) -> List[int]:
        return sorted(self._seeds.keys())

    def highest_completed_level(self) -> Optional[int]:
        levels = self.completed_levels()
        return max(levels) if levels else None

    # ------------------------------------------------------------------
    # Thermodynamic helpers
    # ------------------------------------------------------------------

    def transition_potential(self, from_level: int, to_level: Optional[int] = None) -> float:
        """
        Thermodynamic driving force for the from_level -> to_level transition.

        Uses per-DOF action density (S/N_dof), which is strictly decreasing.
        If to_level is registered: exact = S_per_dof(from) - S_per_dof(to).
        If to_level is not registered: predicted via sigma reduction law.

        Positive = transition is energetically obligatory.
        """
        seed_from = self._seeds.get(from_level)
        if seed_from is None or math.isnan(seed_from.s_residual_per_dof):
            return float("nan")

        actual_to = to_level if to_level is not None else from_level + 1
        seed_to = self._seeds.get(actual_to)

        if seed_to is not None and not math.isnan(seed_to.s_residual_per_dof):
            return seed_from.s_residual_per_dof - seed_to.s_residual_per_dof
        else:
            return seed_from.transition_potential_to_next()

    def s_residual_series(self) -> Dict[int, float]:
        """Return {level: S_residual} for all registered levels."""
        return {
            lvl: s.S_residual
            for lvl, s in self._seeds.items()
            if not math.isnan(s.S_residual)
        }

    # ------------------------------------------------------------------
    # Integration helpers
    # ------------------------------------------------------------------

    def next_level_inherit_args(self, current_level: int) -> dict:
        """
        Return kwargs to pass to generate_topological_dataset.py for level+1.

        Raises KeyError if current_level not registered.
        """
        seed = self._seeds.get(current_level)
        if seed is None:
            raise KeyError(f"Level {current_level} not registered in GlobalState.")
        return {
            "inherit": seed.hdf5_path,
            "inherit_percentile": seed.inherit_percentile,
            "level": current_level + 1,
            "chi_mean": seed.chi_mean,
            "chi_std": seed.chi_std,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {str(k): asdict(v) for k, v in self._seeds.items()}
        tmp = self._path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self._path)

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                # Backward compat: old seeds lack lambda_homeo / S_residual
                v.setdefault("lambda_homeo", 0.1)
                v.setdefault("S_residual", float("nan"))
                self._seeds[int(k)] = LevelSeed(**v)
            logger.info("[GlobalState] Loaded %d seeds from %s", len(self._seeds), self._path)
        except Exception as exc:
            logger.warning("[GlobalState] Could not load state file: %s", exc)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self) -> str:
        if not self._seeds:
            return "GlobalState: empty (no completed levels)"
        lines = ["GlobalState:"]
        for lvl in sorted(self._seeds):
            s = self._seeds[lvl]
            sr = f"{s.S_residual:.4e}" if not math.isnan(s.S_residual) else "nan"
            tp = s.transition_potential_to_next()
            tp_str = f"{tp:.4e}" if not math.isnan(tp) else "nan"
            lines.append(
                f"  L{lvl}: {s.n_dof:>8} DOF | sigma_inf={s.sigma_plateau:.4f} | "
                f"S_res={sr} | dS->{lvl+1}={tp_str} | f_dom={s.f_dom:.4f}"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"GlobalState(levels={self.completed_levels()}, path={self._path})"
