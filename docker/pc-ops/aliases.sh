# pc-ops aliases

# --- Snapshot commands (locked to state when the image was built) ---
alias backup="python3 /app/pc_backup.py"
alias backup-dry="python3 /app/pc_backup.py --dry-run --debug"
alias restore="python3 /app/pc_restore.py"
alias restore-dry="python3 /app/pc_restore.py --dry-run --debug"

# --- Dev commands (live-mounted from host) ---
alias backup-dev="PYTHONPATH=/app/dev/python/modules:/app/dev/python/modules/boilerplates python3 /app/dev/docker/pc-ops/scripts/pc_backup.py"
alias restore-dev="PYTHONPATH=/app/dev/python/modules:/app/dev/python/modules/boilerplates python3 /app/dev/docker/pc-ops/scripts/pc_restore.py"
