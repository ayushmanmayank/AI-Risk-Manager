"""Extracts the checked-in data snapshot on first startup.

WHY THIS EXISTS: data/processed/*.csv are gitignored -- see .gitignore --
because the full raw datasets are too large/licensed to commit (see
scripts/setup_datasets.py). But the two processed files api/main.py's
startup lifespan actually reads at runtime (features.csv, return_features.csv)
are small enough gzip-compressed (71MB and <1MB) to check in directly as
data/processed/*.csv.gz. That means a fresh clone can run the API with NO
setup step at all -- no Kaggle account, no script -- which matters for
anyone (e.g. judges) who just wants to start the app, not rebuild the
pipeline from raw sources.

This only extracts what's missing; a real local rebuild
(scripts/setup_datasets.py, or manually re-running the build_features
scripts) always produces the plain .csv, which is what every reader
already looks for, so the freshly-built data always wins -- the bundled
snapshot is a fallback, never an override.
"""

from __future__ import annotations

import gzip
import logging
import shutil
from pathlib import Path

logger = logging.getLogger("fraud_api")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# (plain CSV every reader expects, bundled gzip snapshot committed to git)
_BUNDLED_SNAPSHOTS = (
    (PROCESSED_DIR / "features.csv", PROCESSED_DIR / "features.csv.gz"),
    (PROCESSED_DIR / "return_features.csv", PROCESSED_DIR / "return_features.csv.gz"),
)


def ensure_bundled_data_extracted() -> None:
    for csv_path, gz_path in _BUNDLED_SNAPSHOTS:
        if csv_path.exists():
            continue
        if not gz_path.exists():
            continue  # Missing entirely -- the reader that needs it will raise its own clear error.
        logger.info("extracting bundled data snapshot %s -> %s", gz_path.name, csv_path.name)
        with gzip.open(gz_path, "rb") as f_in, open(csv_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
