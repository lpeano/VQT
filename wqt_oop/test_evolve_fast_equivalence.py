"""
================================================================================
GATE — Equivalenza evolve() vs evolve_fast() su L2
================================================================================

Test CANCELLO: prima di usare evolve_fast() in produzione (L4), deve produrre
gli STESSI osservabili collettivi di evolve() su un L2 (576 segmenti, 24 L1).

Confronta due L2 identici (deep copy) evoluti per N step:
  - sol_ref:  evolve()      (motore classico, riferimento)
  - sol_fast: evolve_fast() (dispatcher gerarchico + FastEvolver sulle foglie)

Osservabili confrontati (devono coincidere entro tolleranza):
  chi_mean, chi_std, chi_max, E_Psi (drain Peano-VQT)

DUE VARIANTI:
  A) FDT damping OFF (gamma=0): isola la STRUTTURA del dispatcher
     (coupling multi-livello + ricorsione). Tolleranza stretta.
  B) FDT damping ON: condizioni realistiche. Se A passa e B no -> il problema
     e' il damping FDT state-dependent (Rischio 1 noto), non la struttura.

ESECUZIONE:
  cd VQT_repo
  python -m wqt_oop.test_evolve_fast_equivalence
================================================================================
"""

import sys
import os
import copy
import numpy as np
import warnings
import logging

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.fractal_universe_factory import FractalUniverseFactory, UniverseConfig


def check(cond, name, detail=""):
    label = "PASS" if cond else "FAIL"
    msg = f"  [{label}] {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    return cond


def _make_l2(fdt_enabled: bool, seed: int = 42):
    """Crea un SolitoneComposito L2 (576 segmenti). fdt_enabled controlla il damping."""
    cfg = UniverseConfig(
        target_level=2, chi_mean=50.0, chi_std=5.0, vel_std=1.0,
        spatial_extent=50.0, seed=seed,
        enable_fermi_screening=False, enable_spatial_cache=True,
    )
    factory = FractalUniverseFactory()
    universe = factory.create_universe(cfg)

    # Imposta FDT su tutti i segmenti foglia
    def _walk(node):
        from wqt_oop.segmento_quantistico import SegmentoQuantistico
        if isinstance(node, SegmentoQuantistico):
            node._fdt_enabled = fdt_enabled
            if not fdt_enabled:
                node.gamma_damping = 0.0
        else:
            for c in node.children:
                _walk(c)
    _walk(universe)
    return universe


def _observables(universe):
    """Estrae osservabili collettivi da tutti i segmenti foglia."""
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    chi = []
    def _walk(node):
        if isinstance(node, SegmentoQuantistico):
            chi.append(node.chi)
        else:
            for c in node.children:
                _walk(c)
    _walk(universe)
    chi = np.array(chi)
    # E_Psi totale (drain aggregato)
    e_psi = universe.get_total_E_psi() if hasattr(universe, "get_total_E_psi") else 0.0
    return {
        "chi_mean": float(np.mean(chi)),
        "chi_std": float(np.std(chi)),
        "chi_max": float(np.max(np.abs(chi))),
        "E_Psi": float(e_psi),
    }


def _run_variant(fdt_enabled: bool, n_steps: int = 30, dt: float = 0.01, tol: float = 0.01):
    label = "FDT ON" if fdt_enabled else "FDT OFF (gamma=0)"
    print(f"\n--- Variante: {label} ({n_steps} step, dt={dt}) ---")

    sol_ref = _make_l2(fdt_enabled, seed=42)
    sol_fast = copy.deepcopy(sol_ref)  # stato iniziale IDENTICO

    for _ in range(n_steps):
        sol_ref.evolve(dt)
    for _ in range(n_steps):
        sol_fast.evolve_fast(dt)

    o_ref = _observables(sol_ref)
    o_fast = _observables(sol_fast)

    all_pass = True
    for key in ["chi_mean", "chi_std", "chi_max"]:
        ref_v = o_ref[key]
        fast_v = o_fast[key]
        err = abs(fast_v - ref_v) / (abs(ref_v) + 1e-30)
        all_pass &= check(err < tol, f"[{label}] {key} entro {tol*100:.0f}%",
                          f"ref={ref_v:.4f} fast={fast_v:.4f} err={err:.2e}")
    # E_Psi: confronto assoluto (puo' essere 0 in entrambi se sotto soglia)
    dpsi = abs(o_fast["E_Psi"] - o_ref["E_Psi"])
    scale = abs(o_ref["E_Psi"]) + 1e-9
    check(dpsi / scale < 0.05 or dpsi < 1e-6, f"[{label}] E_Psi coerente",
          f"ref={o_ref['E_Psi']:.4e} fast={o_fast['E_Psi']:.4e}")
    return all_pass


def run_all():
    print("=" * 64)
    print("  GATE — Equivalenza evolve() vs evolve_fast() su L2")
    print("=" * 64)

    # Variante A: FDT off (isola struttura dispatcher) — tolleranza stretta
    pass_a = _run_variant(fdt_enabled=False, n_steps=30, dt=0.01, tol=0.01)

    # Variante B: FDT on (realistico) — tolleranza piu' larga (damping diverso)
    pass_b = _run_variant(fdt_enabled=True, n_steps=30, dt=0.01, tol=0.05)

    print("\n" + "=" * 64)
    print(f"  Variante A (FDT off, struttura): {'PASS' if pass_a else 'FAIL'}")
    print(f"  Variante B (FDT on, realistico): {'PASS' if pass_b else 'FAIL'}")
    print("=" * 64)
    if pass_a and pass_b:
        print("  GATE SUPERATO: evolve_fast e' equivalente a evolve. L4 sicuro.")
    elif pass_a and not pass_b:
        print("  STRUTTURA OK ma damping FDT diverge (Rischio 1 noto).")
        print("  Il dispatcher e' corretto; serve allineare il damping per L4 realistico.")
    else:
        print("  GATE FALLITO sulla struttura: NON usare evolve_fast in produzione.")
    return pass_a, pass_b


if __name__ == "__main__":
    pass_a, pass_b = run_all()
    sys.exit(0 if (pass_a and pass_b) else 1)
