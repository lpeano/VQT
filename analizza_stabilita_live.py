#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizzatore in Tempo Reale del Log di Stabilità
==================================================

Monitora stabilita.log e fornisce statistiche live sull'errore di chiusura spinoriale.

OBIETTIVO:
----------
Verificare se il manifold reale con chiralità DX/SX riesce a chiudere lo spinore
a 720° (4π), validando il modello fisico.

CRITERI DI VALIDAZIONE:
-----------------------
- Errore < 0.01: ECCELLENTE (chiusura quasi perfetta)
- Errore < 0.05: BUONO (entro tolleranza fisica)
- Errore < 0.10: ACCETTABILE (validazione del modello)
- Errore > 0.10: CRITICO (modello non validato)
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Path al file di log
log_path = os.path.join(os.path.dirname(__file__), 'stabilita.log')

# Liste per tracciare l'evoluzione
frames = []
lambdas = []
chis = []
contorsioni = []
errori = []
status_list = []

def leggi_log():
    """Legge il file di log e restituisce i dati."""
    global frames, lambdas, chis, contorsioni, errori, status_list
    
    frames_new = []
    lambdas_new = []
    chis_new = []
    contorsioni_new = []
    errori_new = []
    status_new = []
    
    if not os.path.exists(log_path):
        return False
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Salta header (prime 4 righe)
        for line in lines[4:]:
            line = line.strip()
            if not line or line.startswith('=') or line.startswith('-'):
                continue
            if 'Fine simulazione' in line:
                break
            
            # Parse linea
            parts = line.split()
            if len(parts) >= 5:
                try:
                    frame = int(parts[0])
                    lambda_val = float(parts[1])
                    chi = float(parts[2])
                    K = float(parts[3])
                    errore = float(parts[4])
                    status = ' '.join(parts[5:]) if len(parts) > 5 else 'N/A'
                    
                    frames_new.append(frame)
                    lambdas_new.append(lambda_val)
                    chis_new.append(chi)
                    contorsioni_new.append(K)
                    errori_new.append(errore)
                    status_new.append(status)
                except ValueError:
                    continue
        
        # Aggiorna liste globali
        frames = frames_new
        lambdas = lambdas_new
        chis = chis_new
        contorsioni = contorsioni_new
        errori = errori_new
        status_list = status_new
        
        return len(frames) > 0
    
    except Exception as e:
        print(f"Errore lettura log: {e}")
        return False

def analizza_stabilita():
    """Analizza i dati e fornisce statistiche."""
    if len(errori) == 0:
        return None
    
    errori_abs = [abs(e) for e in errori]
    
    stats = {
        'n_frames': len(frames),
        'ultimo_frame': frames[-1] if frames else 0,
        'errore_medio': np.mean(errori_abs),
        'errore_std': np.std(errori_abs),
        'errore_min': np.min(errori_abs),
        'errore_max': np.max(errori_abs),
        'errore_corrente': errori_abs[-1] if errori_abs else 0,
        'contorsione_media': np.mean(contorsioni) if contorsioni else 0,
        'chi_corrente': chis[-1] if chis else 0,
        'lambda_corrente': lambdas[-1] if lambdas else 0
    }
    
    # Conta stati
    n_stabile = sum(1 for s in status_list if 'STABILE' in s)
    n_buono = sum(1 for s in status_list if 'BUONO' in s)
    n_accettabile = sum(1 for s in status_list if 'ACCETTABILE' in s)
    n_instabile = sum(1 for s in status_list if 'INSTABILE' in s)
    
    stats['percentuale_stabile'] = (n_stabile / len(status_list) * 100) if status_list else 0
    stats['percentuale_buono'] = (n_buono / len(status_list) * 100) if status_list else 0
    stats['percentuale_accettabile'] = (n_accettabile / len(status_list) * 100) if status_list else 0
    stats['percentuale_instabile'] = (n_instabile / len(status_list) * 100) if status_list else 0
    
    # Trend (ultimi 50 frame)
    if len(errori_abs) > 50:
        trend_recente = np.mean(errori_abs[-50:]) - np.mean(errori_abs[-100:-50])
        stats['trend'] = 'CONVERGENTE ↓' if trend_recente < 0 else 'DIVERGENTE ↑'
    else:
        stats['trend'] = 'IN VALUTAZIONE...'
    
    return stats

def stampa_report():
    """Stampa report dettagliato."""
    stats = analizza_stabilita()
    if stats is None:
        print("In attesa di dati...")
        return
    
    print("\n" + "=" * 80)
    print("REPORT STABILITÀ TOPOLOGICA SPINORIALE")
    print("=" * 80)
    print(f"Frame analizzati: {stats['n_frames']}/500 ({stats['n_frames']/5:.1f}%)")
    print(f"Lambda corrente: {stats['lambda_corrente']:.6f}")
    print(f"Chi corrente: {stats['chi_corrente']:.6f}")
    print()
    
    print("CONTORSIONE K (Tensore):")
    print(f"  Media: {stats['contorsione_media']:.6e}")
    print()
    
    print("ERRORE CHIUSURA SPINORIALE (Deviazione da 4π):")
    print(f"  Corrente: {stats['errore_corrente']:.6f}")
    print(f"  Media:    {stats['errore_medio']:.6f}")
    print(f"  Std Dev:  {stats['errore_std']:.6f}")
    print(f"  Range:    [{stats['errore_min']:.6f}, {stats['errore_max']:.6f}]")
    print(f"  Trend:    {stats['trend']}")
    print()
    
    print("DISTRIBUZIONE STATI:")
    print(f"  STABILE (< 0.01):       {stats['percentuale_stabile']:.1f}%")
    print(f"  BUONO (< 0.05):         {stats['percentuale_buono']:.1f}%")
    print(f"  ACCETTABILE (< 0.10):   {stats['percentuale_accettabile']:.1f}%")
    print(f"  INSTABILE (> 0.10):     {stats['percentuale_instabile']:.1f}%")
    print()
    
    # Verdetto validazione
    print("=" * 80)
    print("VALIDAZIONE MODELLO:")
    print("=" * 80)
    
    if stats['errore_medio'] < 0.01:
        print("✅ ECCELLENTE: Chiusura spinoriale quasi perfetta!")
        print("   Il manifold DX/SX chiude correttamente a 720° (4π).")
        validato = True
    elif stats['errore_medio'] < 0.05:
        print("✅ BUONO: Chiusura entro tolleranza fisica.")
        print("   Il modello è validato per solitoni fermionici.")
        validato = True
    elif stats['errore_medio'] < 0.10:
        print("✓ ACCETTABILE: Modello validato con deviazioni moderate.")
        print("   Possibile calibrazione dei parametri per migliorare.")
        validato = True
    else:
        print("⚠️  CRITICO: Errore superiore alla soglia di validazione (0.10).")
        print("   Il modello richiede revisione dei parametri geometrici.")
        validato = False
    
    if validato:
        print("\n🎉 MODELLO VALIDATO: La chiralità DX/SX stabilizza lo spinore! 🎉")
    else:
        print("\n⚠️  Modello non validato con i parametri correnti.")
    
    print("=" * 80)

def monitora_live():
    """Monitora il log in modalità live (console)."""
    print("=" * 80)
    print("MONITORAGGIO LIVE - Stabilità Topologica")
    print("=" * 80)
    print("Premere Ctrl+C per terminare")
    print()
    
    try:
        while True:
            if leggi_log():
                os.system('cls' if os.name == 'nt' else 'clear')
                stampa_report()
            else:
                print("In attesa del file stabilita.log...")
            
            time.sleep(2)  # Aggiorna ogni 2 secondi
    
    except KeyboardInterrupt:
        print("\n\nMonitoraggio terminato.")

def genera_grafico():
    """Genera grafico finale dell'evoluzione."""
    if not leggi_log():
        print("Nessun dato disponibile per il grafico.")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Evoluzione Stabilità Topologica Spinoriale', fontsize=16, weight='bold')
    
    # Grafico 1: Errore di chiusura
    axes[0, 0].plot(frames, [abs(e) for e in errori], 'b-', linewidth=2, alpha=0.7)
    axes[0, 0].axhline(y=0.01, color='g', linestyle='--', label='Soglia STABILE', alpha=0.5)
    axes[0, 0].axhline(y=0.05, color='orange', linestyle='--', label='Soglia BUONO', alpha=0.5)
    axes[0, 0].axhline(y=0.10, color='r', linestyle='--', label='Soglia ACCETTABILE', alpha=0.5)
    axes[0, 0].set_xlabel('Frame')
    axes[0, 0].set_ylabel('|Errore| da 4π')
    axes[0, 0].set_title('Errore Chiusura Spinoriale')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].set_yscale('log')
    
    # Grafico 2: Contorsione K
    axes[0, 1].plot(frames, contorsioni, 'r-', linewidth=2, alpha=0.7)
    axes[0, 1].set_xlabel('Frame')
    axes[0, 1].set_ylabel('||K|| (Norma Frobenius)')
    axes[0, 1].set_title('Tensore di Contorsione')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Grafico 3: Chi
    axes[1, 0].plot(frames, chis, 'g-', linewidth=2, alpha=0.7)
    axes[1, 0].set_xlabel('Frame')
    axes[1, 0].set_ylabel('χ (Potenziale di Scala)')
    axes[1, 0].set_title('Evoluzione χ')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Grafico 4: Correlazione K vs Errore
    errori_abs = [abs(e) for e in errori]
    scatter = axes[1, 1].scatter(contorsioni, errori_abs, c=frames, cmap='viridis', s=20, alpha=0.6)
    axes[1, 1].set_xlabel('||K|| (Contorsione)')
    axes[1, 1].set_ylabel('|Errore| da 4π')
    axes[1, 1].set_title('Correlazione Contorsione vs Errore')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].set_yscale('log')
    cbar = plt.colorbar(scatter, ax=axes[1, 1])
    cbar.set_label('Frame')
    
    plt.tight_layout()
    output_path = os.path.join(os.path.dirname(__file__), 'analisi_stabilita.png')
    plt.savefig(output_path, dpi=150)
    print(f"\nGrafico salvato in: {output_path}")
    plt.show()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--grafico':
        genera_grafico()
    else:
        # Monitora live
        try:
            monitora_live()
        except KeyboardInterrupt:
            print("\n\nGenerazione grafico finale...")
            genera_grafico()
