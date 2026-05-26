# run_manifold_sim.py (VERSIONE VERIFICATA)
import time
import numpy as np
from WQT_manifold_refactored import SolitonManifold
from renderer import VQTRenderer
from video_exporter import VideoExporter
from persistence import HDF5Logger

def main():
    # 1. Setup componenti
    manifold = SolitonManifold(planck_length=1.616e-35, chiralità=1)
    logger = HDF5Logger("vqt_data.h5")
    renderer = VQTRenderer()
    exporter = VideoExporter(fps=30)

    print("Inizio simulazione VQT endless...")
    
    iteration = 0
    try:
        while True:
            # 2. Evoluzione (Assicurati che congiungi() ritorni un np.array o dict)
            state = manifold.congiungi()
            
            # 3. Persistenza: scrittura su HDF5
            logger.save_state(iteration, state)
            
            # 4. Rendering: trasformazione stato in frame
            frame = renderer.render(state)
            exporter.add_frame(frame)
            
            iteration += 1
            # Controllo di flusso opzionale per non saturare la CPU
            time.sleep(0.001)
            
    except KeyboardInterrupt:
        print("\nFinalizzazione in corso...")
        exporter.save_as_mpeg("simulazione_vqt.mpg")
        print("Simulazione salvata.")

if __name__ == "__main__":
    main()