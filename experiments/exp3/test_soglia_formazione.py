"""
================================================================================
SOGLIA DI FORMAZIONE DEL DIFETTO vs ATTRAVERSAMENTO DI sqrt(2)
================================================================================

Domanda (riconciliazione dei due fenomeni): la soglia temporale oltre la quale
un difetto si forma e si congela (Kibble-Zurek, dal quench test: <40 step nessun
difetto, >=100 step difetto) COINCIDE con l'istante in cui chi_max attraversa
sqrt(2)*chi_stable = 70.7 ?

Se SI: sqrt(2) e' "quando il difetto si forma" e la massa e' "cio' che resta".
I due fenomeni (transizione geometrica e massa) sono lo STESSO evento in due
momenti -> teoria riconciliata.

Protocollo (per ogni seed):
  1. Evolvi fino a 100 step registrando chi_max(t).
  2. Determina cross_step = primo step in cui chi_max attraversa sqrt(2)*chi_stable.
  3. A pre-steps {40,50,...,100}: quench su COPIA -> E_psi_residual (massa).
  4. soglia_massa = primo pre-step con massa > soglia.
  5. Confronta soglia_massa con cross_step (per ogni seed e in media).

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_soglia_formazione.py
================================================================================
"""

import sys, os, copy
import numpy as np
import warnings, logging
from dataclasses import replace as dc_replace

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.energy_metrics import PeanoVQTAnalyzer, freeze_and_measure_mass

SQRT2 = np.sqrt(2)
CHI_STABLE = 50.0
THRESH = SQRT2 * CHI_STABLE  # 70.71
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)


def _make_segs(rng, chi_mean, base0, n=24):
    segs = [SegmentoQuantistico(chi=chi_mean + 8 * rng.standard_normal(),
                                vel=1.0 * rng.standard_normal(), physics=base0)
            for _ in range(n)]
    for s in segs:
        s._fdt_enabled = True
    return segs


def make(seed, chi_mean=65.0, level=1):
    """Costruisce un SolitoneComposito L1 o L2 in regime critico (chi_max>70.7)."""
    rng = np.random.default_rng(seed)
    base0 = dc_replace(PhysicsContext.for_level(0), zero_point_amplitude=0.0)
    p1 = dc_replace(PhysicsContext.for_level(1, base_context=base0),
                    zero_point_amplitude=0.0)
    if level == 1:
        sol = SolitoneComposito(_make_segs(rng, chi_mean, base0), p1,
                                screening_enabled=False)
    elif level == 2:
        p2 = dc_replace(PhysicsContext.for_level(2, base_context=base0),
                        zero_point_amplitude=0.0)
        L1s = [SolitoneComposito(_make_segs(rng, chi_mean, base0), p1,
                                 screening_enabled=False) for _ in range(24)]
        sol = SolitoneComposito(L1s, p2, screening_enabled=False)
    elif level == 3:
        p2 = dc_replace(PhysicsContext.for_level(2, base_context=base0),
                        zero_point_amplitude=0.0)
        p3 = dc_replace(PhysicsContext.for_level(3, base_context=base0),
                        zero_point_amplitude=0.0)
        L2s = []
        for _ in range(24):
            L1s = [SolitoneComposito(_make_segs(rng, chi_mean, base0), p1,
                                     screening_enabled=False) for _ in range(24)]
            L2s.append(SolitoneComposito(L1s, p2, screening_enabled=False))
        sol = SolitoneComposito(L2s, p3, screening_enabled=False)
    elif level == 4:
        p2 = dc_replace(PhysicsContext.for_level(2, base_context=base0),
                        zero_point_amplitude=0.0)
        p3 = dc_replace(PhysicsContext.for_level(3, base_context=base0),
                        zero_point_amplitude=0.0)
        p4 = dc_replace(PhysicsContext.for_level(4, base_context=base0),
                        zero_point_amplitude=0.0)
        L3s = []
        for _ in range(24):
            L2s = []
            for _ in range(24):
                L1s = [SolitoneComposito(_make_segs(rng, chi_mean, base0), p1,
                                         screening_enabled=False) for _ in range(24)]
                L2s.append(SolitoneComposito(L1s, p2, screening_enabled=False))
            L3s.append(SolitoneComposito(L2s, p3, screening_enabled=False))
        sol = SolitoneComposito(L3s, p4, screening_enabled=False)
    else:
        raise ValueError("level deve essere 1, 2, 3 o 4")
    sol._peano_analyzer = PeanoVQTAnalyzer(chi_saturation_threshold=1e12, drain_rate=0.0)
    return sol


def chi_max(sol):
    """chi_max sui SEGMENTI FOGLIA (ricorsivo), non sulle medie dei figli diretti.
    Fix 2026-06-03: a livello root (L2+) _get_child_chi restituisce la MEDIA dei
    figli L1, che non raggiunge mai sqrt(2)*chi_stable. I picchi reali vivono nelle
    foglie. Per L1 e' identico (i figli diretti SONO le foglie)."""
    leaves = []

    def _walk(n):
        if isinstance(n, SegmentoQuantistico):
            leaves.append(abs(n.chi))
        else:
            for c in n.children:
                _walk(c)
    _walk(sol)
    return float(np.max(leaves))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--pre", type=str, default="40,50,60,70,80,90,100")
    ap.add_argument("--quench-steps", type=int, default=1500)
    args = ap.parse_args()

    level = args.level
    pre_points = [int(x) for x in args.pre.split(",")]
    seeds = list(range(1, args.seeds + 1))
    q_steps = args.quench_steps
    dt = 0.01

    print("=" * 72)
    print(f"  SOGLIA DI FORMAZIONE DIFETTO vs ATTRAVERSAMENTO sqrt(2)*chi_stable [L{level}]")
    print(f"  soglia chi: sqrt(2)*{CHI_STABLE:.0f} = {THRESH:.2f}  |  N_seg = {24**level}")
    print("=" * 72)

    soglia_massa, cross_steps = [], []
    mass_grid = np.zeros((len(seeds), len(pre_points)))

    for si, seed in enumerate(seeds):
        sol = make(seed, level=level)
        chimax_traj = [chi_max(sol)]
        cross = None
        snapshots = {}
        for step in range(1, max(pre_points) + 1):
            sol.compute_hamiltonian()
            sol.evolve(dt)
            cm = chi_max(sol)
            chimax_traj.append(cm)
            # attraversamento (in qualsiasi direzione) della soglia
            if cross is None and (chimax_traj[-2] - THRESH) * (cm - THRESH) <= 0:
                cross = step
            if step in pre_points:
                snapshots[step] = copy.deepcopy(sol)
        cross_steps.append(cross if cross is not None else np.nan)

        # quench ad ogni pre-step
        masses = []
        for pj, pre in enumerate(pre_points):
            r = freeze_and_measure_mass(snapshots[pre], max_steps=q_steps, dt=dt)
            masses.append(r["E_psi_residual"])
            mass_grid[si, pj] = r["E_psi_residual"]
        masses = np.array(masses)
        thr_mass = 0.01 * (mass_grid.max() + 1e-30)
        # soglia di formazione = primo pre-step con massa significativa
        sig = np.where(masses > max(thr_mass, 1.0))[0]
        soglia_massa.append(pre_points[sig[0]] if len(sig) else np.nan)

    cross_steps = np.array(cross_steps, dtype=float)
    soglia_massa = np.array(soglia_massa, dtype=float)

    print(f"\n  {'seed':>5} {'cross_sqrt2(step)':>17} {'soglia_massa(step)':>18}")
    print("  " + "-" * 42)
    for seed, c, s in zip(seeds, cross_steps, soglia_massa):
        cs = f"{c:.0f}" if np.isfinite(c) else "mai"
        ss = f"{s:.0f}" if np.isfinite(s) else "no-massa"
        print(f"  {seed:>5} {cs:>17} {ss:>18}")

    valid = np.isfinite(cross_steps) & np.isfinite(soglia_massa)
    print()
    if np.sum(valid) >= 3:
        c = cross_steps[valid]; s = soglia_massa[valid]
        print(f"  cross_sqrt2  medio: {np.mean(c):.1f} +- {np.std(c):.1f} step")
        print(f"  soglia_massa media: {np.mean(s):.1f} +- {np.std(s):.1f} step")
        diff = np.mean(s) - np.mean(c)
        corr = np.corrcoef(c, s)[0, 1] if len(c) > 2 else np.nan
        print(f"  differenza media (soglia - cross): {diff:+.1f} step")
        print(f"  correlazione per-seed cross<->soglia: {corr:.2f}")
        if abs(diff) < 15 and (np.isnan(corr) or corr > 0.4):
            print("  -> COINCIDENZA: la soglia di formazione segue l'attraversamento di sqrt(2).")
            print("     I due fenomeni sono RICONCILIATI (sqrt2 = formazione del difetto).")
        else:
            print("  -> NON coincidono: soglia di formazione e attraversamento sqrt(2) disgiunti.")
    else:
        print("  Dati insufficienti (pochi attraversamenti o nessuna massa).")

    # Grafico
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    mass_mean = np.nanmean(mass_grid, axis=0)
    ax1.plot(pre_points, mass_mean, "o-", color="#2ca02c", label="massa media post-quench")
    if np.sum(valid):
        ax1.axvline(np.nanmean(cross_steps[valid]), color="red", ls="--",
                    label=f"cross sqrt(2) medio ({np.nanmean(cross_steps[valid]):.0f})")
    ax1.set_xlabel("pre-steps (storia dinamica)"); ax1.set_ylabel("E_psi_residual media")
    ax1.set_title("Soglia di formazione della massa"); ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    ax2.scatter(cross_steps[valid], soglia_massa[valid], s=50, c="#1f77b4", edgecolor="k")
    lim = [0, max(pre_points) + 10]
    ax2.plot(lim, lim, "k:", alpha=0.5, label="y=x (coincidenza)")
    ax2.set_xlabel("cross sqrt(2) (step)"); ax2.set_ylabel("soglia massa (step)")
    ax2.set_title("Soglia massa vs attraversamento sqrt(2)"); ax2.legend(fontsize=8); ax2.grid(alpha=0.3)

    fig.suptitle("Riconciliazione: soglia di formazione del difetto vs sqrt(2)",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"soglia_formazione_L{level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
