"""
================================================================================
P9 — TEST: la linewidth di risonanza scala con la rigidita' di L? (FORMALIZЗ. sez.9)
================================================================================

Ipotesi (2026-06-08): i modi-divisore Z_24 sono le PORTANTI; la loro larghezza di
riga (quanto un difetto spalma l'energia sui modi) e' fissata dalla RIGIDITA' locale
del livello = il coupling scale-dipendente alpha_K(L) ~ 1/24^L. Predizione analitica
(healing length GL xi ~ sqrt(alpha_K/beta) ~ 24^(-L/2)):
    concentrazione spettrale  C_L ~ xi_L ~ 24^(-L/2)
    -> rapporto tra livelli consecutivi  C_L / C_(L+1) = sqrt(24) ~ 4.9

Questo tool, dai campi salvati (test_osservabili_rg.py --save-field) in
experiments/exp3/fields/, per ogni campo:
  1. ricostruisce i blocchi L1 (reshape(-1,24), ordine DFS) e prende il RING LOCALE
     del difetto (blocco con la foglia piu' deviata);
  2. misura la CONCENTRAZIONE spettrale C = (IPR-flat)/flat dei canali ampiezza
     (m=tanh(chi/chi0)) e fase (phi=tau);
  3. misura n_eff della torsione sul ring (diagnostica secondaria);
poi AGGREGA per livello e confronta il rapporto C_L/C_(L+1) MISURATO col PREDETTO
sqrt(alpha_K(L)/alpha_K(L+1)) (=sqrt(24) se alpha_K~1/24^L).

ESITO: rapporti ~sqrt(24) -> rigidita' regge (spalmamento FISICO, legge di risonanza
generalizzata = pettine Z_24 + linewidth ~24^(L/2)). Scorrelato -> ipotesi falsificata.

NB: serve fields a >=2 livelli. I campi L3 NON esistono (campagna L3 girata prima di
--save-field): generarne con
  python experiments/exp3/test_osservabili_rg.py --level 3 --seeds 3 --chi-means 66 \
    --workers 3 --save-field
np.fft only (no integratore spettrale).

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/analyze_rigidita_linewidth.py
================================================================================
"""

import os, sys, glob, re
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))
FIELDS_DIR = os.path.join(ROOT, "experiments", "exp3", "fields")
CHI_STABLE = 50.0


def defect_ring_raw(chi_flat, tau_flat, chi0):
    """Ring L1 (24 segmenti) col difetto: ritorna (chi_ring, tau_ring) GREZZI."""
    if chi_flat.size % 24 != 0:
        return None
    bc = chi_flat.reshape(-1, 24); bt = tau_flat.reshape(-1, 24)
    pozzo = chi0 * (1.0 if np.mean(chi_flat) >= 0 else -1.0)
    b = int(np.argmax(np.abs(bc - pozzo).max(axis=1)))
    return bc[b], bt[b]


def spectral_concentration(sig):
    """C = (IPR - flat)/flat dello spettro AC di sig (n campioni). C=0 piatto."""
    n = len(sig)
    P = np.abs(np.fft.fft(sig - sig.mean())) ** 2
    ac = P[1:]
    s = ac.sum()
    if s < 1e-30:
        return 0.0
    frac = ac / s
    ipr = float(np.sum(frac ** 2))
    flat = 1.0 / (n - 1)
    return (ipr - flat) / flat


def torsion_neff(chi_ring, W):
    """n_eff della densita' di torsione sul ring (quante foglie portano la frustrazione)."""
    rho = np.array([np.sum(W[i] * (chi_ring[i] - chi_ring) ** 2) for i in range(len(chi_ring))])
    s = rho.sum()
    if s < 1e-30:
        return float("nan")
    p = rho / s
    return 1.0 / float(np.sum(p ** 2))


def _sem(a):
    a = np.asarray(a, float)
    return float(a.std() / np.sqrt(len(a))) if len(a) > 1 else float("nan")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="P9 - linewidth vs rigidita' di scala")
    ap.add_argument("--chi0", type=float, default=CHI_STABLE)
    args = ap.parse_args()

    from wqt_oop.physics_context import PhysicsContext
    from test_soglia_formazione import make
    # W = matrice di coupling L1 (24x24, identica a ogni livello)
    sol1 = make(1, chi_mean=50, level=1)
    W = sol1.coupling_matrix
    W = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))

    files = sorted(glob.glob(os.path.join(FIELDS_DIR, "campo_L*.npz")))
    print("=" * 74)
    print("  P9 - LINEWIDTH DI RISONANZA vs RIGIDITA' DI SCALA (alpha_K ~ 1/24^L)")
    print("=" * 74)
    if not files:
        print(f"  Nessun campo in {FIELDS_DIR}. Generarli con --save-field.")
        return

    by_level = {}
    for f in files:
        mo = re.search(r"campo_L(\d+)_", os.path.basename(f))
        if mo:
            by_level.setdefault(int(mo.group(1)), []).append(f)

    print(f"  Livelli con campi: {sorted(by_level)} "
          f"({sum(len(v) for v in by_level.values())} campi)\n")
    print(f"  {'L':>3} {'n':>4} {'alpha_K':>10} {'C_amp':>8} {'C_fase':>8} {'n_eff_tors':>11}")
    print("  " + "-" * 52)

    res = {}
    for lev in sorted(by_level):
        aK = PhysicsContext.for_level(lev).alpha_K
        Ca, Cp, Ne = [], [], []
        for f in by_level[lev]:
            d = np.load(f)
            lr = defect_ring_raw(d["chi"].astype(float), d["tau"].astype(float), args.chi0)
            if lr is None:
                continue
            chi_r, tau_r = lr
            Ca.append(spectral_concentration(np.tanh(chi_r / args.chi0)))
            Cp.append(spectral_concentration(tau_r))
            Ne.append(torsion_neff(chi_r, W))
        if not Ca:
            continue
        res[lev] = {"aK": aK, "Ca": np.array(Ca), "Cp": np.array(Cp), "Ne": np.array(Ne)}
        print(f"  {lev:>3} {len(Ca):>4} {aK:>10.3g} "
              f"{np.mean(Ca):>8.3f} {np.mean(Cp):>8.3f} {np.nanmean(Ne):>11.2f}")

    # ---- confronto rapporti misurati vs predetti sqrt(alpha_K(L)/alpha_K(L+1)) ----
    levs = sorted(res)
    if len(levs) >= 2:
        print("\n  CONFRONTO con la legge di rigidita' (C_L/C_(L+1) atteso = "
              "sqrt(alpha_K(L)/alpha_K(L+1))):")
        print(f"  {'L->L+1':>8} {'C_amp ratio':>12} {'C_fase ratio':>13} "
              f"{'PREDETTO':>10}")
        for a, b in zip(levs[:-1], levs[1:]):
            pred = np.sqrt(res[a]["aK"] / res[b]["aK"])
            ra = np.mean(res[a]["Ca"]) / (np.mean(res[b]["Ca"]) + 1e-30)
            rp = np.mean(res[a]["Cp"]) / (np.mean(res[b]["Cp"]) + 1e-30)
            print(f"  {f'{a}->{b}':>8} {ra:>12.2f} {rp:>13.2f} {pred:>10.2f}")
        print("\n  Se i rapporti misurati ~ PREDETTO (sqrt(24)~4.9 per passo singolo) entro")
        print("  le barre -> la rigidita' FISSA la linewidth: legge di risonanza")
        print("  generalizzata = pettine Z_24 + Gamma(L)~24^(L/2). Servono piu' seed/livelli.")
    else:
        print(f"\n  Solo {len(levs)} livello con campi: serve almeno L2+L3 (o +L4) per il")
        print(f"  rapporto. Genera campi L3 con --save-field (vedi header).")


if __name__ == "__main__":
    main()
