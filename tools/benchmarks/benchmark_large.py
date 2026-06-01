import numpy as np
import time
from scipy.spatial import cKDTree

N = 331776
# L4 spatial extent is roughly 50.0
positions = np.random.rand(N, 3) * 50
neighborhood_radius = 2.0  # Just guessing typical radius

t0 = time.time()
tree = cKDTree(positions)
pairs = tree.query_pairs(neighborhood_radius)
t1 = time.time()
print(f"Tree + query_pairs time: {t1-t0:.4f} s")
print(f"Number of pairs: {len(pairs)}")
