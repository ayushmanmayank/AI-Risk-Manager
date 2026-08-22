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
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Dependencies next so this layer is cached across rebuilds that only
# change application code.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY src/ ./src/
COPY simulator/ ./simulator/
COPY models/ ./models/

# Created empty here; docker-compose.yml's volume mount overlays the real
# data/ directory (processed features + the persistent predictions.db)
# over this at runtime. The API will fail to start if features.csv isn't
# actually present at runtime -- see README.md's "Dataset setup" section,
# which must be done before first run.
RUN mkdir -p data/processed data/raw

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
