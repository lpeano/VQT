import h5py
import numpy as np

filename = 'cosmology_L3_equilibrio.h5'

print("=" * 80)
print(f"ANALISI DETTAGLIATA: {filename}")
print("=" * 80)

with h5py.File(filename, 'r') as f:
    # Attributi root
    print("\n[ROOT ATTRIBUTES]")
    for key, val in f.attrs.items():
        print(f"  {key}: {val}")
    
    # Frames
    frames = sorted(f['frames'].keys())
    print(f"\n[FRAMES]")
    print(f"  Total frames: {len(frames)}")
    print(f"  First frame: {frames[0]}")
    print(f"  Last frame: {frames[-1]}")
    
    # Dettagli primo frame
    first_frame = f['frames'][frames[0]]
    print(f"\n[PRIMO FRAME - {frames[0]}]")
    for key in first_frame.keys():
        dataset = first_frame[key]
        print(f"  {key}: shape={dataset.shape}, dtype={dataset.dtype}")
    
    # Attributi primo frame
    if first_frame.attrs:
        print(f"\n[ATTRIBUTI PRIMO FRAME]")
        for key, val in first_frame.attrs.items():
            print(f"  {key}: {val}")
    
    # Timestamp se presente
    if 'timestamp' in first_frame.attrs:
        t_start = first_frame.attrs['timestamp']
        last_frame = f['frames'][frames[-1]]
        t_end = last_frame.attrs['timestamp']
        print(f"\n[TIMELINE]")
        print(f"  t_start: {t_start} s")
        print(f"  t_end: {t_end} s")
        print(f"  Duration: {t_end - t_start} s")
        print(f"  dt stimato: {(t_end - t_start)/(len(frames)-1):.4f} s")
    
    # Numero segmenti
    positions = first_frame['positions'][:]
    print(f"\n[DATASET STRUCTURE]")
    print(f"  Segments: {len(positions)}")
    print(f"  Expected: 13824 (24^3)")
    print(f"  Match: {'✓ OK' if len(positions) == 13824 else '✗ MISMATCH'}")

print("=" * 80)
