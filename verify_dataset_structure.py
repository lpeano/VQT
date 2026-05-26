import h5py

print("="*80)
print("DATASET STRUCTURE ANALYSIS")
print("="*80)

for dataset_name in ['cosmology_L3.h5', 'cosmology_L3_equilibrio.h5']:
    try:
        f = h5py.File(dataset_name, 'r')
        print(f"\n📁 {dataset_name}")
        print(f"   Frames: {len(list(f['frames'].keys()))}")
        
        frame0 = f['frames']['frame_000000']
        print(f"\n   Keys in frame_000000:")
        for key in frame0.keys():
            data = frame0[key]
            if hasattr(data, 'shape'):
                print(f"      - {key:30s} shape: {data.shape}")
            else:
                print(f"      - {key:30s} (group)")
        
        # Verifica connettività esplicita
        has_connectivity = any(k in frame0.keys() for k in ['edges', 'connectivity', 'faces', 'triangles', 'adjacency'])
        print(f"\n   ❓ Connectivity data: {'✓ YES' if has_connectivity else '✗ NO (need reconstruction)'}")
        
        f.close()
    except Exception as e:
        print(f"\n   ⚠️ File not found or error: {e}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("Se manca connettività esplicita (edges/faces), usiamo:")
print("  1. Marching Cubes (Ricostruzione campo χ) ✓ IMPLEMENTATO")
print("  2. Gaussian Smoothing (Elimina L0 noise) ✓ IMPLEMENTATO")
print("  3. Poly3DCollection (Mesh rendering) ✓ IMPLEMENTATO")
print("="*80)
