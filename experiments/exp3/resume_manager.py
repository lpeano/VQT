"""
ResumeManager — persistenza robusta per run di simulazione lunghi.

Gestisce tre file ruotanti per garantire il recovery anche in caso di crash
durante la scrittura:

  resume.json       <- stato completo piu' recente (golden copy)
  resume.json.tmp   <- scrittura in corso (atomica via os.replace)
  resume.json.bak   <- penultimo stato completo (fallback se main e' corrotto)

Sequenza di salvataggio (atomica a due livelli):
  1. Scrivi tutto su .tmp
  2. Copia main -> .bak  (preserva il penultimo stato)
  3. os.replace(.tmp, main)  (atomico sul filesystem: o riesce o rimane .tmp)

Sequenza di caricamento con recovery:
  1. Prova main  -> valida entry per entry -> usa se ok
  2. Prova .tmp  -> idem (crash dopo scrittura ma prima di replace)
  3. Prova .bak  -> idem (crash durante il copy main->bak)
  4. Start fresh -> log di quante entry sono andate perse

Ogni entry viene validata individualmente: le entry corrotte vengono scartate
(non invalidano l'intero file). I seed scartati vengono rieseguiti.

USO:
  from resume_manager import ResumeManager

  rm = ResumeManager("experiments/exp3/resume/mytest_L3.json")

  for seed in seeds:
      if rm.has(seed):
          result = rm.get(seed)
          # usa result["mtot"], result["neff_dict"]
          continue
      # ... esegui il calcolo ...
      rm.save(seed, mtot=h["M_tot"], neff_dict=neff_dict)

  # a fine run: archivia il file di ripresa
  rm.archive()
"""

import os
import json
import shutil
import datetime
import math
import numpy as np


class ResumeManager:
    """Gestisce la persistenza robusta dei risultati con recovery a due livelli."""

    REQUIRED_KEYS = {"mtot", "neff_dict"}

    def __init__(self, path: str, verbose: bool = True):
        self.path = path
        self.bak = path + ".bak"
        self.tmp = path + ".tmp"
        self.verbose = verbose
        self.data: dict = {}
        self._n_recovered = 0
        self._n_discarded = 0
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._load()

    # ------------------------------------------------------------------
    # Interfaccia pubblica
    # ------------------------------------------------------------------

    def has(self, seed: int) -> bool:
        """True se il seed e' gia' stato completato e l'entry e' valida."""
        return str(seed) in self.data

    def get(self, seed: int) -> dict:
        """Ritorna l'entry del seed (dict con mtot e neff_dict)."""
        return self.data[str(seed)]

    def save(self, seed: int, mtot: float, neff_dict: dict,
             chi_profile: list | None = None) -> None:
        """
        Salva atomicamente il risultato del seed.

        chi_profile: se fornito (lista di float), viene salvato nel file di
        ripresa. Permette di ricostruire lo stato fisico congelato a L per
        usarlo come sotto-blocco nella costruzione del livello L+1.
        Dimensione indicativa: ~13824 float per L3 (~110 KB nel JSON).
        """
        entry = {
            "mtot": float(mtot),
            "neff_dict": {
                str(d): {
                    "n_eff": float(v["n_eff"]) if "n_eff" in v else float("nan"),
                    "n_blocks": int(v["n_blocks"]) if "n_blocks" in v else 0,
                }
                for d, v in neff_dict.items()
                if isinstance(v, dict)
            },
        }
        # Il profilo chi NON va nel JSON (troppo voluminoso a L3+).
        # Viene salvato come file numpy float32 separato: ~54 KB per L3
        # (vs ~250 KB nel JSON in float64). Percorso: resume/<stem>_chi_<seed>.npy
        if chi_profile is not None:
            chi_path = self._chi_path(seed)
            arr = np.array(chi_profile, dtype=np.float32)
            np.save(chi_path + ".tmp", arr)
            if os.path.exists(chi_path):
                shutil.copy2(chi_path, chi_path + ".bak")
            os.replace(chi_path + ".tmp", chi_path)
            entry["has_chi"] = True  # flag nel JSON: "il .npy esiste"
        self.data[str(seed)] = entry
        self._atomic_write()

    def _chi_path(self, seed: int) -> str:
        """Percorso del file .npy del profilo chi per il seed dato."""
        stem = os.path.splitext(self.path)[0]
        return f"{stem}_chi_{seed}.npy"

    def has_chi_profile(self, seed: int) -> bool:
        """True se il profilo chi e' disponibile su disco per questo seed."""
        return (self.has(seed)
                and self.data[str(seed)].get("has_chi", False)
                and os.path.exists(self._chi_path(seed)))

    def get_chi_profile(self, seed: int) -> np.ndarray:
        """Carica e ritorna il profilo chi dal file .npy (float32)."""
        path = self._chi_path(seed)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Profilo chi non trovato: {path}")
        return np.load(path)  # float32, shape (N_leaves,)

    def archive(self) -> str:
        """Archivia il file di ripresa con timestamp (chiamare a fine run)."""
        if not os.path.exists(self.path):
            return ""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.path.replace(".json", f"_done_{ts}.json")
        shutil.move(self.path, archive_path)
        # pulisce tmp e bak
        for f in (self.tmp, self.bak):
            try:
                os.remove(f)
            except FileNotFoundError:
                pass
        if self.verbose:
            print(f"  [resume] archiviato: {archive_path}")
        return archive_path

    @property
    def n_completed(self) -> int:
        return len(self.data)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_entry(self, entry) -> bool:
        """Verifica che un'entry abbia tutti i campi richiesti e valori finiti."""
        if not isinstance(entry, dict):
            return False
        if not self.REQUIRED_KEYS.issubset(entry.keys()):
            return False
        mtot = entry.get("mtot")
        if not isinstance(mtot, (int, float)) or not math.isfinite(float(mtot)):
            return False
        neff = entry.get("neff_dict")
        if not isinstance(neff, dict):
            return False
        for depth_val in neff.values():
            if not isinstance(depth_val, dict):
                return False
            if "n_eff" not in depth_val or "n_blocks" not in depth_val:
                return False
        return True

    def _try_load_file(self, path: str) -> dict | None:
        """
        Tenta di caricare e validare un file JSON.
        Ritorna il dict delle entry valide, o None se il file non e' leggibile.
        Scarta silenziosamente le entry corrotte (non invalida l'intero file).
        """
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, IOError, ValueError, UnicodeDecodeError) as e:
            if self.verbose:
                print(f"  [resume] file non leggibile ({type(e).__name__}: {e}): {path}")
            return None

        if not isinstance(raw, dict):
            if self.verbose:
                print(f"  [resume] struttura inattesa (non e' un dict): {path}")
            return None

        valid = {}
        corrupt = []
        for key, val in raw.items():
            if self._validate_entry(val):
                valid[key] = val
            else:
                corrupt.append(key)

        if corrupt and self.verbose:
            print(f"  [resume] {len(corrupt)} entry corrotte scartate "
                  f"(seed {corrupt[:5]}{'...' if len(corrupt)>5 else ''}): {path}")
        self._n_discarded += len(corrupt)
        return valid

    def _load(self) -> None:
        """
        Carica con fallback a tre livelli: main -> tmp -> bak -> vuoto.
        Logga il percorso usato e quante entry sono state recuperate.
        """
        candidates = [
            (self.path, "principale"),
            (self.tmp,  "tmp (crash durante rename)"),
            (self.bak,  "backup (crash durante copia)"),
        ]
        for path, label in candidates:
            result = self._try_load_file(path)
            if result is not None:
                self.data = result
                self._n_recovered = len(result)
                if self._n_recovered > 0 and self.verbose:
                    print(f"  [resume] {self._n_recovered} seed caricati "
                          f"da {label}")
                return

        # nessun file valido trovato
        self.data = {}
        if self.verbose:
            print("  [resume] nessun file di ripresa trovato — partenza da zero")

    def _atomic_write(self) -> None:
        """
        Scrittura a due livelli:
          1. Serializza su .tmp
          2. Ruota: main -> .bak (copia, non move, per safety)
          3. os.replace(.tmp -> main)  — atomico sul filesystem
        """
        # 1. scrivi su tmp
        try:
            with open(self.tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            if self.verbose:
                print(f"  [resume] WARN: scrittura .tmp fallita ({e}) — "
                      f"risultato del seed NON persistito")
            return

        # 2. ruota main -> bak (se main esiste)
        if os.path.exists(self.path):
            try:
                shutil.copy2(self.path, self.bak)
            except IOError:
                pass  # se la copia bak fallisce non e' fatale

        # 3. rinomina atomicamente tmp -> main
        try:
            os.replace(self.tmp, self.path)
        except IOError as e:
            if self.verbose:
                print(f"  [resume] WARN: rename .tmp -> main fallito ({e}) — "
                      f"dati in .tmp, recovery al prossimo avvio")
