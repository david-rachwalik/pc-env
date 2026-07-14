# EmulationStation DE ([ES-DE](https://es-de.org)) Environment Guide

This document outlines the architecture, installation, and daily workflows for maintaining a highly optimized, natively integrated retro gaming environment on Linux.

## 1. Emulators & Provisioning

To avoid the restrictive `/mnt` and `/media` drive sandboxing inherent to Flatpaks (like those used by EmuDeck), this environment relies on native system packages and standalone user-space **AppImages**. This grants emulators unrestricted access to your external drives.

### Automated Installation

Run the automated bash provisioner to fetch and integrate the latest AppImages into the system `$PATH` and application menu:

```bash
sudo bash ~/Repos/pc-env/setup-linux/provision-apps/appimage.sh
```

**Provisioned Emulators:**

- **[EmulationStation DE](https://gitlab.com/es-de/emulationstation-de/-/blob/master/USERGUIDE.md)** (Frontend)
- **[RetroArch](https://www.retroarch.com):** (Pre-PS1/Misc)
- **DuckStation** (PS1, 1995)
- **PCSX2** (PS2, 2000)
- **Xemu** (Xbox, 2001)
- **RPCS3** (PS3, 2006)

Because RetroArch no longer publishes official AppImages, it is installed globally via APT to ensure unrestricted filesystem access:

```bash
sudo apt-get install -y retroarch
```

### RetroArch Core Setup

#### Automated Configuration & Core Synchronization

To avoid manually configuring system directories or clicking through the RetroArch GUI to download cores, run the dedicated emulation setup script:

```bash
bash ~/Repos/pc-env/setup-linux/provision-apps/games/setup.sh
```

**What this script automates:**

1. **Scaffolding:** Builds all `bios/`, `system/`, and `flash/` directories ahead of time (for RetroArch, PCSX2, DuckStation, and Xemu).
2. **Core Retrieval:** Silently fetches and extracts `.so` libretro cores directly from the buildbot (`Mesen`, `Snes9x`, `Flycast`, `MAME`, etc.).
3. **ROM Integration:** Triggers the Docker `link-esde-roms` pipeline to dynamically map your source ROM drive to your local ES-DE path based on standard bracket notation.

#### Manual Steps (What the Automated process handles)

Since RetroArch is a fresh binary, you need to manually download the emulation "cores" (the actual console emulators running inside it).

1. Open the **RetroArch** app from your desktop menu.
2. Go to **Main Menu** -> **Online Updater** -> **Core Downloader**.
3. Install the recommended cores for your systems (e.g., _Nintendo - SNES / SFC (Snes9x)_, _Sony - PlayStation (PCSX ReARMed)_).

Once the cores and BIOS files are in place, ES-DE will transparently detect RetroArch through your system `$PATH` and launch your titles immediately.

### BIOS / Firmware Placement

Before games will boot, BIOS/Driver files must be placed in their respective emulator directories. Check the [libretro BIOS Hub](https://docs.libretro.com/library/bios) or emulator-specific wikis for exact naming conventions.

_(Tip: Launch each emulator from the desktop menu at least once to auto-generate these folders so they don't have to be created manually)._

- **RetroArch:** `~/.config/retroarch/system/`
- **DuckStation:** `~/.local/share/duckstation/bios/`
- **PCSX2:** `~/.config/PCSX2/bios/`
- **Xemu:** `~/.local/share/xemu/xemu/flash/`

---

## 2. ROM Conversion & Compression

The [`rom-convert`](docker-compose.yml) container automatically compresses raw ROM dumps into modern, space-saving formats (7z, CHD, RVZ, rebuilt ISO) while keeping the host machine completely free of dependencies.

### Compression Usage

Run the custom alias against any standardized folder on the source drive:

```bash
roms "/mnt/Z/roms/(1995) PlayStation [psx]"
```

### Conversion Pipeline

1. **Detection:** Sniffs the console type using bracket notation (e.g., `[psx]`).
2. **Lazy-Loading:** Evaluates the required tool directly inside the Docker container (`chdman`, `extract-xiso`, `DolphinTool`, or `7zip`). Tools are only loaded if the system actually requires them.
3. **Processing:** Compresses files into the hidden `_converted_roms` folder.
4. **Validation:** Verifies the cryptographic integrity of the output.
5. **Idempotency:** Drops a `converted_log` tracker file. Successive runs will safely skip existing files.

---

## 3. ES-DE Symlink Mapping

To prevent data duplication across drives while catering to ES-DE's strict folder naming requirements (e.g., `psx`, `xbox360`), directories are mapped using zero-byte symlinks.

### Symlink Execution

```bash
link-roms --dry-run
link-roms
```

### Mapping Architecture

1. Scans the storage drive (`/mnt/Z/roms`) for folders ending with system brackets (e.g. `[snes]`).
2. Maps an absolute symlink to the target ES-DE directory (`/home/rhodair/ROMs`).
3. Automatically detects existing physical folders and renames them to `-bak` to prevent destructive overwriting.
4. To point ES-DE to this linked hierarchy, update the path in ES-DE's Main Menu > **Utilities** > **ROM Directory**.

---

## 4. Scraping (The "Steam" Aesthetic)

When using built-in scrapers (like [ScreenScraper](https://www.screenscraper.fr) or TheGamesDB), certain artifacts should be omitted to save space, reduce API quota exhaustion, and achieve a clean, modern "Steam Library" look.

- **🟢 KEEP:** Miximages, Box Art (2D over 3D), Marquees (Clear Logos), Fan Art (Backgrounds), Screenshots, Game Manuals, Text Metadata.
- **🔴 SKIP:** Videos (Massive space/performance drain), Box Back Covers, Physical Media (Discs/Cartridges).

---

## 5. Backup & Restore Operations

System configurations, emulator BIOS files, and memory card save states are actively tracked by the `pc-ops` Docker container to ensure data persistence across formats or hardware failures.

_(Configuration mappings are maintained in `docker/pc-ops/scripts/data_apps.py`)._

### State Management

Backup current emulator states to remote cloud storage:

```bash
backup-dev --dry-run
backup-dev
```

Restore emulator states to a fresh system:

```bash
restore-dev --only-apps
```
