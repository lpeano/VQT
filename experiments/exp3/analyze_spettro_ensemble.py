"""
================================================================================
P8 — ANALISI D'ENSEMBLE dello spettro a due canali (ring LOCALE del difetto)
================================================================================

Risolve il limite di P7 (un campo solo): legge TUTTI i campi congelati salvati da
P1 (--save-field) in experiments/exp3/fields/, e per ogni campo:
  1. ricostruisce i blocchi L1 dal flat array: reshape(-1, 24) [ordine DFS -> ogni
     riga = i 24 segmenti di un blocco L1];
  2. trova il blocco L1 che contiene il difetto (foglia piu' deviata dal pozzo) =
     RING LOCALE non diluito;
  3. costruisce psi sul ring: ampiezza m=tanh(chi/chi0), fase phi=tau;
  4. DFT su Z_24 -> canale radiale vs fase, cross-correlazione, spettri.
Poi AGGREGA per livello: media +- sem della cross-correlazione (con t-stat vs 0) e
spettri medi. Solo cosi' si distingue un accoppiamento FISICO (xcorr significativa,
|t|>2) dal RUMORE (xcorr singola ~1.5-2.5 sigma, segno casuale: vedi P7 L2 +0.35 vs
L3 -0.33). Lo spettro di potenza |DFT|^2 e' invariante per traslazione -> NON serve
allineare i core.

ATTENZIONE (gotcha): usa solo np.fft (DFT esatta), MAI l'integratore spettrale
(bug 38%). Analisi diagnostica su campi fermi.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/analyze_spettro_ensemble.py
  python experiments/exp3/analyze_spettro_ensemble.py --chi0 50 --fields-dir ...
================================================================================
"""

import os, sys, glob, re
import numpy as np
from math import gcd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIELDS_DIR = os.path.join(ROOT, "experiments", "exp3", "fields")
FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)
DIVISORS_24 = [1, 2, 3, 4, 6, 8, 12, 24]
CHI_STABLE = 50.0


def local_ring(chi_flat, tau_flat, chi0):
    """Dal flat array (ordine DFS) ricostruisce i blocchi L1 = reshape(-1,24),
    trova il blocco col difetto (foglia piu' deviata dal pozzo dominante) e
    ritorna (m, phi) dei suoi 24 segmenti. None se non ben formato."""
    if chi_flat.size % 24 != 0:
        return None
    blocks_chi = chi_flat.reshape(-1, 24)
    blocks_tau = tau_flat.reshape(-1, 24)
    pozzo = chi0 * (1.0 if np.mean(chi_flat) >= 0 else -1.0)
    dev = np.abs(blocks_chi - pozzo).max(axis=1)     # deviazione max per blocco
    b = int(np.argmax(dev))                          # blocco col difetto piu' forte
    m = np.tanh(blocks_chi[b] / chi0)
    phi = blocks_tau[b].astype(float)
    return m, phi


def two_channel(m, phi):
    """Decomposizione a due canali su un ring di n=len(m). Ritorna dict."""
    n = len(m)
    A = np.fft.fft(m)
    P = np.fft.fft(phi - phi.mean())
    pow_amp = np.abs(A) ** 2
    pow_pha = np.abs(P) ** 2
    E_amp = float(pow_amp[1:].sum())
    E_pha = float(pow_pha[1:].sum())
    a = m - m.mean(); b = phi - phi.mean()
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-30
    xcorr = float(np.dot(a, b) / denom)
    return {"xcorr": xcorr, "E_amp": E_amp, "E_pha": E_pha,
            "pow_amp": pow_amp, "pow_pha": pow_pha, "n": n}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="P8 - ensemble spettro a due canali (ring locale)")
    ap.add_argument("--chi0", type=float, default=CHI_STABLE)
    ap.add_argument("--fields-dir", type=str, default=FIELDS_DIR)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.fields_dir, "campo_L*.npz")))
    print("=" * 72)
    print("  P8 - ENSEMBLE SPETTRO A DUE CANALI (ring locale del difetto)")
    print("=" * 72)
    if not files:
        print(f"  Nessun campo in {args.fields_dir}.")
        print("  Generarli con: test_osservabili_rg.py ... --save-field")
        return

    # raggruppa per livello (dal nome file campo_L{level}_cm{cm}_seed{seed}.npz)
    by_level = {}
    for f in files:
        mobj = re.search(r"campo_L(\d+)_", os.path.basename(f))
        if mobj:
            by_level.setdefault(int(mobj.group(1)), []).append(f)

    print(f"  Campi trovati: {len(files)}  |  livelli: {sorted(by_level)}")
    print(f"\n  {'L':>3} {'n_campi':>8} {'<xcorr>':>9} {'+-sem':>7} {'t=mean/sem':>11} "
          f"{'verdetto':>22}")
    print("  " + "-" * 66)

    results = {}
    for lev in sorted(by_level):
        xs, Eamp, Epha, spec_pha = [], [], [], []
        for f in by_level[lev]:
            d = np.load(f)
            chi = d["chi"].astype(float); tau = d["tau"].astype(float)
            lr = local_ring(chi, tau, args.chi0)
            if lr is None:
                continue
            tc = two_channel(*lr)
            xs.append(tc["xcorr"]); Eamp.append(tc["E_amp"]); Epha.append(tc["E_pha"])
            spec_pha.append(tc["pow_pha"])
        if not xs:
            continue
        xs = np.array(xs)
        mean = float(xs.mean())
        sem = float(xs.std() / np.sqrt(len(xs))) if len(xs) > 1 else float("nan")
        t = mean / sem if (sem and not np.isnan(sem) and sem > 0) else float("nan")
        if len(xs) < 2:
            verdetto = "1 campo: no stat"
        elif abs(t) > 2:
            verdetto = "ACCOPPIATO (|t|>2)"
        else:
            verdetto = "compat. con 0 (rumore)"
        print(f"  {lev:>3} {len(xs):>8} {mean:>9.3f} {sem:>7.3f} {t:>11.2f} {verdetto:>22}")
        results[lev] = {"xs": xs, "spec_pha": np.array(spec_pha),
                        "Eamp": np.array(Eamp), "Epha": np.array(Epha)}

    # --- spettro di fase medio: dove sta la potenza, in media? (per livello) ---
    print("\n  SPETTRO DI FASE MEDIO (potenza per modo, normalizzata):")
    for lev in sorted(results):
        sp = results[lev]["spec_pha"]
        if sp.size == 0:
            continue
        mean_sp = sp.mean(axis=0)
        n = mean_sp.size
        ac = mean_sp[1:].copy()
        ac = ac / (ac.sum() + 1e-30)
        top = np.argsort(ac)[::-1][:4] + 1
        flat = 1.0 / (n - 1)
        ipr = float(np.sum(ac ** 2))
        modi = ", ".join(f"m={m}(per{n//gcd(m,n)})" for m in top)
        print(f"   L{lev}: IPR={ipr:.3f} (piatto={flat:.3f}; "
              f"{'CONCENTRATO' if ipr > 3*flat else 'spalmato'}) | dominanti: {modi}")

    print("\n  NB: |t|>2 -> accoppiamento massa<->fase statisticamente reale.")
    print("      |t|<2 -> compatibile con canali ortogonali (rumore): servono piu' campi.")
    print("      I 'periodi' dei modi dominanti sono divisori di 24 (struttura base).")


if __name__ == "__main__":
    main()
