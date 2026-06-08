"""
================================================================================
P10 — CLUSTERING DELLA MATERIA: rete cosmica o distribuzione uniforme?
================================================================================

Ipotesi (utente 2026-06-08): i difetti (kink) NON sono distribuiti in modo omogeneo,
ma tendono ad aggregarsi/incapsularsi in modo gerarchico — zone di addensamento e
vuoti, "come la natura fa" (rete cosmica). Connette Ramo B (kink/massa) e Ramo A
(struttura cosmica).

TEST: dai campi salvati (test_osservabili_rg.py --save-field), trova i difetti
(|chi-pozzo|>0.6*chi0) e ne misura la DISTRIBUZIONE SPAZIALE sulla gerarchia. Il flat
array e' in ordine DFS -> reshape(-1, 24^k) raggruppa i blocchi di livello k. Per ogni
scala k si conta i difetti per blocco e si misura:
  - FATTORE DI FANO  F = Var/media dei conteggi:
        F ~ 1  -> POISSON (uniforme/casuale: nessun clustering)
        F > 1  -> SOVRA-DISPERSO (CLUSTERIZZATO: zone dense + vuoti) = rete cosmica
        F < 1  -> sotto-disperso (regolare/anticlustering)
  - FRAZIONE DI VUOTI  f0 (blocchi con 0 difetti) vs Poisson exp(-media):
        f0 > exp(-media) -> piu' vuoti dell'atteso = i difetti si ammassano altrove.

NB: serve abbastanza difetti per blocco (i campi ad alto chi_mean; vicino soglia c'e'
~1 difetto -> niente statistica di clustering). Con pochi difetti, Fano e' rumoroso ->
aggregare su piu' campi/seed. Il clustering emerge alle scale GRANDI (k alto) se i
difetti si raggruppano in certe regioni L2/L3.

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/analyze_clustering.py
  python experiments/exp3/analyze_clustering.py --thr 0.6
================================================================================
"""

import os, sys, glob, re
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIELDS_DIR = os.path.join(ROOT, "experiments", "exp3", "fields")
CHI_STABLE = 50.0


def defect_mask(chi_flat, chi0, thr):
    pozzo = chi0 * (1.0 if np.mean(chi_flat) >= 0 else -1.0)
    return np.abs(chi_flat - pozzo) > thr * chi0


def field_level(n_leaves):
    return int(round(np.log(n_leaves) / np.log(24)))


def clustering_stats(mask):
    """Per ogni scala k (blocco=24^k), ritorna dict di statistiche di clustering."""
    n = mask.size
    L = field_level(n)
    out = []
    for k in range(1, L):                  # k=L sarebbe l'intero sistema (1 blocco)
        bs = 24 ** k
        counts = mask.reshape(-1, bs).sum(axis=1).astype(float)
        nb = counts.size
        mean = float(counts.mean())
        var = float(counts.var())
        fano = var / mean if mean > 1e-12 else float("nan")
        f0 = float(np.mean(counts == 0))
        f0_pois = float(np.exp(-mean)) if mean < 700 else 0.0
        out.append({"k": k, "blocco": bs, "n_blocchi": nb, "mean": mean,
                    "fano": fano, "f0": f0, "f0_pois": f0_pois})
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="P10 - clustering della materia (rete cosmica?)")
    ap.add_argument("--thr", type=float, default=0.6, help="soglia difetto |chi-pozzo|>thr*chi0")
    ap.add_argument("--chi0", type=float, default=CHI_STABLE)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(FIELDS_DIR, "campo_L*.npz")))
    print("=" * 76)
    print("  P10 - CLUSTERING DELLA MATERIA: rete cosmica o distribuzione uniforme?")
    print("=" * 76)
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

    for lev in sorted(by_level):
        # aggrega le statistiche su tutti i campi del livello, per scala k
        per_k = {}
        ndef_tot = []
        for f in by_level[lev]:
            d = np.load(f)
            mask = defect_mask(d["chi"].astype(float), args.chi0, args.thr)
            ndef_tot.append(int(mask.sum()))
            for st in clustering_stats(mask):
                per_k.setdefault(st["k"], {"fano": [], "f0": [], "f0p": [], "mean": [],
                                           "blocco": st["blocco"], "nb": st["n_blocchi"]})
                if not np.isnan(st["fano"]):
                    per_k[st["k"]]["fano"].append(st["fano"])
                per_k[st["k"]]["f0"].append(st["f0"])
                per_k[st["k"]]["f0p"].append(st["f0_pois"])
                per_k[st["k"]]["mean"].append(st["mean"])
        print(f"  L{lev}: {len(by_level[lev])} campi | difetti/campo: "
              f"medio {np.mean(ndef_tot):.1f} (range {min(ndef_tot)}-{max(ndef_tot)})")
        if max(ndef_tot) < 3:
            print(f"    -> troppo pochi difetti per il clustering (serve chi_mean alto / plasma).")
        print(f"    {'scala k':>8} {'blocco':>8} {'n_bloc':>7} {'def/bloc':>9} "
              f"{'FANO':>7} {'vuoti':>7} {'vuoti_Pois':>11} {'verdetto':>16}")
        for k in sorted(per_k):
            d = per_k[k]
            fano = np.mean(d["fano"]) if d["fano"] else float("nan")
            f0 = np.mean(d["f0"]); f0p = np.mean(d["f0p"]); mn = np.mean(d["mean"])
            if np.isnan(fano):
                verdetto = "no difetti"
            elif fano > 1.5:
                verdetto = "CLUSTERIZZATO"
            elif fano < 0.67:
                verdetto = "regolare"
            else:
                verdetto = "~Poisson (unif.)"
            print(f"    {k:>8} {d['blocco']:>8} {d['nb']:>7} {mn:>9.2f} "
                  f"{fano:>7.2f} {f0:>7.2f} {f0p:>11.2f} {verdetto:>16}")
        print()

    print("  LETTURA: FANO>1.5 a qualche scala = i difetti si AMMASSANO (rete cosmica);")
    print("  FANO~1 = uniforme/casuale (Poisson). vuoti>vuoti_Pois conferma l'addensamento.")
    print("  Clustering che CRESCE con k = aggregazione gerarchica (macro-kink a scale alte).")
    print("  NB: con pochi difetti il Fano e' rumoroso -> servono campi a chi_mean alto +")
    print("  ensemble di seed. Falsificabile: Fano~1 ovunque -> ipotesi rete cosmica FALSA.")


if __name__ == "__main__":
    main()
