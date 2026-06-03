"""
================================================================================
RIPRODUCIBILITA' DEL DIFETTO — fase fisica o evento raro? (niente pooling)
================================================================================

Motivazione (2026-06-03): la "particella" della finestra (loc_ratio medio ~57 a
L2) ha mostrato forte VARIANZA seed-a-seed: la diagnostica a 4 seed (chi_mean=68)
ha dato TUTTE le foglie con rho_tors<1e-5 (vuoto freddo, nessun difetto assoluto),
mentre il grafico a 6 seed aveva nodi "caldi" da 1-2 seed soltanto. Il pooling ha
creato una falsa bimodalita'. La SOC e' falsificata.

Domanda decisiva: il difetto e' una FASE TERMODINAMICA (nasce quasi sempre ->
frazione di nucleazione alta) o un EVENTO RARO/stocastico (nasce in pochi seed)?

Protocollo (Gold Standard, NIENTE pooling):
  Per ogni chi_mean nella/intorno alla finestra, per N_seed seed INDIPENDENTI:
    1. make(seed, chi_mean, level) -> pre-evoluzione (registra peak chi_max/stable).
    2. quench T->0 (freeze_and_measure_mass return_frozen).
    3. PER SEED (non aggregato): loc_ratio, M_tot, n_eff, max/median di rho_tors.
    4. Classifica il seed: difetto LOCALIZZATO se loc_ratio > LOC_THR.
  Output per chi_mean:
    - frazione di nucleazione (seed con difetto / totale)
    - distribuzione di loc_ratio e M_tot tra i seed (mediana, IQR, min-max)
    - quanti seed restano "vuoto freddo" (max rho_tors < COLD_THR)

Interpretazione:
  frazione alta (>0.8) + M_tot poco disperso -> FASE FISICA solida.
  frazione bassa (<0.2) o M_tot su ordini di grandezza -> evento raro/fluttuazione.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/test_riproducibilita_difetto.py            # L2, 20 seed
================================================================================
"""

import sys, os
import numpy as np
import warnings, logging

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wqt_oop.energy_metrics import compute_hierarchical_mass, freeze_and_measure_mass
from test_soglia_formazione import make, chi_max
from test_soc_distribuzione import collect_rho_tors

CHI_STABLE = 50.0
LOC_THR = 5.0       # loc_ratio sopra cui il difetto e' "localizzato" (uniforme=1)
COLD_THR = 1e-3     # max rho_tors sotto cui la foglia piu' calda e' "vuoto freddo"
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--chi-means", type=str, default="62,68,74")
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    chi_means = [float(x) for x in args.chi_means.split(",")]
    dt = 0.01
    N = 24 ** args.level

    print("=" * 82)
    print("  RIPRODUCIBILITA' DEL DIFETTO - per-seed, niente pooling (fase vs evento raro)")
    print(f"  L{args.level} (N={N})  |  {len(seeds)} seed/punto  |  "
          f"localizzato se loc_ratio>{LOC_THR:.0f}  |  vuoto freddo se max(rho)<{COLD_THR:g}")
    print("=" * 82)

    summary = []
    for cm in chi_means:
        locs, mtots, neffs, maxrho, peaks = [], [], [], [], []
        for seed in seeds:
            sol = make(seed, chi_mean=cm, level=args.level)
            pk = chi_max(sol) / CHI_STABLE
            for _ in range(args.pre):
                sol.compute_hamiltonian(); sol.evolve(dt)
                pk = max(pk, chi_max(sol) / CHI_STABLE)
            r = freeze_and_measure_mass(sol, max_steps=args.quench_steps, dt=dt,
                                        return_frozen=True)
            h = compute_hierarchical_mass(r["frozen"])
            rho = collect_rho_tors(r["frozen"])
            locs.append(h["localization_ratio"])
            mtots.append(h["M_tot"])
            neffs.append(h["n_eff"])
            maxrho.append(float(np.max(rho)) if rho.size else 0.0)
            peaks.append(pk)

        locs = np.array(locs); mtots = np.array(mtots)
        maxrho = np.array(maxrho); peaks = np.array(peaks)
        n_loc = int(np.sum(locs > LOC_THR))
        n_cold = int(np.sum(maxrho < COLD_THR))
        frac_nucl = n_loc / len(seeds)
        # dispersione di M_tot tra i soli seed "localizzati"
        m_loc = mtots[locs > LOC_THR]
        if m_loc.size:
            decades = np.log10(m_loc.max() + 1e-30) - np.log10(m_loc.min() + 1e-30)
        else:
            decades = np.nan

        summary.append((cm, float(np.mean(peaks)), frac_nucl, n_cold, locs, mtots, decades))

        print(f"\n  [chi_mean={cm:.0f}]  peak medio~{np.mean(peaks):.2f}")
        print(f"    frazione di NUCLEAZIONE (loc>{LOC_THR:.0f}): {n_loc}/{len(seeds)} = {frac_nucl:.2f}")
        print(f"    seed 'vuoto freddo' (max rho<{COLD_THR:g}): {n_cold}/{len(seeds)}")
        print(f"    loc_ratio:  mediana={np.median(locs):.1f}  IQR=[{np.percentile(locs,25):.1f},"
              f"{np.percentile(locs,75):.1f}]  min={locs.min():.1f}  max={locs.max():.1f}")
        print(f"    M_tot:      mediana={np.median(mtots):.2e}  min={mtots.min():.2e}  max={mtots.max():.2e}")
        if np.isfinite(decades):
            print(f"    dispersione M_tot tra i localizzati: {decades:.1f} ordini di grandezza")

    # --- verdetto ---
    print("\n  " + "=" * 78)
    print("  VERDETTO: fase fisica o evento raro?")
    print("  " + "-" * 78)
    for cm, peak, frac, n_cold, locs, mtots, dec in summary:
        if frac > 0.8:
            tag = "FASE FISICA (nucleazione quasi certa)"
        elif frac < 0.2:
            tag = "EVENTO RARO (fluttuazione/seed-dipendente)"
        else:
            tag = "INTERMEDIO (nucleazione parziale)"
        disp = f", M_tot su {dec:.1f} decadi" if np.isfinite(dec) else ""
        print(f"  chi_mean={cm:.0f} (peak~{peak:.2f}): frazione={frac:.2f} -> {tag}{disp}")

    # --- grafico: distribuzione per-seed di loc_ratio (strip) + frazione nucleazione ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    for i, (cm, peak, frac, n_cold, locs, mtots, dec) in enumerate(summary):
        jit = i + 0.08 * np.random.standard_normal(len(locs))
        ax1.scatter(jit, locs, s=30, alpha=0.7, edgecolor="k", linewidth=0.4)
    ax1.axhline(LOC_THR, color="red", ls="--", label=f"soglia localizzazione ({LOC_THR:.0f})")
    ax1.axhline(1.0, color="gray", ls="-", alpha=0.4, label="uniforme (campo)")
    ax1.set_xticks(range(len(summary)))
    ax1.set_xticklabels([f"{s[0]:.0f}\n(peak~{s[1]:.2f})" for s in summary])
    ax1.set_xlabel("chi_mean"); ax1.set_ylabel("loc_ratio per seed")
    ax1.set_title("Distribuzione per-seed (no pooling): quanto e' riproducibile?")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    fracs = [s[2] for s in summary]
    cms = [f"{s[0]:.0f}" for s in summary]
    bars = ax2.bar(cms, fracs, color="#2ca02c", edgecolor="k", alpha=0.8)
    ax2.axhline(0.8, color="green", ls=":", label="fase fisica (>0.8)")
    ax2.axhline(0.2, color="red", ls=":", label="evento raro (<0.2)")
    ax2.set_ylim(0, 1); ax2.set_xlabel("chi_mean"); ax2.set_ylabel("frazione di nucleazione")
    ax2.set_title("Frazione di nucleazione del difetto")
    ax2.legend(fontsize=8); ax2.grid(alpha=0.3, axis="y")

    fig.suptitle(f"Riproducibilita' del difetto: fase fisica vs evento raro [L{args.level}]",
                 fontweight="bold")
    fig.tight_layout()
    out = os.path.join(FIGDIR, f"riproducibilita_difetto_L{args.level}.png")
    fig.savefig(out, dpi=120); plt.close(fig)
    print(f"\n  Grafico salvato: {out}")


if __name__ == "__main__":
    main()
