import numpy as np
import time
from scipy.spatial import cKDTree

N = 331776
positions = np.random.rand(N, 3) * 50

t0 = time.time()
tree = cKDTree(positions)
k = 2
dists, _ = tree.query(positions, k=k)
nn_col = dists[:, 1]
neighborhood_radius = float(np.mean(nn_col)) * 2.0
t1 = time.time()
print(f"Estimate radius time: {t1-t0:.4f} s")
print(f"Estimated radius: {neighborhood_radius}")

t2 = time.time()
pairs = tree.query_pairs(neighborhood_radius)
t3 = time.time()
print(f"query_pairs time: {t3-t2:.4f} s")
print(f"Number of pairs: {len(pairs)}")
