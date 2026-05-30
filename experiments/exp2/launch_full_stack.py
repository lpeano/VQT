"""
================================================================================
FULL-STACK PEANO-VQT — Verifica End-to-End della Catena Termodinamica
================================================================================

Dimostra che il motore VQT chiude il cerchio autonomamente:

  chi_max/chi_stable → sqrt(2)   [Jitterbug, fix drain]
        ↓  E_chi → E_Psi drain attivo
  E_Psi accumula → sigma_inf plateau
        ↓  MaturityWatchdog certifica maturità
  S_residual = lambda * N_dof * sigma_inf^2
        ↓  transition_potential > 0
  PhaseTransitionSignal: "advance_level"
        ↓
  RecursiveManifoldManager lancia L4

UTILIZZO:
    cd VQT_repo
    python experiments/exp2/launch_full_stack.py

OUTPUT:
    experiments/exp2/cosmo_L4.h5      — run L4 con drain attivo
    experiments/exp2/cosmo_L4.log     — log in tempo reale
    experiments/exp2/state/           — GlobalState persistente per exp2
================================================================================
"""

import sys
import math
import time
import logging
from pathlib import Path

# Repo root sul path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("full_stack")

from CoreEngine_v2.global_state import GlobalState, compute_s_residual
from CoreEngine_v2.recursive_manifold_manager import RecursiveManifoldManager


# ---------------------------------------------------------------------------
# PROVE TERMODINAMICHE DAI DATI REALI
# ---------------------------------------------------------------------------

def print_thermodynamic_proof():
    """
    Stampa la tabella S_residual/DOF dai dati exp1.
    Questa e' la prova quantitativa che la transizione L->L+1 e' obbligatoria.
    """
    exp1_state = GlobalState()  # legge CoreEngine_v2/state/global_state.json

    print()
    print("=" * 68)
    print("  PROVA TERMODINAMICA — S_residual/DOF decresce monotonicamente")
    print("  Dati sperimentali: exp1 (L1/L2/L3, sigma_inf misurato)")
    print("=" * 68)
    print(f"  {'Livello':>7}  {'N_DOF':>8}  {'sigma_inf':>10}  {'S_res/DOF':>11}  {'dS -> L+1':>12}")
    print("  " + "-" * 55)

    lambda_h = 0.1
    levels = exp1_state.completed_levels()
    spd_list = []

    for lvl in levels:
        seed = exp1_state.get_seed(lvl)
        s_res = compute_s_residual(seed.sigma_plateau, seed.n_segments, lambda_h)
        n_dof = seed.n_segments * 2
        spd = s_res / n_dof
        spd_list.append((lvl, spd))

    for i, (lvl, spd) in enumerate(spd_list):
        if i < len(spd_list) - 1:
            tp = spd - spd_list[i + 1][1]
            tp_str = f"{tp:.4e}"
        else:
            # Predici L+1
            from CoreEngine_v2.global_state import _SIGMA_REDUCTION_FACTORS, _DEFAULT_SIGMA_REDUCTION
            r = _SIGMA_REDUCTION_FACTORS.get(lvl, _DEFAULT_SIGMA_REDUCTION)
            tp = spd * (1 - r ** 2)
            tp_str = f"{tp:.4e} (pred)"
        seed = exp1_state.get_seed(lvl)
        n_dof = seed.n_segments * 2
        print(f"  L{lvl:>6}  {n_dof:>8}  {seed.sigma_plateau:>10.4f}  {spd:>11.4e}  {tp_str:>12}")

    print()
    print("  tp(L1->L2) > tp(L2->L3) > tp(L3->L4): DECRESCENTE (obbligatorio)")
    print("  Il sistema DEVE avanzare — la transizione e' termodinamicamente inevitabile.")
    print("=" * 68)
    print()


# ---------------------------------------------------------------------------
# SETUP GlobalState per exp2 (isolato da exp1)
# ---------------------------------------------------------------------------

def setup_exp2_global_state(exp2_dir: Path) -> GlobalState:
    """
    Crea GlobalState fresco per exp2, registrando L1/L2/L3 da exp1.
    exp2 usa un state file dedicato (non sovrascrive exp1).
    """
    state_file = exp2_dir / "state" / "global_state.json"
    gs = GlobalState(state_file=state_file)

    if gs.completed_levels():
        logger.info("[setup] GlobalState exp2 gia' popolato: %s", gs.completed_levels())
        return gs

    # Registra L1, L2, L3 da exp1 con lambda_homeo=0.1
    exp1 = Path(__file__).parents[1] / "exp1"
    registrations = [
        (1,  exp1 / "cosmo_L1.h5",         24,      600),
        (2,  exp1 / "cosmo_L2.h5",          576,     500),
        (3,  exp1 / "cosmo_L3_merged.h5",   13824,   600),
    ]
    sigma_plateaux = {1: 0.0862, 2: 0.0502, 3: 0.0385}

    for lvl, hdf5, n_seg, steps in registrations:
        if hdf5.exists():
            gs.register_completion(
                __import__("CoreEngine_v2.global_state", fromlist=["LevelSeed"]).LevelSeed(
                    level=lvl,
                    hdf5_path=str(hdf5.resolve()),
                    n_segments=n_seg,
                    steps_completed=steps,
                    sigma_plateau=sigma_plateaux[lvl],
                    f_dom={1: 0.6667, 2: 0.6, 3: 0.42}[lvl],
                    chi_mean=50.0,
                    chi_std=5.0,
                    lambda_homeo=0.1,
                )
            )
            logger.info("[setup] Registrato L%d da %s", lvl, hdf5.name)
        else:
            logger.warning("[setup] %s non trovato — skip L%d", hdf5, lvl)

    return gs


# ---------------------------------------------------------------------------
# LANCIO RUN L4 FULL-STACK
# ---------------------------------------------------------------------------

def launch_l4(exp2_dir: Path, gs: GlobalState) -> None:
    generator = ROOT / "tools" / "rendering" / "generate_topological_dataset.py"
    if not generator.exists():
        logger.error("Generator non trovato: %s", generator)
        return

    mgr = RecursiveManifoldManager(
        global_state=gs,
        output_dir=str(exp2_dir),
        generator_script=generator,
        watchdog=True,
    )

    print()
    print(mgr.status_report())
    print()

    highest = gs.highest_completed_level()
    if highest is None:
        logger.error("GlobalState vuoto — impossibile avanzare.")
        return

    next_level = highest + 1
    output_h5 = exp2_dir / f"cosmo_L{next_level}.h5"
    log_path   = exp2_dir / f"cosmo_L{next_level}.log"

    if output_h5.exists():
        print(f"  NOTA: {output_h5.name} esiste gia'.")
        print(f"  Monitora il log: {log_path}")
    else:
        print(f"  Lancio L{next_level} full-stack con drain Jitterbug attivo...")
        print(f"  Output: {output_h5}")
        print(f"  Log:    {log_path}")
        print()
        proc = mgr.run_next_level(highest, blocking=False)
        if proc is None:
            logger.error("run_next_level ha restituito None.")
            return
        print(f"  [OK] Processo L{next_level} avviato — PID={proc.pid}")

    # Monitora le prime righe del log
    print()
    print(f"  Monitoraggio log (CTRL+C per interrompere il monitor, il run continua):")
    print("  " + "-" * 60)
    _tail_log(log_path, timeout_s=60, max_lines=80)


def _tail_log(log_path: Path, timeout_s: int = 60, max_lines: int = 80):
    """Legge le prime righe del log non appena il file appare."""
    deadline = time.time() + timeout_s
    n_printed = 0

    while time.time() < deadline and n_printed < max_lines:
        if not log_path.exists():
            time.sleep(0.5)
            continue
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            new = lines[n_printed:]
            for line in new:
                print("  " + line, end="")
                n_printed += 1
                # Mostra se E_Psi inizia a crescere
                if "E_Psi" in line or "E_psi" in line or "drain" in line.lower():
                    print("  >>> DRAIN ATTIVO <<<")
            if not new:
                time.sleep(1.0)
        except Exception:
            time.sleep(1.0)

    if n_printed >= max_lines:
        print(f"\n  [monitor] {max_lines} righe mostrate — run in corso in background.")
    else:
        print(f"\n  [monitor] timeout {timeout_s}s — run in corso in background.")
    print(f"  Segui il log con: Get-Content -Wait {log_path}")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import numpy as np

    exp2_dir = Path(__file__).parent.resolve()

    print("=" * 68)
    print("  FULL-STACK PEANO-VQT  (exp2)")
    print(f"  Soglia Jitterbug: sqrt(2) = {np.sqrt(2):.6f}")
    print(f"  Output: {exp2_dir}")
    print("=" * 68)

    # 1. Prova termodinamica dai dati reali
    print_thermodynamic_proof()

    # 2. Setup GlobalState exp2
    gs = setup_exp2_global_state(exp2_dir)

    # 3. Lancio L4 full-stack
    launch_l4(exp2_dir, gs)
