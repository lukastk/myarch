# myarch

myarch is a reproducible, keyboard-first Arch Linux desktop built on Hyprland. It is the standalone desktop layer for two profiles:

- `pocket4` — GPD Pocket 4, including transformed high-DPI display, touchscreen gestures, tablet scaling, on-screen keyboard, adaptive one/two-row bars, and thermal controls.
- `ideapad` — Lenovo IdeaPad Slim 5, including native trackpad gestures and the same workspace/desktop model. The profile is implemented but must be deployed separately after Pocket 4 validation.

myarch began as an extraction of the Hyprland target from [`myrig`](https://github.com/lukastk/myrig). Its visual system is inspired by Omarchy's restrained, flat desktop design, while preserving the deeper machine-specific behavior already proven on the Pocket 4.

## Design principles

- **Additive capability:** visual simplification does not delete hardware controls or established workflows.
- **One authority per behavior:** Pocket display, tablet, OSK, thermal, brightness, display-layout, dictation, and Sesh actions delegate to their existing backend commands.
- **Explicit profiles:** hardware differences are selected by `--profile pocket4|ideapad`; they are never guessed.
- **Loud failures:** required external integrations and unexpected state fail visibly.
- **Atomic configuration:** rendered files are replaced atomically while Hyprland autoreload is paused, followed by one coherent reload.
- **Source ownership:** myarch owns desktop packages/configuration; fleet composition and non-desktop services remain in myrig.

## Features

- Modular Hyprland Lua source rendered into one parser-safe `hyprland.lua`
- 15-workspace model, role workspaces, scratchpad, workspace chooser, and Hyprexpo overview
- Hyprexpo on both profiles; Hyprgrass touchscreen gestures on Pocket 4
- Omarchy-inspired minimalist Waybar with a collapsed tray and state-driven indicators
- Four Pocket bar states: 1600/1280/1000/800 logical pixels, with one/two-row and compact layouts
- Pocket display rotation coupled to touchscreen transform, explicit tablet scaling, OSK, gaps, and thermal controls
- `mydictation` hold/latch/cleanup workflow and touch controls
- Display layouts, sub-backlight gamma dimming, wallpaper rotation/pinning, idle inhibition, lock/idle policy, and graphical-session environment repair
- Unified `myarch menu`, keybinding catalogue, themes, audio/network/Bluetooth/display/power/Tailscale control surfaces
- Screenshot, OCR, QR, colour, and GPU screen-recording workflows
- Arthur, Tokyo Night, and Matte Black semantic themes across the bar, borders, terminals, notifications, and lock screen
- Idempotent package/config/system/plugin installer with profile tests and secret scanning

## Install

myarch supports Arch Linux and expects a live Hyprland session for the runtime plugin/reload phase.

```bash
git clone https://github.com/lukastk/myarch.git ~/mysetup/myarch
cd ~/mysetup/myarch
./install.sh --profile pocket4
# or, when explicitly deploying the second profile:
./install.sh --profile ideapad
```

The first installation defaults to the `arthur` theme. Select explicitly with `--theme arthur|tokyo-night|matte-black`. `--config-only` renders/reloads without package, service, plugin, or external-integration work. `--skip-runtime` is for a session-less provision; plugin compilation is then explicitly deferred and the installer must be rerun inside Hyprland.

### External profile contracts

Both profiles require:

- `~/Pictures/wallpapers` — provisioned independently, because a private binary wallpaper collection does not belong in this public repository.
- `~/mysetup/mydictation/install.sh` — the standalone dictation source/install integration.

The Pocket profile also expects Myrig's system-level Pocket provisioning to have installed `wvkbd-deskintl` and `pocket4-mode`/`gpd-fanctl`. myarch owns their desktop controls, not those hardware backends.

## Commands

```bash
myarch menu
myarch keys
myarch doctor

myarch theme list
myarch theme set tokyo-night
myarch theme pick

myarch panel audio|network|bluetooth|display|power|tailscale

myarch capture screenshot [region|fullscreen]
myarch capture text
myarch capture qr
myarch capture color
myarch capture record [--fullscreen] [--audio none|desktop|microphone|both]
myarch capture stop
```

Important keybindings include `Super+R` (myarch menu), `Super+Alt+Space` (applications), `Super+G` (overview), `Super+D` (dictation), `Super+V` (clipboard history), Print / `Super+Shift+S` (screenshots), and `Super+Ctrl+S` (capture menu). The complete catalogue is in [`docs/keybindings.tsv`](docs/keybindings.tsv) and available through `myarch keys`.

## Repository layout

```text
home/                 files installed under $HOME
src/hyprland/         ordered Lua/Jinja source fragments
profiles/             explicit machine contracts
themes/               semantic palettes
system/keyd/           root-owned Caps→F12 mapping
install.sh             package bootstrap
install.py             renderer, system integration, plugins, migrations
scripts/test           local validation entry point
tests/                 render/config/profile tests
docs/                  architecture and parity documentation
```

Static home files are symlinked to the clone. Templates are rendered atomically to their final destinations and carry a generated-file notice. Installed-file state and backups live under `~/.local/state/myarch/`.

## Development and validation

```bash
./scripts/test
./scripts/check-secrets.py
```

The test suite renders every template for both profiles and all themes, parses Waybar JSONC, checks the theme/profile contracts and binding catalogue, compiles Python, runs ShellCheck, and scans source files for credential material.

Pocket validation additionally covers all four orientation/scale states, Hyprland config errors, plugin state, display/touch coupling, OSK and gesture behavior, dictation, Sesh/SST, capture, idle/lock, fonts, and bar resource use. See [`docs/pocket4.md`](docs/pocket4.md) and [`docs/feature-parity.md`](docs/feature-parity.md).

## Attribution

myarch is MIT licensed. See [`NOTICE.md`](NOTICE.md) for Omarchy attribution and provenance notes.