import numpy as np
import time
from scipy.spatial import cKDTree
import scipy.sparse as sp

N = 14000
positions = np.random.rand(N, 3) * 10
K_squared_values = np.random.rand(N)
neighborhood_radius = 0.5

def old_compute(positions, K_squared_values, neighborhood_radius):
    N = len(positions)
    f_detorsion = np.ones(N, dtype=np.float64)
    tree = cKDTree(positions)
    neighbors_list = tree.query_ball_tree(tree, neighborhood_radius)

    for i, hood_indices in enumerate(neighbors_list):
        if len(hood_indices) <= 1:
            continue
        K_local = K_squared_values[list(hood_indices)]
        K_mean = float(np.mean(K_local))
        if K_mean > 1e-12:
            CV = float(np.std(K_local)) / K_mean
            f_detorsion[i] = 1.0 / (1.0 + CV)
    return f_detorsion

def new_compute(positions, K_squared_values, neighborhood_radius):
    N = len(positions)
    f_detorsion = np.ones(N, dtype=np.float64)
    tree = cKDTree(positions)
    
    pairs = np.array(list(tree.query_pairs(neighborhood_radius)))
    
    if len(pairs) > 0:
        row = np.concatenate([pairs[:, 0], pairs[:, 1], np.arange(N)])
        col = np.concatenate([pairs[:, 1], pairs[:, 0], np.arange(N)])
        data = np.ones(len(row), dtype=np.float64)
        
        A = sp.csr_matrix((data, (row, col)), shape=(N, N))
        
        counts = A.sum(axis=1).A1
        
        K_sums = A.dot(K_squared_values)
        K_mean = K_sums / counts
        
        # calculate sum of squares
        # note: np.std computes population standard deviation, so div by N, not N-1
        K_sq_sums = A.dot(K_squared_values**2)
        K_var = (K_sq_sums / counts) - K_mean**2
        K_var = np.maximum(K_var, 0.0)
        K_std = np.sqrt(K_var)
        
        valid = (K_mean > 1e-12) & (counts > 1)
        
        CV = np.zeros(N, dtype=np.float64)
        CV[valid] = K_std[valid] / K_mean[valid]
        
        f_detorsion[valid] = 1.0 / (1.0 + CV[valid])
    else:
        # If no pairs, counts is 1 everywhere, valid is false, so it's all ones.
        pass
    
    return f_detorsion

t0 = time.time()
r_old = old_compute(positions, K_squared_values, neighborhood_radius)
t1 = time.time()

t2 = time.time()
r_new = new_compute(positions, K_squared_values, neighborhood_radius)
t3 = time.time()

print(f"Old time: {t1-t0:.4f} s")
print(f"New time: {t3-t2:.4f} s")
print(f"Max diff: {np.max(np.abs(r_old - r_new))}")
