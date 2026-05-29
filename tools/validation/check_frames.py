import h5py

files = [
    ('cosmology_L3_NEW.h5', 'L3_NEW'),
    ('cosmology_L2_NEW.h5', 'L2_NEW'),
    ('cosmology_L3.h5', 'L3_OLD'),
    ('cosmology_L3_equilibrio.h5', 'L3_equilibrio'),
    ('cosmology_L2.h5', 'L2_OLD'),
]

print("=" * 60)
print("CONFRONTO FRAMES")
print("=" * 60)

for filename, label in files:
    try:
        with h5py.File(filename, 'r') as f:
            frames = len(list(f['frames'].keys()))
            size_mb = f.attrs.get('file_size_mb', 'N/A')
            print(f"{label:20s}: {frames:4d} frames | {filename}")
    except FileNotFoundError:
        print(f"{label:20s}: FILE NON TROVATO | {filename}")

print("=" * 60)
