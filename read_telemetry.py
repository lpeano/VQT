#!/usr/bin/env python3
"""Legge telemetria da file HDF5 e mostra dati energia/tempo"""
import sys
import h5py
import numpy as np

if len(sys.argv) < 2:
    print("Uso: python read_telemetry.py <file.h5>")
    sys.exit(1)

filename = sys.argv[1]

try:
    with h5py.File(filename, 'r') as f:
        tel = f['telemetria_scalare'][:]
        
        if len(tel) == 0:
            print("File vuoto")
            sys.exit(0)
        
        # Filtra frame validi (rm > 0)
        valid = tel['rm'] > 0
        tel_valid = tel[valid]
        
        if len(tel_valid) == 0:
            print("Nessun frame valido")
            sys.exit(0)
        
        print(f"\n{'='*70}")
        print(f"  TELEMETRIA: {filename}")
        print(f"{'='*70}\n")
        
        print(f"Frames totali:  {len(tel)}")
        print(f"Frames validi:  {len(tel_valid)}")
        print(f"Tempo totale:   {tel_valid[-1]['tempo_assol']:.6f} s")
        print(f"\n{'='*70}")
        print(f"  ULTIMI 10 FRAMES")
        print(f"{'='*70}\n")
        
        print(f"{'Frame':<8} {'Tempo (s)':<12} {'rm (m)':<12} {'χ_medio':<12} "
              f"{'H (1/s)':<12} {'K':<12}")
        print(f"{'-'*70}")
        
        for i in range(max(0, len(tel_valid)-10), len(tel_valid)):
            frame = tel_valid[i]
            print(f"{frame['frame_id']:<8} "
                  f"{frame['tempo_assol']:<12.6f} "
                  f"{frame['rm']:<12.3e} "
                  f"{frame['chi_medio']:<12.3f} "
                  f"{frame['h_fisica']:<12.3e} "
                  f"{frame['contorsione_k_medio']:<12.3e}")
        
        print(f"\n{'='*70}")
        print(f"  STATISTICHE")
        print(f"{'='*70}\n")
        
        print(f"rm min/max:     {tel_valid['rm'].min():.3e} / {tel_valid['rm'].max():.3e} m")
        print(f"χ min/max:      {tel_valid['chi_medio'].min():.3f} / {tel_valid['chi_medio'].max():.3f}")
        print(f"H min/max:      {tel_valid['h_fisica'].min():.3e} / {tel_valid['h_fisica'].max():.3e} 1/s")
        print(f"K min/max:      {tel_valid['contorsione_k_medio'].min():.3e} / {tel_valid['contorsione_k_medio'].max():.3e}")
        
        # Se ci sono campi vettoriali (24 campi locali)
        if 'chi_vettore' in tel.dtype.names:
            print(f"\n{'='*70}")
            print(f"  24 CAMPI LOCALI (ultimo frame)")
            print(f"{'='*70}\n")
            
            last = tel_valid[-1]
            chi_vec = last['chi_vettore']
            vel_vec = last['vel_vettore']
            cont_loc = last['contorsione_locale']
            
            print(f"χ:  min={chi_vec.min():.3f}, max={chi_vec.max():.3f}, "
                  f"std={chi_vec.std():.3f}, Var={chi_vec.var():.3e}")
            print(f"v:  min={vel_vec.min():.3e}, max={vel_vec.max():.3e}, "
                  f"std={vel_vec.std():.3e}")
            print(f"K:  min={cont_loc.min():.3e}, max={cont_loc.max():.3e}, "
                  f"std={cont_loc.std():.3e}")
            
except FileNotFoundError:
    print(f"File non trovato: {filename}")
    sys.exit(1)
except Exception as e:
    print(f"Errore: {e}")
    sys.exit(1)
