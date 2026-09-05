"""One-command dataset setup: takes a fresh clone to a state where the API
can actually start.

WHY THIS EXISTS: neither dataset is committed (both are gitignored -- see
.gitignore and README's Dataset setup for why: 150MB+ raw files, one of
them licensed behind a Kaggle account), but BOTH are read during FastAPI's
startup lifespan (api/main.py). A clone with no data doesn't degrade
gracefully, it exits before binding the port. That made first-run setup a
multi-step manual sequence -- download, unzip, convert two Excel sheets,
run two builders -- every step of which had to be transcribed correctly
from the README. This script is that sequence, executed rather than
described.

THE ONE THING THIS CANNOT DO FOR YOU: `creditcard.csv` requires a free
Kaggle account, so it cannot be fetched unattended without your API token.
That single manual download is checked FIRST, before the 45MB UCI download
below, so a missing file fails in under a second instead of after a long
wait for a step that was always going to fail.

WHAT IT DOES, in order:

  1. Verify data/raw/creditcard.csv is present (manual prerequisite --
     see above). Fail immediately and actionably if not.
  2. Build data/processed/features.csv via src/features/build_features.py.
  3. Ensure data/raw/online_retail_ii.csv exists -- downloading UCI's
     Online Retail II zip and concatenating its two sheets if not. Unlike
     the Kaggle dataset, this one needs no account, so it IS fully
     automatable. Intermediates (zip, xlsx) go to a temp dir and are
     deleted; only the CSV the builder actually reads is kept, so this
     leaves no untracked clutter in data/raw/.
  4. Build data/processed/return_features.csv (+ the product-level table)
     via src/features/build_return_features.py.
  5. Verify -- not assume -- that all four files now exist, and say so.

IDEMPOTENT: every build step is skipped if its output is already present,
so re-running after a partial failure resumes rather than redoing ~10
minutes of work. Pass --force to rebuild everything from scratch anyway.

This script never writes to models/ -- the two committed .pkl models are
read-only inputs here, exactly as they are everywhere else in this project.

Usage:
    python scripts/setup_data.py
    python scripts/setup_data.py --force
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from src.features import build_features, build_return_features  # noqa: E402

CREDITCARD_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"
RETAIL_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "online_retail_ii.csv"
RETURN_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "return_features.csv"
RETURN_PRODUCTS_PATH = PROJECT_ROOT / "data" / "processed" / "return_features_products.csv"

KAGGLE_DATASET_URL = "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud"
RETAIL_ZIP_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
# The two sheets inside online_retail_II.xlsx. Named explicitly rather than
# read with sheet_name=None: if UCI ever reshapes the workbook, a missing
# sheet should be a loud KeyError naming the sheet, not a silent partial
# dataset that trains a quietly worse model.
RETAIL_SHEETS = ("Year 2009-2010", "Year 2010-2011")


def _missing_kaggle_dataset_message() -> str:
    return (
        f"\nERROR: required dataset not found:\n"
        f"  {CREDITCARD_PATH}\n\n"
        f"This is the one file this script cannot download for you: Kaggle\n"
        f"requires a (free) account, so it needs your credentials.\n\n"
        f"To fix:\n"
        f"  1. Download creditcard.csv from:\n"
        f"     {KAGGLE_DATASET_URL}\n"
        f"  2. Place it at exactly (the filename matters):\n"
        f"     {CREDITCARD_PATH}\n"
        f"  3. Re-run: python scripts/setup_data.py\n"
    )


def ensure_creditcard_present() -> None:
    """Hard prerequisite check, deliberately run before any slow work."""
    if not CREDITCARD_PATH.exists():
        print(_missing_kaggle_dataset_message(), file=sys.stderr)
        raise SystemExit(1)
    print(f"[1/4] Found Kaggle dataset: {CREDITCARD_PATH.name}")


def build_fraud_features(force: bool) -> None:
    if FEATURES_PATH.exists() and not force:
        print("[2/4] features.csv already present -- skipping (use --force to rebuild)")
        return
    print("[2/4] Building features.csv (this reads ~150MB and takes a minute)...")
    build_features.main()


def download_retail_dataset() -> None:
    """Fetch UCI Online Retail II and flatten both sheets into one CSV.

    Intermediates live in a temp dir that is removed on the way out --
    data/raw/ only ever gains the .csv the builder reads. That matters
    because .gitignore excludes data/raw/*.csv but NOT *.zip or *.xlsx: a
    leftover 45MB workbook would show up as untracked in every subsequent
    `git status`.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        zip_path = tmp_dir / "online_retail_ii.zip"

        print(f"      Downloading {RETAIL_ZIP_URL} (~45MB, no account needed)...")
        with urllib.request.urlopen(RETAIL_ZIP_URL) as response, open(zip_path, "wb") as out:
            shutil.copyfileobj(response, out)

        print("      Extracting...")
        with zipfile.ZipFile(zip_path) as archive:
            xlsx_names = [n for n in archive.namelist() if n.lower().endswith(".xlsx")]
            if not xlsx_names:
                raise RuntimeError(
                    f"No .xlsx found inside {RETAIL_ZIP_URL} -- archive contents: "
                    f"{archive.namelist()}"
                )
            archive.extract(xlsx_names[0], tmp_dir)
            xlsx_path = tmp_dir / xlsx_names[0]

        print("      Converting both sheets to CSV (slow -- Excel parsing, ~1M rows)...")
        frame = pd.concat(
            [pd.read_excel(xlsx_path, sheet_name=sheet) for sheet in RETAIL_SHEETS],
            ignore_index=True,
        )
        RETAIL_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(RETAIL_RAW_PATH, index=False)
        print(f"      Wrote {len(frame):,} rows to {RETAIL_RAW_PATH.name}")


def ensure_retail_raw_present(force: bool) -> None:
    if RETAIL_RAW_PATH.exists() and not force:
        print("[3/4] online_retail_ii.csv already present -- skipping download")
        return
    print("[3/4] Fetching UCI Online Retail II dataset...")
    download_retail_dataset()


def build_return_feature_table(force: bool) -> None:
    if RETURN_FEATURES_PATH.exists() and not force:
        print("[4/4] return_features.csv already present -- skipping (use --force to rebuild)")
        return
    print("[4/4] Building return_features.csv...")
    build_return_features.main()


def verify() -> None:
    """Confirm the real post-condition: every file the API's startup reads
    is on disk. Checked rather than inferred from 'no step raised'.
    """
    required = {
        "data/raw/creditcard.csv": CREDITCARD_PATH,
        "data/processed/features.csv": FEATURES_PATH,
        "data/raw/online_retail_ii.csv": RETAIL_RAW_PATH,
        "data/processed/return_features.csv": RETURN_FEATURES_PATH,
        "data/processed/return_features_products.csv": RETURN_PRODUCTS_PATH,
    }
    missing = [label for label, path in required.items() if not path.exists()]
    if missing:
        print("\nERROR: setup finished but these files are still missing:", file=sys.stderr)
        for label in missing:
            print(f"  - {label}", file=sys.stderr)
        raise SystemExit(1)

    print("\n=== Dataset setup complete ===")
    for label, path in required.items():
        print(f"  {label}  ({path.stat().st_size / 1_048_576:.1f} MB)")
    print("\nThe API can now start:")
    print("  python -m uvicorn api.main:app --reload --port 8000")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild every artifact even if it already exists.",
    )
    args = parser.parse_args()

    ensure_creditcard_present()
    build_fraud_features(args.force)
    ensure_retail_raw_present(args.force)
    build_return_feature_table(args.force)
    verify()


if __name__ == "__main__":
    main()
