# wqt_oop/reference/ — moduli di RIFERIMENTO (non in produzione)

Moduli **non importati** dal motore: tenuti come riferimento per **task pendenti**, NON
cancellati (la fisica che contengono serve ai prossimi passi).

| File | Cos'e' | Pendente collegato |
|---|---|---|
| `dinamica_hamiltoniana_chiralita_RECUPERATO.py` | Motore chirale ORIGINALE recuperato da git (5afefb9), cancellato nel cleanup a5b417e. Trasporto di densita' SX/DX con **inversione/attrazione sopra 720** (`max(0, K2-4pi)`), porosita' (disaccoppiamento exp). | **Bounce vero** (overshoot oltre rho* + rovesciamento) e **flip di chiralita'** al bounce. La sua "inversione sopra 720" e' il riferimento. |
| `chiralita_ec.py` | Trasporto di densita' chirale adattato al motore (K2 dal gradiente, soglia rho* derivata). Superato dal motore spinoriale (`motore_chirale_spinoriale.py`) per la dinamica, ma utile per il **trasporto di densita'**. | Migrazione/aggregazione della materia (collasso dinamico). |

Il motore di produzione e' `wqt_oop/motore_chirale_spinoriale.py` (spinore: beta/alpha=
pendenza, 180/720, torsione dallo spin). Questi file NON vanno importati dal codice attivo.
