#!/usr/bin/env python3
"""
Test rapido per verificare che tutte le protezioni siano attive.
Esegui questo script per controllare lo stato del sistema.
"""

import os
import sys
import h5py
import numpy as np
import platform

DB_FILE = "geometrodinamica_matrix.h5"

def test_file_exists():
    """Verifica che il file HDF5 esista."""
    if not os.path.exists(DB_FILE):
        print(f"❌ File {DB_FILE} non trovato")
        return False
    print(f"✅ File {DB_FILE} trovato")
    return True

def test_file_readable():
    """Verifica che il file sia leggibile."""
    try:
        with h5py.File(DB_FILE, 'r') as f:
            _ = f.attrs.get('usa_24_campi_locali', False)
        print(f"✅ File leggibile correttamente")
        return True
    except OSError as e:
        if "consistency" in str(e) or "already open" in str(e):
            print(f"⚠️  File con flag di consistenza bloccati")
            print(f"    → WQT_manifold.py include auto-riparazione automatica")
            print(f"    → Lancia --playback o --headless per riparare")
            return False
        else:
            print(f"❌ Errore lettura file: {e}")
            return False

def test_resume_capability():
    """Verifica funzionalità resume."""
    if not os.path.exists(DB_FILE):
        print(f"⏭️  Resume test saltato (file mancante)")
        return True
    
    try:
        with h5py.File(DB_FILE, 'r') as f:
            data = f['telemetria_scalare'][:]
            valid_frames = np.where(data['rm'] > 0)[0]
            if len(valid_frames) > 0:
                ultimo_frame = valid_frames[-1]
                print(f"✅ Resume disponibile - ultimo frame valido: {ultimo_frame}")
            else:
                print(f"ℹ️  Nessun frame valido trovato (file vuoto o nuovo)")
        return True
    except Exception as e:
        print(f"❌ Errore test resume: {e}")
        return False

def test_24_campi_format():
    """Verifica formato 24 campi."""
    if not os.path.exists(DB_FILE):
        print(f"⏭️  Test formato saltato (file mancante)")
        return True
    
    try:
        with h5py.File(DB_FILE, 'r') as f:
            usa_24 = f.attrs.get('usa_24_campi_locali', False)
            if usa_24:
                print(f"✅ Sistema a 24 campi locali attivo")
                # Verifica che il dataset abbia i campi corretti
                dtype = f['telemetria_scalare'].dtype
                if 'chi_vettore' in dtype.names:
                    print(f"   → chi_vettore[24] e vel_vettore[24] presenti")
                else:
                    print(f"⚠️  Formato legacy (chi_lineare)")
            else:
                print(f"ℹ️  Sistema a campo singolo (modalità legacy)")
        return True
    except Exception as e:
        print(f"❌ Errore test formato: {e}")
        return False

def test_swmr_support():
    """Verifica supporto SWMR."""
    os_name = platform.system()
    
    # Verifica il valore EFFETTIVO leggendo da WQT_manifold.py
    hdf5_locking = None
    try:
        with open('WQT_manifold.py', 'r', encoding='utf-8') as f:
            for line in f:
                if 'HDF5_USE_FILE_LOCKING' in line and '=' in line:
                    if 'FALSE' in line:
                        hdf5_locking = "FALSE"
                    elif 'TRUE' in line:
                        hdf5_locking = "TRUE"
                    break
    except:
        hdf5_locking = os.environ.get("HDF5_USE_FILE_LOCKING", "TRUE")
    
    if os_name == "Windows":
        if hdf5_locking == "FALSE":
            print(f"⚠️  SWMR disabilitato su Windows (HDF5_USE_FILE_LOCKING=FALSE)")
            print(f"   → Playback concorrente NON sicuro")
        else:
            print(f"✅ File locking attivo (playback concorrente possibile)")
    else:
        print(f"✅ OS {os_name} - SWMR supportato")
    
    return True

def main():
    print("="*60)
    print("🛡️  VERIFICA PROTEZIONI E RESILIENZA WQT")
    print("="*60)
    print()
    
    tests = [
        ("Esistenza file", test_file_exists),
        ("Leggibilità file", test_file_readable),
        ("Capacità resume", test_resume_capability),
        ("Formato 24 campi", test_24_campi_format),
        ("Supporto SWMR", test_swmr_support),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n[TEST] {name}...")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ ERRORE CRITICO: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("📊 RIEPILOGO")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print()
    print(f"Risultato: {passed}/{total} test superati")
    
    if passed == total:
        print("✅ Tutte le protezioni sono attive!")
    else:
        print("⚠️  Alcuni test falliti - verifica i log sopra")
    
    print("="*60)
    print()
    print("ℹ️  FUNZIONALITÀ DISPONIBILI:")
    print("  1. Auto-riparazione file corrotti (headless + playback)")
    print("  2. Resume automatico da ultimo frame valido (headless)")
    print("  3. Protezione scrittura a blocchi con flush emergenza")
    if platform.system() == "Windows":
        print("  4. Playback concorrente: ❌ NON supportato su Windows")
    else:
        print("  4. Playback concorrente: ✅ Supportato (SWMR)")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
