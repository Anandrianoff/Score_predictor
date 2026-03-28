"""
Ensure repo layout imports work without a prior `pip install -e .`.

Call `ensure_project_import_paths()` at the top of entrypoints (bot, workers, API).
"""

from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    """Repository root (parent of `src/`)."""
    return Path(__file__).resolve().parents[2]


def ensure_project_import_paths() -> Path:
    """
    Prepend paths so these imports work:
    - `from score_predictor...`
    - `import DataManager` (module DataManager/DataManager.py)
    - `from Utils import utils`
    - `ludobot.app` modules on path as flat imports
    - `ThresholdRFClassifier` from ML Core
    """
    root = repo_root()
    to_add = [
        root / "src",
        root,
        root / "DataManager",
        root / "Utils",
        root / "ludobot",
        root / "ludobot" / "app",
        root / "ML Core",
        root / "API core",
    ]
    for p in to_add:
        s = str(p.resolve())
        if s not in sys.path:
            sys.path.insert(0, s)
    return root
