# Docker-free run (Windows PowerShell). First set your Tiger Cloud connection string:
#   $env:PGDOCTOR_DSN = "postgres://tsdbadmin:PASSWORD@HOST:PORT/tsdb?sslmode=require"
$ErrorActionPreference = "Stop"
if (-not $env:PGDOCTOR_DSN) { throw "Set `$env:PGDOCTOR_DSN first" }
python scripts/run_sql.py sql/01_schema.sql
python scripts/run_sql.py sql/02_seed_data.sql --days 7 --devices 100
python scripts/benchmark.py --dir queries/before --label before
Get-ChildItem queries/before/*.sql | ForEach-Object {
  python -m pgdoctor diagnose --file $_.FullName --out-dir reports/before | Out-Null }
python scripts/run_sql.py sql/03_fixes.sql
python scripts/run_sql.py sql/04_anomaly.sql
python scripts/benchmark.py --dir queries/after --label after
Write-Host "Done. See results/benchmark.md and reports/before/"
