"""
================================================================================
TEST DI FALSIFICABILITA' — Il drain Peano-VQT e' fisica o trucco matematico?
================================================================================

TASK 0 (precede L3). Tre test per stabilire se il drain e' un processo fisico
emergente o un artefatto della costruzione. Vedi MIGRAZIONE_CHECKPOINT.md.

TEST A — Emergenza di sqrt(2) sui dati storici (ZERO calcolo)
  Nei file generati SENZA drain efficace, chi_max/chi_stable converge a sqrt(2)
  al picco, indipendentemente dalle condizioni iniziali? Se si' -> la soglia e'
  emergente (geometria reale), non imposta a mano.

TEST B — Robustezza al drain_rate (parametro libero)
  Variando drain_rate in [0.01..0.5] su un L1 in regime critico (chi_max>70.7):
  il PLATEAU di E_Psi e' indipendente dal rate? Se si' -> il rate e' solo
  cinetica (come la velocita' di raffreddamento), la transizione e' fisica.

TEST C — Riconfigurazione drain OFF (regime critico, stabilizzatori isolati)
  Con chi_max>70.7 e FDT/zero-point DISATTIVATI (per isolare il drain):
  drain ON vs OFF. Se OFF -> divergenza (E_RX/chi esplodono), il drain e' un
  meccanismo di scarico FISICO necessario. Se OFF resta stabile -> patch.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_falsificabilita.py
================================================================================
"""

import sys
import os
import numpy as np
import warnings
import logging
from dataclasses import replace as dc_replace

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.energy_metrics import PeanoVQTAnalyzer, load_h5_and_validate

SQRT2 = np.sqrt(2)
CHI_STABLE = 50.0


# ===========================================================================
# Costruzione di un L1 in regime CRITICO (chi_max > sqrt(2)*chi_stable = 70.7)
# con stabilizzatori controllabili
# ===========================================================================

def make_l1_critical(chi_mean, chi_std, seed, fdt=False, zero_point=False,
                     drain_threshold=SQRT2, drain_rate=0.1):
    rng = np.random.default_rng(seed)
    base0 = PhysicsContext.for_level(0)
    if not zero_point:
        base0 = dc_replace(base0, zero_point_amplitude=0.0)
    physics1 = PhysicsContext.for_level(1, base_context=base0)
    if not zero_point:
        physics1 = dc_replace(physics1, zero_point_amplitude=0.0)

    segs = []
    for i in range(24):
        chi = chi_mean + chi_std * rng.standard_normal()
        vel = 0.3 * rng.standard_normal()
        s = SegmentoQuantistico(chi=chi, vel=vel, physics=base0)
        s._fdt_enabled = fdt
        if not fdt:
            s.gamma_damping = 0.0
        segs.append(s)
    sol = SolitoneComposito(segs, physics1, screening_enabled=False)
    # Imposta soglia e rate del drain
    sol._peano_analyzer = PeanoVQTAnalyzer(
        chi_saturation_threshold=drain_threshold, drain_rate=drain_rate
    )
    return sol


def _chi_array(sol):
    return np.array([c.chi for c in sol.children])


# ===========================================================================
# TEST A — Emergenza sqrt(2) sui dati storici
# ===========================================================================

def test_A_emergenza():
    print("\n" + "=" * 70)
    print("  TEST A — Emergenza di sqrt(2) sui dati storici (zero calcolo)")
    print("=" * 70)
    files = {
        "L2_topo":  os.path.join(ROOT, "data", "cosmo_L2_topo.h5"),
        "L2_var":   os.path.join(ROOT, "data", "cosmo_L2_variational.h5"),
        "L3_full":  os.path.join(ROOT, "data", "cosmo_L3_full.h5"),
        "L3":       os.path.join(ROOT, "experiments", "exp1", "cosmo_L3.h5"),
        "L3_ext":   os.path.join(ROOT, "experiments", "exp1", "cosmo_L3_ext.h5"),
        "L3_ext2":  os.path.join(ROOT, "experiments", "exp1", "cosmo_L3_ext2.h5"),
        "L3_ext3":  os.path.join(ROOT, "experiments", "exp1", "cosmo_L3_ext3.h5"),
        "L4":       os.path.join(ROOT, "experiments", "exp1", "cosmo_L4.h5"),
    }
    print(f"  Ipotesi: chi_max_peak / chi_stable -> sqrt(2) = {SQRT2:.4f}")
    print(f"  {'File':10} {'ratio':>8} {'dev%':>8} {'~sqrt2?':>8}")
    print("  " + "-" * 40)
    ratios = []
    for name, fp in files.items():
        if not os.path.exists(fp):
            continue
        try:
            r = load_h5_and_validate(fp, chi_stable=CHI_STABLE, verbose=False)
            ratio = r.get("jitterbug_ratio", 0.0)
            if ratio <= 0:
                continue
            dev = (ratio - SQRT2) / SQRT2 * 100
            ok = "SI" if abs(dev) < 10 else "no"
            ratios.append(ratio)
            print(f"  {name:10} {ratio:>8.4f} {dev:>+7.1f}% {ok:>8}")
        except Exception as e:
            print(f"  {name:10} ERR {e}")
    if ratios:
        ratios = np.array(ratios)
        print(f"\n  Media ratio = {np.mean(ratios):.4f} (sqrt2={SQRT2:.4f}), "
              f"std = {np.std(ratios):.4f}")
        frac_ok = np.mean(np.abs(ratios - SQRT2) / SQRT2 < 0.10)
        verdetto = "EMERGENTE (a favore fisica)" if frac_ok >= 0.6 else "NON robusto"
        print(f"  File entro 10% da sqrt2: {frac_ok*100:.0f}%  ->  {verdetto}")
        return frac_ok >= 0.6
    print("  Nessun file storico analizzabile.")
    return None


# ===========================================================================
# TEST B — Robustezza al drain_rate
# ===========================================================================

def test_B_robustezza_rate():
    print("\n" + "=" * 70)
    print("  TEST B — Robustezza al drain_rate (regime critico chi_max>70.7)")
    print("=" * 70)
    rates = [0.01, 0.05, 0.1, 0.3, 0.5]
    n_steps = 80
    dt = 0.01
    print(f"  {'drain_rate':>11} {'chi_max_0':>10} {'E_Psi_plateau':>14} {'fase_finale':>14}")
    print("  " + "-" * 54)
    plateaus = []
    for rate in rates:
        sol = make_l1_critical(chi_mean=62.0, chi_std=6.0, seed=42,
                               fdt=False, zero_point=False, drain_rate=rate)
        chi_max_0 = float(np.max(np.abs(_chi_array(sol))))
        for _ in range(n_steps):
            sol.compute_hamiltonian()  # triggera drain (guard per-step)
            # avanza dinamica con evolve classico (FDT off, gamma 0)
            sol.evolve(dt)
        e_psi = sol.get_total_E_psi()
        triad = sol.get_energy_triad()
        ratio_fin = float(np.max(np.abs(_chi_array(sol)))) / CHI_STABLE
        fase = ("Icosaedr" if ratio_fin >= SQRT2 else
                "Cubottae" if ratio_fin >= 1.0 else "Ottaedr")
        plateaus.append(e_psi)
        print(f"  {rate:>11.2f} {chi_max_0:>10.2f} {e_psi:>14.4e} {fase:>14}")
    plateaus = np.array(plateaus)
    # Il plateau dipende dal rate?
    if np.max(plateaus) > 0:
        cv = np.std(plateaus) / (np.mean(plateaus) + 1e-30)
        print(f"\n  Coeff. variazione plateau E_Psi sul rate: {cv:.3f}")
        print(f"  (basso = plateau indipendente dal rate = fisico; "
              f"alto = dipende dal rate = sospetto)")
        return cv
    print("  E_Psi=0 per tutti i rate: drain non scattato (chi sotto soglia?).")
    return None


# ===========================================================================
# TEST C — Riconfigurazione drain OFF (stabilizzatori isolati)
# ===========================================================================

def test_C_drain_off():
    print("\n" + "=" * 70)
    print("  TEST C — Drain OFF vs ON (regime critico, FDT+zero-point OFF)")
    print("=" * 70)
    n_steps = 120
    dt = 0.01

    def run(drain_on):
        thr = SQRT2 if drain_on else 1e12  # 1e12 = drain mai attivo
        sol = make_l1_critical(chi_mean=62.0, chi_std=6.0, seed=7,
                               fdt=False, zero_point=False,
                               drain_threshold=thr, drain_rate=0.1)
        hist_chimax, hist_eRX, hist_H = [], [], []
        for _ in range(n_steps):
            sol.compute_hamiltonian()
            sol.evolve(dt)
            chi = np.abs(_chi_array(sol))
            hist_chimax.append(float(np.max(chi)))
            tr = sol.get_energy_triad()
            hist_eRX.append(abs(tr.E_RX) if tr else np.nan)
            hist_H.append(sol.compute_hamiltonian())
        return (np.array(hist_chimax), np.array(hist_eRX),
                np.array(hist_H), sol.get_total_E_psi())

    cmax_on, eRX_on, H_on, epsi_on = run(True)
    cmax_off, eRX_off, H_off, epsi_off = run(False)

    print(f"  {'metrica':>16} {'drain ON':>14} {'drain OFF':>14}")
    print("  " + "-" * 46)
    print(f"  {'chi_max iniz.':>16} {cmax_on[0]:>14.2f} {cmax_off[0]:>14.2f}")
    print(f"  {'chi_max finale':>16} {cmax_on[-1]:>14.2f} {cmax_off[-1]:>14.2f}")
    print(f"  {'chi_max MAX':>16} {np.max(cmax_on):>14.2f} {np.max(cmax_off):>14.2f}")
    print(f"  {'E_RX finale':>16} {eRX_on[-1]:>14.4e} {eRX_off[-1]:>14.4e}")
    print(f"  {'E_RX MAX':>16} {np.max(eRX_on):>14.4e} {np.max(eRX_off):>14.4e}")
    print(f"  {'E_Psi totale':>16} {epsi_on:>14.4e} {epsi_off:>14.4e}")

    # Criterio: senza drain, chi_max o E_RX divergono rispetto a ON?
    div_chi = np.max(cmax_off) / (np.max(cmax_on) + 1e-30)
    div_eRX = np.max(eRX_off) / (np.max(eRX_on) + 1e-30)
    finite_off = np.all(np.isfinite(cmax_off)) and np.all(np.isfinite(eRX_off))
    print(f"\n  Rapporto divergenza (OFF/ON): chi_max={div_chi:.2f}  E_RX={div_eRX:.2f}")
    print(f"  Stato OFF finito (no overflow): {finite_off}")
    if div_chi > 1.5 or div_eRX > 1.5 or not finite_off:
        print("  -> Senza drain il sistema DIVERGE: drain = scarico FISICO necessario.")
        return "fisico"
    else:
        print("  -> Senza drain il sistema resta STABILE: drain non necessario alla")
        print("     stabilita' (patch o bookkeeping, non meccanismo di scarico).")
        return "patch"


def test_B2_geometrica():
    """Re-Test B con E_Psi GEOMETRICA (istantanea, no drain_rate).
    Confronta la dipendenza da dt/rate dell'accumulo vs della formula geometrica."""
    print("\n" + "=" * 70)
    print("  TEST B2 — E_Psi geometrica vs accumulo (indipendenza da dt/rate)")
    print("=" * 70)
    from wqt_oop.energy_metrics import compute_geometric_E_psi
    print(f"  {'dt':>6} {'rate':>6} {'E_Psi_accum':>13} {'E_Psi_geom':>12}")
    print("  " + "-" * 42)
    accum, geom = [], []
    for dt, rate in [(0.005, 0.1), (0.01, 0.1), (0.02, 0.1),
                     (0.01, 0.01), (0.01, 0.3), (0.01, 0.5)]:
        sol = make_l1_critical(chi_mean=62.0, chi_std=6.0, seed=42,
                               fdt=False, zero_point=False, drain_rate=rate)
        nst = int(round(0.8 / dt))
        for _ in range(nst):
            sol.compute_hamiltonian()
            sol.evolve(dt)
        a_v = sol.get_total_E_psi()
        g_v = compute_geometric_E_psi(sol)["E_psi_geom"]
        accum.append(a_v); geom.append(g_v)
        print(f"  {dt:>6.3f} {rate:>6.2f} {a_v:>13.4e} {g_v:>12.4e}")
    accum, geom = np.array(accum), np.array(geom)
    cv_a = np.std(accum) / (np.mean(accum) + 1e-30)
    cv_g = np.std(geom) / (np.mean(geom) + 1e-30)
    print(f"\n  CV accumulo (drain): {cv_a:.3f}  (alto = artefatto)")
    print(f"  CV geometrica:       {cv_g:.3f}  (basso = fisico)")
    verdetto = cv_g < cv_a / 2
    print(f"  -> E_Psi geometrica {'RIMUOVE' if verdetto else 'NON rimuove'} "
          f"la dipendenza dal rate.")
    return cv_a, cv_g


def main():
    print("#" * 70)
    print("#  FALSIFICABILITA' DEL DRAIN PEANO-VQT — fisica o trucco?")
    print("#" * 70)
    a = test_A_emergenza()
    b = test_B_robustezza_rate()
    c = test_C_drain_off()
    b2 = test_B2_geometrica()

    print("\n" + "#" * 70)
    print("#  SINTESI")
    print("#" * 70)
    print(f"  TEST A (emergenza sqrt2):     {'a favore' if a else 'NON robusto/nd'}")
    print(f"  TEST B (CV plateau vs rate):  {b if b is not None else 'nd'}"
          + ("  (basso=fisico)" if b is not None else ""))
    print(f"  TEST C (drain OFF):           {c}")
    print(f"  TEST B2 (geom vs accumulo):   CV_accum={b2[0]:.2f} CV_geom={b2[1]:.2f}"
          + ("  -> geometrica fisica" if b2[1] < b2[0]/2 else ""))
    print("#" * 70)


if __name__ == "__main__":
    main()
