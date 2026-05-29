import h5py

with h5py.File('cosmology_L3_equilibrio.h5', 'r') as f:
    last = f['frames']['frame_000019']
    print(f"Ultimo frame: step={last.attrs['step']}, time={last.attrs['time']}s")
    
    first = f['frames']['frame_000000']
    print(f"Primo frame: step={first.attrs['step']}, time={first.attrs['time']}s")
    
    total_steps = last.attrs['step']
    save_interval = (last.attrs['step'] - first.attrs['step']) / 19
    
    print("\n" + "="*60)
    print("PARAMETRI RICOSTRUITI:")
    print("="*60)
    print(f"--steps {total_steps}")
    print(f"--save-interval {int(save_interval)}")
    print(f"--dt 0.01")
    print("="*60)
    
    # Stima tempo
    if total_steps == 100:
        time_estimate = 100 * 31.5  # secondi per step
        print(f"\nTempo stimato: {time_estimate:.0f} secondi = {time_estimate/60:.1f} minuti")
