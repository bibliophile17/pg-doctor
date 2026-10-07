#!/usr/bin/env bash
# End-to-end: start DB, seed, benchmark before, apply fixes, benchmark after, generate reports.
set -euo pipefail
export PGPASSWORD=pgdoctor
PSQL="psql -h localhost -U postgres -d iot -v ON_ERROR_STOP=1"
docker compose up -d
until $PSQL -c "select 1" >/dev/null 2>&1; do sleep 2; done
$PSQL -f sql/02_seed_data.sql
python scripts/benchmark.py --dir queries/before --label before
for f in queries/before/*.sql; do python -m pgdoctor diagnose --file "$f" --out-dir reports/before > /dev/null; done
$PSQL -f sql/03_fixes.sql
$PSQL -f sql/04_anomaly.sql
python scripts/benchmark.py --dir queries/after --label after
echo "Done. See results/benchmark.md and reports/before/*.md"
