import h5py
import sys

f = h5py.File('cosmology_L3.h5', 'r')
frame = f['frames']['frame_000000']
n_segments = len(frame['positions'])
n_frames = len(list(f['frames'].keys()))

print(f'Dataset: cosmology_L3.h5')
print(f'Segments: {n_segments}')
print(f'Frames: {n_frames}')
print(f'Chi range: [{frame["chi_values"][:].min():.2f}, {frame["chi_values"][:].max():.2f}]')
print(f'K range: [{frame["contorsione_locale"][:].min():.2e}, {frame["contorsione_locale"][:].max():.2e}]')

if n_segments < 13824:
    print(f'\n❌ ERROR: Expected 13824 segments, found {n_segments}')
    sys.exit(1)
else:
    print(f'\n✓ Dataset validated: {n_segments} segments (L3 fractal level)')

f.close()
