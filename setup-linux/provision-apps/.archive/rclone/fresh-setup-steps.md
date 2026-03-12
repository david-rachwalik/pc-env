# ═══════════════════════════════════════════════════════════════

# 🚀 Fresh System OneDrive Sync Setup

# ═══════════════════════════════════════════════════════════════

# Step 1: Run the provisioning script

cd ~/Repos/pc-env
sudo bash setup-linux/provision-apps/rclone/enable-systemd.sh

# Expected output: "⚠️ MANUAL CONFIGURATION REQUIRED FOR: onedrive"

# ───────────────────────────────────────────────────────────────

# Step 2: Configure OneDrive remote (one-time manual step)

# ───────────────────────────────────────────────────────────────

rclone config create "onedrive" "onedrive"

# This will:

# 1. Open browser for Microsoft authentication

# 2. Save credentials to ~/.config/rclone/rclone.conf

# 3. Auto-refresh tokens (valid for 90 days between uses)

# Test it works:

rclone lsf onedrive: --max-depth 1

# ───────────────────────────────────────────────────────────────

# Step 3: Re-run provisioning to create systemd services

# ───────────────────────────────────────────────────────────────

sudo bash setup-linux/provision-apps/rclone/enable-systemd.sh

# This will now:

# ✅ Create systemd service: rclone-bisync-onedrive.service

# ✅ Create systemd timer: rclone-bisync-onedrive.timer (daily at 6am CST)

# ✅ Enable and start the timer

# ───────────────────────────────────────────────────────────────

# Step 4: Verify everything is set up

# ───────────────────────────────────────────────────────────────

# Check timer is active:

systemctl status rclone-bisync-onedrive.timer

# Expected output:

# ● rclone-bisync-onedrive.timer - Run Rclone OneDrive Bisync Daily at 6am CST

# Loaded: loaded (/etc/systemd/system/rclone-bisync-onedrive.timer; enabled; preset: enabled)

# Active: active (waiting) since ...

# Trigger: Wed 2026-02-04 12:00:00 UTC; ...

# See all scheduled rclone timers:

systemctl list-timers 'rclone-\*'

# ───────────────────────────────────────────────────────────────

# Step 5: Perform initial sync (recommended to do manually first)

# ───────────────────────────────────────────────────────────────

# Option A: Trigger via systemd (logs to journalctl)

sudo systemctl start rclone-bisync-onedrive.service

# Watch it run in real-time:

journalctl -u rclone-bisync-onedrive.service -f

# Option B: Run script directly (see output immediately)

~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync.sh onedrive OneDrive

# ───────────────────────────────────────────────────────────────

# Step 6: Verify sync worked

# ───────────────────────────────────────────────────────────────

# Check files synced:

ls -lah ~/OneDrive

# Check last sync status:

journalctl -u rclone-bisync-onedrive.service -n 50

# Look for:

# ✅ "Bisync completed successfully!"

# ❌ "Bisync failed" - follow recovery instructions in output

# ═══════════════════════════════════════════════════════════════

# 🎉 Done! OneDrive will now sync daily at 6am CST automatically

# ═══════════════════════════════════════════════════════════════

# Ongoing maintenance commands:

# View next scheduled run:

systemctl list-timers rclone-bisync-onedrive.timer

# Manually trigger sync anytime:

sudo systemctl start rclone-bisync-onedrive.service

# Check if sync is currently running:

systemctl is-active rclone-bisync-onedrive.service

# View sync history:

journalctl -u rclone-bisync-onedrive.service --since "1 week ago"

# Disable daily sync (keep service available for manual runs):

sudo systemctl disable rclone-bisync-onedrive.timer

# Re-enable daily sync:

sudo systemctl enable --now rclone-bisync-onedrive.timer
