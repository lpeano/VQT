import numpy as np
import time

def from_coupling_matrix():
    W_dense = np.random.rand(24, 24)
    D = np.diag(np.sum(W_dense, axis=1))
    L = D - W_dense
    eigvals, eigvecs = np.linalg.eigh(L)

t0 = time.time()
for _ in range(13824):
    from_coupling_matrix()
t1 = time.time()
print(f"Time for 13824 matrix ops: {t1-t0:.4f} s")
