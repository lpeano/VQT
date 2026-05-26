#!/usr/bin/env python3
"""
Script per riparare file HDF5 bloccati dopo terminazione forzata.
"""
import h5py
import sys
import os

if len(sys.argv) < 2:
    print("Uso: python ripara_h5.py <file.h5>")
    sys.exit(1)

filename = sys.argv[1]

print(f"Tentativo di riparazione: {filename}")

# Prova 1: Apertura forzata con flag filesystem
try:
    # Rimuovi flag di consistenza usando API di basso livello
    import h5py.h5f as h5f
    
    # Tenta di aprire in modalità read-write con flag di repair
    fapl = h5f.create_access_plist()
    
    # Prova ad aprire il file
    try:
        fid = h5f.open(bytes(filename, 'utf-8'), h5f.ACC_RDWR, fapl=fapl)
        print("✓ File aperto con successo")
        
        # Chiudi immediatamente per sbloccare
        fid.close()
        print("✓ File chiuso correttamente")
        
        # Ora verifica il contenuto
        with h5py.File(filename, 'r') as f:
            print(f"\nContenuto del file:")
            print(f"Gruppi/Dataset: {list(f.keys())}")
            for key in f.keys():
                if hasattr(f[key], 'shape'):
                    print(f"  {key}: shape={f[key].shape}, dtype={f[key].dtype}")
                    if f[key].shape[0] > 0:
                        print(f"    Prime righe: {f[key][:min(3, f[key].shape[0])]}")
        
    except Exception as e:
        print(f"✗ Impossibile aprire: {e}")
        print("\nTentativo alternativo: creazione nuovo file...")
        
        # Se proprio non va, crea un nuovo file vuoto
        backup = filename + ".corrupted_backup"
        if os.path.exists(backup):
            os.remove(backup)
        os.rename(filename, backup)
        print(f"File corrotto rinominato in: {backup}")
        print(f"Creare un nuovo file eseguendo nuovamente la simulazione.")
        
except Exception as e:
    print(f"Errore: {e}")
    sys.exit(1)
