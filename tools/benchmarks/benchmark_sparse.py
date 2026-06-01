import numpy as np
import time
import scipy.sparse as sp

N = 331776
pairs = np.random.randint(0, N, size=(1000000, 2))

t0 = time.time()
row = np.concatenate([pairs[:, 0], pairs[:, 1], np.arange(N)])
col = np.concatenate([pairs[:, 1], pairs[:, 0], np.arange(N)])
data = np.ones(len(row), dtype=np.float64)

A = sp.csr_matrix((data, (row, col)), shape=(N, N))
counts = A.sum(axis=1).A1

K_squared_values = np.random.rand(N)
K_sums = A.dot(K_squared_values)
K_mean = K_sums / counts

K_sq_sums = A.dot(K_squared_values**2)
K_var = (K_sq_sums / counts) - K_mean**2
K_var = np.maximum(K_var, 0.0)
K_std = np.sqrt(K_var)
t1 = time.time()
print(f"Sparse matrix and dot product time: {t1-t0:.4f} s")
