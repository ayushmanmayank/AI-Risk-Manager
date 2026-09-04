#!/bin/sh
# Runs as root (the image's default at container start, despite the
# Dockerfile also creating appuser -- see its own comment for why), for
# exactly one reason: docker-compose.yml bind-mounts the host's ./data
# directory over /app/data at RUNTIME, and whatever's already in it
# (a DB file created by an earlier root-run container before this
# hardening pass, or a fresh directory Docker itself creates owned by
# root if nothing exists yet) arrives with whatever ownership it already
# has -- the image's own build-time `chown` (Dockerfile) only touched
# what existed at BUILD time, which the volume mount overlays and
# replaces entirely at container start. Without this, appuser can`t
# write to a root-owned predictions.db and every /predict call fails
# with "attempt to write a readonly database" (found live, not a
# theoretical concern -- see the hardening pass's own verification notes).
#
# Fixes ownership on every container start (idempotent, cheap even when
# already correct) then drops to appuser via gosu and execs the real
# command -- so the actual application process still runs as non-root,
# same security property the Dockerfile's USER/appuser setup was for;
# only this one-time startup fix needs root, not the long-running server.
set -e
# Skip the chown when ownership is already correct -- the first run after
# this hardening pass needs it (an old root-owned DB from before), but
# every restart after that doesn't, and re-chowning the whole directory
# (features.csv alone is 162MB+) on every single container start was
# real, measured startup overhead (see docker-compose.yml's healthcheck
# start_period comment) worth skipping once it's no longer necessary.
if [ "$(stat -c '%U' /app/data 2>/dev/null)" != "appuser" ]; then
    chown -R appuser:appuser /app/data
fi
exec gosu appuser "$@"
