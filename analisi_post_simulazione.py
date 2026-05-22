"""
ANALISI POST-SIMULAZIONE WQT
Script di post-processing per trasformare i dati grezzi HDF5 in pannello scientifico
senza ricalcolare la simulazione. Genera dataset derivati con formattazione human-readable.

Autore: Sistema WQT Manifold
Data: 2026
"""

import numpy as np
import h5py
import sys
import argparse
from datetime import datetime

# --- ARGOMENTI LINEA DI COMANDO ---
parser = argparse.ArgumentParser(description='Post-processing dati HDF5 simulazione geometrodinamica')
parser.add_argument('--input', type=str, default='geometrodinamica_matrix.h5', help='File HDF5 di input')
parser.add_argument('--output', type=str, default='geometrodinamica_extended.h5', help='File HDF5 di output esteso')
parser.add_argument('--overwrite', action='store_true', help='Sovrascrive file di output se esiste')
args = parser.parse_args()

# --- FUNZIONI DI FORMATTAZIONE (IDENTICHE A WQT_manifold.py) ---
def format_human_time(seconds):
    """Converte il tempo emergente in formato leggibile umano con unità appropriate."""
    if seconds == 0:
        return "0 s"
    
    abs_seconds = abs(seconds)
    segno = "⏪ " if seconds < 0 else ""  # Freccia retrocausale per tempo negativo
    
    # Scale temporali subatomiche
    if abs_seconds < 1e-15:
        return f"{segno}{abs_seconds * 1e18:.2f} as"  # attosecondi
    elif abs_seconds < 1e-12:
        return f"{segno}{abs_seconds * 1e15:.2f} fs"  # femtosecondi
    elif abs_seconds < 1e-9:
        return f"{segno}{abs_seconds * 1e12:.2f} ps"  # picosecondi
    elif abs_seconds < 1e-6:
        return f"{segno}{abs_seconds * 1e9:.2f} ns"   # nanosecondi
    elif abs_seconds < 1e-3:
        return f"{segno}{abs_seconds * 1e6:.2f} μs"   # microsecondi
    elif abs_seconds < 1:
        return f"{segno}{abs_seconds * 1e3:.2f} ms"   # millisecondi
    # Scale umane
    elif abs_seconds < 60:
        return f"{segno}{abs_seconds:.2f} s"
    elif abs_seconds < 3600:
        return f"{segno}{abs_seconds / 60:.2f} min"
    elif abs_seconds < 86400:
        return f"{segno}{abs_seconds / 3600:.2f} ore"
    elif abs_seconds < 31557600:  # anno siderale
        return f"{segno}{abs_seconds / 86400:.2f} giorni"
    # Scale cosmiche
    elif abs_seconds < 3.15576e9:  # 100 anni
        return f"{segno}{abs_seconds / 31557600:.2f} anni"
    elif abs_seconds < 3.15576e12:  # 100,000 anni
        return f"{segno}{abs_seconds / 3.15576e7:.2f} millenni"
    elif abs_seconds < 3.15576e15:  # 100 milioni di anni
        return f"{segno}{abs_seconds / 3.15576e10:.2f} Myr"  # Milioni di anni (Megayears)
    else:
        return f"{segno}{abs_seconds / 3.15576e13:.2f} Gyr"  # Miliardi di anni (Gigayears)

def format_hubble(h_value):
    """Formatta il parametro di Hubble locale in unità leggibili con contesto fisico."""
    if abs(h_value) < 1e-50:
        return "H: ZERO (STASI METRICA)"
    
    abs_h = abs(h_value)
    segno = "↓" if h_value < 0 else "↑"
    
    # Conversione a unità cosmologiche standard (km/s/Mpc)
    # H_0 ~ 70 km/s/Mpc ~ 2.27e-18 s^-1
    h_cosmo_units = abs_h / 2.27e-18 * 70.0  # conversione a km/s/Mpc
    
    # Scale fisiche
    if abs_h < 1e-25:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (ultra-lento)"
    elif abs_h < 1e-20:
        return f"H {segno}: {h_cosmo_units:.2f} km/s/Mpc (cosmologico)"
    elif abs_h < 1e-15:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (galattico)"
    elif abs_h < 1e-10:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (stellare)"
    elif abs_h < 1e-5:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (planetario)"
    elif abs_h < 1:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (rapido)"
    else:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (esplosivo)"

def calcola_stato_temporale(h_value):
    """Determina lo stato fisico del sistema basandosi su H."""
    if abs(h_value) < 1e-43:
        return "STAZIONARIO (VUOTO QUANTISTICO)"
    elif h_value > 0:
        return "ESPANSIONE"
    elif h_value < 0:
        return "CONTRAZIONE"
    else:
        return "EQUILIBRIO"

def ricostruisci_tempo_emergente(telemetria_array):
    """Ricostruisce il tempo emergente cumulativo dai dati telemetrici.
    
    Il tempo emergente è calcolato come integrale della variazione geometrica:
    dt_emergente = sqrt(curvatura^2 + torsione^2) * delta_lambda
    
    Parametri:
    -----------
    telemetria_array : numpy structured array
        Array con campi: rm, g_geo, z_geo, h_fisica, etc.
    
    Ritorna:
    --------
    tempo_emergente_array : numpy array
        Serie temporale del tempo emergente cumulativo [secondi]
    """
    n_frames = len(telemetria_array)
    tempo_emergente = np.zeros(n_frames, dtype='f8')
    
    delta_lambda = 0.1  # Incremento parametro affine standard
    
    print("[RICOSTRUZIONE] Calcolo tempo emergente cumulativo da geometria...")
    
    for i in range(1, n_frames):
        rm = telemetria_array[i]['rm']
        g_geo = telemetria_array[i]['g_geo']
        z_geo = telemetria_array[i]['z_geo']
        
        if rm > 0:
            # Estrazione approssimativa di curvatura e torsione dai dati salvati
            # Curvatura scalare ~ G_geometrica * rm^2
            curvatura_scalare = np.abs(g_geo) * (rm**2)
            
            # Torsione ~ sqrt(Z_geometrica) / rm
            torsione = np.sqrt(np.abs(z_geo)) / (rm + 1e-12)
            
            # Incremento temporale emergente
            dt_emergente = np.sqrt(curvatura_scalare**2 + torsione**2) * delta_lambda
            tempo_emergente[i] = tempo_emergente[i-1] + dt_emergente
        else:
            # Frame vuoto, mantieni valore precedente
            tempo_emergente[i] = tempo_emergente[i-1]
    
    print(f"[RICOSTRUZIONE] ✓ Tempo emergente: {tempo_emergente[0]:.3e} → {tempo_emergente[-1]:.3e} s")
    return tempo_emergente

def calcola_tempo_fisico_calibrato(tempo_assoluto_array, esponente_array):
    """Calcola il tempo fisico in secondi calibrato sulla scala metrica.
    
    T_fisico = T_adimensionale × (L / c)
    dove L = 10^esponente metri
    """
    c_luce = 299792458.0  # m/s
    scala_metri = 10.0 ** esponente_array
    tempo_caratteristico = scala_metri / c_luce
    
    return tempo_assoluto_array * tempo_caratteristico

# --- PROCESSING PRINCIPALE ---
def main():
    print(f"\n{'='*70}")
    print(f"  ANALISI POST-SIMULAZIONE WQT MANIFOLD")
    print(f"  Generazione pannello scientifico da dati HDF5")
    print(f"{'='*70}\n")
    
    # Verifica esistenza file di input
    import os
    if not os.path.exists(args.input):
        print(f"[ERRORE] File di input non trovato: {args.input}")
        sys.exit(1)
    
    # Verifica sovrascrittura file output
    if os.path.exists(args.output) and not args.overwrite:
        print(f"[ERRORE] File di output già esistente: {args.output}")
        print(f"         Usa --overwrite per sovrascrivere")
        sys.exit(1)
    
    print(f"[INPUT]  Lettura da: {args.input}")
    print(f"[OUTPUT] Scrittura in: {args.output}\n")
    
    # Apertura file input in lettura
    with h5py.File(args.input, 'r', libver='latest') as f_input:
        print("[LETTURA] Caricamento telemetria scalare...")
        
        # Verifica presenza dataset
        if 'telemetria_scalare' not in f_input:
            print("[ERRORE] Dataset 'telemetria_scalare' non trovato nel file HDF5")
            sys.exit(1)
        
        # Lettura dati grezzi
        telemetria = f_input['telemetria_scalare'][:]
        n_frames_totali = f_input['telemetria_scalare'].shape[0]
        
        # Trova ultimo frame valido (rm > 0)
        valid_mask = telemetria['rm'] > 0
        n_frames_validi = np.sum(valid_mask)
        
        print(f"[LETTURA] Frame totali: {n_frames_totali}")
        print(f"[LETTURA] Frame validi: {n_frames_validi}")
        
        if n_frames_validi == 0:
            print("[ERRORE] Nessun frame valido trovato nel file")
            sys.exit(1)
        
        # Estrazione dati validi
        telemetria_valida = telemetria[valid_mask]
        
        print(f"[LETTURA] Range esponente metrico: {telemetria_valida['esponente'].min():.2f} → {telemetria_valida['esponente'].max():.2f}")
        print(f"[LETTURA] Range H_fisica: {telemetria_valida['h_fisica'].min():.3e} → {telemetria_valida['h_fisica'].max():.3e}\n")
        
        # --- CALCOLI DERIVATI ---
        print("[PROCESSING] Calcolo dataset derivati...\n")
        
        # 1. Ricostruzione tempo emergente cumulativo
        tempo_emergente = ricostruisci_tempo_emergente(telemetria_valida)
        
        # 2. Calcolo tempo fisico calibrato
        tempo_fisico = calcola_tempo_fisico_calibrato(
            telemetria_valida['tempo_assol'], 
            telemetria_valida['esponente']
        )
        
        print(f"[PROCESSING] Tempo fisico calibrato: {tempo_fisico[0]:.3e} → {tempo_fisico[-1]:.3e} s\n")
        
        # 3. Formattazione stringhe leggibili
        print("[FORMATTING] Generazione stringhe human-readable...")
        tempo_emergente_str = [format_human_time(t) for t in tempo_emergente]
        tempo_fisico_str = [format_human_time(t) for t in tempo_fisico]
        hubble_str = [format_hubble(h) for h in telemetria_valida['h_fisica']]
        stato_str = [calcola_stato_temporale(h) for h in telemetria_valida['h_fisica']]
        
        print(f"[FORMATTING] ✓ Generati {len(tempo_emergente_str)} record formattati\n")
        
        # --- SCRITTURA FILE OUTPUT ---
        print(f"[SCRITTURA] Creazione file esteso: {args.output}")
        
        with h5py.File(args.output, 'w', libver='latest') as f_output:
            # Copia attributi globali
            f_output.attrs['creato_da'] = 'analisi_post_simulazione.py'
            f_output.attrs['data_elaborazione'] = datetime.now().isoformat()
            f_output.attrs['file_sorgente'] = args.input
            f_output.attrs['n_frames_validi'] = n_frames_validi
            
            # Copia metadati originali se presenti
            for attr_name in f_input.attrs:
                f_output.attrs[f'originale_{attr_name}'] = f_input.attrs[attr_name]
            
            # Dataset originali (copia integrale)
            print("[SCRITTURA] Copia telemetria originale...")
            f_output.create_dataset('telemetria_scalare_originale', data=telemetria_valida, 
                                   compression='lzf', chunks=(min(2048, n_frames_validi),))
            
            # Dataset derivati (solo dati validi)
            print("[SCRITTURA] Creazione dataset derivati...")
            
            f_output.create_dataset('tempo_emergente_cumulativo', data=tempo_emergente, 
                                   dtype='f8', compression='lzf',
                                   chunks=(min(2048, n_frames_validi),))
            f_output['tempo_emergente_cumulativo'].attrs['unita'] = 'secondi'
            f_output['tempo_emergente_cumulativo'].attrs['descrizione'] = 'Tempo proprio emergente integrato da curvatura e torsione'
            
            f_output.create_dataset('tempo_fisico_calibrato', data=tempo_fisico, 
                                   dtype='f8', compression='lzf',
                                   chunks=(min(2048, n_frames_validi),))
            f_output['tempo_fisico_calibrato'].attrs['unita'] = 'secondi'
            f_output['tempo_fisico_calibrato'].attrs['descrizione'] = 'Tempo cosmologico calibrato sulla scala metrica (T = L/c)'
            
            # Dataset formattati (stringhe human-readable)
            print("[SCRITTURA] Creazione dataset formattati...")
            
            # Uso h5py.string_dtype per UTF-8 con caratteri speciali (μ, frecce, ecc.)
            str_dtype = h5py.string_dtype(encoding='utf-8', length=None)  # Variable-length UTF-8
            
            f_output.create_dataset('tempo_emergente_formattato', data=tempo_emergente_str, 
                                   dtype=str_dtype, compression='lzf')
            f_output['tempo_emergente_formattato'].attrs['descrizione'] = 'Tempo emergente in formato leggibile umano'
            
            f_output.create_dataset('tempo_fisico_formattato', data=tempo_fisico_str, 
                                   dtype=str_dtype, compression='lzf')
            f_output['tempo_fisico_formattato'].attrs['descrizione'] = 'Tempo fisico in formato leggibile umano'
            
            f_output.create_dataset('hubble_formattato', data=hubble_str, 
                                   dtype=str_dtype, compression='lzf')
            f_output['hubble_formattato'].attrs['descrizione'] = 'Parametro di Hubble in unità cosmologiche standard'
            
            f_output.create_dataset('stato_temporale', data=stato_str, 
                                   dtype=str_dtype, compression='lzf')
            f_output['stato_temporale'].attrs['descrizione'] = 'Stato del sistema: Espansione/Contrazione/Stazionario'
            
            # Serie temporali analitiche aggiuntive
            print("[SCRITTURA] Calcolo serie temporali analitiche...")
            
            # Conversione Hubble in km/s/Mpc
            hubble_cosmo = telemetria_valida['h_fisica'] / 2.27e-18 * 70.0
            f_output.create_dataset('hubble_km_s_mpc', data=hubble_cosmo, 
                                   dtype='f8', compression='lzf',
                                   chunks=(min(2048, n_frames_validi),))
            f_output['hubble_km_s_mpc'].attrs['unita'] = 'km/s/Mpc'
            f_output['hubble_km_s_mpc'].attrs['descrizione'] = 'Parametro di Hubble in unità cosmologiche standard'
            
            # Età apparente dell'universo simulato (1/H) dove H > 0
            eta_apparente = np.zeros_like(telemetria_valida['h_fisica'])
            mask_positivo = telemetria_valida['h_fisica'] > 1e-43
            eta_apparente[mask_positivo] = 1.0 / telemetria_valida['h_fisica'][mask_positivo]
            
            f_output.create_dataset('eta_apparente_universo', data=eta_apparente, 
                                   dtype='f8', compression='lzf',
                                   chunks=(min(2048, n_frames_validi),))
            f_output['eta_apparente_universo'].attrs['unita'] = 'secondi'
            f_output['eta_apparente_universo'].attrs['descrizione'] = 'Età apparente = 1/H (tempo di Hubble)'
            
            print(f"[SCRITTURA] ✓ File esteso creato con successo\n")
    
    # --- STATISTICHE FINALI ---
    print(f"{'='*70}")
    print(f"  STATISTICHE DATASET ESTESO")
    print(f"{'='*70}")
    print(f"  Frame processati:        {n_frames_validi}")
    print(f"  Tempo emergente finale:  {format_human_time(tempo_emergente[-1])}")
    print(f"  Tempo fisico finale:     {format_human_time(tempo_fisico[-1])}")
    print(f"  Hubble medio:            {format_hubble(np.mean(telemetria_valida['h_fisica']))}")
    print(f"  Stato dominante:         {calcola_stato_temporale(np.median(telemetria_valida['h_fisica']))}")
    print(f"{'='*70}\n")
    
    print(f"[COMPLETATO] File di output salvato: {args.output}")
    print(f"[COMPLETATO] ✓ Post-processing completato con successo\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERROTTO] Elaborazione interrotta dall'utente")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERRORE CRITICO] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
