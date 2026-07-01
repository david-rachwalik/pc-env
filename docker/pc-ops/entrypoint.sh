#!/bin/sh
set -e

# Create a shell configuration file if it doesn't exist
if [ ! -f /root/.shrc ]; then
    echo '# pc-ops aliases' > /root/.shrc

    # Snapshot commands (locked to state when the image was built)
    echo 'alias backup="python3 /app/docker/pc-ops/pc_backup.py"' >> /root/.shrc
    echo 'alias backup-dry="python3 /app/docker/pc-ops/pc_backup.py --dry-run --debug"' >> /root/.shrc
    echo 'alias restore="python3 /app/docker/pc-ops/pc_restore.py"' >> /root/.shrc
    echo 'alias restore-dry="python3 /app/docker/pc-ops/pc_restore.py --dry-run --debug"' >> /root/.shrc

    # Dev commands (live-mounted from host)
    echo 'alias backup-dev="PYTHONPATH=/app/dev/python/modules:/app/dev/python/modules/boilerplates python3 /app/dev/docker/pc-ops/pc_backup.py"' >> /root/.shrc
    echo 'alias restore-dev="PYTHONPATH=/app/dev/python/modules:/app/dev/python/modules/boilerplates python3 /app/dev/docker/pc-ops/pc_restore.py"' >> /root/.shrc
fi

# Ensure the custom aliases are sourced for interactive shells
if ! grep -q ". /root/.shrc" /root/.profile; then
    echo '\n[ -f /root/.shrc ] && . /root/.shrc' >> /root/.profile
fi

exec "$@"
