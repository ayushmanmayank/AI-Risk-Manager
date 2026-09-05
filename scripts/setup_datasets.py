"""One-command dataset setup -- fetches both raw datasets this project
needs, respecting each one's actual licensing situation rather than just
making the "repo doesn't run on a fresh clone" problem go away by any
means necessary.

Two very different datasets, two very different rules:

- **UCI Online Retail II** (CC BY 4.0, no account required): downloaded
  directly from UCI's own servers. Fully automated here -- nothing to
  configure, nothing borrowed from anyone else's redistribution rights.

- **Kaggle's creditcard.csv** (requires YOUR OWN free Kaggle account):
  this script automates the DOWNLOAD step via Kaggle's own official API,
  using YOUR OWN credentials -- it does not, and cannot, bypass the
  account requirement, and this repo never bundles or redistributes the
  file itself (see the Dockerfile's own comment on why: it's a licensed
  download). If the Kaggle API isn't configured yet, this script says so
  plainly and prints the manual steps instead of failing silently or
  pretending it worked.

Idempotent: skips any dataset already present at its expected path, so
re-running this after a partial setup (e.g. Kaggle auth wasn't ready
yet) only fetches what's still missing.

Usage:  python scripts/setup_datasets.py
"""

from __future__ import annotations

import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

CREDITCARD_PATH = RAW_DIR / "creditcard.csv"
ONLINE_RETAIL_PATH = RAW_DIR / "online_retail_ii.csv"

UCI_ONLINE_RETAIL_II_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"


def setup_online_retail_ii() -> None:
    if ONLINE_RETAIL_PATH.exists():
        print(f"[online_retail_ii] already present at {ONLINE_RETAIL_PATH}, skipping.")
        return

    print("[online_retail_ii] downloading from UCI (CC BY 4.0, no account needed)...")
    zip_path = RAW_DIR / "online_retail_ii.zip"
    urllib.request.urlretrieve(UCI_ONLINE_RETAIL_II_URL, zip_path)

    print("[online_retail_ii] unzipping...")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(RAW_DIR)
    zip_path.unlink()

    xlsx_path = RAW_DIR / "online_retail_II.xlsx"
    if not xlsx_path.exists():
        sys.exit(
            f"[online_retail_ii] expected {xlsx_path} after unzipping, but it isn't there -- "
            "UCI may have changed their archive's internal layout. Check data/raw/ manually."
        )

    try:
        import openpyxl  # noqa: F401  -- only checking it's importable before pandas needs it
    except ImportError:
        sys.exit(
            "[online_retail_ii] needs 'openpyxl' to read the downloaded .xlsx -- a one-time "
            "conversion dependency, not a project requirement (see README's Dataset setup). "
            "Run: pip install openpyxl, then re-run this script."
        )

    print("[online_retail_ii] converting both sheets to a single CSV...")
    import pandas as pd

    df = pd.concat(
        [
            pd.read_excel(xlsx_path, sheet_name="Year 2009-2010"),
            pd.read_excel(xlsx_path, sheet_name="Year 2010-2011"),
        ],
        ignore_index=True,
    )
    df.to_csv(ONLINE_RETAIL_PATH, index=False)
    xlsx_path.unlink()
    print(f"[online_retail_ii] done -- wrote {ONLINE_RETAIL_PATH}")


def setup_creditcard() -> None:
    if CREDITCARD_PATH.exists():
        print(f"[creditcard] already present at {CREDITCARD_PATH}, skipping.")
        return

    print("[creditcard] this dataset requires YOUR OWN Kaggle account -- attempting an")
    print("[creditcard] automated download via the official Kaggle API...")

    try:
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", "mlg-ulb/creditcardfraud", "-p", str(RAW_DIR), "--unzip"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        result = None

    if result is None or result.returncode != 0:
        print()
        print("[creditcard] automated download not available -- either the 'kaggle' CLI isn't")
        print("[creditcard] installed, or there's no API token at ~/.kaggle/kaggle.json yet.")
        print("[creditcard] That's expected on a fresh machine; this script cannot and does not")
        print("[creditcard] bypass the account requirement. To enable it:")
        print("[creditcard]   1. pip install kaggle")
        print("[creditcard]   2. https://www.kaggle.com/settings -> API -> 'Create New Token',")
        print("[creditcard]      save the downloaded kaggle.json to ~/.kaggle/kaggle.json")
        print("[creditcard]      (chmod 600 ~/.kaggle/kaggle.json on Linux/Mac)")
        print("[creditcard]   3. Re-run this script")
        print("[creditcard] Or skip the API entirely and download it by hand:")
        print("[creditcard]   https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
        print(f"[creditcard]   -> place creditcard.csv at {CREDITCARD_PATH}")
        if result is not None and result.stderr:
            print(f"[creditcard] (kaggle CLI said: {result.stderr.strip()})")
        return

    if not CREDITCARD_PATH.exists():
        sys.exit(
            f"[creditcard] the Kaggle CLI reported success but {CREDITCARD_PATH} wasn't created -- "
            "check data/raw/ manually; Kaggle may have changed the archive's internal filename."
        )
    print(f"[creditcard] done -- wrote {CREDITCARD_PATH}")


def build_features() -> None:
    """Run the repo's own feature builders for whichever raw datasets are
    now present.

    These are the exact scripts the README documents -- invoked unchanged,
    as a subprocess, with no arguments and no reimplementation of what
    they do. Nothing here computes a feature, and nothing here touches a
    model: the builders remain the single source of truth for both, so
    the tables produced are byte-for-byte what running them by hand
    produces.

    Chained here because printing "Next: run these two commands" and
    stopping is the step people were missing -- the raw CSV lands, the
    script exits 0 looking successful, and the API then fails at startup
    on a *derived* file that setup never actually derived.
    """
    builders = (
        (CREDITCARD_PATH, PROCESSED_DIR / "features.csv", "src/features/build_features.py"),
        (ONLINE_RETAIL_PATH, PROCESSED_DIR / "return_features.csv", "src/features/build_return_features.py"),
    )

    for raw_path, built_path, script in builders:
        if not raw_path.exists():
            print(f"[build] skipping {script} -- its raw input ({raw_path.name}) isn't here yet.")
            continue
        if built_path.exists():
            print(f"[build] {built_path.name} already present, skipping {script}.")
            continue

        print(f"[build] running {script} (this takes a minute on the full dataset)...")
        result = subprocess.run([sys.executable, script], cwd=PROJECT_ROOT)
        if result.returncode != 0:
            sys.exit(f"[build] {script} failed (exit {result.returncode}) -- see its output above.")
        print(f"[build] done -- wrote {built_path}")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    setup_online_retail_ii()
    print()
    setup_creditcard()
    print()
    build_features()
    print()

    still_missing = [p.name for p in (PROCESSED_DIR / "features.csv", PROCESSED_DIR / "return_features.csv") if not p.exists()]
    if still_missing:
        print(f"Setup incomplete -- still missing: {', '.join(still_missing)}.")
        print("The API needs both before it will start; re-run this script once the")
        print("raw dataset(s) noted above are in place.")
    else:
        print("Setup complete -- both feature tables are built. The API can start:")
        print("  uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
