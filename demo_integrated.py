"""
================================================================================
DEMO RAPIDA - WQT MANIFOLD INTEGRATO
================================================================================

Script di esempio per testare tutte le modalità dell'applicazione integrata.

ATTENZIONE: La modalità interattiva richiede chiusura manuale della finestra.
================================================================================
"""

import os
import sys
import subprocess
import time

SCRIPT_PATH = "WQT_manifold_integrated.py"

def print_header(titolo):
    """Stampa header demo."""
    print("\n" + "="*70)
    print(f" {titolo}")
    print("="*70)

def demo_headless():
    """Demo modalità headless (calcolo puro)."""
    print_header("DEMO 1: Modalità HEADLESS (Solo calcolo)")
    
    db_file = "demo_headless.h5"
    
    # Rimuovi file esistente
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"[CLEANUP] Rimosso {db_file} esistente")
    
    print("\n[INFO] Eseguo simulazione headless: 5 manifold, 3 secondi, 24 fps")
    print("[INFO] Questo genererà 72 frame di dati senza visualizzazione")
    print()
    
    cmd = [
        sys.executable, SCRIPT_PATH,
        "--headless",
        "--n-manifold", "5",
        "--duration", "3",
        "--fps", "24",
        "--db", db_file,
        "--cores", "2"
    ]
    
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    
    if result.returncode == 0:
        print(f"[SUCCESS] ✓ Simulazione completata in {elapsed:.1f} secondi")
        
        # Verifica file HDF5
        if os.path.exists(db_file):
            size_mb = os.path.getsize(db_file) / (1024 * 1024)
            print(f"[SUCCESS] ✓ File HDF5 creato: {db_file} ({size_mb:.2f} MB)")
        
        # Mostra ultimi 10 righe output
        print("\n[OUTPUT] Ultime righe:")
        for line in result.stdout.splitlines()[-5:]:
            print(f"  {line}")
    else:
        print(f"[ERROR] ✗ Simulazione fallita con codice {result.returncode}")
        print(f"[ERROR] Stderr:\n{result.stderr}")

def demo_analisi_hdf5():
    """Demo analisi dati HDF5."""
    print_header("DEMO 2: Analisi Dati HDF5")
    
    db_file = "demo_headless.h5"
    
    if not os.path.exists(db_file):
        print(f"[ERROR] File {db_file} non trovato. Esegui prima demo_headless()")
        return
    
    try:
        import h5py
        import numpy as np
        
        with h5py.File(db_file, 'r') as f:
            telemetria = f['telemetria_scalare'][:]
            
            print(f"\n[INFO] Dataset: {len(telemetria)} frame")
            print(f"[INFO] Attributi:")
            for key, val in f.attrs.items():
                print(f"  - {key}: {val}")
            
            # Statistiche
            print("\n[STATISTICHE]")
            print(f"  N_manifold medio: {np.mean(telemetria['n_manifold']):.1f}")
            print(f"  N_manifold finale: {telemetria[-1]['n_manifold']}")
            print(f"  Torsione media: {np.mean(telemetria['torsione_media']):.3f}")
            print(f"  Energia totale media: {np.mean(telemetria['energia_totale']):.3e}")
            print(f"  Generazione massima: {np.max(telemetria['generazione_max'])}")
            
            # Evoluzione popolazione
            pop = telemetria['n_manifold']
            print(f"\n[EVOLUZIONE POPOLAZIONE]")
            print(f"  Iniziale: {pop[0]}")
            print(f"  Massima: {np.max(pop)} (frame {np.argmax(pop)})")
            print(f"  Finale: {pop[-1]}")
        
        print("\n[SUCCESS] ✓ Analisi completata")
    
    except ImportError:
        print("[ERROR] h5py non installato. Usa: pip install h5py")
    except Exception as e:
        print(f"[ERROR] Errore durante analisi: {e}")

def demo_playback_film():
    """Demo generazione filmato da HDF5."""
    print_header("DEMO 3: Generazione Filmato (Playback + Film)")
    
    db_file = "demo_headless.h5"
    output_mp4 = "demo_output.mp4"
    
    if not os.path.exists(db_file):
        print(f"[ERROR] File {db_file} non trovato. Esegui prima demo_headless()")
        return
    
    # Verifica FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        if result.returncode != 0:
            print("[ERROR] FFmpeg non trovato nel PATH")
            print("[INFO] Installa FFmpeg: https://ffmpeg.org/download.html")
            return
    except FileNotFoundError:
        print("[ERROR] FFmpeg non installato")
        print("[INFO] Windows: choco install ffmpeg")
        return
    
    print(f"\n[INFO] Generazione filmato da {db_file}...")
    print(f"[INFO] Output: {output_mp4}")
    print("[ATTENZIONE] Questo richiederà alcuni minuti...")
    print()
    
    cmd = [
        sys.executable, SCRIPT_PATH,
        "--playback",
        "--film",
        "--db", db_file,
        "--output", output_mp4,
        "--fps", "24"
    ]
    
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    
    if result.returncode == 0 and os.path.exists(output_mp4):
        size_mb = os.path.getsize(output_mp4) / (1024 * 1024)
        print(f"\n[SUCCESS] ✓ Filmato creato in {elapsed:.1f} secondi")
        print(f"[SUCCESS] ✓ File: {output_mp4} ({size_mb:.2f} MB)")
    else:
        print(f"[ERROR] ✗ Generazione fallita")
        if result.stderr:
            print(f"[ERROR] Stderr:\n{result.stderr}")

def demo_interattivo():
    """Demo modalità interattiva (richiede chiusura manuale)."""
    print_header("DEMO 4: Modalità INTERATTIVA (Animazione Real-Time)")
    
    print("\n[ATTENZIONE] Questa demo apre una finestra matplotlib.")
    print("[ATTENZIONE] Chiudi la finestra manualmente per terminare.")
    print()
    
    risposta = input("Vuoi procedere? (s/N): ").strip().lower()
    
    if risposta not in ['s', 'si', 'y', 'yes']:
        print("[INFO] Demo interattiva saltata")
        return
    
    print("\n[INFO] Avvio simulazione interattiva: 3 manifold, 5 secondi")
    print("[INFO] Chiudi la finestra per terminare")
    print()
    
    cmd = [
        sys.executable, SCRIPT_PATH,
        "--n-manifold", "3",
        "--duration", "5",
        "--fps", "24",
        "--db", "demo_interattivo.h5"
    ]
    
    # Esegui in foreground
    subprocess.run(cmd)
    
    print("\n[SUCCESS] ✓ Demo interattiva completata")

def menu_principale():
    """Menu interattivo."""
    print("\n" + "="*70)
    print(" DEMO WQT MANIFOLD INTEGRATO")
    print("="*70)
    print("\nScegli demo da eseguire:")
    print("  1. Modalità HEADLESS (calcolo puro)")
    print("  2. Analisi dati HDF5")
    print("  3. Generazione filmato MP4")
    print("  4. Modalità INTERATTIVA (visualizzazione real-time)")
    print("  5. Esegui tutte le demo (tranne interattiva)")
    print("  0. Esci")
    print()
    
    while True:
        scelta = input("Scelta [0-5]: ").strip()
        
        if scelta == '0':
            print("\n[INFO] Uscita")
            break
        elif scelta == '1':
            demo_headless()
        elif scelta == '2':
            demo_analisi_hdf5()
        elif scelta == '3':
            demo_playback_film()
        elif scelta == '4':
            demo_interattivo()
        elif scelta == '5':
            demo_headless()
            demo_analisi_hdf5()
            demo_playback_film()
            print("\n[INFO] Tutte le demo automatiche completate!")
        else:
            print("[ERROR] Scelta non valida")
        
        print()

if __name__ == "__main__":
    # Verifica che script esista
    if not os.path.exists(SCRIPT_PATH):
        print(f"[ERROR] Script {SCRIPT_PATH} non trovato nella directory corrente")
        print(f"[INFO] Directory corrente: {os.getcwd()}")
        sys.exit(1)
    
    menu_principale()
