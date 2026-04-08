#!/bin/bash
set -euo pipefail

# =============================================================================
# Logging and Utility Functions
# =============================================================================
# A simple logging function with color and formatting
log() {
    local color_green='\033[0;32m'
    local color_cyan='\033[0;36m'
    local color_reset='\033[0m'
    # echo -e "${color_green}==> ${1}${color_reset}"
    echo -e "${color_cyan}${1}${color_reset}"
}

# =============================================================================
# USER LOGIC: This function contains all the steps that should be run
# as the non-root 'serveruser'.
# =============================================================================
run_as_user() {
    # --- Config ---
    GIT_REPO_URL="https://github.com/Crypto137/MHServerEmu.git"
    # Use 'master' for nightly, or a specific tag like 'v1.1.0'
    MH_VERSION="${MH_VERSION:-master}"
    SOLUTION_FILE="MHServerEmu.sln"
    
    # Define paths for clarity
    BIN_DIR="/app/src/MHServerEmu/bin/x64/Release/net8.0"
    EXECUTABLE_PATH="$BIN_DIR/MHServerEmu"
    GAME_DATA_DIR="$BIN_DIR/Data/Game"

    # Change to the app directory
    cd /app

    # --- Git Operations ---
    # Check if .git directory exists to verify repo
    if [ ! -d ".git" ]; then
        log "🚀 Repository not found.  Cloning version '${MH_VERSION}'..."
        # Clone into a temporary directory, then move contents to the current directory
        # (grouped commands to ensure they complete before proceeding)
        {
            git clone --depth 1 --branch "$MH_VERSION" "$GIT_REPO_URL" /tmp/git-clone && \
            mv /tmp/git-clone/.git . && \
            mv /tmp/git-clone/* . && \
            rm -rf /tmp/git-clone;
        } || { echo "❌ Git clone or move failed." >&2; exit 1; }
        # Force a build after cloning
        touch .force-build
    else
        log "🔄 Repository exists.  Checking for updates to '${MH_VERSION}'..."
        # Reset any potential partial changes from a previous failed run
        git reset --hard HEAD >/dev/null
        git fetch origin >/dev/null
        git checkout "$MH_VERSION" >/dev/null

        # Check if the local branch is behind the remote
        if ! git status -uno | grep -q "Your branch is up to date"; then
            log "New changes found.  Pulling updates..."
            git pull origin "$MH_VERSION" --ff-only # fast-forward pull
            # Force a rebuild since code has changed
            touch .force-build
        else
            log "No new changes found in the repository."
        fi
    fi

    # --- Build Operations ---
    # Build only if the executable doesn't exist or if a rebuild is forced
    if [ ! -f "$EXECUTABLE_PATH" ] || [ -f ".force-build" ]; then
        log "🛠️ Building solution..."
        dotnet restore "$SOLUTION_FILE"
        dotnet build "$SOLUTION_FILE" --no-restore --configuration Release
        rm -f .force-build # Clean up the marker file
    else
        log "Build is up-to-date.  Skipping."
    fi

    # --- Create Symlinks ---
    # This runs after the build, ensuring the target directory exists
    log "🔗 Verifying directories and symlinks..."
    mkdir -p "$GAME_DATA_DIR"
    # Create symlinks from the mounted files to where the app expects them
    # The -f flag ensures we overwrite any old symlinks from a previous run
    ln -sf /gamefiles/ConfigOverride.ini "$BIN_DIR/ConfigOverride.ini"
    ln -sf /gamefiles/mu_cdata.sip "$GAME_DATA_DIR/mu_cdata.sip"
    ln -sf /gamefiles/Calligraphy.sip "$GAME_DATA_DIR/Calligraphy.sip"

    # --- Run Server ---
    log "✅ Setup complete.  Starting server..."
    # Use exec to make the server the main process
    exec "$EXECUTABLE_PATH"
}

# =============================================================================
# ROOT EXECUTION: Main entrypoint of the container.
# =============================================================================

# Export functions so they are available to the subshell spawned by gosu
export -f run_as_user log

# --- Initial Permissioning (as root) ---
# Set ownership on all required directories every time
# (most robust approach in case, for example, named volumes were recreated)
log "🔐 Enforcing permissions..."
chown -R serveruser:serveruser /app /data
# Ignore harmless errors for read-only files inside /gamefiles
(chown -R serveruser:serveruser /gamefiles) 2>/dev/null || true

# --- Switch to Non-Root User ---
log "--- 🚀 Switching to user 'serveruser' for all operations ---"
exec gosu serveruser /bin/bash -c "run_as_user"
