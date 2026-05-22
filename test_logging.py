"""
Script di test per il sistema di logging eventi WQT
Simula eventi critici per verificare il funzionamento del diario di bordo
"""
import sys
sys.path.insert(0, '.')

# Importa le funzioni dal modulo principale
from datetime import datetime

def format_human_time(seconds):
    """Converte il tempo emergente in formato leggibile umano."""
    if seconds == 0:
        return "0 s"
    
    abs_seconds = abs(seconds)
    segno = "⏪ " if seconds < 0 else ""
    
    if abs_seconds < 1e-15:
        return f"{segno}{abs_seconds * 1e18:.2f} as"
    elif abs_seconds < 1e-12:
        return f"{segno}{abs_seconds * 1e15:.2f} fs"
    elif abs_seconds < 1e-9:
        return f"{segno}{abs_seconds * 1e12:.2f} ps"
    elif abs_seconds < 1e-6:
        return f"{segno}{abs_seconds * 1e9:.2f} ns"
    elif abs_seconds < 1e-3:
        return f"{segno}{abs_seconds * 1e6:.2f} μs"
    elif abs_seconds < 1:
        return f"{segno}{abs_seconds * 1e3:.2f} ms"
    elif abs_seconds < 60:
        return f"{segno}{abs_seconds:.2f} s"
    elif abs_seconds < 3600:
        return f"{segno}{abs_seconds / 60:.2f} min"
    elif abs_seconds < 86400:
        return f"{segno}{abs_seconds / 3600:.2f} ore"
    elif abs_seconds < 31557600:
        return f"{segno}{abs_seconds / 86400:.2f} giorni"
    elif abs_seconds < 3.15576e9:
        return f"{segno}{abs_seconds / 31557600:.2f} anni"
    else:
        return f"{segno}{abs_seconds / 3.15576e13:.2f} Gyr"

def format_hubble(h_value):
    """Formatta il parametro di Hubble."""
    if abs(h_value) < 1e-50:
        return "H: ZERO (STASI METRICA)"
    
    abs_h = abs(h_value)
    segno = "↓" if h_value < 0 else "↑"
    h_cosmo_units = abs_h / 2.27e-18 * 70.0
    
    if abs_h < 1e-25:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (ultra-lento)"
    elif abs_h < 1e-20:
        return f"H {segno}: {h_cosmo_units:.2f} km/s/Mpc (cosmologico)"
    else:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (rapido)"

def log_evento_visivo(tipo_evento, descrizione, tempo_emergente, metrica_exp, hubble_value):
    """Registra eventi scientifici nel diario di bordo."""
    log_file = 'osservazioni_simulazione.log'
    timestamp_reale = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tempo_formattato = format_human_time(tempo_emergente)
    hubble_formattato = format_hubble(hubble_value)
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"="*80 + "\n")
        f.write(f"[{timestamp_reale}] EVENTO: {tipo_evento}\n")
        f.write(f"Descrizione: {descrizione}\n")
        f.write(f"Tempo Emergente: {tempo_formattato} ({tempo_emergente:.6e} s)\n")
        f.write(f"Scala Metrica: 10^({metrica_exp:.2f}) m\n")
        f.write(f"Parametro di Hubble: {hubble_formattato} ({hubble_value:.6e} s⁻¹)\n")
        f.write(f"="*80 + "\n\n")

# === TEST EVENTI ===
print("\n=== TEST SISTEMA DI LOGGING EVENTI WQT ===\n")

# Test 1: Inversione temporale
print("Test 1: Simulazione INVERSIONE TEMPORALE...")
log_evento_visivo(
    "INVERSIONE_TEMPORALE",
    "Il parametro di Hubble è diventato negativo. Il manifold è in fase di contrazione retrocausale.",
    tempo_emergente=1.234e-9,  # 1.23 ns
    metrica_exp=-32.5,
    hubble_value=-5.67e-15
)
print("  ✓ Evento loggato: INVERSIONE_TEMPORALE")

# Test 2: Vuoto quantistico
print("Test 2: Simulazione VUOTO QUANTISTICO...")
log_evento_visivo(
    "VUOTO_QUANTISTICO",
    "Il parametro di Hubble è sceso sotto la scala di Planck (H < 1e-43 s⁻¹). Il tempo geometrico è effettivamente congelato.",
    tempo_emergente=4.567e-12,  # 4.56 ps
    metrica_exp=-35.2,
    hubble_value=8.9e-44
)
print("  ✓ Evento loggato: VUOTO_QUANTISTICO")

# Test 3: Transizione di fase
print("Test 3: Simulazione TRANSIZIONE DI FASE...")
log_evento_visivo(
    "TRANSIZIONE_FASE",
    "Attraversamento della scala di Grande Unificazione (GUT). Possibile cambio di regime fisico.",
    tempo_emergente=7.89e-6,  # 7.89 μs
    metrica_exp=-30.1,
    hubble_value=2.34e-10
)
print("  ✓ Evento loggato: TRANSIZIONE_FASE")

print("\n=== TEST COMPLETATO ===")
print(f"File generato: osservazioni_simulazione.log")
print("\nVisualizza con: Get-Content osservazioni_simulazione.log\n")
