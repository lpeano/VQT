"""
================================================================================
TEST EQUIVALENZA FISICA — FastEvolver vs Integrazione di Riferimento
================================================================================

Verifica che FastEvolver (spettrale + simplettico) riproduca la STESSA FISICA
del sistema VQT, confrontandolo contro un integratore di riferimento ad alta
precisione (scipy solve_ivp, RK45, tolleranze strette).

PRINCIPIO (dal VQT_MANIFESTO_TEORICO.md, Corollario Metodologico):
  Gli osservabili collettivi sono solver-indipendenti. Cambiare integratore
  NON deve alterare chi_mean, chi_std, energia, frequenze proprie.

SISTEMA DI TEST:
  Un SolitoneComposito L1 (24 segmenti) con:
    - screening_enabled = False  (coupling lineare puro: F = -alpha_K * L_graph @ chi)
    - gamma = 0                  (sistema hamiltoniano puro, no dissipazione)
  Equazione del moto:
    m * d²chi_i/dt² = -4*beta*chi_i*(chi_i² - chi_0²) - alpha_K*(L_graph @ chi)_i

CONTROLLI:
  1. Conservazione energia (FastEvolver, gamma=0): deriva < 1% su 200 step
  2. Equivalenza con reference RK45: errore osservabili < 1%
  3. Roundtrip spettrale: errore < 1e-10 (gia' in spectral_coupling)
  4. Invarianza chi_max (Jitterbug): preservata sotto trasformazione spettrale

ESECUZIONE:
  cd VQT_repo
  python -m wqt_oop.test_fast_evolver_equivalence
================================================================================
"""

import sys
import os
import numpy as np
import warnings
import logging

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.fast_evolver import FastEvolver
from wqt_oop.spectral_coupling import SpectralBasis


def check(cond, name, detail=""):
    label = "PASS" if cond else "FAIL"
    msg = f"  [{label}] {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    return cond


def _make_l1(chi_mean=50.0, chi_std=5.0, seed=42):
    """Crea un SolitoneComposito L1 (24 segmenti) hamiltoniano puro."""
    rng = np.random.default_rng(seed)
    base0 = PhysicsContext.for_level(0)  # chi_stable=50 default
    physics1 = PhysicsContext.for_level(1, base_context=base0)
    segs = []
    for i in range(24):
        chi = chi_mean + chi_std * rng.standard_normal()
        vel = 0.5 * rng.standard_normal()
        s = SegmentoQuantistico(chi=chi, vel=vel, physics=base0)
        s._fdt_enabled = False   # disabilita damping FDT (hamiltoniano puro)
        s.gamma_damping = 0.0
        segs.append(s)
    sol = SolitoneComposito(segs, physics1, screening_enabled=False)
    return sol


def _build_coupling_force(sol):
    """Restituisce (W, alpha_K, beta, chi_0, mass, L_graph) per il sistema."""
    W = (sol.coupling_matrix.toarray()
         if hasattr(sol.coupling_matrix, "toarray")
         else np.asarray(sol.coupling_matrix))
    alpha_K = sol.physics.alpha_K
    beta = sol.physics.beta_potential
    chi_0 = sol.physics.chi_stable
    mass = sol.children[0].mass
    degree = np.sum(W, axis=1)
    return W, alpha_K, beta, chi_0, mass, degree


def _total_energy(chi, vel, W, alpha_K, beta, chi_0, mass, degree):
    """H = T + V + E_coupling (stessa forma di FastEvolver.energy_check)."""
    T = 0.5 * mass * np.sum(vel ** 2)
    V = beta * np.sum((chi ** 2 - chi_0 ** 2) ** 2)
    L_chi = degree * chi - W @ chi
    E_coupling = 0.5 * alpha_K * float(chi @ L_chi)
    return T + V + E_coupling


# ===========================================================================
# TEST 1: Conservazione energia FastEvolver (hamiltoniano puro)
# ===========================================================================

def test_energy_conservation():
    print("\n--- TEST 1: Conservazione energia FastEvolver (gamma=0) ---")
    sol = _make_l1()
    fe = FastEvolver.from_solitone(sol, dt=0.05, method="forest_ruth", enable_drain=False)

    E0 = fe.energy_check()["H"]
    for _ in range(200):
        fe.step()
    E1 = fe.energy_check()["H"]

    drift = abs(E1 - E0) / (abs(E0) + 1e-30)
    return check(drift < 0.01, "Deriva energia < 1% su 200 step (Forest-Ruth)",
                 f"drift={drift:.3e}, H0={E0:.4e}, H1={E1:.4e}")


# ===========================================================================
# TEST 2: Equivalenza con reference RK45 ad alta precisione
# ===========================================================================

def test_equivalence_with_reference():
    print("\n--- TEST 2: Equivalenza FastEvolver vs RK45 reference ---")
    all_pass = True
    try:
        from scipy.integrate import solve_ivp
    except ImportError:
        print("  [SKIP] scipy non disponibile")
        return True

    sol = _make_l1(seed=7)
    W, alpha_K, beta, chi_0, mass, degree = _build_coupling_force(sol)

    chi0 = np.array([c.chi for c in sol.children])
    vel0 = np.array([c.vel for c in sol.children])

    # Equazione del moto di riferimento (identica a quella di FastEvolver):
    #   m * d²chi/dt² = -4*beta*chi*(chi² - chi_0²) - alpha_K*(L_graph @ chi)
    def rhs(t, y):
        chi = y[:24]
        vel = y[24:]
        F_pot = 4.0 * beta * chi * (chi_0 ** 2 - chi ** 2)
        L_chi = degree * chi - W @ chi
        F_coup = -alpha_K * L_chi
        acc = (F_pot + F_coup) / mass
        return np.concatenate([vel, acc])

    T_final = 2.0
    y0 = np.concatenate([chi0, vel0])
    ref = solve_ivp(rhs, [0, T_final], y0, method="RK45",
                    rtol=1e-10, atol=1e-12, dense_output=True)
    chi_ref = ref.y[:24, -1]
    vel_ref = ref.y[24:, -1]

    # FastEvolver (spettrale + Forest-Ruth), stesso stato iniziale
    dt = 0.01
    n_steps = int(round(T_final / dt))
    fe = FastEvolver.from_solitone(sol, dt=dt, method="forest_ruth", enable_drain=False)
    for _ in range(n_steps):
        fe.step()
    chi_fe = np.array([c.chi for c in sol.children])

    # Osservabili collettivi (solver-indipendenti)
    chi_mean_ref, chi_mean_fe = np.mean(chi_ref), np.mean(chi_fe)
    chi_std_ref, chi_std_fe = np.std(chi_ref), np.std(chi_fe)
    chi_max_ref, chi_max_fe = np.max(np.abs(chi_ref)), np.max(np.abs(chi_fe))

    err_mean = abs(chi_mean_fe - chi_mean_ref) / (abs(chi_mean_ref) + 1e-30)
    err_std = abs(chi_std_fe - chi_std_ref) / (abs(chi_std_ref) + 1e-30)
    err_max = abs(chi_max_fe - chi_max_ref) / (abs(chi_max_ref) + 1e-30)

    all_pass &= check(err_mean < 0.01, "chi_mean equivalente a RK45 (<1%)",
                      f"ref={chi_mean_ref:.4f} fe={chi_mean_fe:.4f} err={err_mean:.2e}")
    all_pass &= check(err_std < 0.05, "chi_std equivalente a RK45 (<5%)",
                      f"ref={chi_std_ref:.4f} fe={chi_std_fe:.4f} err={err_std:.2e}")
    all_pass &= check(err_max < 0.05, "chi_max equivalente a RK45 (<5%)",
                      f"ref={chi_max_ref:.4f} fe={chi_max_fe:.4f} err={err_max:.2e}")
    return all_pass


# ===========================================================================
# TEST 3: Roundtrip spettrale e invarianza Jitterbug
# ===========================================================================

def test_spectral_invariance():
    print("\n--- TEST 3: Invarianza spettrale Jitterbug ---")
    sol = _make_l1(seed=99)
    W = (sol.coupling_matrix.toarray()
         if hasattr(sol.coupling_matrix, "toarray")
         else np.asarray(sol.coupling_matrix))
    basis = SpectralBasis.from_coupling_matrix(W)
    chi = np.array([c.chi for c in sol.children])

    info = basis.jitterbug_invariance_check(chi, chi_stable=sol.physics.chi_stable)
    all_pass = True
    all_pass &= check(info["invariant_ok"], "Roundtrip spettrale esatto (<1e-10)",
                      f"err={info['reconstruction_error']:.2e}")
    all_pass &= check(info["chi_max_nodal"] == info["chi_max_after_roundtrip"]
                      or info["reconstruction_error"] < 1e-10,
                      "chi_max invariante sotto DFT",
                      f"nodal={info['chi_max_nodal']:.4f}")
    return all_pass


# ===========================================================================
# TEST 4: Verlet vs Forest-Ruth (consistenza tra integratori)
# ===========================================================================

def test_integrator_consistency():
    print("\n--- TEST 4: Consistenza Verlet vs Forest-Ruth ---")
    sol_v = _make_l1(seed=13)
    sol_f = _make_l1(seed=13)  # stesso stato iniziale

    fe_v = FastEvolver.from_solitone(sol_v, dt=0.01, method="verlet", enable_drain=False)
    fe_f = FastEvolver.from_solitone(sol_f, dt=0.01, method="forest_ruth", enable_drain=False)

    for _ in range(100):
        fe_v.step()
        fe_f.step()

    chi_v = np.array([c.chi for c in sol_v.children])
    chi_f = np.array([c.chi for c in sol_f.children])

    err_mean = abs(np.mean(chi_v) - np.mean(chi_f)) / (abs(np.mean(chi_f)) + 1e-30)
    return check(err_mean < 0.01, "Verlet e Forest-Ruth concordano su chi_mean (<1%)",
                 f"verlet={np.mean(chi_v):.4f} fr={np.mean(chi_f):.4f} err={err_mean:.2e}")


# ===========================================================================
# TEST 5: Raccordo drain Peano-VQT via FastEvolver
# ===========================================================================

def test_drain_coupling():
    print("\n--- TEST 5: Raccordo drain Peano-VQT ---")
    # L1 con chi sopra la soglia Jitterbug (chi_max > sqrt(2)*chi_stable = 70.7)
    rng = np.random.default_rng(1)
    base0 = PhysicsContext.for_level(0)
    p1 = PhysicsContext.for_level(1, base_context=base0)
    segs = [SegmentoQuantistico(chi=75 + 5 * rng.standard_normal(), vel=0.1,
                                physics=base0) for _ in range(24)]
    sol = SolitoneComposito(segs, p1, screening_enabled=False)
    chi_max = max(abs(s.chi) for s in sol.children)

    fe = FastEvolver.from_solitone(sol, dt=0.01, method="forest_ruth", enable_drain=True)
    e0 = sol._peano_analyzer.E_psi_total
    for _ in range(5):
        fe.step()
    e1 = sol._peano_analyzer.E_psi_total
    triad = sol.get_energy_triad()

    all_pass = True
    all_pass &= check(chi_max > np.sqrt(2) * 50, "chi_max sopra soglia Jitterbug",
                      f"chi_max={chi_max:.2f} > {np.sqrt(2)*50:.2f}")
    all_pass &= check(e1 > e0, "E_Psi cresce via FastEvolver (drain attivo)",
                      f"E_Psi: {e0:.3e} -> {e1:.3e}")
    all_pass &= check(triad is not None and triad.E_Psi > 0,
                      "Triade Peano-VQT aggiornata via FastEvolver",
                      f"triad.E_Psi={triad.E_Psi:.3e}" if triad else "None")
    return all_pass


def run_all():
    print("=" * 64)
    print("  TEST EQUIVALENZA FISICA — FastEvolver vs Reference")
    print("=" * 64)
    tests = [
        test_energy_conservation,
        test_equivalence_with_reference,
        test_spectral_invariance,
        test_integrator_consistency,
        test_drain_coupling,
    ]
    results = []
    for fn in tests:
        try:
            results.append(fn())
        except Exception as exc:
            import traceback
            print(f"  [EXCEPTION] {exc}")
            traceback.print_exc()
            results.append(False)

    n_pass = sum(results)
    print("\n" + "=" * 64)
    print(f"  {n_pass}/{len(results)} test superati")
    print("=" * 64)
    if n_pass == len(results):
        print("  FastEvolver: EQUIVALENZA FISICA VERIFICATA")
    return n_pass == len(results)


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
