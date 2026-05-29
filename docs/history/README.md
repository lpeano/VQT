# Documentazione Storica VQT

Questa cartella conserva documenti che descrivono **modelli o codice superati**
dall'attuale motore `wqt_oop/` (+ estensione Peano-VQT). Sono mantenuti per
tracciabilità dell'evoluzione della ricerca.

> ⚠️ **Nessuno di questi documenti descrive il codice corrente.** Per lo stato
> dell'arte vedere `docs/VQT_MANIFESTO_TEORICO.md` e `docs/TOPOLOGICAL_DYNAMICS.md`.

---

## Cosa è stato superato e da cosa

| Documento | Modello descritto | Superato da |
|---|---|---|
| `TEORIA_FISICA_COMPLETA.md` | χ come "potenziale di scala", saturazione `χ_sat=150·tanh(χ/150)`, forza di richiamo armonica `F=−ω·χ` | Potenziale di **doppio pozzo** `V(χ)=β(χ²−χ₀²)²` con χ₀=50 (vedi `physics_context.py`, `segmento_quantistico.py`) |
| `ARCHITETTURA_24_CAMPI_LOCALI.md` | Proposta di transizione da scalare globale a 24 campi locali | **Già implementata** in `solitone_composito.py` (24 `SegmentoQuantistico`) |
| `SISTEMA_TERMODINAMICO_APERTO.md` | Coupling via diffusione laplaciana `F_i=α(χᵢ₊₁−2χᵢ+χᵢ₋₁)` | Coupling **Yukawa pair-wise** `W_ij·(χᵢ−χⱼ)` con `W_ij=exp(−d_ij/L_eff)` (vedi `sparse_coupling.py`) |
| `RISULTATI_VALIDAZIONE_BOUNCE.md` | Validazione bounce su `WQT_manifold.py` v2.0 | Motore monolitico sostituito dal pacchetto OOP `wqt_oop/` |
| `RENDERING_DINAMICO_TECNICO.md` | Rendering con metrica esponenziale `rm∝e^(χκ)`, χ→±∞ (modello cosmologico) | Modello χ confinato a ±χ₀ (doppio pozzo); rendering attuale in `FIELD_GEOMETRY_RENDERING.md` |
| `VELOCITA_LUCE_LOCALE.md` | `c_locale=c/n_geo`, `n_geo=1+α·ρ_SX/ρ_tot` con split chiralità SX/DX | Formula presente **solo** in `WQT_manifold.py` (monolite); il codice corrente usa screening Fermi-Dirac destro/sinistro |

---

## Perché conservarli

1. **Tracciabilità**: documentano le ipotesi fisiche testate e scartate.
2. **Contesto storico**: il modello χ-potenziale-di-scala e il bounce quantistico
   sono le fondamenta concettuali da cui è emerso il modello a doppio pozzo.
3. **Riferimento per `WQT_manifold.py`**: il vecchio monolite esiste ancora nel
   repository; questi documenti ne descrivono la fisica.

*Spostati in history/ il 2026-05-29 durante la riorganizzazione dell'archivio scientifico.*
