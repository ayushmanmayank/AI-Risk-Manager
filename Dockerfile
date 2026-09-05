# Backend: FastAPI fraud-detection API.
#
# Data (data/raw, data/processed) and the SQLite DB are deliberately NOT
# baked into this image -- see docker-compose.yml's volume mount. The raw
# Kaggle dataset is a licensed download that can't be redistributed, and
# the processed features file is 160MB+ and fully regenerable; baking
# either in would bloat the image and go stale the moment the pipeline is
# rerun. The trained model IS baked in (see models/fraud_model_v1.pkl
# below) -- it's small (~600KB) and stable, so the container is
# immediately functional without requiring a volume mount to get exactly
# right first.
FROM python:3.12-slim

WORKDIR /app

# libgomp1: XGBoost's Linux wheels are commonly built against OpenMP and
# can fail at import time on a bare slim/Debian image with
# "libgomp.so.1: cannot open shared object file" -- a well-known,
# easy-to-hit Docker+XGBoost gotcha. Installing it costs a few seconds
# and a few hundred KB; not installing it risks a container that never
# starts. (Could not verify this end-to-end in this environment -- see
# README's Docker section.)
# gosu alongside libgomp1: lets docker-entrypoint.sh drop from root to
# appuser after fixing the bind-mounted data/ directory's ownership (see
# that script's own comment) -- the standard, purpose-built tool for
# exactly this "start as root for one setup step, exec the real process
# as non-root" pattern (the same one the official postgres/mysql images
# use), rather than a hand-rolled su/setpriv invocation with its own
# signal-forwarding footguns.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 gosu \
    && rm -rf /var/lib/apt/lists/*

# Dependencies next so this layer is cached across rebuilds that only
# change application code.
COPY requirements.txt .
# pip itself upgraded first -- pip-audit flagged 3 known CVEs in the
# base image's bundled pip (PYSEC-2026-196, PYSEC-2026-3721), fixed by
# 26.1.2+. Not part of the running app's own attack surface (pip is a
# build-time tool, never imported by api/main.py), but free to fix and
# leaves nothing outdated on the record.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY src/ ./src/
COPY simulator/ ./simulator/
COPY models/ ./models/

# Created empty here; docker-compose.yml's volume mount overlays the real
# data/ directory (processed features + the persistent predictions.db)
# over this at runtime. No manual step needed before first run: the host
# repo's data/processed/*.csv.gz snapshots ride along in the bind mount,
# and api/services/data_bootstrap.py extracts them to features.csv /
# return_features.csv on first startup if they're not already there --
# see README.md's "Dataset setup" section.
RUN mkdir -p data/processed data/raw

# Dedicated non-root user, not the image default (root) -- standard
# container hardening: if the app process is ever compromised (a
# dependency RCE, an unexpected deserialization path, etc.), a non-root
# process is confined to what this one user can touch rather than
# starting from root inside the container. The uid/gid (1000) is
# arbitrary but fixed, matching the common convention; ownership of /app
# is granted explicitly since files were COPYed in as root during the
# build stages above.
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid appuser --no-create-home appuser \
    && chown -R appuser:appuser /app

# No `USER appuser` here (deliberately) -- docker-compose.yml's runtime
# volume mount (./data:/app/data) overlays this build-time chown
# entirely with whatever the HOST directory's ownership already is,
# which appuser then can't necessarily write to (found live: a
# root-owned predictions.db from before this hardening pass produced
# "attempt to write a readonly database" on every /predict call). The
# container therefore still starts as root, same as the plain image
# default -- but only to let docker-entrypoint.sh fix that mounted
# directory's ownership and immediately drop to appuser via gosu before
# the actual long-running server process ever starts. The real
# application process still ends up non-root either way; this only
# moves WHEN that switch happens, from build time to the first moment
# after the volume is actually mounted.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
