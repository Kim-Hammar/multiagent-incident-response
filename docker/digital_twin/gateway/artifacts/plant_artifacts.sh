#!/bin/bash
# Runtime-only artifacts for gateway (sourced by entrypoint).
# Static files (auth.log, alert.log) are baked in by plant_static.sh.
set +e
# Nothing runtime-only needed for gateway; static artifacts cover everything.
