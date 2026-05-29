"""
GlobalState — Persistent seed cache for VQT topological levels.

Persists to CoreEngine_v2/state/global_state.json.
One LevelSeed per completed simulation level.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_STATE_FILE = Path(__file__).parent / "state" / "global_state.json"


@dataclass
class LevelSeed:
    """Topological seed produced by a completed simulation level."""

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

    @property
    def n_dof(self) -> int:
        return self.n_segments * 2


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
        logger.info(
            "[GlobalState] L%d registered — %d segments, %d steps, "
            "σ_∞=%.4f, f_dom=%.4f",
            seed.level, seed.n_segments, seed.steps_completed,
            seed.sigma_plateau, seed.f_dom,
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
        tmp.replace(self._path)  # atomic on most OS

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
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
            lines.append(
                f"  L{lvl}: {s.n_segments:>8} DOF | {s.steps_completed:>5} steps | "
                f"σ_∞={s.sigma_plateau:.4f} | f_dom={s.f_dom:.4f} | {Path(s.hdf5_path).name}"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"GlobalState(levels={self.completed_levels()}, path={self._path})"
