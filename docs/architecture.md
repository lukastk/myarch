# Architecture

## Installation transaction

`install.sh` validates Arch/profile, installs a declarative pacman package set, and invokes `install.py`. The Python installer:

1. validates profile and semantic-theme contracts;
2. resolves a live Hyprland instance when present;
3. records and temporarily enables `misc.disable_autoreload` and `debug.suppress_errors`;
4. migrates known desktop state from the former myrig namespace when needed;
5. renders templates atomically and symlinks static files;
6. writes an installed-file manifest and removes only stale files it can prove myarch owns;
7. configures keyd, Bluetooth, NTP, and font caches;
8. validates/install external profile contracts;
9. updates, adds, and enables ABI-locked Hyprpm plugins;
10. restores Hyprland's prior reload/error settings, performs one reload, and restarts Waybar/Mako.

There is no compatibility namespace for Omarchy. myarch commands and state are native.

## Configuration ownership

The Hyprland source is split by concern under `src/hyprland/`, but concatenated before Jinja rendering. Concatenation intentionally preserves the original single Lua lexical scope: local terminal helpers and callbacks can be shared without globals, `require` tricks, or generated compatibility wrappers.

Static files under `home/` become symlinks into the repository. `.jinja` files are rendered directly to their destination through a same-directory temporary file and `os.replace`, so file watchers see either the complete old version or complete new version. Backups and the ownership manifest live under `~/.local/state/myarch/`.

## Profiles

Profiles are explicit TOML contracts. `pocket4` selects Foot, battery `BATT`, touchscreen/Hyprgrass, narrow bar files, Pocket scripts, and the Pocket dictation capture level. `ideapad` selects Kitty, battery `BAT1`, native gestures, and excludes all Pocket-only files.

A profile is never inferred from hostname or hardware. This keeps a wrong install loud and reviewable.

## Themes

Each theme provides semantic shell roles and a 16-colour terminal palette. Jinja applies them to:

- Waybar surface/state colours;
- active/inactive Hyprland borders and shadows;
- Foot and Kitty;
- Mako;
- hyprlock.

Wallpaper state is independent. `myarch theme set` rerenders configuration and does not alter the current/pinned wallpaper.

## Control surfaces

Waybar presents quiet status and critical Pocket controls. Richer operations go through `myarch menu` and Wofi/application/TUI surfaces. `myarch` dispatches commands as argv through Python subprocess APIs; it does not build shell strings from selections.

Sesh, Voxtype, NetworkManager, BlueZ, PipeWire, Tailscale, display-mode, Pocket scripts, and gpd-fanctl remain state authorities. myarch presents their verbs; its small Voxtype adapter translates compositor edges into public recording/profile commands and owns only the established hold/tap gesture plus Pocket microphone-volume transaction.

## Myrig integration

Myrig clones the repository in its common Mysetup phase. The `myarch` target depends on `wallpapers`, `rustdesk`, and the shared `fonts` target; a thin pyinfra module invokes `install.sh --profile pocket4|ideapad`. Three shell shims source myarch's zsh helpers into the existing myrig startup tree. No desktop implementation remains in myrig.