# PC Env Setup

## [Rclone](https://rclone.org): Sync Cloud Storage

Rclone is a command-line program to manage files on cloud storage.&nbsp; It supports over 70 cloud storage providers.&nbsp; Rclone has powerful cloud equivalents to the unix commands `rsync`, `cp`, `mv`, `mount`, `ls`, `ncdu`, `tree`, `rm`, and `cat`.&nbsp; Rclone's familiar syntax includes shell pipeline support, and `--dry-run` protection.&nbsp; Rclone is mature, open-source software originally inspired by rsync and written in Go.

Rclone really looks after your data.&nbsp; It preserves timestamps and verifies checksums at all times.&nbsp; Transfers over limited bandwidth; intermittent connections, or subject to quota can be restarted, from the last good file transferred.&nbsp; You can check the integrity of your files.

<sup><sub>**Cloud Providers:**&nbsp; [Google Drive](https://rclone.org/drive), [OneDrive](https://rclone.org/onedrive)</sub></sup>

###### Planned Uses

1. Mount Google Drive (`~/GoogleDrive`)
2. Sync Google Drive Obsidian Directory (`~/ObsidianVaults`)
3. Sync Microsoft OneDrive (`~/OneDrive`)
4. Serve Local Media Directories (`/mnt` `/media/root/HDD-01` `/media/root/HDD-02`)

### [Common Commands](https://rclone.org/commands/rclone)

_[version](https://rclone.org/commands/rclone_version/):_&nbsp; Show the version number

```sh
rclone version
```

_[listremotes](https://rclone.org/commands/rclone_listremotes):_&nbsp; List all remotes defined in the config file and environment variables

```sh
rclone listremotes
```

_[lsf](https://rclone.org/commands/rclone_lsf):_&nbsp; List directories and objects in `remote:path`, formatted for parsing

```sh
rclone lsf <remote>:<path/to/files>
```

#### [Mount](https://rclone.org/commands/rclone_mount) the Remote as a File System

Mount the remote as file system on a mountpoint ([VFS File Caching](https://rclone.org/commands/rclone_mount/#vfs-file-caching))

```sh
rclone mount "<remote>:<path/to/files>" "</path/to/local>" \
    --vfs-cache-mode writes \
    --vfs-cache-max-age 24h \
    --filters-file "$FILTERS_FILE" \
    --log-file "$LOG_FILE" \
    --log-level INFO
```

#### [BiSync](https://rclone.org/commands/rclone_bisync):&nbsp; Perform 2-way Synchronization ([Limitations](https://rclone.org/bisync/#limitations), [Filtering](https://rclone.org/bisync/#filtering))

Perform a safe test run

```sh
rclone bisync "<remote>:<path/to/files>" "</path/to/local>" \
    --dry-run \
    --check-access \
    --check-first \
    --filters-file "$FILTERS_FILE" \
    --log-level INFO
```

Perform an initial sync ([resync](https://rclone.org/bisync/#resync), clone remote)

```sh
rclone bisync "<remote>:<path/to/files>" "</path/to/local>" \
    --resync \
    --check-access \
    --check-first \
    --filters-file "$FILTERS_FILE" \
    --log-file "$LOG_FILE" \
    --log-level INFO
```

Perform a regular sync of latest changes ([track renames](https://rclone.org/docs/#track-renames))

```sh
rclone bisync "<remote>:<path/to/files>" "</path/to/local>" \
    --track-renames \
    --check-access \
    --check-first \
    --filters-file "$FILTERS_FILE" \
    --backup-dir "$BACKUP_DIR" \
    --log-file "$LOG_FILE" \
    --log-level INFO
```

#### [Serve](https://rclone.org/commands/rclone_serve) a Remote Over a Protocol

_[webdav](https://rclone.org/commands/rclone_serve_webdav):_&nbsp; Serve `remote:path` over WebDAV

```sh
rclone serve webdav remote:path --addr :8080 --vfs-cache-mode full --vfs-cache-max-age 1h --vfs-cache-poll-interval 10s
```

### Setup Commands

Check which config file rclone is using

```sh
rclone config files
```

Configure rclone manually/interactively

```sh
rclone config
```

Configure rclone with preset values (opens browser to authenticate)

```sh
rclone config create "<remote-name>" "<storage-type>"
```

---

### Other

- **[Rclone UI](https://rcloneui.com):**&nbsp; Stop remembering flags & commands and do more with Rclone
