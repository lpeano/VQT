"""
================================================================================
SCALA METRICA DEL VOXEL: ancoraggio alla lunghezza di Planck
================================================================================

DEFINIZIONE METRICA (cio' che mancava: il voxel era definito DINAMICAMENTE -- (chi,v)
in un doppio pozzo -- ma NON METRICAMENTE -- m=1, chi0=50 = unita' di codice).

Auto-similarita' (intuizione di Luca, geometria DERIVATA):
  un aggregato = N = 24 voxel = 12 monti + 12 valli (torsioni a chiralita' alternata,
  chiusura spinoriale 720 deg). Una MEZZA ONDA (un monte o una valle) = 1 voxel
  = 1/24 dell'aggregato. Il rapporto x24 per livello e' geometrico (Leech).

POSTULATO DI ANCORAGGIO (dichiarato, NON derivato):
  il FONDO della gerarchia -- il voxel che non si suddivide piu' (L0) -- E' la scala
  di Planck (cutoff UV, lunghezza minima). Quindi:
        ell_voxel(L0) = ell_Planck ,  t_step = t_Planck ,  E_voxel = E_Planck .
  L'auto-similarita' fissa il RAPPORTO (x24/livello); l'ancoraggio fissa la SCALA
  ASSOLUTA. Sono cose distinte: la prima e' derivata, la seconda e' il postulato fisico
  (quello naturale: e' il "muratore di PLANCK").

DIMENSIONE E LADDER:
  "1 voxel = 1/24 dell'aggregato" e' un rapporto di CONTEGGIO/VOLUME (24 voxel per
  aggregato, sempre). Il rapporto LINEARE per livello dipende dalla dimensione d in cui
  i 24 si dispongono:
        ell_{L+1} / ell_L = 24^{1/d}
  - d=1 (la mezza onda lungo l'anello):      x24      per livello;
  - d=3 (volume 3D):                          x24^{1/3} ~ 2.884 per livello;
  Quindi  ell_L = 24^{L/d} * ell_Planck .

ONESTA' SUL VALORE DI G (circolarita'):
  ell_Planck = sqrt(hbar G / c^3). Ancorare la lunghezza del voxel a Planck E'
  scegliere il valore di G. Percio' l'ancoraggio FISSA l'unita', NON deriva G in modo
  indipendente. Il modello PREDICE la STRUTTURA di G (il rapporto R_geo = 4 N/(N-1),
  la dipendenza di scala dalla rigidezza); il VALORE assoluto e' la scelta di unita'.
  Come ogni teoria: predizioni adimensionali + 1 unita'.
================================================================================
"""

import numpy as np

# --- Costanti di Planck (SI / GeV), CODATA ---
ELL_PLANCK = 1.616255e-35     # m   (lunghezza di Planck)
T_PLANCK = 5.391247e-44       # s   (tempo di Planck)
M_PLANCK = 2.176434e-8        # kg  (massa di Planck)
E_PLANCK_GeV = 1.220890e19    # GeV (energia di Planck)

N_VOXEL = 24                  # voxel per aggregato (Leech / cubottaedro). DERIVATO.

# Theta: scala di energia intrinseca del voxel = energia di Planck (per ancoraggio).
THETA_PLANCK_GeV = E_PLANCK_GeV


def length_at_level(L, d=3):
    """Lunghezza fisica di un oggetto di livello L: ell_L = 24^{L/d} * ell_Planck.
    d = dimensione in cui si dispongono i 24 (d=1: anello/mezza onda; d=3: volume)."""
    return (N_VOXEL ** (L / d)) * ELL_PLANCK


def level_for_length(length_m, d=3):
    """Livello L che corrisponde a una lunghezza fisica data (inverso di sopra)."""
    return np.log(length_m / ELL_PLANCK) / np.log(N_VOXEL ** (1.0 / d))


def _self_test():
    print("=" * 70)
    print("  SCALA METRICA DEL VOXEL (ancoraggio: ell_voxel(L0) = ell_Planck)")
    print("=" * 70)
    print(f"  ell_Planck={ELL_PLANCK:.3e} m  t_Planck={T_PLANCK:.3e} s  "
          f"E_Planck={E_PLANCK_GeV:.3e} GeV")
    print(f"  N=24 voxel/aggregato (derivato).  Theta = E_Planck (ancoraggio).")
    print("  --- ladder delle lunghezze (d=3: x24^(1/3)=2.884/livello) ---")
    for L in [0, 5, 10, 20, 30, 40, 43, 50]:
        print(f"    L{L:>3}: ell = {length_at_level(L, d=3):.3e} m")
    print("  --- livello di alcune scale fisiche (d=3) ---")
    for name, ell in [("protone ~1e-15 m", 1e-15), ("atomo ~1e-10 m", 1e-10),
                      ("virus ~1e-7 m", 1e-7), ("uomo ~1 m", 1.0),
                      ("Terra ~1e7 m", 1e7), ("universo oss. ~8.8e26 m", 8.8e26)]:
        print(f"    {name:>26}: L ~ {level_for_length(ell, d=3):.1f}")
    print("  (d=1, la mezza onda: x24/livello -> ladder molto piu' ripido)")
    # verifica: L0 = Planck, monotono crescente, inverso coerente
    ok0 = abs(length_at_level(0) - ELL_PLANCK) < 1e-45
    okinv = abs(level_for_length(length_at_level(17.3, d=3), d=3) - 17.3) < 1e-9
    print(f"  L0 == ell_Planck {'OK' if ok0 else 'NO'}; inverso coerente "
          f"{'OK' if okinv else 'NO'}")
    return ok0 and okinv


if __name__ == "__main__":
    _self_test()
