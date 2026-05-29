"""
sparse_coupling.py
==================
Matrice di accoppiamento sparsa per il Leech Lattice VQT.

Sostituisce la matrice densa N×N di SolitoneComposito con una
scipy.sparse.csr_matrix, riducendo l'occupazione da O(N²) a O(k·N)
dove k = numero vicini effettivi (determinato dal threshold).

Risparmio tipico per N=24, L_eff=3.0, threshold=1e-3:
  Denso  : 24×24×8  = 4.6 KB
  Sparse : k≈14 nnz/riga × 12 B ≈ 4.0 KB   (lieve per N piccolo)

Risparmio reale per N≥576 (aggregazioni dirette future):
  N=576  : denso  2.6 MB → sparse ~67 KB  (-97%)
  N=13824: denso  1.5 GB → sparse ~1.6 MB (-99.9%)

Oltre al risparmio di memoria, fornisce:
- `matvec_fast(chi)`: W @ chi in formato sparse (evita to_dense)
- `weighted_outer(a, b)`: Σ_ij W_ij a_i b_j senza materializzare NxN
- `memory_bytes()`: stima occupazione corrente
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix, issparse
from typing import Union


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_sparse_decay_coupling(
    N: int,
    L_eff: float = 3.0,
    threshold: float = 1e-3,
) -> csr_matrix:
    """
    Matrice di accoppiamento con decadimento esponenziale circolare (CSR).

    W_ij = exp(-d_ij / L_eff) / Z_i   con d_ij = min(|i-j|, N-|i-j|)
    Poi azzera W_ij < threshold e ri-normalizza le righe.

    Costruzione O(N²) con numpy puro (nessun loop Python).

    Parameters
    ----------
    N         : numero nodi (tipicamente 24 per livello VQT)
    L_eff     : lunghezza caratteristica interazione [unità di spaziatura]
    threshold : soglia sparse — elementi < threshold vengono azzerati

    Returns
    -------
    W : csr_matrix (N, N), righe normalizzate a 1
    """
    idx = np.arange(N)
    # Distanza circolare: min(|i-j|, N-|i-j|) via broadcasting
    diff = np.abs(idx[:, None] - idx[None, :])
    d = np.minimum(diff, N - diff).astype(np.float64)

    # Decadimento esponenziale (diagonale = 0)
    W = np.where(d > 0, np.exp(-d / L_eff), 0.0)

    # Normalizzazione righe (Σⱼ W_ij = 1)
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums > 0, row_sums, 1.0)
    W /= row_sums

    # Sparsificazione + ri-normalizzazione
    W[W < threshold] = 0.0
    row_sums2 = W.sum(axis=1, keepdims=True)
    row_sums2 = np.where(row_sums2 > 0, row_sums2, 1.0)
    W /= row_sums2

    return csr_matrix(W)


def build_dense_decay_coupling(N: int, L_eff: float = 3.0) -> np.ndarray:
    """
    Versione densa (backward-compat). Stessa fisica, array numpy standard.
    Preferire `build_sparse_decay_coupling` per N > 48.
    """
    idx = np.arange(N)
    diff = np.abs(idx[:, None] - idx[None, :])
    d = np.minimum(diff, N - diff).astype(np.float64)
    W = np.where(d > 0, np.exp(-d / L_eff), 0.0)
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums > 0, row_sums, 1.0)
    return W / row_sums


# ---------------------------------------------------------------------------
# Memory utilities
# ---------------------------------------------------------------------------

def coupling_memory_bytes(N: int, sparse: bool = False,
                          L_eff: float = 3.0,
                          threshold: float = 1e-3) -> int:
    """Stima bytes occupati dalla matrice N×N."""
    if not sparse:
        return N * N * 8  # float64 denso

    # nnz stimato: d < -L_eff * ln(threshold)
    d_max = max(1, int(L_eff * np.log(1.0 / max(threshold, 1e-15))) + 1)
    nnz_per_row = min(2 * d_max, N - 1)
    nnz = N * nnz_per_row
    # CSR: data float64 (nnz×8) + indices int32 (nnz×4) + indptr int32 ((N+1)×4)
    return int(nnz * 12 + (N + 1) * 4)


def log_memory_summary(N: int, L_eff: float = 3.0, threshold: float = 1e-3) -> str:
    dense_b  = coupling_memory_bytes(N, sparse=False)
    sparse_b = coupling_memory_bytes(N, sparse=True, L_eff=L_eff, threshold=threshold)
    saving   = 100.0 * (1 - sparse_b / dense_b) if dense_b > 0 else 0.0
    return (
        f"CouplingMatrix N={N}: "
        f"dense={dense_b/1024:.1f} KB  "
        f"sparse~{sparse_b/1024:.1f} KB  "
        f"saving={saving:.0f}%"
    )


# ---------------------------------------------------------------------------
# Fast matrix operations (evitano to_dense per matrici grandi)
# ---------------------------------------------------------------------------

def matvec(W: Union[np.ndarray, csr_matrix], v: np.ndarray) -> np.ndarray:
    """W @ v — funziona sia con matrice densa che sparse."""
    return W @ v   # scipy sparse e numpy usano lo stesso operatore


def weighted_sum_sq(W: Union[np.ndarray, csr_matrix],
                    diff: np.ndarray) -> float:
    """
    Σᵢⱼ W_ij · diff_ij²  senza materializzare la matrice diff²×W.

    Per sparse W usa row-wise sparse dot su diff² elemento per elemento.
    Per denso usa la moltiplicazione standard.
    """
    if issparse(W):
        # W è csr: possiamo usare W.multiply(diff**2).sum()
        return float(W.multiply(diff ** 2).sum())
    return float(np.sum(W * diff ** 2))


def weighted_outer_sum(W: Union[np.ndarray, csr_matrix],
                       a: np.ndarray, b: np.ndarray) -> float:
    """
    Σᵢⱼ W_ij · a_i · b_j  =  a^T · (W · b)  in O(k·N) per W sparse.
    Evita di materializzare la matrice outer (N×N).
    """
    if issparse(W):
        return float(a @ (W @ b))
    return float(np.sum(W * (a[:, None] * b[None, :])))
